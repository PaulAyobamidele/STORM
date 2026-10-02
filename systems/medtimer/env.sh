# env.sh -- MedTimer concretization environment. SOURCE it, do not execute:
#
#     source systems/medtimer/env.sh
#
# Must be sourced in the SAME shell that runs run_case.sh / run.py / seed.sh.
# It puts adb and the emulator on PATH (the SDK is a Homebrew install, not the
# Android Studio default), names the device and the Appium port, and reports
# what is actually up so a stale value fails loudly here rather than three
# minutes into a run.
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
export DEVICE="${DEVICE:-emulator-5554}"
export APPIUM_PORT="${APPIUM_PORT:-4723}"
# --device-config is a JSON STRING (run.py does json.loads on it)
export DEV="{\"appPackage\":\"com.futsch1.medtimer\",\"appActivity\":\"com.futsch1.medtimer.MainActivity\",\"deviceName\":\"$DEVICE\",\"udid\":\"$DEVICE\",\"server_url\":\"http://127.0.0.1:$APPIUM_PORT\"}"

_dev_state=$(adb -s "$DEVICE" get-state 2>/dev/null || echo "absent")
_appium=$(curl -s --max-time 2 "http://127.0.0.1:$APPIUM_PORT/status" | grep -o '"ready":true' || echo "no answer")
echo "medtimer env: device $DEVICE = $_dev_state; appium :$APPIUM_PORT = $_appium"
[ "$_dev_state" = "device" ] || echo "  !! the device is not attached: start the emulator (medtimer_test)"
[ "$_appium" = '"ready":true' ] || echo "  !! Appium is not answering on :$APPIUM_PORT (start it with ANDROID_HOME exported)"
