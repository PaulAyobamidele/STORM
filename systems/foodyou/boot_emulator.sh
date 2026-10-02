#!/usr/bin/env bash
# boot_emulator.sh -- start the FoodYou emulator with working internet, and PROVE it.
#
#     source systems/foodyou/env.sh
#     bash systems/foodyou/boot_emulator.sh            # first AVD found
#     bash systems/foodyou/boot_emulator.sh Pixel_6_API_34
#
# The emulator already shares the Mac's connection: it sits behind a virtual
# router that NATs to the host, so nothing needs bridging. What actually breaks
# is narrower, and this script addresses each:
#
#   1. DNS. The emulator inherits the host's resolvers, which on macOS are often
#      a VPN's or a link-local address it cannot reach. Symptom: ping 1.1.1.1
#      works, ping by hostname does not. Fixed by passing -dns-server explicitly.
#   2. Radios left off. EXTAPI_FAIL injects `svc data disable ; svc wifi disable`
#      and only restores on the normal path, so an interrupted disruption run
#      leaves the device offline -- and every later run silently sees an
#      unreachable Open Food Facts. Re-enabled below.
#   3. Airplane mode, same story.
#
# NEVER add -wipe-data or -no-snapshot-load here. FoodYou must stay onboarded:
# seed_foods.sh writes to an existing database and run.py relaunches with
# noReset:true. Wiping means re-doing onboarding by hand before anything runs.
set -u

AVD="${1:-}"
DNS="${EMULATOR_DNS:-1.1.1.1,8.8.8.8}"
PKG=com.maksimowiczm.foodyou

if ! command -v emulator > /dev/null 2>&1; then
	echo "emulator not on PATH -- run 'source systems/foodyou/env.sh' first" >&2
	exit 1
fi

