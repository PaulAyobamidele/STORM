#!/usr/bin/env python3
"""
classify_failure.py — decide WHY a concretization run reported its verdict.

A FAIL printed by run.py answers only "the walk ended badly". It does not say
whether the SUT actually contradicted the specification (a genuine ioco
counter-example) or whether the tester never managed to apply its own stimuli
(an execution artifact, which under ioco is not a FAIL at all — an unappliable
stimulus makes the run INCONCLUSIVE, because no observation was ever put to the
oracle).

This reads one captured run log — stdout AND stderr of

    python -u framework/scripts/run.py ... --report --verbose 2>&1 | tee log

— locates the step that ended the walk, and buckets it:

  IOCO        the SUT produced an observable the spec forbids, or produced a
              value the oracle rejects. A real counter-example.
  QUIESCENCE  the SUT stayed silent where the spec required an output. Genuine
              ioco failure ONLY if the observation was reachable and --timeout
              was long enough; always flagged REVIEW.
  ARTIFACT    the tester's own stimulus, navigation, or parameter resolution
              failed. Says nothing about the SUT. Should have been INCONC.
  APP-ERROR-BOUNDARY  the failing step LOOKS like ARTIFACT ("element not
              found") but the screen captured at that moment shows the
              app's own crash/error boundary, not a missing UI target —
              i.e. the app crashed and took the element with it. A real
              finding, not a tester defect. Checked by opening the capture
              this run's own log already points to (`screen state
              captured: ... / X.xml`), not guessed at.
              FoodYou v47 (disruption_db) is the case this exists for: an
              "Element not found: Go back|Close sheet" ARTIFACT that was
              really the app replacing its whole UI with a stack trace.
  UNCLASSIFIED  the walk returned FAIL without logging a step — read the trace.

Usage:
    python framework/scripts/classify_failure.py RUN.log            # one line
    python framework/scripts/classify_failure.py RUN.log --trace 12 # + context
    python framework/scripts/classify_failure.py RUN.log --json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Error-string taxonomy.
#
# Every pattern below is an error string algorithm.py attaches to a FAIL
# StepResult, or a terminal logger line it emits when it returns a verdict
# without logging a step. Keep this table in sync with algorithm.py: an
# unmatched error string degrades to UNCLASSIFIED rather than being guessed at.
# ---------------------------------------------------------------------------

TAXONOMY: list[tuple[str, str, str]] = [
    # (regex, class, why this class)

    # --- the SUT contradicted the spec -------------------------------------
    (r"classifies as .*, expected",
     "IOCO", "observed total falls in a different bucket than the model's"),
    (r"observed [\d.]+ kcal, expected authoritative",
     "IOCO", "observed per-food quantity differs from the authoritative value"),
    (r"Constraint violation at .*: expected .*, got",
     "IOCO", "observed value contradicts a value fixed earlier in the run"),
    (r"Constraint violation at",
     "IOCO", "observed value violates a constraint on the gate"),
    (r"Unexpected output at",
     "IOCO", "SUT emitted an output not in the spec's expected set"),
    (r"No expected output matched",
     "IOCO", "no allowed output was observed within the timeout"),
    (r"Attack/Failure observed",
     "IOCO", "SUT took a branch the spec marks as an attack/failure"),

    # --- the SUT went silent ------------------------------------------------
    (r"Quiescence at ",
     "QUIESCENCE", "observe timed out where the spec required an output"),
    (r"Quiescence: .* timed out after",
     "QUIESCENCE", "observe timed out where the spec required an output"),
    (r"Typed observe timed out",
     "QUIESCENCE", "typed observe timed out"),
    (r"Observation timed out after traversal",
     "QUIESCENCE", "observe timed out after the traversal path ran"),

    # --- the environment could never run this test case --------------------
    # Decided before the walk starts, so it is not a step failure at all. First in
    # the table because it is the most specific claim available.
    (r"UNREALIZABLE|not executable in this environment",
     "UNREALIZABLE", "test case needs an abstract value this deployment cannot produce"),

    # --- the tester lost track of the SUT ----------------------------------
    # Distinct from ARTIFACT: not "a step failed" but "the tester no longer knows
    # what screen it is on", so every step after it is meaningless. Listed first
    # because these strings also contain the wording of the step that failed.
    (r"tester lost track of the SUT",
     "LOST-SYNC", "screen belief contradicted by the device"),
    (r"declared it lands on .*, but the SUT shows",
     "LOST-SYNC", "gate did not land where the model said it would"),
    (r"screen tracker drift at",
     "LOST-SYNC", "believed screen is not an arm of this gate"),
    (r"precondition not met at",
     "LOST-SYNC", "gate anchor never appeared"),

    # --- the tester failed, not the SUT ------------------------------------
    (r"Typed UI action failed",
     "ARTIFACT", "driver could not perform a tester stimulus"),
    (r"Traversal action failed",
     "ARTIFACT", "driver could not complete a traversal step"),
    (r"UI action failed",
     "ARTIFACT", "driver could not perform a tester stimulus"),
    (r"No traversal actions for screen",
     "ARTIFACT", "System Interface has no path from the current screen"),
    (r"Param resolution failed",
     "ARTIFACT", "an abstract parameter had no concrete interpretation"),
    (r"Cannot resolve typed structural label",
     "ARTIFACT", "structural label carries no executable UI entry"),
    (r"Failed to activate disruption",
     "ARTIFACT", "the fault could not be injected"),
    (r"DisruptionExecutor not configured",
     "ARTIFACT", "run invoked without --disruption-mapping"),
]

# Terminal logger lines that carry the cause when no FAIL step was logged.
LOGGER_CAUSES = [
    (r"No expected output matched after (\d+)s",
     "IOCO", "observation exhausted with no allowed output and no quiescence branch"),
    (r"Attack/Failure observed: (.*)",
     "IOCO", "SUT took a branch the spec marks as an attack/failure"),
]

VERDICT_RE = re.compile(r"Verdict:\s*(?:\x1b\[[0-9;]*m)?(PASS|FAIL|INCONC)")
# UNEXECUTABLE is reported by run.py on its own "Status:" line, never as a
# Verdict, so it needs its own pattern. Matched FIRST by `analyse`: a run that
# never happened has no verdict to classify, and the classes below (ARTIFACT,
# LOST-SYNC, HARNESS-FAILURE) describe WHY it did not happen -- they are the
# diagnosis of an unexecuted run, not a re-reading of an outcome.
STATUS_UNEXEC_RE = re.compile(r"Status:\s*(?:\x1b\[[0-9;]*m)?UNEXECUTABLE")
# print_report renders "  GATE_NAME<pad>STATUS  -- error  captured={...}"
STEP_RE = re.compile(r"^\s{2}(\S+)\s+(PASS|FAIL|INCONC|ok)\b(.*)$")
ERROR_RE = re.compile(r"--\s*(.*?)(?:\s{2}captured=|$)")

# executors.py's _capture_failure logs exactly this line when it saves a
# screenshot/XML dump; the two paths are separated by " / ".
CAPTURE_LINE_RE = re.compile(r"screen state captured:\s*\S+\.png\s*/\s*(\S+\.xml)")

# SUT-agnostic signals that the CAPTURED SCREEN is the app's own crash/error
# boundary rather than whatever the tester's selector was looking for. Not
# tied to any one SUT's wording — a Java/Kotlin stack frame and an
# *Exception class name are platform-level, and "something went wrong" is
# common in-app fallback-UI phrasing across many apps, not FoodYou-specific.
APP_ERROR_BOUNDARY_RE = re.compile(
    r"\bat\s+[\w.$]+\([\w.<>]+:\d+\)"      # a real stack frame
    r"|\b\w+Exception\b"                    # ...Exception class name
    r"|[Ss]omething went wrong",             # common in-app crash-screen phrasing
)


def _capture_shows_app_error_boundary(lines: list[str], log_path: str) -> bool:
    """Best-effort: does the LAST capture this run took show the app's own
    crash/error boundary rather than a missing UI target?

    Never raises — a capture file that moved, was never written (older
    sweeps before captures were case-scoped), or isn't there yet is not a
    reason to crash a classifier; it just means this check abstains and the
    normal ARTIFACT/LOST-SYNC classification stands.
    """
    xml_rel = None
    for ln in reversed(lines):
        m = CAPTURE_LINE_RE.search(ln)
        if m:
            xml_rel = m.group(1)
            break
    if not xml_rel:
        return False

    # Try relative to the log's own directory first (captures are co-located
    # with their case's log as of the 2026-09-01 chain-of-custody fix), then
    # relative to the current working directory (older sweeps wrote the flat,
    # repo-root-relative tmp/failure_artifacts/ path — e.g. FoodYou v47).
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(log_path)), os.path.basename(xml_rel)),
        xml_rel,
        os.path.abspath(xml_rel),
    ]
    for path in candidates:
        try:
            with open(path, errors="replace") as f:
                content = f.read()
        except OSError:
            continue
        return bool(APP_ERROR_BOUNDARY_RE.search(content))
    return False
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def classify_error(text: str) -> tuple[str, str]:
    """Bucket one error string. Returns (class, why)."""
    # A step the algorithm guarded to INCONCLUSIVE names its own reason, e.g.
    #   "INCONCLUSIVE (tester lost track of the SUT: ...): Typed UI action failed"
    # Classify on the REASON first: the trailing "<something> failed" describes
    # the step that tripped, not why the run is inconclusive, and matching on it
    # would file every guarded step under ARTIFACT regardless of cause.
    m = re.search(r"INCONCLUSIVE \((.*?)\):", text)
    if m:
        reason = m.group(1)
        for pattern, cls, why in TAXONOMY:
            if re.search(pattern, reason):
                return cls, why
        return "ARTIFACT", f"guarded to INCONCLUSIVE: {reason}"
    for pattern, cls, why in TAXONOMY:
        if re.search(pattern, text):
            return cls, why
    return "UNCLASSIFIED", "error string not in the taxonomy"


def analyse(path: str) -> dict:
    with open(path, errors="replace") as f:
        lines = [ANSI_RE.sub("", ln.rstrip("\n")) for ln in f]

    # Checked before the verdict scan: an unexecuted run has no verdict, and
    # letting a stray "Verdict:" line elsewhere in the log win would restore
    # exactly the confusion this status exists to remove.
    verdict = None
    if any(STATUS_UNEXEC_RE.search(ln) for ln in lines):
        verdict = "UNEXECUTABLE"
    else:
        for ln in lines:
            m = VERDICT_RE.search(ln)
            if m:
                verdict = m.group(1)
                break

    # --- the execution report: first step whose status is FAIL -------------
    in_report = False
    fail_gate = fail_error = None
    steps = 0
    for ln in lines:
        if ln.startswith("Execution Report"):
            in_report = True
            continue
        if in_report and ln.startswith("Captured values"):
            in_report = False
            continue
        if not in_report:
            continue
        m = STEP_RE.match(ln)
        if not m:
            continue
        steps += 1
        # INCONC counts too: since the walker gained the INCONCLUSIVE guard, the
        # step that ended the walk is often logged INCONC rather than FAIL, and
        # it still carries the error string that explains why.
        if m.group(2) in ("FAIL", "INCONC") and fail_gate is None:
            fail_gate = m.group(1)
            em = ERROR_RE.search(m.group(3))
            fail_error = em.group(1).strip() if em else ""

    # --- fall back to the terminal logger line -----------------------------
    from_logger = False
    if fail_error is None:
        for ln in reversed(lines):
            for pattern, _cls, _why in LOGGER_CAUSES:
                if re.search(pattern, ln):
                    fail_error = ln.split("  ", 1)[-1].strip()
                    fail_gate = "(no step logged)"
                    from_logger = True
                    break
            if from_logger:
                break

    # Arithmetic inconsistencies are findings, not verdicts: the model specifies
    # buckets, so they never end the walk and never appear as a FAIL step. Scan
    # for them separately or they would be invisible in a PASS run — which is
    # exactly where they matter, since the bucket oracle is blind above ~3.5
    # portions and a wrong total there still classifies correctly.
    arithmetic = sorted({ln.split("ARITHMETIC INCONSISTENCY", 1)[1].lstrip(": ").strip()
                         for ln in lines if "ARITHMETIC INCONSISTENCY" in ln})
    # Same treatment for delta violations: "the total did not move as the action
    # implies" never ends a walk, so it would otherwise be invisible in a PASS —
    # which is exactly where it hides, since saturated buckets accept any large
    # total. Collected separately so a run can report both kinds at once.
    arithmetic += sorted({ln.split("TOTAL DELTA", 1)[1].lstrip(": ").strip()
                          for ln in lines if "TOTAL DELTA" in ln})
    # The strongest of the three: the displayed total against the sum of the
    # foods actually logged. Exact, mix-of-foods safe, and invisible to the band
    # oracle, which tolerates half a portion either way.
    arithmetic += sorted({ln.split("TOTAL MISMATCH", 1)[1].lstrip(": ").strip()
                          for ln in lines if "TOTAL MISMATCH" in ln})
    # The application contradicting its OWN two views of the same day: the energy
    # it displays against the macros it displays. Not a conformance verdict -- the
    # specification models energy only, so a discrepancy violates nothing it
    # asserts -- but it is how the DB_CORRUPT defect of 2026-08-23 was caught, and
    # it must not be invisible just because the model cannot express it.
    arithmetic += sorted({ln.split("MACRO INCONSISTENCY", 1)[1].lstrip(": ").strip()
                          for ln in lines if "MACRO INCONSISTENCY" in ln})
    # The exact-sum ledger abstains when it loses a movement, rather than
    # reporting a confident wrong number. That is the right call, but an
    # abstention must not be silent either: a run whose strongest oracle switched
    # itself off is weaker evidence than one where it ran, and only this line
    # says so.
    abstained = any("exact-sum ledger UNKNOWN" in ln for ln in lines)

    if fail_error is None:
        cls, why = ("NONE", "run did not fail") if verdict == "PASS" \
            else ("UNCLASSIFIED", "no FAIL step and no terminal cause in the log")
        fail_gate, fail_error = "", ""
    else:
        cls, why = classify_error(fail_error)

    # --- APP-ERROR-BOUNDARY ----------------------------------------------------
    # An "element not found" ARTIFACT (or LOST-SYNC precondition-not-met) can be
    # the tester's own selector going stale -- or it can be the app crashing and
    # taking the target element down with it. Those look identical from the
    # error string alone; they are not identical from the screen the run
    # captured at that moment. Checked here, narrowly: only reclassify a
    # failure that already looks like a missing UI target, and only on direct
    # evidence from the capture the run itself took, never a guess.
    #
    # This is why v47 (disruption_db) sat filed as ARTIFACT for over a week:
    # "Element not found: Go back|Close sheet" is exactly what a stale
    # selector looks like from the log alone. The capture showed FoodYou's own
    # error boundary -- "Oops! Something went wrong" plus a live
    # SQLiteConstraintException stack trace -- in place of the whole UI. That
    # is the campaign's most important single result, not a tester defect.
    if cls in ("ARTIFACT", "LOST-SYNC") and _capture_shows_app_error_boundary(lines, path):
        cls, why = ("APP-ERROR-BOUNDARY",
                     "captured screen shows the app's own crash/error boundary "
                     "in place of the expected UI, not a missing UI target")

    # --- HARNESS-FAILURE ------------------------------------------------------
    # The apparatus broke, so the run says nothing about the SUT or the model.
    # Checked LAST and allowed to override, because these failures surface as
    # whatever error string happened to be in flight when the tooling died -- in
    # the 2026-08-23 sweep they arrived as UNCLASSIFIED, and reconstructing them
    # afterwards took a grep across 748 logs.
    #
    # This is deliberately narrow: only conditions that are unambiguously the
    # apparatus. An unappliable stimulus is ARTIFACT and a lost screen is
    # LOST-SYNC; neither belongs here, because both are the tester interacting
    # with the SUT and failing. These are the tester failing to run at all.
    for pat, reason in (
        (r"Appium Settings app is not running|instrumentation process cannot be initialized",
         "the Appium session died mid-run"),
        (r"Exceeded MAX_STEPS",
         "the walker exhausted its step budget"),
        (r"Traceback \(most recent call last\)|AttributeError|TypeError: ",
         "an unhandled Python exception in the framework"),
        (r"isn't responding|Process system isn't responding|ANR in ",
         "the device showed a system-level not-responding dialog"),
    ):
        if any(re.search(pat, ln) for ln in lines):
            cls, why = "HARNESS-FAILURE", reason
            break

    return {
        "log": path,
        "verdict": verdict or "ERROR",
        "class": cls,
        "why": why,
        "gate": fail_gate,
        "error": fail_error,
        "steps": steps,
        "from_logger": from_logger,
        "review": cls == "QUIESCENCE",
        "arithmetic": arithmetic,
        "abstained": abstained,
    }


def tail_trace(path: str, n: int) -> list[str]:
    """Last n walker lines (INFO/WARNING/ERROR) before the report."""
    out = []
    with open(path, errors="replace") as f:
        for ln in f:
            ln = ANSI_RE.sub("", ln.rstrip("\n"))
            if re.match(r"^(INFO|WARNING|ERROR|DEBUG)\s", ln):
                out.append(ln)
    return out[-n:]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("log", nargs="+", help="captured run log(s)")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument("--trace", type=int, default=0,
                    help="also print the last N walker lines")
    ap.add_argument("--tsv", action="store_true",
                    help="verdict<TAB>class<TAB>gate<TAB>error (for shell drivers)")
    args = ap.parse_args()

    results = [analyse(p) for p in args.log]

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    for r in results:
        if args.tsv:
            # Columns 5 and 6 carry what the verdict cannot: findings that never
            # end a walk, and whether the strongest oracle was still running.
            # Appended, so any caller reading only 1-4 is unaffected.
            print("\t".join([r["verdict"], r["class"], r["gate"], r["error"],
                             str(len(r["arithmetic"])),
                             "UNKNOWN" if r["abstained"] else "ok"]))
            continue
        flag = "  [REVIEW]" if r["review"] else ""
        print(f"{r['log']}")
        print(f"  verdict : {r['verdict']}")
        print(f"  class   : {r['class']}{flag}  ({r['why']})")
        print(f"  gate    : {r['gate'] or '-'}")
        print(f"  error   : {r['error'] or '-'}")
        print(f"  steps   : {r['steps']}")
        if r["arithmetic"]:
            print(f"  ARITHMETIC ({len(r['arithmetic'])}) — findings the bucket "
                  f"oracle cannot see:")
            for a in r["arithmetic"]:
                print(f"    {a}")
        if r["abstained"]:
            print("  LEDGER  : ABSTAINED — a staged movement was never applied, so"
                  " the exact-sum")
            print("            check switched itself off partway. This run is "
                  "weaker evidence")
            print("            than one where it ran; grep 'ledger UNKNOWN' for "
                  "where it stopped.")
        if args.trace:
            print("  trace   :")
            for ln in tail_trace(r["log"], args.trace):
                print(f"    {ln}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
