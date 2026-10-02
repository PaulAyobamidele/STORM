#!/bin/sh
# seed.sh -- put SimpleBaby back to a clean first launch and PROVE it: every
# fault undone, the app cleared (account, device key, local store), the app on
# its welcome screen. Safe to run twice. The SI creates the account (or guest)
# and the child itself, so nothing is invented here.
set -e
DEVICE="${DEVICE:-emulator-5556}"
PKG=com.anonymous.bt_sdk53
A="adb -s $DEVICE"
DB="docker exec -i supabase_db_SimpleBaby psql -U postgres -d postgres -tAc"

$A shell am force-stop "$PKG"
$A shell rm -f /data/local/tmp/fault_ballast /data/local/tmp/fault_doze_state
$A shell dumpsys deviceidle unforce >/dev/null 2>&1 || true
$A shell svc wifi enable >/dev/null 2>&1 || true
$A shell svc data enable >/dev/null 2>&1 || true
docker start supabase_rest_SimpleBaby >/dev/null 2>&1 || true
docker unpause supabase_db_SimpleBaby >/dev/null 2>&1 || true
$DB "DROP TRIGGER IF EXISTS fault_abort_write ON feeding_logs; DROP FUNCTION IF EXISTS fault_abort_write(); DROP TRIGGER IF EXISTS fault_keep_row ON feeding_logs; DROP FUNCTION IF EXISTS fault_keep_row();" >/dev/null
$A shell pm clear "$PKG" | tr -d '\r'
$A shell am start -n "$PKG/.MainActivity" >/dev/null

i=0
until [ "$(docker inspect -f '{{.State.Health.Status}}' supabase_db_SimpleBaby 2>/dev/null)" = "healthy" ]; do
  i=$((i+1)); [ $i -gt 90 ] && break; sleep 1
done
bad=0
chk() { [ "$2" = "$3" ] || { echo "seed: NOT CLEAN: $1 is '$2', want '$3'" >&2; bad=1; }; }
chk "fault triggers" "$($DB "SELECT count(*) FROM pg_trigger WHERE tgname LIKE 'fault_%'")" "0"
chk "db paused" "$(docker inspect -f '{{.State.Paused}}' supabase_db_SimpleBaby)" "false"
chk "rest running" "$(docker inspect -f '{{.State.Running}}' supabase_rest_SimpleBaby)" "true"
chk "wifi" "$($A shell settings get global wifi_on | tr -d '\r')" "1"
chk "ballast" "$($A shell 'test -f /data/local/tmp/fault_ballast && echo yes || echo no' | tr -d '\r')" "no"
chk "device key" "$($A shell "grep -c key_v1-ENCRYPTION_KEY /data/data/$PKG/shared_prefs/SecureStore.xml 2>/dev/null || echo 0" | tr -d '\r' | head -1)" "0"
chk "guest keys" "$($A shell "sqlite3 /data/data/$PKG/databases/RKStorage \"SELECT count(*) FROM catalystLocalStorage WHERE key LIKE 'sb:%'\" 2>/dev/null || echo 0" | tr -d '\r' | head -1)" "0"
i=0
until $A shell dumpsys activity activities 2>/dev/null | grep -q "topResumedActivity.*$PKG"; do
  i=$((i+1)); [ $i -gt 30 ] && { echo "seed: the app did not come to the foreground" >&2; bad=1; break; }; sleep 1
done
[ $bad -eq 0 ] || exit 1
echo "seed: $PKG cleared on $DEVICE, no fault in place, app on its welcome screen"
