#!/bin/sh
# check_env.sh -- refuse a sweep unless everything a verdict depends on is in
# place: the device, root, the RELEASE build, Appium, the Supabase stack
# healthy and fault-free, and the host can reach the REST API.
. "$(cd "$(dirname "$0")" && pwd)/env.sh" >/dev/null
bad=0
fail() { echo "check_env: $1" >&2; bad=1; }
[ "$(adb -s "$DEVICE" get-state 2>/dev/null)" = "device" ] || fail "device $DEVICE is not attached"
[ "$(adb -s "$DEVICE" shell id -u 2>/dev/null | tr -d '\r')" = "0" ] || fail "adbd is not root"
adb -s "$DEVICE" shell pm list packages 2>/dev/null | grep -q "$SB_PKG" || fail "$SB_PKG is not installed"
adb -s "$DEVICE" shell dumpsys package "$SB_PKG" 2>/dev/null | grep -q DEBUGGABLE && fail "debug build installed; build the release variant"
curl -s --max-time 2 "http://127.0.0.1:$APPIUM_PORT/status" | grep -q '"ready":true' || fail "Appium is not ready on :$APPIUM_PORT"
i=0
until [ "$(docker inspect -f '{{.State.Health.Status}}' supabase_db_SimpleBaby 2>/dev/null)" = "healthy" ]; do
  i=$((i+1)); [ $i -gt 90 ] && break; sleep 1
done
[ "$(docker inspect -f '{{.State.Health.Status}}' supabase_db_SimpleBaby 2>/dev/null)" = "healthy" ] || fail "database container is not healthy after 90 s"
i=0
until [ "$(curl -s -o /dev/null -w '%{http_code}' -H "apikey: $(sed -n 's/^EXPO_PUBLIC_SUPABASE_KEY=//p' "$(cd "$(dirname "$0")" && pwd)/sut/simplebaby/.env")" 'http://127.0.0.1:54321/rest/v1/feeding_logs?select=id')" = "200" ]; do
  i=$((i+1)); [ $i -gt 60 ] && break; sleep 1
done
KEY=$(sed -n 's/^EXPO_PUBLIC_SUPABASE_KEY=//p' "$(cd "$(dirname "$0")" && pwd)/sut/simplebaby/.env")
[ "$(curl -s -o /dev/null -w '%{http_code}' -H "apikey: $KEY" 'http://127.0.0.1:54321/rest/v1/feeding_logs?select=id')" = "200" ] || fail "REST API does not answer 200"
[ "$(docker exec -i supabase_db_SimpleBaby psql -U postgres -d postgres -tAc "SELECT count(*) FROM pg_trigger WHERE tgname LIKE 'fault_%'")" = "0" ] || fail "a fault trigger is in place"
[ "$(adb -s "$DEVICE" shell settings get global wifi_on | tr -d '\r')" = "1" ] || fail "the device network is off"
[ $bad -eq 0 ] && echo "check_env: ready (release build, root, Appium, Supabase healthy and fault-free)"
exit $bad
