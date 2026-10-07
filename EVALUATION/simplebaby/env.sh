# env.sh -- SimpleBaby concretization environment. SOURCE it, do not execute:
#
#     source EVALUATION/simplebaby/env.sh
#
# Same shell as run_case.sh / run_variants.sh / seed.sh. Puts adb and the
# emulator on PATH (Homebrew SDK), pins the run to emulator-5556 with its own
# Appium system port (a FoodYou or MedTimer run on :5554 can never collide),
# turns adbd into root (the release build is not debuggable; the injections
# read /data/data directly) and reports what is actually up.
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
export DEVICE="${DEVICE:-emulator-5556}"
export ANDROID_SERIAL="$DEVICE"
export APPIUM_PORT="${APPIUM_PORT:-4723}"
export SB_SYSTEM_PORT="${SB_SYSTEM_PORT:-8201}"
export SB_PKG=com.anonymous.bt_sdk53
export DEV="{\"appPackage\":\"$SB_PKG\",\"appActivity\":\".MainActivity\",\"deviceName\":\"$DEVICE\",\"udid\":\"$DEVICE\",\"systemPort\":$SB_SYSTEM_PORT,\"server_url\":\"http://127.0.0.1:$APPIUM_PORT\"}"

_dev_state=$(adb -s "$DEVICE" get-state 2>/dev/null || echo "absent")
if [ "$_dev_state" = "device" ]; then
  adb -s "$DEVICE" root >/dev/null 2>&1
  adb -s "$DEVICE" wait-for-device
  _uid=$(adb -s "$DEVICE" shell id -u 2>/dev/null | tr -d '\r')
  _app=$(adb -s "$DEVICE" shell pm list packages 2>/dev/null | grep -c "$SB_PKG")
  _dbg=$(adb -s "$DEVICE" shell dumpsys package "$SB_PKG" 2>/dev/null | grep -c "DEBUGGABLE")
else
  _uid=""; _app=0; _dbg=0
fi
_appium=$(curl -s --max-time 2 "http://127.0.0.1:$APPIUM_PORT/status" | grep -o '"ready":true' || echo "no answer")
_sb=$(docker ps --filter name=supabase_db_SimpleBaby --filter status=running -q 2>/dev/null | wc -l | tr -d ' ')
echo "simplebaby env: device $DEVICE = $_dev_state, adbd uid=${_uid:-?}; app installed=$_app debuggable=$_dbg; appium :$APPIUM_PORT = $_appium; supabase db up=$_sb"
[ "$_dev_state" = "device" ] || echo "  !! the device is not attached: start simplebaby_test on port 5556"
[ "$_uid" = "0" ] || echo "  !! adbd is not root: the injections need it"
[ "$_app" = "1" ] || echo "  !! $SB_PKG is not installed on $DEVICE"
[ "$_dbg" = "0" ] || echo "  !! this is a debug build: build the release variant (no LogBox, no dev launcher)"
[ "$_appium" = '"ready":true' ] || echo "  !! Appium is not answering on :$APPIUM_PORT"
[ "$_sb" = "1" ] || echo "  !! the Supabase db container is not running (supabase start)"
