#!/usr/bin/env bash
# check_env.sh -- assert the environment can actually support the test, BEFORE running it.
#
#     bash systems/foodyou/check_env.sh          # exit 0 = ready, 1 = not
#     bash systems/foodyou/check_env.sh --quiet  # for use inside sweep scripts
#
# WHY THIS EXISTS
# The specification says an Open Food Facts search returns results, so a search
# that fails is a conformance FAIL. That is only a sound verdict if the device
# could have reached Open Food Facts in the first place. Without this check the
# two situations are indistinguishable:
#
#     the emulator's wifi is off   -> search fails -> "FAIL: FoodYou is broken"
#     FoodYou's fetch path is bad  -> search fails -> "FAIL: FoodYou is broken"
#
# Only the second is a finding. The first is a statement about the laptop, and a
# sweep of them looks exactly like a discovery. This is not hypothetical: an
# earlier sweep produced 54 FAILs, none of which were about the app.
#
# So: prove the preconditions, or refuse to run. A refusal is INCONCLUSIVE for
# environment reasons -- which is honest -- and it is loud, which a quietly wrong
# sweep is not.
set -u

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1
say() { [ "$QUIET" -eq 1 ] || echo "$@"; }

# macOS ships no `timeout`, and every check below can block indefinitely:
# `ping -W` bounds the wait for a REPLY, not the name lookup, so a dead resolver
# hangs forever -- which is precisely the state this script exists to detect. A
# check that hangs is worse than one that fails: it stalls the sweep with no
# message at all.
OUT=$(mktemp)
trap 'rm -f "$OUT"' EXIT
with_timeout() {
	secs="$1"; shift
	: > "$OUT"
	"$@" > "$OUT" 2>&1 &
	pid=$!
	i=0
	while kill -0 "$pid" 2>/dev/null; do
		if [ "$i" -ge "$secs" ]; then
			kill -9 "$pid" 2>/dev/null
			wait "$pid" 2>/dev/null
			return 124                     # timed out
		fi
		sleep 1
		i=$((i + 1))
	done
	wait "$pid" 2>/dev/null
}

PKG=com.maksimowiczm.foodyou
DB=databases/open_source_database.db
OFF_PROBE="https://world.openfoodfacts.org/api/v2/product/3017620422003"
fail=0
note() { echo "  [FAIL] $*" >&2; fail=1; }

# LOCAL_ONLY=1 downgrades the CONNECTIVITY checks to warnings while leaving every
# other check fatal. It exists because "the device is offline" blocks two things
# and nothing else:
#
#   * the extapi_fail purpose
#   * the external-catalogue branches of other purposes
#
# The remaining seven purposes are entirely local -- SQLite, process, filesystem
# -- and a network failure tells you nothing about them. Refusing to run them is
# strictness in the wrong place, and the alternative people actually reach for is
# SKIP_ENV_CHECK=1, which also discards the FIXTURE check. That one matters: a
# drifted catalogue energy silently invalidates every arithmetic verdict in the
# sweep, offline or not.
#
# So this is the narrow escape hatch. It never suppresses the fixture, database
# or device checks, and any result it permits must be reported as measured on an
# offline device.
LOCAL_ONLY="${LOCAL_ONLY:-0}"
netnote() {
	if [ "$LOCAL_ONLY" = "1" ]; then
		say "  [warn] $*"
		say "         (LOCAL_ONLY=1: offline is not fatal for local-fault purposes,"
		say "          but NO external-source verdict from this run is meaningful)"
	else
		note "$@"
	fi
}

say "environment check:"

# --- 1. a device at all -----------------------------------------------------
if ! with_timeout 10 adb shell true; then
	note "no device (or adb is not responding). Start it:"
	note "  bash systems/foodyou/boot_emulator.sh"
	echo "NOT READY -- see above" >&2
	exit 1
fi
say "  [ok]   device reachable"

# --- 2. radios on -----------------------------------------------------------
# EXTAPI_FAIL disables these and restores only on the normal path, so an
# interrupted disruption run leaves them off and poisons every later sweep.
air=$(adb shell settings get global airplane_mode_on 2>/dev/null | tr -d '\r')
if [ "$air" = "1" ]; then
	netnote "airplane mode is ON -- a stranded EXTAPI_FAIL is the usual cause."
	netnote "  fix: adb shell settings put global airplane_mode_on 0"
else
	say "  [ok]   airplane mode off"
fi

# --- 3. the device can route out (TCP, not ICMP) ----------------------------
# WAS `ping`. Fixed 2026-09-01: campus/eduroam-style networks commonly block
# ICMP as policy while leaving real traffic untouched, so ping reported this
# exact device "offline" while it had completely working HTTPS -- confirmed
# directly: `nc -w 5 1.1.1.1 443` succeeded from both the Mac and the emulator
# in the same session `ping 1.1.1.1` failed on both. A network-level VPN can
# still cause a genuine failure here; the point is ping cannot tell that case
# apart from "this network filters ICMP", and TCP to the port the app actually
# uses can. `nc` is toybox's build (Android 28+); syntax is `-w SECS`, not `-z`.
with_timeout 15 adb shell "echo | nc -w 5 1.1.1.1 443 >/dev/null 2>&1 && echo TCP_OK"
if grep -q "TCP_OK" "$OUT" 2>/dev/null; then
	say "  [ok]   device has a route to the internet"
