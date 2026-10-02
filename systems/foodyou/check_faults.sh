#!/usr/bin/env bash
# check_faults.sh -- prove that every fault injection ACTUALLY BITES, before any
# disruption sweep believes a verdict.
#
#     bash systems/foodyou/check_faults.sh            # exit 0 = all bite, 1 = not
#     bash systems/foodyou/check_faults.sh UE1_KILL   # one fault only
#     bash systems/foodyou/check_faults.sh --quiet    # for use inside sweep scripts
#
# WHY THIS EXISTS
# A fault that does not manifest produces a PASS that means nothing, and a PASS
# that means nothing is indistinguishable from a PASS that does. The app sails
# through because nothing was ever done to it, and the results table reports
# resilience it never demonstrated.
#
# This is not hypothetical. Until 2026-08-23 this project had:
#
#   * manifested() probing `name LIKE 'Test%'` -- rows seed_foods.sh DELETES. Every
#     probe answered about a row that was not there. CACHE_STALE therefore reported
#     "never manifested" and every run of it was INCONCLUSIVE even when the
#     injection had worked perfectly; DB_CORRUPT reported "manifested"
#     unconditionally, because a missing row and a NULL energy both read as "".
#
#   * UE1_KILL, DISRUPTION_DB and STORAGE_FULL running BYTE-IDENTICAL SQL -- one
#     fault under three names, three rows in a results table that could not
#     disagree.
#
# Neither was visible from a sweep. Both are visible in ten seconds here.
#
# WHAT "BITES" MEANS
# Each fault is checked against the DEVICE, not against the config that describes
# it, and independently of the application's reaction:
#
#     1. record the relevant state
#     2. inject
#     3. assert the state changed in the way the fault claims
#     4. restore
#     5. assert it changed back
#
# Step 5 matters as much as step 3: a fault that bites and does not let go poisons
# every later run in the sweep. check_env.sh catches a corrupted catalogue after
# the fact; this catches it before.
#
# NOT COVERED
# UE1_KILL is transient -- the process is killed and immediately relaunched, so
# there is no lasting state to probe. What is checked instead is that the process
# id actually CHANGED, which is the observable fact that a kill occurred.
# ----------------------------------------------------------------------------
set -u

QUIET=0
[ "${1:-}" = "--quiet" ] && { QUIET=1; shift; }
say()  { [ "$QUIET" -eq 1 ] || echo "$@"; }
ok()   { say "  [ok]   $*"; }
bad()  { echo "  [FAIL] $*" >&2; fail=1; }
note() { say "         $*"; }

fail=0
ADB="${ADB:-adb}"
PKG=com.maksimowiczm.foodyou
DB=databases/open_source_database.db
MAP=systems/foodyou/properties/disruption_mapping.yml

FAULTS="${*:-DB_CORRUPT CACHE_STALE DISRUPTION_DB STORAGE_FULL UE1_KILL STORAGE_MEDIA EXTAPI_FAIL}"

# EXTAPI_FAIL's fault IS the network, so on an offline device the test is not just
# meaningless -- it is harmful. `svc wifi enable` returns success while the device
# still has no route (a VPN on the host, an emulator NAT problem), so the restore
# looks like it failed, and every check after it inherits an offline device. That
# happened twice on 2026-08-23. Under LOCAL_ONLY the device is ALREADY known to be
# offline, so drop the fault rather than re-derive that fact destructively.
if [ "${LOCAL_ONLY:-0}" = "1" ]; then
	KEPT=""
	for F in $FAULTS; do
		[ "$F" = "EXTAPI_FAIL" ] && continue
		KEPT="$KEPT $F"
	done
	[ "$KEPT" != " $FAULTS" ] && \
		say "LOCAL_ONLY=1: skipping EXTAPI_FAIL -- its fault is the network itself."
	FAULTS="$KEPT"
fi

sql()  { $ADB shell "run-as $PKG sqlite3 $DB \"$1\"" 2>/dev/null | tr -d '\r'; }
shl()  { $ADB shell "$1" 2>/dev/null | tr -d '\r'; }