# macOS has no `timeout`, and a broken resolver makes a hostname ping block
# forever (-W bounds the wait for a reply, not the lookup).
OUT=$(mktemp); trap 'rm -f "$OUT"' EXIT
with_timeout() {
	secs="$1"; shift
	: > "$OUT"; "$@" > "$OUT" 2>&1 & pid=$!; i=0
	while kill -0 "$pid" 2>/dev/null; do
		[ "$i" -ge "$secs" ] && { kill -9 "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; return 124; }
		sleep 1; i=$((i + 1))
	done
	wait "$pid" 2>/dev/null
}

# --- 1. boot, unless one is already up -------------------------------------
# -dns-server is applied at BOOT ONLY. An emulator that is already running was
# started without it, so skipping the boot silently skips the DNS fix too -- and
# the script then reports a DNS failure it was supposed to prevent. Restart when
# the caller asks for it.
if [ "${FORCE_REBOOT:-0}" = "1" ] && with_timeout 10 adb shell true; then
	echo "FORCE_REBOOT=1 -- stopping the running emulator so -dns-server applies"
	adb emu kill > /dev/null 2>&1
	# `adb emu kill` returns immediately, but the process holds the AVD's .lock
	# files for a while after. Booting into that lock fails with "Running multiple
	# emulators with the same AVD", and the failure looks identical to a slow boot
	# from the outside -- so wait for the device to actually go away rather than
	# guessing at a sleep.
	echo -n "  waiting for it to release the AVD lock"
	i=0
	while adb devices 2>/dev/null | grep -q "emulator-.*device"; do
		[ "$i" -ge 30 ] && { echo; echo "  emulator did not exit after 30s; try: pkill -f qemu-system" >&2; break; }
		echo -n "."
		sleep 1
		i=$((i + 1))
	done
	sleep 2      # the lock file outlives the adb entry by a moment
	echo " done"
fi
if with_timeout 10 adb shell true; then
	echo "emulator already running -- skipping boot"
	echo "  NOTE: -dns-server was NOT applied (it is a boot-time flag). If DNS"
	echo "        fails below, restart with:"
	echo "        FORCE_REBOOT=1 EMULATOR_DNS=8.8.8.8 bash $0 ${AVD:-}"
else
	if [ -z "$AVD" ]; then
		AVD=$(emulator -list-avds | head -1)
	fi
	if [ -z "$AVD" ]; then
		echo "no AVD found. Create one in Android Studio, or:" >&2
		echo "  sdkmanager 'system-images;android-34;google_apis;arm64-v8a'" >&2
		echo "  avdmanager create avd -n foodyou -k 'system-images;android-34;google_apis;arm64-v8a'" >&2
		exit 1
	fi
	echo "booting AVD: $AVD  (dns=$DNS)"
	# -netdelay/-netspeed off any artificial throttling, which otherwise makes a
	# slow remote source indistinguishable from a broken one -- exactly the
	# distinction these tests are trying to draw.
	emulator -avd "$AVD" \
	         -dns-server "$DNS" \
	         -netdelay none -netspeed full \
	         > /tmp/emulator-"$AVD".log 2>&1 &
	echo "  log: /tmp/emulator-$AVD.log"

	# Bounded, and it says what it is waiting for. An unbounded row of dots is
	# indistinguishable from a crashed emulator, which is how the last attempt
	# looked stuck when the log had the answer all along.
	echo -n "waiting for device"
	adb wait-for-device
	i=0
	until [ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; do
		if [ "$i" -ge 150 ]; then          # 5 minutes
			echo
			echo "still not booted after 5 minutes. The emulator log has the reason:" >&2
			echo "    tail -40 /tmp/emulator-$AVD.log" >&2
			echo "  a stale AVD lock and a slow cold boot look the same from here." >&2
			exit 1
		fi
		[ $((i % 15)) -eq 0 ] && [ "$i" -gt 0 ] && \
			echo -n " [${i}s, bootanim=$(adb shell getprop init.svc.bootanim 2>/dev/null | tr -d '\r')]"
		echo -n "."
		sleep 2
		i=$((i + 2))
	done
	echo " booted"
fi

# --- 2. undo anything that left the device offline --------------------------
echo "restoring connectivity state:"
adb shell settings put global airplane_mode_on 0 > /dev/null 2>&1
adb shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false > /dev/null 2>&1
adb shell svc wifi enable  > /dev/null 2>&1
adb shell svc data enable  > /dev/null 2>&1
echo "  airplane_mode_on = $(adb shell settings get global airplane_mode_on | tr -d '\r')  (want 0)"
echo "  wifi/data        = enabled"
sleep 3   # let the stack settle before testing it

# --- 3. prove it, layer by layer -------------------------------------------
# Separated on purpose: "no internet" and "no DNS" need different fixes, and a
# single pass/fail cannot tell you which you have.
fail=0

echo
echo "connectivity:"
# WAS `ping`. Fixed 2026-09-01: campus/eduroam-style networks commonly block
# ICMP as policy while leaving real traffic untouched, so ping reported this
# device "offline" while `nc -w 5 1.1.1.1 443` succeeded from both the Mac and
# the emulator in the same session. TCP to the port the app actually uses asks
# the question that matters instead of one ICMP happens to answer differently
# on this network. toybox nc syntax: `-w SECS`, not `-z`.
with_timeout 15 adb shell "echo | nc -w 5 1.1.1.1 443 >/dev/null 2>&1 && echo TCP_OK"
if grep -q "TCP_OK" "$OUT" 2>/dev/null; then
	echo "  [ok]   raw IP      (TCP to 1.1.1.1:443)"
else
	echo "  [FAIL] raw IP      -- the emulator has no route out at all"
	fail=1
fi

with_timeout 15 adb shell "echo | nc -w 5 world.openfoodfacts.org 443 >/dev/null 2>&1 && echo TCP_OK"
rc=$?
if grep -q "TCP_OK" "$OUT" 2>/dev/null; then
	echo "  [ok]   DNS         (TCP to world.openfoodfacts.org:443)"
elif [ "$rc" -eq 124 ]; then
	echo "  [FAIL] DNS         -- the resolver accepts queries and never answers."
	echo "                        Restart (the flag is boot-time only):"
	echo "                        FORCE_REBOOT=1 EMULATOR_DNS=8.8.8.8 bash $0 $AVD"
	fail=1
else
	echo "  [FAIL] DNS         -- IP works but names do not resolve."
	echo "                        FORCE_REBOOT=1 EMULATOR_DNS=8.8.8.8 bash $0 $AVD"
	echo "                        (a VPN on the Mac is the usual cause)"
	fail=1
fi

# The host's view, for comparison. If the service is down, that is not a device
# problem and no amount of emulator fiddling will fix it.
code=$(curl -sS -m 15 -o /dev/null -w '%{http_code}' \
       https://world.openfoodfacts.org/api/v2/product/3017620422003 2>/dev/null)
echo "  [--]   Open Food Facts from the Mac: HTTP ${code:-no-response}"

# --- 4. app state -----------------------------------------------------------
echo
echo "app state:"
if adb shell "run-as $PKG test -f databases/open_source_database.db" > /dev/null 2>&1; then
	echo "  [ok]   database present (still onboarded)"
	adb shell "run-as $PKG sqlite3 databases/open_source_database.db \
	  \"SELECT '         sourceType='||sourceType||' -> '||COUNT(*)||' products' \
	    FROM Product GROUP BY sourceType;\"" 2>/dev/null | tr -d '\r'
	echo "         (sourceType 0=User 1=OpenFoodFacts 2=USDA 3=Swiss)"
else
	echo "  [WARN] database missing -- FoodYou is not onboarded. Launch it once and"
	echo "         accept the intro screens, then re-run seed_foods.sh."
fi

echo
if [ "$fail" -eq 0 ]; then
	echo "READY. The emulator can reach the internet."
	echo "If Open Food Facts still shows its error card now, that is FoodYou's own"
	echo "fetch path failing -- a real finding, not an environment problem."
else
	echo "NOT READY -- fix the [FAIL] lines above before drawing any conclusion"
	echo "about Open Food Facts. An offline device makes every external-source"
	echo "result meaningless."
	exit 1
fi
