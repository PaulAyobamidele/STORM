#!/bin/sh
# run_variants.sh — walk EVERY extracted controllable variant of one test
# purpose through the concretizer, not just the canonical pick.
#
# WHY THIS EXISTS
# ----------------
# run_matrix.sh walks exactly one .aut per purpose (the canonical file). That
# is one resolution out of however many extract_all produced -- for
# infra_cron_dead, one out of 1295. A single PASS there says nothing about the
# other 1294; app1_write_fail's own canonical variant.1 turned out to be one
# of the ~197/200 that never even exercises the fault (confirmed earlier this
# session, walked, produced a false FAIL). This walks ALL of them, individually,
# through the real concretizer against the live SUT, and records every verdict
# -- not a hand-picked one, not a structural proxy for one.
#
# RESUMABLE BY DESIGN. Before walking a variant, checks whether it already has
# a result recorded and skips it if so. A ~3,700-variant sweep across seven
# purposes will run for a long time; interrupting it (laptop sleep, browser
# crash, a bad page load) must not lose completed work or force a restart from
# variant 1. Reset failures are NOT recorded as done, specifically so they get
# retried on the next invocation rather than permanently skipped.
#
# Usage:
#   cd EVALUATION/moodle
#   sh run_variants.sh app1_write_fail            # every variant
#   sh run_variants.sh app1_write_fail 50 100     # only variants 50..100
#   HEADLESS=0 sh run_variants.sh app1_write_fail 1 1   # watch one
# ---------------------------------------------------------------------------
set -u

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
SUT="$ROOT/EVALUATION/moodle"
DOCKER="$SUT/sut/moodle-docker"
TCDIR="$SUT/Test_Cases"
URL="${MOODLE_URL:-http://localhost:8080}"

PURPOSE="${1:?usage: sh run_variants.sh <purpose> [start] [end]}"
START="${2:-}"
END="${3:-}"

VARDIR="$TCDIR/variants/$PURPOSE"
RESULTS="$SUT/variant_results_${PURPOSE}.log"
LOGDIR="$SUT/variant_logs/$PURPOSE"
mkdir -p "$LOGDIR"

if [ ! -d "$VARDIR" ]; then
  echo "ERROR: $VARDIR not found. Pull the variants from the node first:" >&2
  echo "  rsync -av paulad@narval.computecanada.ca:/scratch/paulad/testor_moodle/variants/ $TCDIR/variants/" >&2
  exit 1
fi

MOODLE_DOCKER_WWWROOT="$SUT/sut/moodle"
MOODLE_DOCKER_DB=pgsql
export MOODLE_DOCKER_WWWROOT MOODLE_DOCKER_DB

# Same reason as run_matrix.sh: run.py's own sys.path.insert adds
# framework/scripts, but the package is framework/concretization, one level up.
PYTHONPATH="$ROOT/framework${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH

# Explicit venv interpreter, not bare `python3`. Bare python3 resolves via
# PATH, which the interactive shell's venv activation puts first -- but a
# backgrounded `caffeinate -i sh -c '...' &` subshell does not reliably
# inherit that, and falls through to the system python3, which has no
# packages installed. Measured directly: every walk in this session's first
# background run crashed on `import yaml` at run.py's very first import,
# before doing anything -- silently producing a `NONE` verdict per variant
# rather than an obvious error, because the crash happens inside a redirected
# subprocess whose stderr only run_variants.sh itself ever looks at.
PYTHON3="$ROOT/.venv/bin/python3"
[ -x "$PYTHON3" ] || PYTHON3="python3"

HEADLESS="${HEADLESS:-1}"
HEADLESS_FLAG=""
[ "$HEADLESS" = "0" ] && HEADLESS_FLAG="--no-headless"

touch "$RESULTS"

TOTAL=0
DONE_NOW=0

for AUT in $(ls "$VARDIR"/tc_${PURPOSE}.*.aut 2>/dev/null | sort -t. -k2 -n); do
  N=$(echo "$AUT" | sed -E "s/.*tc_${PURPOSE}\.([0-9]+)\.aut/\1/")
  TOTAL=$((TOTAL + 1))

  [ -n "$START" ] && [ "$N" -lt "$START" ] && continue
  [ -n "$END" ]   && [ "$N" -gt "$END" ]   && continue

  # RESUMABLE: skip a variant only if it already has a REAL recorded verdict.
  # A recorded NONE means run.py itself crashed before producing a verdict
  # line (measured cause: the interpreter running it had no packages
  # installed) -- that is not a completed attempt, and treating it as one
  # would silently skip the variant forever on every future resume.
  if awk -F'\t' -v n="$N" '$1==n && $2!="NONE"{f=1} END{exit !f}' "$RESULTS" 2>/dev/null; then
    continue
  fi

  echo "== $PURPOSE variant $N/$TOTAL =="

  if ! ( cd "$DOCKER" && bin/moodle-docker-compose exec -T webserver php /dev/stdin \
           < "$SUT/reset_moodle.php" ) > "/tmp/moodle-reset-${PURPOSE}-${N}.log" 2>&1; then
    echo "   reset FAILED -- NOT recording a result, will retry next invocation"
    continue
  fi

  LOG="$LOGDIR/tc_${PURPOSE}.${N}.log"
  # Wall-clock walk time (run.py only, not the reset). date +%s, not $SECONDS:
  # this is #!/bin/sh. Appended as field 5 so $2/$4 readers keep working.
  start_ts=$(date +%s)
  ( cd "$ROOT" && "$PYTHON3" "$ROOT/framework/scripts/run.py" \
      --aut "$AUT" \
      --platform html \
      --url "$URL" \
      --system-interface "$SUT/model/system_interface_moodle.lnt" \
      --concrete-domain "$SUT/properties/concrete_domain.yml" \
      --type-description "$SUT/properties/type_description.yml" \
      --disruption-mapping "$SUT/properties/disruption_mapping.yml" \
      $HEADLESS_FLAG \
      --report ) \
      > "$LOG" 2>&1
  RC=$?
  elapsed=$(( $(date +%s) - start_ts ))

  VERDICT=$(sed 's/\x1b\[[0-9;]*m//g' "$LOG" \
            | grep -oE "^Verdict: [A-Z]+" | head -1 | awk '{print $2}')
  VERDICT="${VERDICT:-NONE}"

  UNCONFIRMED="-"
  if grep -q "injection FAILED or was not confirmed\|PRE-injection failed\|POISONED" "$LOG"; then
    UNCONFIRMED="UNCONFIRMED"
  fi

  printf "%s\t%s\t%s\t%s\t%s\n" "$N" "$VERDICT" "$RC" "$UNCONFIRMED" "$elapsed" >> "$RESULTS"
  echo "   verdict: $VERDICT (exit $RC) $UNCONFIRMED ${elapsed}s"
  DONE_NOW=$((DONE_NOW + 1))
done

echo "======================================================================"
echo "walked $DONE_NOW variant(s) this invocation. results -> $RESULTS"
echo "per-variant logs -> $LOGDIR/"
echo
echo "tally (all recorded results so far, including earlier invocations):"
awk -F'\t' '{print $2, $4}' "$RESULTS" | sort | uniq -c
