"""Fault injection driven entirely by the SUT's disruption mapping.

In the concretization story this is the fault switch: algorithm.py calls
DisruptionExecutor when the AUT says a disruption should be activated.

---------------------------------------------------------------------------
WHY THIS WAS REWRITTEN
---------------------------------------------------------------------------
The previous implementation could only POST to entry['endpoint'].  Three
consequences, all observed:

  * Any fault declaring a non-HTTP mechanism had no 'endpoint' key, so
    `entry['endpoint']` raised an UNCAUGHT KeyError -- the try: block began on
    the following line.  Four of Moodle's eight disruptions crashed the walk.

  * restore() swallowed every exception with `pass`, never checked the
    response status, then unconditionally cleared active_disruption and
    returned True.  A restore that 404'd or threw reported success, so a fault
    could stay latched and silently poison every later test case.  This is the
    same defect the FoodYou campaign found in fault_injector.py's adb path,
    where it was fixed -- but the fix was never ported here, and this is the
    path the web SUTs use.

  * Nothing ever verified that a fault actually took effect.  A self-test that
    runs the injection commands itself proves the COMMANDS work; it does not
    prove the INJECTOR works.  Only an inject -> verify -> restore -> verify
    cycle driven through this class does that.

---------------------------------------------------------------------------
THE FRAMEWORK STAYS SUT-AGNOSTIC
---------------------------------------------------------------------------
No system name, table name, selector, endpoint or gate name appears in this
file.  A mechanism is a NAME plus a command template, both supplied by the
SUT's disruption_mapping.yml.  Adding a fault kind for a new SUT means editing
that YAML, never this module.

Mapping schema (legacy 'disruptions:' with 'endpoint:' is still accepted):

    mechanisms:                 # how to run each mechanism's payload
      postgres:
        command: ["docker", "compose", "exec", "-T", "db",
                  "psql", "-U", "moodle", "-d", "moodle", "-tAc"]
        cwd: systems/<sut>/sut/<compose-dir>
        env: {KEY: value}
      shell:
        command: ["bash", "-lc"]

    faults:
      SOME_FAULT:
        mechanism: postgres
        network: false          # true => algorithm.py may use its connectivity path
        inject:  "<payload passed to the mechanism command>"
        restore: "<payload>"
        verify_injected: {payload: "<query>", equals: "1"}
        verify_restored: {payload: "<query>", equals: "0"}

FAIL CLOSED.  If a restore cannot be confirmed, the executor marks itself
poisoned.  Bookkeeping that has lost track must abstain, not hand back a
confident wrong verdict; algorithm.py reads is_poisoned() and abstains.
"""

import os
import logging
import subprocess

import yaml
import requests

logger = logging.getLogger(__name__)


