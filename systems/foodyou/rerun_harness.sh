#!/usr/bin/env bash
# rerun_harness.sh -- re-run the 18 harness cases from HANDOVER.md §6 in one go.
#
#     source systems/foodyou/env.sh
#     bash systems/foodyou/rerun_harness.sh
#
# These 18 never produced a verdict for APPARATUS reasons -- step-budget
# exhaustion, Appium session death, a weak manifestation probe, one empty screen
# capture -- not because the SUT did anything. All three fixes are in:
#
#   step budget          algorithm.py:2332   MAX_STEPS = max(500, 4*|transitions|)
#   Appium reconnect     executors.py:1725
#   ballast probe        fault_injector.py:201
#
# so the question this run answers is narrow: do they produce a verdict NOW.
#
# WHY REPEATS=3 AND NOT 1. RESULTS_campaign.md §11 lists single-repetition as an
# open threat to validity: the 793-case sweep ran once and no flakiness
# measurement exists. At REPEATS=1 investigate_variants.sh reports every row
# STABLE by construction -- one run cannot disagree with itself -- so the
# stability column would carry no information precisely where it matters most.
# These are the cases most likely to be flaky; 3 repeats is the cheapest real
# evidence available.
#
# WHY THE ENV CHECK IS NOT SKIPPED BETWEEN PURPOSES. ue1_kill and storage_full
# leave the device in states later purposes inherit, and EXTAPI_FAIL restores the
# radios only on the normal path. A mid-run environment failure that goes
# unnoticed produces exactly the sweep this project already had to throw away.
# The per-purpose check costs seconds and makes that failure loud.
set -u

cd "$(dirname "$0")/../.." || exit 1
: "${DEV:?source systems/foodyou/env.sh first (SAME shell -- see env.sh header)}"

REPEATS="${REPEATS:-3}"
STAMP=$(date '+%Y%m%d-%H%M%S')
MASTER="systems/foodyou/rerun_harness.${STAMP}.log"

# Fail fast, once. investigate_variants.sh re-checks per purpose (device state
# drifts between them), but without this gate a down emulator produces six
# identical NOT READY blocks and a run that looks like it did something.
if [ "${SKIP_ENV_CHECK:-0}" != "1" ]; then
	if ! bash systems/foodyou/check_env.sh; then
		echo "refusing to start: the environment cannot support the run." >&2
		echo "  bash systems/foodyou/boot_emulator.sh    # emulator" >&2
		echo "  appium -p \${APPIUM_PORT:-4723}           # in its own terminal" >&2
		exit 1
	fi
fi

# Only logs written AFTER this marker belong to this run. Without it the summary
# greps whatever investigate_*.log happens to be on disk -- which on 2026-09-04
# reported five verdict rows from August under a run where nothing executed.
# A stale row is worse than no row: it is indistinguishable from a real one.
MARKER=$(mktemp) ; trap 'rm -f "$MARKER"' EXIT

# purpose | variants  -- HANDOVER.md §6, both classes merged per purpose.
# NB: the section header says 17; the list enumerates 18. storage_full v25 was
# added by the §1 set-difference check and the count was never updated.
ROWS=(
  "happy|2"
  "input_invalid|11 23"
  "cache_stale|6 7 17"
  "ue1_kill|22 35 53"
  "disruption_db|22 35"
  "storage_full|11 14 17 22 25 35 48"
)

{
  echo "# FoodYou harness re-run -- HANDOVER.md §6 -- $(date '+%Y-%m-%d %H:%M')"
  echo "# repeats=$REPEATS  revision=$(git rev-parse --short HEAD 2>/dev/null || echo UNKNOWN)"
  echo "# dirty=$(git diff --quiet 2>/dev/null && echo no || echo YES-uncommitted-changes)"
  echo
} | tee "$MASTER"

# A purpose that fails must not abort the rest: these are independent cases, and
# losing the five that would have run is worse than one missing row.
rc_any=0
APPIUM_PORT=$(echo "$DEV" | sed -n 's/.*127\.0\.0\.1:\([0-9]*\).*/\1/p')
APPIUM_PORT="${APPIUM_PORT:-4723}"

