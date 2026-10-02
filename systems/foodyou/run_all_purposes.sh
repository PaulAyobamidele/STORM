#!/usr/bin/env bash
# run_all_purposes.sh -- sweep EVERY generated test case of EVERY test purpose.
#
#     source systems/foodyou/env.sh
#     bash systems/foodyou/run_all_purposes.sh                  # all nine, in order
#     bash systems/foodyou/run_all_purposes.sh cache_stale      # named purposes only
#     SMOKE=1 bash systems/foodyou/run_all_purposes.sh          # 1 variant each, ~10 min
#     FORCE=1 bash systems/foodyou/run_all_purposes.sh happy    # redo a finished purpose
#
# This is a driver around run_variants.sh, which already sweeps one purpose. What
# it adds is the three things a 13-hour run needs and a single purpose does not:
#
#   RESUMABLE   A purpose whose sweep log already exists is skipped. An emulator
#               crash at hour nine does not cost the first eight. FORCE=1 overrides.
#   ORDERED     Purposes run control-first (see SWEEP_PLAN.md section 3), so a
#               broken baseline is caught before eleven hours are spent on results
#               that could not be attributed anyway.
#   AGGREGATED  One table across all purposes at the end, including the ARITH
#               column -- findings that never reach a verdict and would otherwise
#               be invisible in a wall of PASSes.
#
# The order is deliberate: `happy` first because it is the control. If the nominal
# path is not clean, no disruption verdict after it can be attributed to its fault.
# ----------------------------------------------------------------------------
set -u

: "${DEV:?source systems/foodyou/env.sh first}"

# Control first, then the fault-free validation purpose, then the disruptions.
#
# storage_full is LAST because its ballast fills the data partition to ~20 MB.
# On 2026-08-24 it ran immediately before storage_media, and the emulator's
# system process then hung -- an Android "isn't responding" dialog sat over
# everything, and all 138 remaining storage_media cases failed on their first
# element without ever reaching their own fault. Whether the ballast caused it is
# not proven, but it is the only fault that touches a system-wide resource, and a
# purpose that may destabilise the device should have nothing scheduled after it.
ALL="happy input_invalid db_corrupt extapi_fail cache_stale ue1_kill disruption_db storage_media storage_full"

if [ "$#" -gt 0 ]; then
	PURPOSES="$*"
else
	PURPOSES="$ALL"
fi

# LOCAL_ONLY=1 means the device has no route out. extapi_fail is the one purpose
# whose fault IS the network: its injection cannot be shown to bite, its restore
# cannot be shown to let go, and its branch needs the external catalogue. Running
# it offline would produce rows that describe the laptop. Drop it explicitly and
# say so, rather than letting it contribute noise to the summary.
if [ "${LOCAL_ONLY:-0}" = "1" ]; then
	KEPT=""
	for P in $PURPOSES; do
		[ "$P" = "extapi_fail" ] && continue
		KEPT="$KEPT $P"
	done
	if [ "$KEPT" != " $PURPOSES" ]; then
		echo "LOCAL_ONLY=1: skipping extapi_fail -- its fault is the network itself."
		echo "  No external-source verdict can be measured on an offline device."
	fi
	PURPOSES="$KEPT"
fi

SUMMARY="systems/foodyou/sweep_all.log"
STARTED=$(date '+%Y-%m-%d %H:%M')

# The environment gate runs ONCE here rather than per purpose: nine identical
# checks over thirteen hours is noise, and a device that dies mid-sweep is caught
# by the per-purpose verdicts turning to ERROR, not by re-asking a question that
# was already answered.
if [ "${SKIP_ENV_CHECK:-0}" != "1" ]; then
	bash systems/foodyou/check_env.sh || exit 1
fi
export SKIP_ENV_CHECK=1

{
	echo "# FoodYou full sweep -- started $STARTED"
	echo "# purposes: $PURPOSES"
	[ -n "${SMOKE:-}" ] && echo "# SMOKE MODE: one variant per purpose"
	echo
} | tee "$SUMMARY"