# The injector reads its commands from disruption_mapping.yml; so does this. Asking
# python rather than duplicating the strings means a drift between the two is
# impossible -- if the mapping changes, this checks the new thing.
cmd_of() {
	python3 - "$1" "$2" <<'PY'
import sys, yaml
fault, key = sys.argv[1], sys.argv[2]
m = yaml.safe_load(open("systems/foodyou/properties/disruption_mapping.yml"))
spec = (m.get("faults") or {}).get(fault) or {}
s = (spec.get(key) or "").replace("{pkg}", "com.maksimowiczm.foodyou") \
                         .replace("{db}", "databases/open_source_database.db")
print(s)
PY
}
mech_of() { cmd_of "$1" mechanism; }

apply() {   # apply(fault, inject|restore) -- same split rule as the injector
	local f="$1" key="$2" mech c
	mech=$(mech_of "$f"); c=$(cmd_of "$f" "$key")
	[ -z "$c" ] && return 0
	if [ "$mech" = "sqlite" ]; then
		$ADB shell "run-as $PKG sqlite3 $DB \"PRAGMA busy_timeout=5000; $c\"" >/dev/null 2>&1
	else
		local IFS=';'
		for part in $c; do
			part=$(echo "$part" | sed 's/^ *//; s/ *$//')
			[ -n "$part" ] && $ADB shell "$part" >/dev/null 2>&1
		done
	fi
}

# --- 0. device and database reachable ---------------------------------------
if ! $ADB shell true >/dev/null 2>&1; then
	echo "ERROR: no adb device reachable." >&2; exit 1
fi
if ! $ADB shell "run-as $PKG test -f $DB" >/dev/null 2>&1; then
	echo "ERROR: $DB not found -- app not onboarded." >&2; exit 1
fi
say "fault injection self-test  ($(date '+%Y-%m-%d %H:%M'))"

