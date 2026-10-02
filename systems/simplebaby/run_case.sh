#!/bin/bash
# run_case.sh <purpose> -- seed a clean app, walk tc_<purpose>.aut, and persist
# everything the verdict rests on: the full walk log, this case's failure
# captures (own folder), and what both stores hold afterwards.
#
#     source systems/simplebaby/env.sh
#     bash systems/simplebaby/run_case.sh nominal_signed
#
#   AUT=<file>   walk this .aut instead of generated/tc/tc_<purpose>.aut (it is
#                installed under the canonical name for the run, because the
#                walker derives the target fault from the file name)
#   LOGFILE=...  the log to write (default generated/logs/<purpose>.log)
#   CAPDIR=...   the captures folder (default generated/captures/<purpose>)
set -o pipefail
NAME="${1:?usage: run_case.sh <purpose>}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SYS="$ROOT/systems/simplebaby"
TC="$SYS/generated/tc/tc_${NAME}.aut"
LOGFILE="${LOGFILE:-$SYS/generated/logs/${NAME}.log}"
CAPDIR="${CAPDIR:-$SYS/generated/captures/${NAME}}"
mkdir -p "$(dirname "$LOGFILE")" "$CAPDIR"
: "${DEV:?source systems/simplebaby/env.sh first}"
: "${DEVICE:=emulator-5556}"

RESTORE=""
if [ -n "$AUT" ] && [ "$AUT" != "$TC" ]; then
  cp "$TC" "$TC.canonical.bak"; cp "$AUT" "$TC"; RESTORE="$TC.canonical.bak"
fi
trap '[ -n "$RESTORE" ] && mv "$RESTORE" "$TC"' EXIT

cd "$ROOT"
export SB_EMAIL="sb$(date +%H%M%S)$$@example.com"
export CONCRETIZATION_DEBUG_DIR="$CAPDIR"
{ echo "=== $NAME  $(date '+%Y-%m-%d %H:%M:%S')  account $SB_EMAIL  aut $(head -1 "$TC")"; } > "$LOGFILE"
bash "$SYS/seed.sh" 2>&1 | tee -a "$LOGFILE"
[ "${PIPESTATUS[0]}" = "0" ] || { echo "RC=seed" | tee -a "$LOGFILE"; exit 3; }

PYTHONPATH=framework .venv/bin/python -u framework/scripts/run.py \
  --aut "$TC" --platform android \
  --system-interface "$SYS/model/system_interface_simplebaby.lnt" \
  --concrete-domain "$SYS/properties/concrete_domain.yml" \
  --type-description "$SYS/properties/type_description.yml" \
  --disruption-mapping "$SYS/properties/disruption_mapping.yml" \
  --device-config "$DEV" --timeout "${TIMEOUT:-15}" --verbose --report \
  2>&1 | tee -a "$LOGFILE"
RC=${PIPESTATUS[0]}
echo "RC=$RC" | tee -a "$LOGFILE"

{
  echo "--- stores after the run ($(date '+%H:%M:%S')):"
  echo "supabase rows of THIS account ($SB_EMAIL): feeding_logs / sleep_logs / children:"
  docker exec -i supabase_db_SimpleBaby psql -U postgres -d postgres -tAc "SELECT (SELECT count(*) FROM feeding_logs f JOIN children c ON c.id=f.child_id JOIN auth.users u ON u.id=c.user_id WHERE u.email='$SB_EMAIL'), (SELECT count(*) FROM sleep_logs f JOIN children c ON c.id=f.child_id JOIN auth.users u ON u.id=c.user_id WHERE u.email='$SB_EMAIL'), (SELECT count(*) FROM children c JOIN auth.users u ON u.id=c.user_id WHERE u.email='$SB_EMAIL')" 2>&1
  echo "feeding rows of this account (item_name tail, time):"
  docker exec -i supabase_db_SimpleBaby psql -U postgres -d postgres -tAc "SELECT right(f.item_name, 12), f.feeding_time FROM feeding_logs f JOIN children c ON c.id=f.child_id JOIN auth.users u ON u.id=c.user_id WHERE u.email='$SB_EMAIL' ORDER BY f.created_at" 2>&1
  echo "device store (guest keys, length):"
  adb -s "$DEVICE" shell "sqlite3 /data/data/com.anonymous.bt_sdk53/databases/RKStorage \"SELECT key, length(value) FROM catalystLocalStorage WHERE key LIKE 'sb:%'\"" 2>&1 | tr -d '\r'
  echo "device key entries: $(adb -s "$DEVICE" shell "grep -c key_v1-ENCRYPTION_KEY /data/data/com.anonymous.bt_sdk53/shared_prefs/SecureStore.xml" 2>&1 | tr -d '\r')"
  echo "fault triggers left: $(docker exec -i supabase_db_SimpleBaby psql -U postgres -d postgres -tAc "SELECT count(*) FROM pg_trigger WHERE tgname LIKE 'fault_%'" 2>&1)"
} 2>&1 | tee -a "$LOGFILE"
echo "--- verdict:"; sed 's/\x1b\[[0-9;]*m//g' "$LOGFILE" | grep -E 'Verdict:|Status:|HARNESS FAILURE' | tail -2
exit $RC