for row in "${ROWS[@]}"; do
  IFS='|' read -r purpose variants <<< "$row"
  echo "=== $purpose : $variants ===" | tee -a "$MASTER"

  # --- restore connectivity BETWEEN purposes ------------------------------
  # The network-disabling disruptions restore the radios only on the normal
  # path, so a purpose that dies mid-walk leaves the device offline and every
  # LATER purpose refuses -- which is what happened on 2026-09-04: input_invalid
  # died at session creation and took cache_stale, ue1_kill, disruption_db and
  # storage_full (15 cases) down with it.
  #
  # Safe here and only here: this runs BETWEEN purposes, never inside a live
  # disruption, and the radios are taken down by the fault injector rather than
  # by FoodYou -- so restoring them cannot mask an app-level finding. Logged
  # loudly because silently repairing apparatus state is how a sweep starts
  # describing the laptop.
  air=$(adb shell settings get global airplane_mode_on 2>/dev/null | tr -d '\r')
  if [ "$air" = "1" ] || ! adb shell ping -c1 -W2 1.1.1.1 2>/dev/null | grep -q "bytes from"; then
    echo "  [restore] device offline before $purpose -- re-enabling radios" | tee -a "$MASTER"
    adb shell settings put global airplane_mode_on 0 >/dev/null 2>&1
    adb shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false >/dev/null 2>&1
    adb shell svc wifi enable >/dev/null 2>&1
    adb shell svc data enable >/dev/null 2>&1
    sleep 5
  fi

  # --- is Appium still alive? ---------------------------------------------
  # A dead Appium fails at NEW_SESSION with RemoteDisconnected, which classifies
  # as HARNESS-FAILURE for every remaining case. Stopping is strictly better than
  # burning the rest of the list on an apparatus that is already gone -- an
  # unmeasured case can be re-run, but the log of a doomed one is just noise.
  if ! curl -s --max-time 5 "http://127.0.0.1:${APPIUM_PORT}/status" >/dev/null 2>&1; then
    echo "!!! Appium is not responding on ${APPIUM_PORT} -- ABORTING before $purpose." | tee -a "$MASTER"
    echo "    Remaining purposes are unmeasured, not failed. Restart it with:" | tee -a "$MASTER"
    echo "      appium -p ${APPIUM_PORT}" | tee -a "$MASTER"
    rc_any=1
    break
  fi
  REPEATS="$REPEATS" bash systems/foodyou/investigate_variants.sh \
      "$purpose" $variants 2>&1 | tee -a "$MASTER"
  rc=${PIPESTATUS[0]}
  if [ "$rc" -ne 0 ]; then
    echo "!!! $purpose exited $rc -- continuing with the next purpose" | tee -a "$MASTER"
    rc_any=1
  fi
  echo | tee -a "$MASTER"
done

{
  echo "================================================================"
  echo "verdict rows -- THIS run only (logs newer than the start marker):"
  echo
  # The '=' rows are investigate_variants.sh's per-variant stability lines: a
  # FLAKY answers the §11 single-repetition threat directly, a STABLE FAIL sends
  # the case back for diagnosis. Every row is labelled with its purpose -- a bare
  # variant number is ambiguous across purposes, and deduping unlabelled rows
  # silently merges different cases that share an index.
  any_rows=0
  for row in "${ROWS[@]}"; do
    IFS='|' read -r purpose _ <<< "$row"
    LOG="systems/foodyou/investigate_${purpose}.log"
    if [ ! -f "$LOG" ]; then
      printf "  %-16s (no log written -- purpose did not run)\n" "$purpose"
      continue
    fi
    if [ ! "$LOG" -nt "$MARKER" ]; then
      printf "  %-16s STALE (last written %s) -- NOT from this run, ignored\n" \
             "$purpose" "$(date -r "$LOG" '+%Y-%m-%d %H:%M' 2>/dev/null || echo unknown)"
      continue
    fi
    # Captured first: `grep | sed && any_rows=1` would set the flag even on no
    # match, because sed succeeds on empty input.
    rows=$(grep '^[0-9][0-9]*  *=' "$LOG" 2>/dev/null)
    if [ -n "$rows" ]; then
      echo "$rows" | sed "s/^/  $(printf '%-16s' "$purpose")/"
      any_rows=1
    else
      printf "  %-16s (log written, but no verdict row -- check the master log)\n" "$purpose"
    fi
  done
  [ "$any_rows" -eq 0 ] && echo "  (none -- no purpose produced a verdict row this run)"
  echo
  [ "$rc_any" -eq 0 ] && echo "all purposes completed" \
                      || echo "at least one purpose exited non-zero -- see above"
  echo "master log: $MASTER"
} | tee -a "$MASTER"
