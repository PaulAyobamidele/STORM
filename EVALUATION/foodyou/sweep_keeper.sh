#!/usr/bin/env bash
# sweep_keeper.sh -- keep a resume sweep going across sleeps, Appium deaths and
# emulator hiccups, without a human watching it.
#
#     source EVALUATION/foodyou/env.sh
#     caffeinate -dimsu bash EVALUATION/foodyou/sweep_keeper.sh storage_media
#
# WHAT SLEEP ACTUALLY DOES. Closing the lid does not pause the sweep; it kills
# the case in flight. The emulator is frozen mid-instruction, Appium's session
# goes stale, adb usually loses the device, and every wait that was running
# expires the instant the clock resumes. caffeinate prevents IDLE sleep only.
# The first line of defence is therefore `sudo pmset -a disablesleep 1` (and
# setting it back to 0 afterwards). This script is the second line: when a case
# dies anyway, it repairs the apparatus and resumes from the next variant with
# no row -- instead of leaving the sweep stalled, or, as on 2026-09-26, burning
# 82 ERROR rows in two minutes against an Appium that was no longer there.
#
# WHAT IT NEVER DOES. It never overwrites a verdict. run_variants_resume.sh
# appends, and only variants without a row are walked. ERROR rows are the one
# exception: under the current semantics a walk that starts ends in PASS, FAIL,
# INCONC or UNEXECUTABLE, so ERROR can only mean the apparatus died before the
# walk began. Those rows are scrubbed so the variants get walked for real.
#
# ONE THING IT CANNOT FIX. A case that straddles a sleep is suspended, not
# killed; on wake its waits expire and it records a verdict that is really a
# sleep artefact. That row looks legitimate. Layer 1 is the only cure.
set -u
cd "$(dirname "$0")/../.." || exit 1
: "${DEV:?source EVALUATION/foodyou/env.sh first (same shell)}"

PURPOSE="${1:?usage: bash EVALUATION/foodyou/sweep_keeper.sh <purpose>}"
PORT=$(echo "$DEV" | sed -n 's/.*127\.0\.0\.1:\([0-9]*\).*/\1/p'); PORT="${PORT:-4723}"
LOG=EVALUATION/foodyou/variants_${PURPOSE}.log
KEEP=EVALUATION/foodyou/keeper_${PURPOSE}.log
APPIUM_LOG=/tmp/appium-${PORT}.log
TOTAL=$(ls EVALUATION/foodyou/Test_Cases/variants/"${PURPOSE}"/*.aut 2>/dev/null | wc -l | tr -d ' ')
[ "$TOTAL" -gt 0 ] || { echo "no variants for $PURPOSE" >&2; exit 1; }

say()       { echo "$(date '+%m-%d %H:%M:%S')  $*" | tee -a "$KEEP"; }
done_rows() { awk 'NF>=4 && $1 ~ /^[0-9]+$/ && $4!="ERROR"' "$LOG" 2>/dev/null | wc -l | tr -d ' '; }
appium_up() { curl -s --max-time 3 "http://127.0.0.1:${PORT}/status" >/dev/null 2>&1; }
device_up() { adb devices 2>/dev/null | grep -qE "emulator-[0-9]+[[:space:]]+device$"; }

scrub_errors() {
	e=$(awk 'NF>=4 && $1 ~ /^[0-9]+$/ && $4=="ERROR"' "$LOG" 2>/dev/null | wc -l | tr -d ' ')
	[ "$e" -gt 0 ] || return 0
	say "scrubbing $e ERROR row(s) -- apparatus died before those walks began; they will be re-walked"
	awk '!(NF>=4 && $1 ~ /^[0-9]+$/ && $4=="ERROR")' "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
}

repair_device() {
	say "device not visible -- restarting adb"
	adb kill-server >/dev/null 2>&1; adb start-server >/dev/null 2>&1; sleep 5
	device_up && { say "  adb reconnected"; return 0; }
	say "  still no device -- rebooting the emulator (boot_emulator.sh)"
	bash EVALUATION/foodyou/boot_emulator.sh >>"$KEEP" 2>&1
	device_up
}

repair_appium() {
	say "Appium not responding on ${PORT} -- starting it"
	# Kill whatever holds the port, not a guess at Appium's command line. A stuck
	# Appium that still owns the socket but will not answer /status is the case
	# that matters: leave it and the new one dies on EADDRINUSE, and the keeper
	# would retry that every five minutes until morning.
	held=$(lsof -ti :"${PORT}" 2>/dev/null)
	[ -n "$held" ] && { say "  port ${PORT} held by pid(s) $held -- killing"; kill $held 2>/dev/null; sleep 2; kill -9 $held 2>/dev/null; }
	sleep 1
	nohup appium -p "$PORT" >"$APPIUM_LOG" 2>&1 &
	for _ in $(seq 1 30); do appium_up && { say "  Appium up (log: $APPIUM_LOG)"; return 0; }; sleep 2; done
	say "  Appium did not answer within 60s -- see $APPIUM_LOG"; return 1
}

say "keeper start: $PURPOSE  $(done_rows)/$TOTAL rows done"
while :; do
	scrub_errors
	n=$(done_rows)
	if [ "$n" -ge "$TOTAL" ]; then say "COMPLETE: $n/$TOTAL"; break; fi

	# Repair in dependency order: no point in Appium without a device, no point
	# in check_env without both. Any failure waits 5 minutes and tries again --
	# a sleeping laptop that just woke can take that long to settle.
	device_up || repair_device || { say "device unrecoverable -- retry in 5 min"; sleep 300; continue; }
	appium_up || repair_appium || { say "Appium unrecoverable -- retry in 5 min"; sleep 300; continue; }
	bash EVALUATION/foodyou/check_env.sh --quiet >>"$KEEP" 2>&1 \
		|| { say "check_env NOT READY -- retry in 5 min (see $KEEP)"; sleep 300; continue; }

	if [ -f "$LOG" ]; then
		say "resuming at $n/$TOTAL"
		bash EVALUATION/foodyou/run_variants_resume.sh "$PURPOSE" >>"$KEEP" 2>&1
	else
		# A purpose that has never been swept has no summary log, and the resume
		# script refuses to invent one. Start the sweep proper; every later pass
		# resumes it. Without this branch a fresh purpose loops forever at 0/N.
		say "no summary log yet -- starting a fresh sweep of $PURPOSE"
		bash EVALUATION/foodyou/run_variants.sh "$PURPOSE" >>"$KEEP" 2>&1
	fi
	say "sweep pass exited -- $(done_rows)/$TOTAL rows"
	sleep 30
done
