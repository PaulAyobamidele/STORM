# env.sh -- FoodYou concretization environment. SOURCE it, do not execute:
#
#     source EVALUATION/foodyou/env.sh
#
# Must be sourced in the SAME shell that runs run.py / run_matrix.sh /
# seed_foods.sh. Sourcing it in one terminal tab and running the test in another
# is the failure that produces both "no adb device reachable" (seed_foods.sh
# cannot find adb on PATH) and a connection refused on port 4723 (run.py sees an
# empty $DEV, so json.loads falls back to {} and the default Appium port) --
# even while the emulator and Appium are perfectly healthy.

# The SDK is a homebrew command-line-tools install, not the Android Studio
# default (~/Library/Android/sdk), so nothing is on PATH by default.
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"

# --device-config is a JSON STRING, not a file path (run.py:119 does
# json.loads(args.device_config or "{}")). server_url must match the port the
# Appium server is actually listening on. THIS DRIFTS -- it was 4725 in August
# (that is what the happy-path logs from 2026-08-23 ran against) and is 4723 as
# of 2026-09-01 (confirmed live: `lsof -nP -iTCP -sTCP:LISTEN | grep 472`). The
# self-check below reports the live port on every source; if it disagrees with
# this value, fix THIS value, don't trust the literal here blindly.
export DEV='{"appPackage":"com.maksimowiczm.foodyou","appActivity":".app.infrastructure.android.MainActivity","deviceName":"emulator-5554","server_url":"http://127.0.0.1:4723"}'

# --- report what is actually up, so a stale assumption fails loudly here ----
if command -v adb > /dev/null 2>&1 ; then
	echo "adb:      $(adb devices | sed -n 2p)"
else
	echo "adb:      NOT ON PATH (check \$ANDROID_HOME)" >&2
fi

APPIUM_PORT=$(echo "$DEV" | sed -n 's/.*127\.0\.0\.1:\([0-9]*\).*/\1/p')
if curl -s --max-time 3 "http://127.0.0.1:${APPIUM_PORT}/status" > /dev/null 2>&1 ; then
	echo "appium:   ready on ${APPIUM_PORT}"
else
	echo "appium:   NOT RESPONDING on ${APPIUM_PORT} -- start it with 'appium -p ${APPIUM_PORT}'" >&2
fi
