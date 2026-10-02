#!/bin/sh
# run_matrix.sh — run the Moodle sweep, one test case at a time, with the
# fixture reset BEFORE EVERY CASE.
#
# ---------------------------------------------------------------------------
# WHY THE RESET IS NOT OPTIONAL
# ---------------------------------------------------------------------------
# Every generated test case starts from the specification's initial state, in
# which the student has NOT submitted and has NO attempt. Moodle renders
# "Edit submission" instead of "Add submission" once a submission exists, and
# the quiz page stops offering "Attempt quiz" once an attempt is open. A case
# run against a fixture left dirty by the previous one therefore stalls on a
# PRECONDITION and reports INCONCLUSIVE -- a verdict about the setup, not about
# Moodle. That happened during development: tc_happy reached VIEW_ASSIGN and
# then timed out waiting for "Add submission".
#
# Without this, a sweep's verdicts depend on the order the cases happen to run
# in, which makes them unattributable.
#
# ---------------------------------------------------------------------------
# WHY EACH CASE RUNS SEPARATELY RATHER THAN VIA --aut-dir
# ---------------------------------------------------------------------------
# --aut-dir walks every AUT in one process, which gives no opportunity to reset
# between them. The isolation above is the whole point, so the loop is here.
#
# Usage:
#   cd systems/moodle
#   sh run_matrix.sh                       # all nine cases
#   sh run_matrix.sh happy                 # just tc_happy
#   sh run_matrix.sh happy app_lazy_regrade
# ---------------------------------------------------------------------------
set -u

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
SUT="$ROOT/systems/moodle"
DOCKER="$SUT/sut/moodle-docker"
TCDIR="$SUT/generated/tc"
URL="${MOODLE_URL:-http://localhost:8080}"
STAMP=$(date +%Y%m%d-%H%M%S)
RESULTS="$SUT/results-$STAMP.log"

MOODLE_DOCKER_WWWROOT="$SUT/sut/moodle"
MOODLE_DOCKER_DB=pgsql
export MOODLE_DOCKER_WWWROOT MOODLE_DOCKER_DB

# run.py does `sys.path.insert(0, os.path.dirname(__file__))', which adds
# framework/scripts -- but the package is framework/concretization, one level
# up. So run.py imports only when the CWD happens to be framework/. Invoked by
# absolute path, as here, it dies with ModuleNotFoundError before parsing any
# argument, and every case in the sweep exits 1 with no verdict at all.
# Setting the path here rather than editing run.py keeps the fix with the
# caller that needs it.
PYTHONPATH="$ROOT/framework${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH

# Explicit venv interpreter, not bare `python3` -- see run_variants.sh for the
# measured failure mode this avoids (silent ModuleNotFoundError inside a
# subprocess whose output only the caller inspects) when this script is ever
# run from a context that doesn't inherit the interactive shell's venv PATH.
PYTHON3="$ROOT/.venv/bin/python3"
[ -x "$PYTHON3" ] || PYTHON3="python3"

# HEADLESS=0 opens a real Chrome window so the run can be watched.
#
# For WATCHING ONLY. A headed browser is a different environment from the one
# the recorded verdicts come from -- the "Attempt quiz" confirmation is a case
# in point: its AMD modal resolves erratically headless and reliably headed, so
# the two take different routes to the same page. Record results from the
# default headless runs; use this to see what a case is doing.
HEADLESS="${HEADLESS:-1}"
HEADLESS_FLAG=""
if [ "$HEADLESS" = "0" ]; then
  HEADLESS_FLAG="--no-headless"
  echo "*** HEADED MODE: a browser window will open. For watching, not for recording. ***"
fi

if [ "$#" -gt 0 ]; then
  CASES="$*"
else
  CASES="happy app1_write_fail app_partial_submission app_grade_stale_sub app_lazy_regrade db_attempt_step_loss infra_cron_dead ue1_lose_conn ue2_session_expire"
fi

echo "results -> $RESULTS"
{
  echo "Moodle sweep $STAMP"
  echo "url=$URL"
  echo "cases: $CASES"
  echo
} | tee "$RESULTS"

# A fault latched by a previously crashed run would apply to the FIRST case of
# this sweep, whose verdict would then describe a fault it never asked for.
# reset_moodle.php drops the known triggers; do it once up front as well.
echo "== clearing any latched fault before the sweep ==" | tee -a "$RESULTS"
( cd "$DOCKER" && bin/moodle-docker-compose exec -T webserver php /dev/stdin \
    < "$SUT/reset_moodle.php" ) >/dev/null 2>&1