else
	netnote "device cannot open a TCP connection to 1.1.1.1:443 -- it is offline."
	netnote "  fix: adb shell svc wifi enable ; adb shell svc data enable"
fi

# --- 4. ... and resolve names ----------------------------------------------
# Separate from step 3 on purpose: DNS breaks on its own and needs a different
# fix from "no route". A hang here IS the symptom -- the resolver is accepting
# the query and never answering -- so treat the timeout as a distinct diagnosis
# rather than lumping it in with "did not resolve". Same TCP-not-ICMP fix as
# step 3, same reason.
with_timeout 15 adb shell "echo | nc -w 5 world.openfoodfacts.org 443 >/dev/null 2>&1 && echo TCP_OK"
rc=$?
if grep -q "TCP_OK" "$OUT" 2>/dev/null; then
	say "  [ok]   device can resolve the external source"
elif [ "$rc" -eq 124 ]; then
	netnote "DNS HANGS on the device -- the resolver never answers."
	netnote "  The emulator's -dns-server is set at BOOT ONLY, so it must be"
	netnote "  restarted, not just re-checked:"
	netnote "    adb emu kill ; sleep 3"
	netnote "    EMULATOR_DNS=8.8.8.8 bash systems/foodyou/boot_emulator.sh"
	netnote "  (a VPN on the Mac is the usual cause of the inherited resolver)"
else
	netnote "device cannot resolve world.openfoodfacts.org (raw IP may still work)."
	netnote "  fix: adb emu kill ; sleep 3"
	netnote "       EMULATOR_DNS=8.8.8.8 bash systems/foodyou/boot_emulator.sh"
fi

# --- 5. the service itself is up -------------------------------------------
# Checked from the Mac. If the service is down, no verdict about the external
# branch means anything, and that is nobody's bug.
code=$(curl -sS -m 15 -o /dev/null -w '%{http_code}' "$OFF_PROBE" 2>/dev/null)
case "$code" in
	2*) say "  [ok]   Open Food Facts responding (HTTP $code)" ;;
	"") netnote "Open Food Facts unreachable from this Mac (no response)." ;;
	*)  netnote "Open Food Facts returned HTTP $code -- the service is degraded." ;;
esac

# --- 6. the app is still onboarded -----------------------------------------
# seed_foods.sh writes to an EXISTING database; without it every run starts on an
# onboarding screen and fails for reasons unrelated to the test.
if with_timeout 15 adb shell "run-as $PKG test -f $DB"; then
	say "  [ok]   app database present (onboarded)"

	# --- 7. the foods under test still hold their authoritative energies ------
	# DB_CORRUPT sets these to NULL and CACHE_STALE sets them to 999, restoring
	# them afterwards. If a run is interrupted in between, the catalogue stays
	# corrupted and EVERY later run quietly measures against wrong data -- the
	# same class of stranded state that left the radios off all day, but harder
	# to notice because nothing looks broken.
	#
	# The expected values are Calorie.abstract_values in type_description.yml.
	want="Corn germ oil|900
Cooking butter|745
Peanut butter|636"
	got=$(with_timeout 20 adb shell "run-as $PKG sqlite3 $DB \
	  \"SELECT name||'|'||CAST(energy AS INT) FROM Product \
	     WHERE name IN ('Peanut butter','Cooking butter','Corn germ oil') \
	     ORDER BY name DESC;\"" ; cat "$OUT" | tr -d '\r')
	if [ "$(echo "$got" | sort)" = "$(echo "$want" | sort)" ]; then
		say "  [ok]   foods under test hold their authoritative energies"
	else
		note "the foods under test do NOT hold their expected energies."
		note "  expected: $(echo "$want" | tr '\n' ' ')"
		note "  found   : $(echo "$got"  | tr '\n' ' ')"
		note "  A NULL or 999 means an interrupted DB_CORRUPT / CACHE_STALE run"
		note "  left the catalogue corrupted. Restore with:"
		note "    adb shell \"run-as $PKG sqlite3 $DB \\\"UPDATE Product SET energy=636 WHERE name='Peanut butter'; UPDATE Product SET energy=745 WHERE name='Cooking butter'; UPDATE Product SET energy=900 WHERE name='Corn germ oil';\\\"\""
	fi
else
	note "FoodYou is not onboarded ($DB missing)."
	note "  fix: launch the app once, accept the intro screens, then seed_foods.sh"
fi

if [ "$fail" -eq 0 ]; then
	say "READY"
	exit 0
fi
echo "NOT READY -- refusing to run." >&2
echo "Any external-source verdict measured now would describe this environment," >&2
echo "not FoodYou. Fix the [FAIL] lines above and re-run." >&2
exit 1
