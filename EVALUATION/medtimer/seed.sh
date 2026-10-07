#!/bin/sh
# seed.sh -- deterministic reset of MedTimer before a run.
#
#     source EVALUATION/foodyou/env.sh        # adb on PATH (or set ANDROID_HOME)
#     sh EVALUATION/medtimer/seed.sh          # DEVICE=emulator-5554 by default
#
# MedTimer ships no data and the debug build has no onboarding, so the reset
# is a clean slate: clear the app's data, grant the one runtime permission the
# first launch would otherwise ask for (POST_NOTIFICATIONS, MainActivity.kt:144-152),
# and prove the store is gone. The fixture itself (one medicine, three units,
# one late reminder) is created by the System Interface's prelude inside the
# walk, so nothing is invented here that the tester later asserts.
set -e
PKG=com.futsch1.medtimer
DEVICE="${DEVICE:-emulator-5554}"
ADB="${ADB:-adb}"
command -v "$ADB" >/dev/null 2>&1 || ADB="${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}/platform-tools/adb"

"$ADB" -s "$DEVICE" shell am force-stop "$PKG"
"$ADB" -s "$DEVICE" shell pm clear "$PKG" | tr -d '\r'
"$ADB" -s "$DEVICE" shell pm grant "$PKG" android.permission.POST_NOTIFICATIONS
# a fault left behind by an interrupted run must not survive the reset
"$ADB" -s "$DEVICE" shell "run-as $PKG rm -f files/fault_ballast" >/dev/null 2>&1 || true
if "$ADB" -s "$DEVICE" shell "run-as $PKG ls databases/medTimer" >/dev/null 2>&1; then
  echo "seed: databases/medTimer still present after pm clear" >&2
  exit 1
fi
echo "seed: $PKG cleared on $DEVICE, POST_NOTIFICATIONS granted, store absent"