for name in $CASES; do
  AUT="$TCDIR/tc_${name}.aut"
  echo "======================================================================" | tee -a "$RESULTS"
  echo "== $name" | tee -a "$RESULTS"

  if [ ! -r "$AUT" ]; then
    echo "   SKIP: $AUT not found (regenerate on the node first)" | tee -a "$RESULTS"
    continue
  fi

  # ---- reset, and REFUSE TO RUN if it failed ----------------------------
  # A silent reset failure is worse than a loud one: the case would still run,
  # still produce a verdict, and that verdict would be attributed to Moodle.
  echo "   resetting fixture..." | tee -a "$RESULTS"
  if ! ( cd "$DOCKER" && bin/moodle-docker-compose exec -T webserver php /dev/stdin \
           < "$SUT/reset_moodle.php" ) > "/tmp/moodle-reset-$name.log" 2>&1; then
    echo "   ERROR: reset FAILED -- refusing to run $name." | tee -a "$RESULTS"
    echo "          A case run on a dirty fixture yields an unattributable" | tee -a "$RESULTS"
    echo "          verdict. See /tmp/moodle-reset-$name.log" | tee -a "$RESULTS"
    continue
  fi

  # ---- run the case -----------------------------------------------------
  # RUN FROM THE REPO ROOT. DisruptionExecutor takes project_root=".", i.e. the
  # CWD, and nothing overrides it; the mechanism's `cwd:' in
  # disruption_mapping.yml is repo-relative. Launching from systems/moodle
  # therefore resolved it to systems/moodle/systems/moodle/sut/moodle-docker,
  # every injection failed with ENOENT, and the case still produced a verdict:
  # a FAIL, because with no fault injected the save SUCCEEDED and the oracle
  # waiting for the error box timed out. A tester defect wearing a
  # conformance verdict. All paths below are absolute, so the cd is safe.
  LOG="$SUT/run-$name-$STAMP.log"
  ( cd "$ROOT" && "$PYTHON3" "$ROOT/framework/scripts/run.py" \
      --aut "$AUT" \
      --platform html \
      --url "$URL" \
      --system-interface "$SUT/model/system_interface_moodle.lnt" \
      --concrete-domain "$SUT/properties/concrete_domain.yml" \
      --type-description "$SUT/properties/type_description.yml" \
      --disruption-mapping "$SUT/properties/disruption_mapping.yml" \
      $HEADLESS_FLAG \
      --report \
      --log-file "$RESULTS" ) \
      > "$LOG" 2>&1
  RC=$?

  # Parse the VERDICT LINE, not the whole log.
  #
  # This used to grep the log for the words PASS/FAIL/INCONCLUSIVE and take the
  # last match, which reports whatever token happens to appear last ANYWHERE --
  # including inside an explanatory message. It misreported an INCONC run as
  # FAIL the moment a log line contained the phrase "rather than a conformance
  # FAIL". The run.py summary prints exactly one "Verdict: X (file)" line; read
  # that, and strip the ANSI colour it is wrapped in.
  VERDICT=$(sed 's/\x1b\[[0-9;]*m//g' "$LOG" \
            | grep -oE "^Verdict: [A-Z]+" | head -1 | awk '{print $2}')
  echo "   verdict: ${VERDICT:-<none: see $LOG>} (exit $RC)" | tee -a "$RESULTS"

  # Injection that could not be CONFIRMED makes the verdict unattributable.
  # DisruptionExecutor already refuses silently-failed injections; surface it.
  if grep -q "injection FAILED or was not confirmed\|PRE-injection failed\|POISONED" "$LOG"; then
    echo "   WARNING: fault state not confirmed -- do NOT record this verdict." | tee -a "$RESULTS"
  fi
done

# Leave the fixture clean so the next thing to touch this SUT starts from a
# known state rather than from whatever the last case happened to leave.
( cd "$DOCKER" && bin/moodle-docker-compose exec -T webserver php /dev/stdin \
    < "$SUT/reset_moodle.php" ) >/dev/null 2>&1

echo "======================================================================" | tee -a "$RESULTS"
echo "sweep complete -> $RESULTS" | tee -a "$RESULTS"