class DisruptionExecutor:
    # Mechanisms handled by an HTTP POST rather than a subprocess.
    HTTP_MECHANISMS = {"http", "endpoint", "rest"}

    def __init__(self, mapping_path: str, base_url: str,
                 project_root: str = ".", dry_run: bool = False):
        with open(mapping_path) as f:
            mapping = yaml.safe_load(f) or {}

        # 'faults' is the current key; 'disruptions' is the legacy one.
        self.faults = mapping.get("faults") or mapping.get("disruptions") or {}
        self.mechanisms = mapping.get("mechanisms", {}) or {}
        self.base_url = (base_url or "").rstrip("/")
        self.project_root = project_root
        self.dry_run = dry_run

        self.active_disruption = None
        # Faults already injected by pre_inject(), so activate_disruption() can
        # recognise them as live instead of re-running the injection.
        self._pre_injected = set()
        # Set when a restore could not be confirmed. Once true the run's
        # remaining verdicts are untrustworthy and must be abstained from.
        self._poisoned = False
        self._poison_reason = None

    # ------------------------------------------------------------------
    # Introspection used by algorithm.py
    # ------------------------------------------------------------------
    def is_fault_gate(self, gate: str) -> bool:
        """True if `gate` names a fault this mapping knows how to inject."""
        return gate in self.faults

    def network_fault_gates(self) -> set:
        """Gates the SUT marks as connectivity faults.

        algorithm.py previously hard-coded a set of FoodYou gate names, so a
        SUT whose connectivity fault had any other name silently got no
        injection at all.  The names now come from the mapping.
        """
        return {k for k, v in self.faults.items()
                if isinstance(v, dict) and v.get("network")}

    def is_poisoned(self) -> bool:
        return self._poisoned

    def poison_reason(self):
        return self._poison_reason

    def _poison(self, reason: str) -> None:
        self._poisoned = True
        self._poison_reason = reason
        logger.error(f"FAULT STATE POISONED: {reason}")
        logger.error("  Verdicts after this point are not trustworthy; abstain.")

    # ------------------------------------------------------------------
    # Mechanism execution
    # ------------------------------------------------------------------
    def _run_mechanism(self, mech: str, payload: str):
        """Run `payload` through mechanism `mech`.

        Returns (ok, output). Never raises: a mechanism that is missing or
        fails is reported, not thrown, so the caller decides the verdict.
        """
        spec = self.mechanisms.get(mech)
        if spec is None:
            return False, f"mechanism {mech!r} is not declared under `mechanisms:`"

        argv = list(spec.get("command") or [])
        if not argv:
            return False, f"mechanism {mech!r} declares no `command:`"
        argv.append(payload)

        root = os.path.abspath(self.project_root)

        cwd = spec.get("cwd") or root
        if not os.path.isabs(cwd):
            cwd = os.path.join(root, cwd)

        # {{PROJECT_ROOT}} in env values becomes the repo root.
        #
        # A mechanism's cwd is usually NOT the repo root (moodle-docker's
        # wrapper must run from its own directory), so a repo-relative env path
        # resolves against the wrong place. moodle-docker-compose then rejects
        # MOODLE_DOCKER_WWWROOT as "not an existing directory" and exits 1, and
        # every fault fails to inject. Absolute paths in the YAML would fix it
        # but hard-code one machine; this placeholder keeps the mapping
        # portable. Substitution is exact-token, so Go templates such as
        # {{.State.Paused}} in a docker inspect probe pass through untouched.
        env = dict(os.environ)
        for k, v in (spec.get("env") or {}).items():
            env[str(k)] = str(v).replace("{{PROJECT_ROOT}}", root)

        if self.dry_run:
            logger.info(f"  [dry-run] {mech}: {' '.join(argv[:-1])} {payload[:80]!r}")
            return True, ""

        try:
            r = subprocess.run(argv, cwd=cwd, env=env, capture_output=True,
                               text=True, timeout=spec.get("timeout", 60))
        except Exception as e:
            return False, f"{mech} execution error: {e}"

        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        if r.returncode != 0:
            # BOTH streams. Wrapper scripts frequently report fatal errors on
            # STDOUT -- moodle-docker-compose prints
            # "Error: $MOODLE_DOCKER_WWWROOT is not set or not an existing
            # directory" there -- so reporting stderr alone produced the
            # useless message "postgres exit 1:" with nothing after the colon,
            # for all eight faults at once.
            detail = err or out or "(no output on either stream)"
            return False, f"{mech} exit {r.returncode}: {detail[:400]}"
        return True, out

    def _run_http(self, entry: dict, which: str):
        """POST for the HTTP mechanism. `which` is 'inject' or 'restore'."""
        key = "endpoint" if which == "inject" else "restore_endpoint"
        params_key = "params" if which == "inject" else "restore_params"
        endpoint = entry.get(key)
        if not endpoint:
            return False, f"no {key!r} declared"
        url = self.base_url + endpoint
        if self.dry_run:
            logger.info(f"  [dry-run] POST {url}")
            return True, ""
        try:
            resp = requests.post(url, json=entry.get(params_key, {}), timeout=10)
        except requests.exceptions.RequestException as e:
            return False, f"POST {url} failed: {e}"
        if resp.status_code != 200:
            return False, f"POST {url} -> HTTP {resp.status_code}"
        return True, resp.text[:200]

    def _dispatch(self, entry: dict, which: str):
        """Run the inject or restore side of `entry`, honouring its mechanism.

        The old restore read the mechanism variable and then ignored it,
        sending SQL to a shell.  Both sides now go through here, so they cannot
        drift apart.
        """
        mech = (entry.get("mechanism") or "http").lower()
        if mech in self.HTTP_MECHANISMS:
            return self._run_http(entry, which)
        payload = entry.get(which)
        if payload is None:
            return False, f"no {which!r} payload declared for mechanism {mech!r}"
        return self._run_mechanism(mech, str(payload))

    def _verify(self, entry: dict, which: str) -> bool:
        """Check a verify_injected / verify_restored probe, if one is declared.

        A fault with no probe is trusted but SAID to be untrusted, so the gap
        is visible in the log rather than silently assumed away.
        """
        probe = entry.get(which)
        if not probe:
            logger.warning(f"  {which}: no probe declared — fault state assumed, not verified")
            return True
        # A probe may name its own mechanism: an HTTP-injected fault has no
        # command to run through, so its probe asks the status endpoint via
        # a shell (curl) instead of being unverifiable.
        mech = (entry.get("mechanism") or "http").lower()
        if isinstance(probe, dict) and probe.get("mechanism"):
            mech = str(probe["mechanism"]).lower()
        payload = probe.get("payload") if isinstance(probe, dict) else str(probe)
        ok, out = self._run_mechanism(mech, str(payload))
        if not ok:
            logger.error(f"  {which}: probe failed to run: {out}")
            return False
        if self.dry_run:
            return True
        expected = str(probe.get("equals")) if isinstance(probe, dict) and "equals" in probe else None
        if expected is None:
            return True
        actual = (out or "").strip()
        if actual != expected:
            logger.error(f"  {which}: probe returned {actual!r}, expected {expected!r}")
            return False
        return True

    # ------------------------------------------------------------------
    # Public API (unchanged signatures — algorithm.py needs no edit)
    # ------------------------------------------------------------------
    def timing(self, key: str) -> str:
        """When a fault must be injected: 'gate' (default), 'pre' or 'none'.

        'gate' fires the fault when its gate is reached in the test case.
        'pre'  fires it before the walk starts.
        'none' injects nothing: the System Interface's own steps realise it.
        """
        entry = self.faults.get(key)
        if not isinstance(entry, dict):
            return "gate"
        return str(entry.get("timing", "gate")).strip().lower()

    def pre_inject(self, labels) -> bool:
        """Inject every `timing: pre` fault whose gate occurs in `labels`.

        WHY THIS EXISTS
        ---------------
        In an actions-first System Interface the concrete steps for a gate are
        emitted BEFORE the gate itself, and a fault gate sits AFTER the stimulus
        it disrupts. So for any fault whose mechanism blocks a WRITE, the write
        has already been committed by the time the gate is reached and the
        injection is a no-op.

        Measured on the Moodle test cases: the transition immediately preceding
        APP_PARTIAL_SUBMISSION is CLICK !SEL_SAVE_CHANGES_BTN, and the one
        preceding both APP1_WRITE_FAIL and DB_ATTEMPT_STEP_LOSS is
        CLICK !SEL_SUBMIT_CONFIRM_BTN. Each fault was therefore installed after
        the write it exists to block. The run still reported a verdict, and that
        verdict described a SUT that had not been disrupted.

        Faults that disrupt a subsequent READ or navigation (a stale-data flag,
        a paused container, a deleted session) are correct at gate time and must
        NOT be marked `pre` — injecting them early would disrupt the setup steps
        as well. The distinction is per-fault and belongs in the mapping, which
        is why this reads `timing:` rather than guessing from the mechanism.

        Returns False if any pre-injection failed, so the caller can refuse to
        attribute the run.
        """
        gates = {str(l).split()[0].upper().rstrip(";") for l in labels}
        ok_all = True
        for key in self.faults:
            if self.timing(key) != "pre" or key.upper() not in gates:
                continue
            if self.activate_disruption(key):
                self._pre_injected.add(key)
                logger.info(f"  {key} pre-injected before the walk (timing: pre)")
            else:
                logger.error(f"  {key}: PRE-injection failed — this run's verdict"
                             f" is not attributable")
                ok_all = False
        return ok_all

    def activate_disruption(self, disruption_key: str) -> bool:
        if self._poisoned:
            logger.error(f"refusing to inject {disruption_key}: {self._poison_reason}")
            return False

        # Already installed before the walk. Re-running the inject payload here
        # would be harmless for an idempotent CREATE OR REPLACE but not for a
        # mechanism that toggles state, so treat it as satisfied.
        if disruption_key in self._pre_injected:
            logger.info(f"  {disruption_key} already active (pre-injected)")
            return True

        entry = self.faults.get(disruption_key)
        if entry is None:
            # Tolerate a decorated label such as "GATE !ARG (X)".
            bare = disruption_key.split()[0].strip().rstrip(";")
            entry = self.faults.get(bare)
            if entry is None:
                logger.error(f"Unknown disruption key: {disruption_key!r}")
                return False
            disruption_key = bare

        # `timing: none` -- the System Interface realises the fault with its
        # own concrete steps (leaving the page mid-submit, priming a cache).
        # There is nothing to inject and nothing to restore; the gate is a
        # marker in the walk, not a command. Reaching it is the injection.
        if self.timing(disruption_key) == "none":
            logger.info(f"  {disruption_key}: realised by the System Interface's "
                        f"own steps (timing: none); nothing injected")
            return True

        ok, out = self._dispatch(entry, "inject")
        if not ok:
            logger.error(f"Disruption activation failed: {disruption_key}: {out}")
            return False

        if not self._verify(entry, "verify_injected"):
            # The command reported success but the fault is not in place.
            # Attempt to clean up, then refuse — a test run against a fault
            # that never bit would report a manufactured result.
            logger.error(f"{disruption_key}: injected but NOT confirmed active")
            self._dispatch(entry, "restore")
            return False

        self.active_disruption = disruption_key
        logger.info(f"Disruption activated and confirmed: {disruption_key}")
        return True

    def restore(self, keys=None) -> bool:
        """Clear every fault this run installed and CONFIRM each is gone.

        Covers the gate-timed fault AND anything pre_inject() put in place: a
        pre-injected trigger is never named in active_disruption, so restoring
        that alone left it latched for the NEXT test case, whose verdict would
        then describe a fault it never asked for.

        `keys`: further fault names the walker activated (it keeps its own
        set; active_disruption holds only the last one).

        Returns False and poisons the executor if any cannot be confirmed.
        """
        todo = list(self._pre_injected)
        if self.active_disruption is not None and self.active_disruption not in todo:
            todo.append(self.active_disruption)
        for k in (keys or ()):
            if k not in todo:
                todo.append(k)
        todo = [k for k in todo if self.timing(k) != "none"]   # SI-realised: nothing installed
        if not todo:
            return True

        all_ok = True
        for key in todo:
            entry = self.faults.get(key) or {}

            ok, out = self._dispatch(entry, "restore")
            if not ok:
                self._poison(f"restore of {key} failed: {out}")
                all_ok = False
                continue

            if not self._verify(entry, "verify_restored"):
                self._poison(f"restore of {key} ran but the fault is still present")
                all_ok = False
                continue

            logger.info(f"Disruption restored and confirmed cleared: {key}")

        if all_ok:
            self.active_disruption = None
            self._pre_injected.clear()
        return all_ok

    def restore_all(self) -> bool:
        """Best-effort clean slate: run every declared restore.

        Used before a sweep so a fault latched by an earlier crashed run cannot
        contaminate the first test case of the next one.
        """
        all_ok = True
        for key, entry in self.faults.items():
            if self.timing(key) == "none":
                continue                    # SI-realised: nothing was installed
            ok, out = self._dispatch(entry, "restore")
            if not ok:
                logger.warning(f"  pre-sweep restore of {key}: {out}")
                all_ok = False
        self.active_disruption = None
        return all_ok