for P in $PURPOSES; do
	LOG="systems/foodyou/variants_${P}.log"

	# Resume: a completed sweep writes the restore line as its last act. A log
	# without it is a partial run and gets redone.
	if [ -z "${FORCE:-}" ] && [ -f "$LOG" ] && grep -q "canonical .* restored" "$LOG"; then
		echo "== $P: already swept ($(grep -c '^[0-9]' "$LOG") variants) -- skipping" | tee -a "$SUMMARY"
		continue
	fi

	echo "==================================================================" | tee -a "$SUMMARY"
	echo "== $P  ($(date '+%H:%M'))" | tee -a "$SUMMARY"

	# RE-CHECK THE FIXTURE BEFORE EVERY PURPOSE, not just once before the sweep.
	#
	# A disruption run whose restore fails leaves the catalogue corrupted, and the
	# next purpose then measures against the PREVIOUS fault's data. On 2026-08-23 a
	# nine-minute smoke run did exactly that: db_corrupt left the energies NULL,
	# cache_stale left them at 999, and the four purposes after it all reported the
	# identical "observed 999 kcal, expected authoritative 900" -- none of which had
	# anything to do with their own fault. Over thirteen hours that is a whole
	# sweep of results describing the first failure.
	#
	# Checking once at the start cannot catch this, because the state is clean at
	# the start. Stop the sweep rather than continue: partial results from a known
	# state beat a full table from an unknown one.
	if ! LOCAL_ONLY="${LOCAL_ONLY:-0}" bash systems/foodyou/check_env.sh --quiet; then
		echo "   ABORT: fixture check failed BEFORE $P -- the device is dirty," | tee -a "$SUMMARY"
		echo "   almost certainly from the previous purpose's restore. Purposes" | tee -a "$SUMMARY"
		echo "   completed so far are valid; nothing after this point would be." | tee -a "$SUMMARY"
		echo "   Repair with the UPDATE in check_env.sh's message, then re-run:" | tee -a "$SUMMARY"
		echo "     bash systems/foodyou/run_all_purposes.sh   # resumes, skips what is done" | tee -a "$SUMMARY"
		break
	fi

	# Show the VERDICT ROWS, not the tail. Both sweep scripts end with a legend and
	# a "written to ..." footer, so `tail -n` prints boilerplate and hides the one
	# thing being waited for -- which is exactly what it did on the first smoke run.
	# The data rows are the ones beginning with a variant number.
	if [ -n "${SMOKE:-}" ]; then
		# One variant, through investigate_variants.sh so the run keeps its full
		# log and gets classified. Smoke is about plumbing, not verdicts.
		REPEATS=1 bash systems/foodyou/investigate_variants.sh "$P" 1 2>&1 \
			| grep -E "^[0-9]+ +[0-9=]" | tee -a "$SUMMARY"
	else
		bash systems/foodyou/run_variants.sh "$P" 2>&1 | grep -E "^[0-9]+ " > /tmp/rv.$$ || true
		n=$(wc -l < /tmp/rv.$$ | tr -d ' ')
		p=$(awk '$4 == "PASS"   {c++} END {print c+0}' /tmp/rv.$$)
		i=$(awk '$4 == "INCONC" {c++} END {print c+0}' /tmp/rv.$$)
		f=$(awk '$4 == "FAIL" || $4 == "ERROR" {c++} END {print c+0}' /tmp/rv.$$)
		printf "   %s: %s cases -> %s PASS, %s INCONC, %s FAIL\n" "$P" "$n" "$p" "$i" "$f" \
			| tee -a "$SUMMARY"
		rm -f /tmp/rv.$$
	fi
done

# --- aggregate ---------------------------------------------------------------
# Verdict counts come from the per-purpose sweep logs; ARITH is recomputed from
# the retained run logs, because an arithmetic finding never terminates a walk and
# therefore never appears in a verdict column. A row of PASSes with ARITH > 0 is
# not a clean result, and this is the only place that says so.
{
	echo
	echo "=================================================================="
	echo "SWEEP SUMMARY   started $STARTED   finished $(date '+%Y-%m-%d %H:%M')"
	echo
	printf "%-16s %6s %6s %6s %6s %6s\n" PURPOSE CASES PASS INCONC FAIL ARITH
	TP=0; TI=0; TF=0; TA=0; TC=0
	for P in $ALL; do
		# SMOKE and full sweeps write to DIFFERENT files, and reading the wrong one
		# gave a summary table listing only `happy` -- the one purpose that had a
		# stale full-sweep log lying around. Pick by mode, and count the ARITH
		# column from wherever that mode's run logs actually landed.
		if [ -n "${SMOKE:-}" ]; then
			LOG="systems/foodyou/investigate_${P}.log"
			RUNLOGS="systems/foodyou/generated/investigate/${P}"
			VCOL=3                       # VARIANT RUN VERDICT ...
		else
			LOG="systems/foodyou/variants_${P}.log"
			RUNLOGS="systems/foodyou/generated/variant_logs/${P}"
			VCOL=4                       # VARIANT STATES TRANSITNS VERDICT
		fi
		[ -f "$LOG" ] || continue
		n=$(awk '$1 ~ /^[0-9]+$/ && $2 ~ /^[0-9]+$/ {c++} END {print c+0}' "$LOG")
		p=$(awk -v k=$VCOL '$1 ~ /^[0-9]+$/ && $2 ~ /^[0-9]+$/ && $k == "PASS"   {c++} END {print c+0}' "$LOG")
		i=$(awk -v k=$VCOL '$1 ~ /^[0-9]+$/ && $2 ~ /^[0-9]+$/ && $k == "INCONC" {c++} END {print c+0}' "$LOG")
		f=$(awk -v k=$VCOL '$1 ~ /^[0-9]+$/ && $2 ~ /^[0-9]+$/ && ($k == "FAIL" || $k == "ERROR") {c++} END {print c+0}' "$LOG")
		a=$(grep -l 'TOTAL MISMATCH\|ARITHMETIC INCONSISTENCY\|TOTAL DELTA\|MACRO INCONSISTENCY\|ledger UNKNOWN' \
		      "$RUNLOGS"/v*.log 2>/dev/null | wc -l | tr -d ' ')
		printf "%-16s %6s %6s %6s %6s %6s\n" "$P" "$n" "$p" "$i" "$f" "$a"
		TC=$((TC+n)); TP=$((TP+p)); TI=$((TI+i)); TF=$((TF+f)); TA=$((TA+a))
	done
	printf "%-16s %6s %6s %6s %6s %6s\n" "TOTAL" "$TC" "$TP" "$TI" "$TF" "$TA"
	echo
	if [ "$TA" -gt 0 ]; then
		echo "ARITHMETIC: $TA run(s) carry a finding the verdict does not show."
		echo "  These do not terminate a walk, so they can sit inside a PASS."
		echo "  Investigate before reporting any purpose as clean."
	fi
	if [ "$TF" -gt 0 ]; then
		echo "$TF non-PASS verdict(s). A FAIL is NOT a counter-example until its log"
		echo "  has been classified and the cause attributed to the app rather than"
		echo "  the tester:"
		echo "    python framework/scripts/classify_failure.py \\"
		echo "      systems/foodyou/generated/variant_logs/<purpose>/v<N>.log --trace 20"
	fi
	echo
	echo "record the per-purpose rows in systems/foodyou/SWEEP_PLAN.md section 5"
} | tee -a "$SUMMARY"

echo "written to $SUMMARY"
