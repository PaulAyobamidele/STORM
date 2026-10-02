#!/usr/bin/env bash
# run_variants.sh -- walk EVERY extracted test case of one purpose and write
# one row per variant to systems/medtimer/variants_<purpose>.log, the file
# framework/scripts/eval_tables.py builds the evaluation table from.
#
#     source systems/medtimer/env.sh
#     bash systems/medtimer/run_variants.sh db_abort
#     ONLY="1 3" bash systems/medtimer/run_variants.sh db_abort
#
# Row schema (tab-separated, fixed for the whole campaign):
#     VARIANT  STATES  TRANSITIONS  TIME_S  VERDICT  NOTE
# STATES / TRANSITIONS come from the variant's own .aut header
# (`des (init, TRANSITIONS, STATES)`); TIME_S is the walk's wall time;
# VERDICT is PASS, FAIL or INCONC as the walk printed it. run.py's exit code 2,
# or a walk that ended without a verdict, is recorded UNEXECUTABLE (one word):
# it is not a verdict, it is a walk to repeat, and eval_tables keeps it out of
# every verdict total. Rows are written by framework/scripts/sweep_row.sh, the
# one format every SUT shares; TIME_S is bash's SECONDS around the walk.
#
# Resuming APPENDS: variants already in the log are skipped, a finished row
# is never overwritten. The header records the git revision and a dirty flag;
# a dirty framework/ is saved as a diff beside the log.
# Per variant: the seed log, the walk log and the failure captures live in
# generated/variant_logs/<purpose>/ (v<N>.seed.log, v<N>.log, v<N>_captures/).
set -u
NAME="${1:?usage: run_variants.sh <purpose>}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
. "$ROOT/framework/scripts/sweep_row.sh"
SYS="$ROOT/systems/medtimer"
VDIR="$SYS/generated/tc/variants/$NAME"
TC="$SYS/generated/tc/tc_${NAME}.aut"
LOGS="$SYS/generated/variant_logs/$NAME"; mkdir -p "$LOGS"
ROWS="$SYS/variants_${NAME}.log"
: "${DEV:?source systems/medtimer/env.sh first}"
: "${DEVICE:=emulator-5554}"

ls "$VDIR"/tc_"$NAME".*.aut >/dev/null 2>&1 || { echo "no variants under $VDIR" >&2; exit 1; }
avd=$(adb -s "$DEVICE" emu avd name 2>/dev/null | head -1 | tr -d '\r')
# medtimer_test2 is a twin (same system image, same APK bytes) for a second runner
case "$avd" in medtimer_test|medtimer_test2) ;; *) echo "device $DEVICE runs AVD '$avd', not medtimer_test(2)" >&2; exit 1 ;; esac

rev=$(git -C "$ROOT" rev-parse --short HEAD)
dirty=$(git -C "$ROOT" status --porcelain -- framework systems/medtimer/model systems/medtimer/properties | head -1)
if [ ! -s "$ROWS" ]; then
  sweep_header MedTimer "$NAME" "rev $rev${dirty:+ (dirty)}" > "$ROWS"
else
  echo "# resumed $(date '+%Y-%m-%d %H:%M') -- rev $rev${dirty:+ (dirty)}" >> "$ROWS"
fi
[ -n "$dirty" ] && git -C "$ROOT" diff -- framework/ > "$LOGS/framework.$(date +%Y%m%d-%H%M).diff"

cp "$TC" "$TC.canonical.bak"
trap 'mv "$TC.canonical.bak" "$TC"' EXIT
for aut in $(ls "$VDIR"/tc_"$NAME".*.aut | sort -t. -k2 -n); do
  i=$(echo "$aut" | sed -e 's/.*\.\([0-9][0-9]*\)\.aut$/\1/')
  if [ -n "${ONLY:-}" ]; then echo " $ONLY " | grep -q " $i " || continue; fi
  if awk -F'\t' -v v="$i" '$1 == v { found = 1 } END { exit !found }' "$ROWS"; then
    echo "v$i already recorded, skipped"; continue
  fi
  # The fixture's doses are at 11:56-11:59 PM TONIGHT: a walk that runs across
  # them would see doses fall due, or (after midnight) move to tomorrow. No
  # case starts between 23:35 and 00:01.
  while [ "$(date +%H%M)" -ge 2335 ] || [ "$(date +%H%M)" -lt 0001 ]; do sleep 30; done
  cp "$aut" "$TC"
  sh "$SYS/seed.sh" > "$LOGS/v$i.seed.log" 2>&1
  export CONCRETIZATION_DEBUG_DIR="$LOGS/v${i}_captures"
  SECONDS=0
  ( cd "$ROOT" && PYTHONPATH=framework .venv/bin/python -u framework/scripts/run.py \
      --aut "$TC" --platform android \
      --system-interface "$SYS/model/system_interface_medtimer.lnt" \
      --concrete-domain "$SYS/properties/concrete_domain.yml" \
      --type-description "$SYS/properties/type_description.yml" \
      --disruption-mapping "$SYS/properties/disruption_mapping.yml" \
      --device-config "$DEV" --timeout "${TIMEOUT:-15}" --verbose --report ) > "$LOGS/v$i.log" 2>&1
  rc=$?
  secs=$SECONDS
  {
    echo "--- database after the walk:"
    adb -s "$DEVICE" shell "run-as com.futsch1.medtimer sqlite3 databases/medTimer \"SELECT medicineId, medicineName, amount FROM Medicine; SELECT reminderEventId, reminderId, status, stockHandled, stockBefore, stockAfter FROM ReminderEvent;\"" 2>&1 | tr -d '\r'
  } >> "$LOGS/v$i.log"
  v=$(sweep_verdict "$rc" "$LOGS/v$i.log")
  note=""
  if [ "$v" = UNEXECUTABLE ]; then
    note=$(sed 's/\x1b\[[0-9;]*m//g' "$LOGS/v$i.log" | grep -m1 -oE '(UNEXECUTABLE \([^)]*\)|HARNESS FAILURE[^.]*|WebDriverException[^.]*)' | tr '\t' ' ' | cut -c1-80)
    note="${note:-no verdict (exit $rc)}"
  fi
  sweep_row "$i" "$aut" "$secs" "$v" "$note" | tee -a "$ROWS"
done