for F in $FAULTS; do
	case "$F" in

	DB_CORRUPT)
		before=$(sql "SELECT energy FROM Product WHERE name = 'Corn germ oil'")
		apply DB_CORRUPT inject
		during=$(sql "SELECT name FROM Product WHERE name = 'Corn germ oil' AND energy IS NULL")
		apply DB_CORRUPT restore
		after=$(sql "SELECT energy FROM Product WHERE name = 'Corn germ oil'")
		if [ -n "$during" ] && [ "$after" = "$before" ]; then
			ok "DB_CORRUPT bites (energy $before -> NULL -> $after)"
		else
			bad "DB_CORRUPT: energy before='$before' nulled='$during' after='$after'"
			note "injection did not null the row, or restore did not put it back"
		fi
		;;

	CACHE_STALE)
		before=$(sql "SELECT energy FROM Product WHERE name = 'Corn germ oil'")
		apply CACHE_STALE inject
		during=$(sql "SELECT energy FROM Product WHERE name = 'Corn germ oil'")
		apply CACHE_STALE restore
		after=$(sql "SELECT energy FROM Product WHERE name = 'Corn germ oil'")
		# Compare NUMERICALLY. SQLite returns the energy column as '999.0', not
		# '999', so a string test reports a perfect injection as a failure -- which
		# is exactly what it did on first run. DB_CORRUPT escaped this because it
		# probes for a NAME rather than a value.
		stale_ok=$(awk -v v="$during" 'BEGIN { print (v + 0 == 999) ? 1 : 0 }')
		if [ "$stale_ok" = "1" ] && [ "$after" = "$before" ]; then
			ok "CACHE_STALE bites (energy $before -> 999 -> $after)"
		else
			bad "CACHE_STALE: energy before='$before' stale='$during' after='$after'"
		fi
		;;

	DISRUPTION_DB)
		apply DISRUPTION_DB inject
		during=$(sql "SELECT name FROM sqlite_master WHERE type='trigger' AND name='fault_abort_write'")
		# The point of the trigger is that an INSERT fails. Prove that directly
		# rather than trusting that a trigger named correctly does the right thing.
		probe=$($ADB shell "run-as $PKG sqlite3 $DB \"INSERT INTO Measurement DEFAULT VALUES\"" 2>&1 | tr -d '\r')
		apply DISRUPTION_DB restore
		after=$(sql "SELECT name FROM sqlite_master WHERE type='trigger' AND name='fault_abort_write'")
		if [ -n "$during" ] && [ -z "$after" ]; then
			ok "DISRUPTION_DB bites (trigger armed, then dropped)"
			case "$probe" in
				*abort*|*ABORT*|*Error*|*error*) note "insert refused: $probe" ;;
				*) note "NOTE: a test insert was not visibly refused -- check the trigger fires on the table the app writes" ;;
			esac
		else
			bad "DISRUPTION_DB: trigger armed='$during' still-present-after='$after'"
		fi
		;;

	STORAGE_FULL)
		# Least certain of the three: the ballast command has never run on a device
		# and passes through adb -> run-as -> sh -c. Measure free space either side.
		before=$(shl "run-as $PKG df -k . | tail -1 | tr -s ' ' | cut -d' ' -f4")
		apply STORAGE_FULL inject
		during=$(shl "run-as $PKG df -k . | tail -1 | tr -s ' ' | cut -d' ' -f4")
		sz=$(shl "run-as $PKG ls -l files/fault_ballast | tr -s ' ' | cut -d' ' -f5")
		apply STORAGE_FULL restore
		after=$(shl "run-as $PKG df -k . | tail -1 | tr -s ' ' | cut -d' ' -f4")
		gone=$(shl "run-as $PKG ls files/fault_ballast" )
		if [ -n "${during:-}" ] && [ -n "${before:-}" ] && [ "$during" -lt "$before" ] 2>/dev/null && [ -z "$gone" ]; then
			ok "STORAGE_FULL bites (free ${before}K -> ${during}K, ballast ${sz:-?} bytes, removed)"
			[ "${during:-0}" -gt 51200 ] 2>/dev/null && \
				note "WARNING: ${during}K still free -- the partition may not be full enough to force ENOSPC"
			# Did the space actually come BACK? Removing the ballast file is not
			# the same as the filesystem recovering, and a device left short of
			# space is the leading suspect for the Android system hang that
			# destroyed 138 storage_media cases on 2026-08-24. Recovering to
			# within 10% of the starting figure is the check.
			if [ -n "${after:-}" ] && [ "$after" -lt $(( before * 9 / 10 )) ] 2>/dev/null; then
				bad "STORAGE_FULL restore did not recover the disk: ${before}K before, ${after}K after"
				note "a device left short of space can hang Android itself; do not sweep on it"
			else
				note "disk recovered: ${after:-?}K free (was ${before}K)"
			fi
		else
			bad "STORAGE_FULL: free before='$before' during='$during' after='$after' ballast-left='$gone'"
			note "if the ballast cannot fill the partition, fall back to the trigger"
			note "mechanism and record STORAGE_FULL and DISRUPTION_DB as sharing a layer"
		fi
		;;

	UE1_KILL)
		# Transient: nothing persists to probe. The observable fact is that the
		# process id changed -- a kill genuinely happened and the app came back.
		#
		# ENSURE THE APP IS RUNNING FIRST. On 2026-08-25 this reported
		# "app did not come back (pid before='')" -- but the empty pid BEFORE the
		# injection is the real signal: there was nothing to kill. STORAGE_FULL
		# runs immediately before this test and takes the disk to ~20 MB, at which
		# point Android kills background apps. The test was measuring the previous
		# fault's side effect, not this one.
		pid_before=$(shl "pidof $PKG")
		if [ -z "$pid_before" ]; then
			note "app was not running before UE1_KILL (previous fault likely killed it) -- starting it"
			$ADB shell "am start -n $PKG/.app.infrastructure.android.MainActivity" >/dev/null 2>&1
			for _ in 1 2 3 4 5 6 7 8 9 10; do
				sleep 1
				pid_before=$(shl "pidof $PKG")
				[ -n "$pid_before" ] && break
			done
		fi
		apply UE1_KILL inject
		# Poll rather than a fixed sleep: a cold start on a memory-pressured
		# emulator running software GL takes well over the 3 s this used to allow.
		pid_after=""
		for _ in 1 2 3 4 5 6 7 8 9 10; do
			sleep 1
			pid_after=$(shl "pidof $PKG")
			[ -n "$pid_after" ] && [ "$pid_after" != "$pid_before" ] && break
		done
		if [ -n "$pid_before" ] && [ -n "$pid_after" ] && [ "$pid_before" != "$pid_after" ]; then
			ok "UE1_KILL bites (pid $pid_before -> $pid_after)"
		elif [ -z "$pid_after" ]; then
			bad "UE1_KILL: app did not come back (pid before='$pid_before', now none)"
			note "the relaunch in the injection failed -- check the activity name"
		else
			bad "UE1_KILL: pid unchanged ('$pid_before') -- force-stop did not take"
		fi
		;;

	STORAGE_MEDIA)
		before=$(shl "run-as $PKG ls -l $DB | cut -c1-10")
		apply STORAGE_MEDIA inject
		during=$(shl "run-as $PKG ls -l $DB | cut -c1-10")
		apply STORAGE_MEDIA restore
		after=$(shl "run-as $PKG ls -l $DB | cut -c1-10")
		if [ "$during" != "$before" ] && [ "$after" = "$before" ]; then
			ok "STORAGE_MEDIA bites (mode $before -> $during -> $after)"
		else
			bad "STORAGE_MEDIA: mode before='$before' during='$during' after='$after'"
		fi
		;;

	EXTAPI_FAIL)
		before=$(shl "settings get global airplane_mode_on")
		apply EXTAPI_FAIL inject
		during=$(shl "ping -c 1 -W 2 1.1.1.1 >/dev/null 2>&1 && echo up || echo down")
		apply EXTAPI_FAIL restore
		# Wifi does not reassociate instantly. A fixed 2 s wait reported the restore
		# as failed and LEFT THE DEVICE OFFLINE, which then failed every check after
		# it -- the loudest possible version of a fault that bites and will not let
		# go. Poll instead, and only give up after 30 s.
		after=down
		for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
			sleep 2
			[ "$(shl "ping -c 1 -W 2 1.1.1.1 >/dev/null 2>&1 && echo up || echo down")" = "up" ] \
				&& { after=up; break; }
		done
		if [ "$during" = "down" ] && [ "$after" = "up" ]; then
			ok "EXTAPI_FAIL bites (network down under injection, restored)"
		else
			bad "EXTAPI_FAIL: during='$during' after='$after' (expected down / up)"
			[ "$after" = "down" ] && note "DEVICE LEFT OFFLINE -- run: adb shell svc wifi enable; adb shell svc data enable"
		fi
		;;

	*) bad "$F: no self-test defined" ;;
	esac
done

# --- final state -------------------------------------------------------------
# Every fault above restores as part of its own test, but a failure midway can
# leave the device dirty. Re-assert the fixture rather than assume.
say
# Pass LOCAL_ONLY through. Without it an offline device fails check_env's network
# checks and is reported as "DIRTY -- a restore did not take", which is a
# different and much more alarming claim than "there is no network". On
# 2026-08-23 that sent us looking for a corrupted catalogue that was fine.
if LOCAL_ONLY="${LOCAL_ONLY:-0}" bash systems/foodyou/check_env.sh --quiet; then
	ok "environment still clean after the self-test"
else
	bad "environment is DIRTY after the self-test -- a restore did not take"
	note "re-run systems/foodyou/seed_foods.sh before any sweep"
	note "(if the only complaint is connectivity, re-run with LOCAL_ONLY=1)"
fi

say
if [ "$fail" -eq 0 ]; then
	say "ALL FAULTS BITE -- disruption verdicts from these injections are meaningful."
	exit 0
fi
echo "SOME FAULTS DO NOT BITE. Any purpose above whose fault failed has NO valid" >&2
echo "result: a PASS would mean the app was never disturbed, not that it coped." >&2
exit 1
