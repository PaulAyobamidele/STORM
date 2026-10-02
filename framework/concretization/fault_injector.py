"""
fault_injector.py
-----------------
Out-of-band Android fault injection for the FoodYou concretization, driven by
systems/foodyou/properties/disruption_mapping.yml.

The model injects each disruption via the environment (adb / sqlite), not through
the UI. The graph walker calls this at two moments:

  * BEFORE the walk  -> `pre_inject(labels)` fires every `timing: pre` fault whose
                        gate appears in the AUT (the corruption/read-only state must
                        pre-exist the read/write it disrupts).
  * AT a fault gate  -> `inject_gate(gate)` fires a `timing: gate` fault the moment
                        its label is reached (mid-write kill, connectivity cut, an
                        unreadable DB right before a read).

`restore()` (called in the run's finally) undoes everything, re-seeding when the
corruption can't be cleanly reversed.

VERIFICATION (generic, read from the mapping). A fault may declare

    verify_injected: {payload: "<sqlite query | adb shell command>", equals: "<text>"}
    verify_restored: {payload: "...", equals: "..."}

The payload runs through the fault's own mechanism (sqlite -> `_scalar`,
anything else -> the device shell) right after the inject / restore command,
and its first output line is compared with `equals`. A mismatch is logged as
an ERROR, the gate is recorded in `unconfirmed` (inject) or `restore_failures`
(restore), and `manifested()` answers from the same probe, so the walker's
"did the fault bite?" question is read from the SUT rather than assumed. A
fault with no probe behaves exactly as before: assumed, and said to be.
Nothing here names a SUT; the probes are the mapping's.

Standalone dry run (prints the adb commands without executing):
    python3 framework/concretization/fault_injector.py
Self-test of the verification bookkeeping (no device):
    .venv/bin/python -m pytest framework/tests/test_fault_injector_probes.py -q
"""

from __future__ import annotations
import logging
import os
import subprocess

logger = logging.getLogger(__name__)


