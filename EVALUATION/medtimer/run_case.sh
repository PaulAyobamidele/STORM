#!/bin/sh
# run_case.sh -- run ONE generated test case against the emulator, from a
# clean app state, with its log kept.
#
#     source EVALUATION/medtimer/env.sh
#     sh EVALUATION/medtimer/run_case.sh nominal            # tc_nominal.aut
#     sh EVALUATION/medtimer/run_case.sh db_abort           # tc_db_abort.aut
#     AUT=path/to/variant.aut sh EVALUATION/medtimer/run_case.sh db_abort   # a variant, under the canonical name
#
# The concretizer derives the TARGET fault from the .aut file name, so a
# variant is copied under the canonical name for its run and the canonical
# file is put back afterwards. Every run starts with seed.sh (pm clear +
# permission grant); the System Interface's prelude then builds the fixture.
# The log goes to generated/logs/<name>.log; the verdict line is the last
# "Verdict:" in it.
set -e
NAME="${1:?usage: run_case.sh <purpose>   (tc_<purpose>.aut)}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SYS="$ROOT/EVALUATION/medtimer"
TC="$SYS/Test_Cases/tc_${NAME}.aut"
LOGS="$SYS/generated/logs"; mkdir -p "$LOGS"
: "${DEV:?source EVALUATION/medtimer/env.sh first}"
: "${DEVICE:=emulator-5554}"

RESTORE=""
if [ -n "$AUT" ] && [ "$AUT" != "$TC" ]; then
  cp "$TC" "$TC.canonical.bak"; cp "$AUT" "$TC"; RESTORE="$TC.canonical.bak"
fi
trap '[ -n "$RESTORE" ] && mv "$RESTORE" "$TC"' EXIT

cd "$ROOT"
sh "$SYS/seed.sh"
PYTHONPATH=framework .venv/bin/python -u framework/scripts/run.py \
  --aut "$TC" --platform android \
  --system-interface "$SYS/model/system_interface_medtimer.lnt" \
  --concrete-domain "$SYS/properties/concrete_domain.yml" \
  --type-description "$SYS/properties/type_description.yml" \
  --disruption-mapping "$SYS/properties/disruption_mapping.yml" \
  --device-config "$DEV" --timeout "${TIMEOUT:-15}" --verbose --report \
  2>&1 | tee "$LOGS/${NAME}.log"
echo "--- verdict:"; grep -E 'Verdict:|Status:|HARNESS FAILURE' "$LOGS/${NAME}.log" | tail -2
# the persisted state after the walk, as evidence beside the verdict
{
  echo "--- database after the run ($(date '+%H:%M:%S')):"
  adb -s "$DEVICE" shell "run-as com.futsch1.medtimer sqlite3 databases/medTimer \"SELECT medicineId, medicineName, amount, unit, cannotBeSkipped FROM Medicine; SELECT reminderEventId, reminderId, status, stockHandled, stockBefore, stockAfter FROM ReminderEvent;\"" 2>&1 | tr -d '\r'
  echo "--- app process: $(adb -s "$DEVICE" shell pidof com.futsch1.medtimer 2>/dev/null | tr -d '\r')"
} | tee -a "$LOGS/${NAME}.log"