class AndroidFaultInjector:
    def __init__(self, mapping: dict, device: str | None, package: str | None,
                 project_root: str = ".", adb: str = "adb", dry_run: bool = False):
        aconf            = (mapping or {}).get("android", {}) or {}
        self.faults      = (mapping or {}).get("faults", {}) or {}
        self.device      = device or aconf.get("device")
        self.package     = package or aconf.get("package")
        self.db          = aconf.get("db", "databases/open_source_database.db")
        self.seed_script = os.path.join(project_root, aconf.get(
            "seed_script", "systems/foodyou/seed_foods.sh"))
        self.adb         = adb
        self.dry_run     = dry_run
        self.project_root = project_root
        self.target      = None           # THIS tc's target fault; injections are limited to it
        self._active: list[str] = []      # gates injected, newest last (LIFO restore)
        # Verification bookkeeping (see the module docstring). Gates whose
        # verify_injected probe disagreed after the inject command; gates whose
        # verify_restored probe disagreed (or whose restore command failed);
        # and the last probe answer per gate, for the log and the tests.
        self.unconfirmed: set[str] = set()
        self.restore_failures: list[str] = []
        self.last_verification: dict[str, object] = {}

    # ------------------------------------------------------------------ utils
    def _subst(self, s: str) -> str:
        return (s or "").replace("{pkg}", self.package or "").replace("{db}", self.db)

    def _adb_shell(self, cmd: str, timeout: int = 30) -> bool:
        """Run one on-device shell command string via `adb -s <dev> shell <cmd>`.
        `timeout` comes from the fault's own `timeout:` key when it declares
        one (a partition fill takes longer than a trigger)."""
        if not cmd:
            return True
        argv = [self.adb] + (["-s", self.device] if self.device else []) + ["shell", cmd]
        if self.dry_run:
            print("  $", " ".join(argv))
            return True
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
            if r.returncode != 0:
                logger.warning(f"adb shell failed ({r.returncode}): {cmd}\n{r.stderr.strip()}")
            return r.returncode == 0
        except Exception as e:
            logger.warning(f"adb shell error: {cmd}: {e}")
            return False

    def _adb_shell_out(self, cmd: str):
        """The probe form of _adb_shell: the command's stdout (stripped, first
        line; "" when it printed nothing) or None when it could not run or
        exited non-zero. A probe needs the VALUE, not just success."""
        if not cmd:
            return None
        argv = [self.adb] + (["-s", self.device] if self.device else []) + ["shell", cmd]
        if self.dry_run:
            print("  $", " ".join(argv))
            return None
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=30)
            if r.returncode != 0:
                return None
            out = (r.stdout or "").strip()
            return out.splitlines()[0].strip() if out else ""
        except Exception as e:
            logger.warning(f"adb shell probe error: {cmd}: {e}")
            return None

    def _host(self, cmd: str, timeout: int = 60) -> bool:
        """Mechanism `host`: run one command in a shell on the TESTER's machine
        (a container, a database, a service the SUT depends on but the device
        does not host). The command is the mapping's; nothing here names a SUT."""
        if not cmd:
            return True
        if self.dry_run:
            print("  $ bash -lc", repr(cmd))
            return True
        try:
            r = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True,
                               timeout=timeout, cwd=self.project_root)
            if r.returncode != 0:
                logger.warning(f"host command failed ({r.returncode}): {cmd}\n"
                               f"{(r.stderr or r.stdout).strip()[:400]}")
            return r.returncode == 0
        except Exception as e:
            logger.warning(f"host command error: {cmd}: {e}")
            return False

    def _host_out(self, cmd: str):
        """Probe form of _host: first stdout line ("" when empty), or None when
        the command could not run or exited non-zero."""
        if not cmd or self.dry_run:
            return None
        try:
            r = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True,
                               timeout=60, cwd=self.project_root)
            if r.returncode != 0:
                return None
            out = (r.stdout or "").strip()
            return out.splitlines()[0].strip() if out else ""
        except Exception as e:
            logger.warning(f"host probe error: {cmd}: {e}")
            return None

    def _probe(self, spec: dict, which: str):
        """Run the fault's `verify_injected` / `verify_restored` probe.

        Returns True (probe agreed), False (probe ran and disagreed) or None
        (no probe declared, dry run, or the probe could not run). None never
        counts against the fault: a tester failing to read the SUT is not
        the SUT failing.
        """
        probe = (spec or {}).get(which)
        if not probe:
            logger.warning(f"  {which}: no probe declared -- fault state assumed, not verified")
            return None
        if self.dry_run:
            return None
        if isinstance(probe, dict):
            payload, expected = probe.get("payload"), probe.get("equals")
        else:
            payload, expected = str(probe), None
        payload = self._subst(str(payload or ""))
        mech = ((probe.get("mechanism") if isinstance(probe, dict) else None)
                or spec.get("mechanism") or "adb").lower()
        if mech == "sqlite":
            actual = self._scalar(payload)
        elif mech == "host":
            actual = self._host_out(payload)
        else:
            actual = self._adb_shell_out(payload)
        if actual is None:
            logger.error(f"  {which}: probe could not run: {payload[:120]}")
            return None
        if expected is None:
            return True
        if str(actual).strip() != str(expected).strip():
            logger.error(f"  {which}: probe returned {actual!r}, expected {expected!r}")
            return False
        return True

    def _sql(self, sql: str) -> bool:
        # single on-device command: run-as PKG sqlite3 DB "<sql>"  (double-quote the
        # SQL so its own single quotes, e.g. 'Test%', survive the device shell).
        # busy_timeout waits out the app's write lock instead of failing (locked).
        return self._adb_shell(
            f'run-as {self.package} sqlite3 {self.db} "PRAGMA busy_timeout=5000; {sql}"')

    def _scalar(self, sql: str):
        """Read-only query -> first column of the first row as a str, or None
        (SQLite NULL, empty result, or error). Used by manifested() to confirm,
        from the SUT's OWN state, whether a fault actually took effect."""
        if self.dry_run:
            return None
        # NO PRAGMA prefix here: `PRAGMA busy_timeout=5000` echoes "5000" as its own
        # result row, which would masquerade as the query's value. Reads on the WAL
        # DB don't block, so the bare SELECT is what we want.
        argv = [self.adb] + (["-s", self.device] if self.device else []) + \
            ["shell", f'run-as {self.package} sqlite3 {self.db} "{sql}"']
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=30)
            if r.returncode != 0:
                return None
            out = (r.stdout or "").strip()
            # "" distinguishes "query ran, no/NULL result" from None ("query errored"),
            # so callers can tell an empty diary from an unreadable one.
            return out.splitlines()[0].strip() if out else ""
        except Exception as e:
            logger.warning(f"scalar query error: {sql}: {e}")
            return None

    def _file_mode(self, path: str):
        """Octal permission bits of an on-device file (e.g. "660", "0"), read via
        `stat -c %a` — NOT a file open, so it survives the file being chmod'd to
        0000. Returns None on any failure (dry-run, no such file, run-as denied),
        distinguishable from "0" (the string) by callers that need to.

        (*) `stat -c` is toybox's Android build; unverified against every OS
        version this suite might run on. Confirm on-device before trusting a
        None as "the fault didn't apply" rather than "stat isn't supported here":
            adb -s <device> shell run-as <pkg> stat -c '%a' databases/open_source_database.db
        """
        if self.dry_run:
            return None
        argv = [self.adb] + (["-s", self.device] if self.device else []) + \
            ["shell", f"run-as {self.package} stat -c '%a' {path}"]
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=30)
            if r.returncode != 0:
                return None
            out = (r.stdout or "").strip()
            return out if out else None
        except Exception as e:
            logger.warning(f"stat query error: {path}: {e}")
            return None

    def _reseed(self) -> bool:
        if self.dry_run:
            print("  $ bash", self.seed_script)
            return True
        try:
            r = subprocess.run(["bash", self.seed_script], capture_output=True,
                               text=True, timeout=180,
                               env={**os.environ})
            return r.returncode == 0
        except Exception as e:
            logger.warning(f"reseed failed: {e}")
            return False

    # --------------------------------------------------------------- injecting
    def _do_inject(self, gate: str) -> None:
        spec = self.faults.get(gate)
        if not spec:
            logger.warning(f"{gate}: no injection spec in disruption_mapping.yml")
            return
        mech = spec.get("mechanism", "none")
        if mech == "none":
            logger.info(f"  {gate}: driven by the AUT (no out-of-band injection)")
            return
        inj = spec.get("inject", "")
        tmo = int(spec.get("timeout", 30))
        if mech == "sqlite":
            ok = self._sql(self._subst(inj))
        elif mech == "host":
            ok = self._host(self._subst(inj), timeout=tmo)
        else:                                   # adb / connectivity are adb-shell strings
            ok = all(self._adb_shell(self._subst(part.strip()), timeout=tmo)
                     for part in inj.split(";") if part.strip())
        self._active.append(gate)
        logger.info(f"  {gate} injected ({mech}){'  [dry-run]' if self.dry_run else ''}"
                    f"{'' if ok else '  — WARNING: command failed'}")
        # Prove it bit. A command that reported success and a fault that is
        # not in place are two different things; only the probe tells them apart.
        v = self._probe(spec, "verify_injected")
        self.last_verification[gate] = v
        if v is False:
            self.unconfirmed.add(gate)
            logger.error(f"  {gate}: injected but NOT confirmed active -- a verdict from "
                         f"this run would describe an undisrupted SUT")
        elif v is True:
            logger.info(f"  {gate}: injection confirmed by probe")

    # The foods under test, exactly as seed_foods.sh verifies them. manifested()
    # probes these by name.
    #
    # This list exists because an earlier version probed `name LIKE 'Test%'` -- the
    # synthetic fixtures seed_foods.sh now DELETES. Every probe therefore answered
    # about a row that was not there: CACHE_STALE reported "never manifested",
    # making every run of it INCONCLUSIVE even when the injection had worked, and
    # DB_CORRUPT reported "manifested" unconditionally, because a missing row and a
    # NULL energy both read as "". Keep this in step with disruption_mapping.yml.
    _FOODS_SQL = "'Peanut butter','Cooking butter','Corn germ oil'"

    def manifested(self, target: str):
        """Did TARGET actually take effect in the SUT? Lets the walker separate a real
        FAIL (fault bit, app still misbehaved) from INCONCLUSIVE (fault never bit /
        precondition absent). Returns True (in effect), False (provably NOT), or None
        (can't tell -> caller keeps its default FAIL). The answer is READ BACK from the
        SUT, so a verdict is never hardcoded — it self-corrects if the SUT/config
        changes (enable OFF, seed a diary row, wire a biting injection...)."""
        t = (target or "").upper()

        # Generic path first: a fault whose mapping declares a verify_injected
        # probe answers from that probe, whatever the fault is called. The
        # name-keyed cases below predate the probes and remain for the one
        # mapping that has none.
        spec = self.faults.get(t) or {}
        if isinstance(spec, dict) and spec.get("verify_injected"):
            # The question is whether the fault was in place when the walk
            # passed its gate, and the probe run AT injection answered it.
            # Re-probing later measures the aftermath instead: a full
            # partition, for instance, is trimmed by the platform the moment a
            # write hits ENOSPC (17 MB of caches freed, observed live), and the
            # later probe then said "not full" about a fault that had already
            # bitten. So the injection-time answer wins when there is one.
            if t in self.last_verification and self.last_verification[t] is not None:
                return self.last_verification[t]
            return self._probe(spec, "verify_injected")

        def _row_exists(sql):
            """True if the query returned a row, False if it ran and found none,
            None if it could not be answered. Probing for a NAME rather than a
            value keeps the three cases distinguishable -- a NULL energy and a
            missing row both read as "" and would otherwise be conflated."""
            hit = self._scalar(sql)
            return None if hit is None else (hit != "")

        if t == "DB_CORRUPT":
            # In effect iff the energy of at least one food under test is now NULL.
            return _row_exists(
                f"SELECT name FROM Product WHERE name IN ({self._FOODS_SQL}) "
                f"AND energy IS NULL LIMIT 1")
        if t == "CACHE_STALE":
            # In effect iff at least one food under test carries the stale value.
            return _row_exists(
                f"SELECT name FROM Product WHERE name IN ({self._FOODS_SQL}) "
                f"AND energy = 999 LIMIT 1")
        if t == "DISRUPTION_DB":
            # Injected as a BEFORE INSERT trigger that raises ABORT, so its presence
            # in the schema is exactly the question "is the write path poisoned?".
            return _row_exists(
                "SELECT name FROM sqlite_master WHERE type = 'trigger' "
                "AND name = 'fault_abort_write' LIMIT 1")
        if t == "STORAGE_FULL":
            # Probe for the BALLAST FILE, not for a failing write.
            #
            # This used to attempt a throwaway `CREATE TABLE`/`DROP TABLE` and
            # treat its success as "the fault did not manifest". That is too weak:
            # the ballast deliberately leaves ~20 MB of headroom so the rest of
            # Android keeps running, and 20 MB is ample for a tiny table. The
            # probe therefore succeeded while the disk was in fact full, and the
            # run was recorded INCONCLUSIVE for a fault that had bitten
            # (storage_full v14, 2026-08-23).
            #
            # The ballast's presence is the injection itself, so it answers the
            # question directly rather than by inference.
            return self._adb_shell(
                f"run-as {self.package} test -f files/fault_ballast")
        if t == "UE1_KILL":
            # Transient by nature: the process is killed and immediately relaunched,
            # so by the time anything could probe, the evidence is gone. None keeps
            # the caller's default rather than inventing a signal. The check that
            # matters for this fault is the invariant at the verdict -- does the
            # displayed total equal the sum of rows actually in the database.
            return None
        if t == "INPUT_INVALID":
            # INPUT_INVALID only "bites" if the app actually COMMITS the bad entry.
            # An empty diary => it was never reached. Paren-free probe (count(*)
            # trips the device shell): a ROWID if any row exists, "" if the query
            # ran and the diary is empty, None on a read error.
            row = self._scalar("SELECT ROWID FROM Measurement LIMIT 1")
            logger.debug(f"  [manifested] {t} Measurement ROWID probe -> {row!r}")
            if row == "":
                return False          # confirmed empty diary -> fault unreachable
            return None               # a row exists, or the read errored -> can't confirm
        if t == "STORAGE_MEDIA":
            # USED TO share the ROWID probe above. That is self-defeating for this
            # fault specifically: STORAGE_MEDIA is `chmod 0000` on the very database
            # the ROWID probe queries, so once the fault is in effect the probe's
            # read fails and returns None ("can't confirm") -- the fault disables
            # its own detector, indistinguishable from the fault never having bitten.
            #
            # `stat` reads inode metadata (mode/size/mtime) via a directory lookup,
            # not a file OPEN, so it is not blocked by the file's own permission
            # bits the way a read/query is. It can therefore confirm the chmod
            # directly instead of inferring it from a read the same chmod breaks.
            mode = self._file_mode(self.db)
            logger.debug(f"  [manifested] STORAGE_MEDIA db mode probe -> {mode!r}")
            if mode is None:
                return None            # stat itself failed -- can't tell
            return mode == "0"         # "0" == chmod 0000 took effect, confirmed
        # EXTAPI_FAIL has no DB signal: the missing external SOURCE is a UI fact the
        # walker reads off the failing selector instead.
        return None

    def gate_faults(self) -> set:
        return {g for g, s in self.faults.items() if s.get("timing") == "gate"}

    def is_fault_gate(self, gate: str) -> bool:
        return gate in self.faults and self.faults[gate].get("timing") != "none"

    def pre_inject(self, aut_labels) -> None:
        """Inject the tc's TARGET fault if it is `timing: pre`. The fault AUTs are
        multi-fault graphs (target + other faults as refused branches), so we inject
        ONLY the target — never some other fault whose gate merely appears."""
        if not self.target:
            return
        spec = self.faults.get(self.target, {})
        if spec.get("timing") == "pre":
            present = {lbl.split()[0].upper().rstrip(";") for lbl in aut_labels}
            if self.target in present:
                logger.info(f"pre-injecting target {self.target} before the walk")
                self._do_inject(self.target)

    def inject_gate(self, gate: str) -> None:
        """Inject a `timing: gate` fault the moment its gate is reached — but only if
        it is THIS tc's target (ignore other faults' gates in the graph)."""
        if self.target and gate != self.target:
            return
        spec = self.faults.get(gate)
        if spec and spec.get("timing") == "gate":
            self._do_inject(gate)

    # ---------------------------------------------------------------- restoring
    def restore(self) -> None:
        if not self._active:
            return
        needs_reseed = False
        failed: list[str] = []
        for gate in reversed(self._active):     # LIFO
            spec = self.faults.get(gate, {})
            rest = spec.get("restore", "")
            if rest == "reseed":
                needs_reseed = True
            elif rest:
                # HONOUR THE MECHANISM, exactly as _do_inject does.
                #
                # This block used to read `mech` and then ignore it, sending every
                # restore -- including SQL -- to the device shell, which answered
                # 127 (command not found) and moved on:
                #
                #   WARNING  adb shell failed (127): UPDATE Product SET energy = 636 ...
                #   INFO       faults restored: DB_CORRUPT
                #
                # Inject honoured the mechanism; restore did not. So every sqlite
                # fault BIT and never LET GO: DB_CORRUPT left the catalogue NULL,
                # CACHE_STALE left it at 999, and DISRUPTION_DB left its
                # RAISE(ABORT) trigger armed -- poisoning every purpose that ran
                # afterwards with data that had nothing to do with their own fault.
                # check_faults.sh could not see it, because that script performs its
                # own correctly-dispatched restore.
                mech = spec.get("mechanism", "adb")
                if mech == "sqlite":
                    # One call: sqlite3 executes multiple statements itself, and
                    # splitting on ';' would break a trigger body.
                    ok = self._sql(self._subst(str(rest)))
                elif mech == "host":
                    ok = self._host(self._subst(str(rest)), timeout=int(spec.get("timeout", 60)))
                else:
                    ok = all(self._adb_shell(self._subst(p.strip()))
                             for p in str(rest).split(";") if p.strip())
                if not ok:
                    failed.append(gate)
                elif self._probe(spec, "verify_restored") is False:
                    # the command ran and the fault is still there
                    failed.append(gate)
            elif spec.get("verify_restored"):
                # nothing to run, but the mapping still says what "restored" looks like
                if self._probe(spec, "verify_restored") is False:
                    failed.append(gate)
        if needs_reseed:
            logger.info(f"  restoring via reseed ({self.seed_script})")
            if not self._reseed():
                failed.append("reseed")
        # Never announce a restore that did not happen. A silent failure here is
        # the most expensive kind: the device stays poisoned, the next purpose runs
        # against it, and its verdicts describe the previous fault.
        self.restore_failures = list(failed)
        if failed:
            logger.error(
                f"  RESTORE FAILED for {', '.join(failed)} -- the device is still "
                f"disrupted. Every later run will measure against this state. "
                f"Re-run {self.seed_script} before continuing.")
        else:
            logger.info(f"  faults restored: {', '.join(self._active)}")
        self._active.clear()


# ---------------------------------------------------------------------------
# Dry-run demo:  python3 framework/concretization/fault_injector.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import yaml, sys
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    mp = os.path.join(root, "systems/foodyou/properties/disruption_mapping.yml")
    mapping = yaml.safe_load(open(mp))
    inj = AndroidFaultInjector(mapping, device="emulator-5554",
                               package="com.maksimowiczm.foodyou",
                               project_root=root, dry_run=True)
    print("== timing: pre  (fired before the walk) ==")
    for g, s in mapping["faults"].items():
        if s.get("timing") == "pre":
            inj._do_inject(g)
    print("\n== timing: gate (fired at the fault gate) ==")
    for g in inj.gate_faults():
        inj._do_inject(g)
    print("\n== restore ==")
    inj.restore()
    sys.exit(0)
