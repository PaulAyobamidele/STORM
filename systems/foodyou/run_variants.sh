#!/usr/bin/env bash
# run_variants.sh -- concretize EVERY controllable test case of one test purpose
# and print a verdict per variant.
#
#     source systems/foodyou/env.sh
#     bash systems/foodyou/run_variants.sh happy
#
# run.py's --aut takes a single file, and the concretizer derives the target
# fault from that file's NAME (algorithm.py: tc_<fault>.aut -> <FAULT>). So a
# variant cannot simply be passed by its own path -- tc_happy.7.aut would parse
# as fault "HAPPY.7", match nothing, and silently run untargeted. Each variant
# is therefore copied over the canonical tc_<purpose>.aut for its run, and the
# canonical file is restored at the end (including on Ctrl-C).
#
# Divergent verdicts across variants are the finding this script exists for:
# they mean the verdict previously reported for this purpose depended on which
# controllability resolution testor happened to pick on the fly.
set -u

PURPOSE="${1:-}"
if [ -z "$PURPOSE" ]; then
	echo "usage: bash systems/foodyou/run_variants.sh <purpose>   (e.g. happy)" >&2
	exit 1
fi
: "${DEV:?source systems/foodyou/env.sh first}"

# See investigate_variants.sh: a sweep against an offline device produces FAILs
# that describe the laptop, not the SUT. SKIP_ENV_CHECK=1 overrides.
if [ "${SKIP_ENV_CHECK:-0}" != "1" ]; then
	bash systems/foodyou/check_env.sh || exit 1
fi

TC=systems/foodyou/generated/tc
CANON="$TC/tc_${PURPOSE}.aut"
LOG="systems/foodyou/variants_${PURPOSE}.log"
LOGDIR="systems/foodyou/generated/variant_logs/${PURPOSE}"
mkdir -p "$LOGDIR"

# Variants live in a per-purpose directory, variants/<purpose>/. Older sets were
# written flat into variants/ -- accept both so an existing suite keeps working.
VDIR="$TC/variants/${PURPOSE}"
[ -d "$VDIR" ] || VDIR="$TC/variants"

# numeric sort by the variant index, so 10..12 do not sort before 2
VARIANTS=$(ls -1 "$VDIR"/tc_"${PURPOSE}".*.aut 2>/dev/null |
           sed 's/.*\.\([0-9][0-9]*\)\.aut$/\1 &/' | sort -n | cut -d' ' -f2)
if [ -z "$VARIANTS" ]; then
	echo "no variants found at $VDIR/tc_${PURPOSE}.*.aut" >&2
	echo "  generate them on the CADP node:  sh generate_tc_all.sh $PURPOSE" >&2
	exit 1
fi
echo "variants from: $VDIR"

# Leaving a variant installed under the canonical name would silently poison
# every later run_matrix.sh, so restore it whatever happens.
BACKUP=$(mktemp)
cp "$CANON" "$BACKUP" 2>/dev/null || true
restore() { [ -s "$BACKUP" ] && cp "$BACKUP" "$CANON" ; rm -f "$BACKUP" ; }
trap 'echo; echo "interrupted -- restoring $CANON"; restore; exit 130' INT TERM

{
	echo "# FoodYou tc variants -- purpose: $PURPOSE -- $(date '+%Y-%m-%d %H:%M')"
	printf "%-9s %8s %12s   %s\n" "VARIANT" "STATES" "TRANSITNS" "VERDICT"
} | tee "$LOG"

for v in $VARIANTS; do
	i=$(echo "$v" | sed 's/.*\.\([0-9][0-9]*\)\.aut$/\1/')
	hdr=$(head -1 "$v" | tr -dc '0-9,')
	ntrans=$(echo "$hdr" | cut -d, -f2)
	nstates=$(echo "$hdr" | cut -d, -f3)

	cp "$v" "$CANON"
	bash systems/foodyou/seed_foods.sh > "$LOGDIR/v${i}.seed.log" 2>&1

	# Keep stdout AND stderr. This used to be `2>/dev/null` with only the verdict
	# word kept, and it is why 54 FAILs sat unreadable: auditing them needed the
	# execution report and the walker trace, and both had been thrown away. Use
	# investigate_variants.sh for the classified view; this keeps the raw record.
	#
	# CONCRETIZATION_DEBUG_DIR scopes failure-capture screenshots/XML to THIS
	# variant's own subdirectory instead of the flat, timestamp-only default
	# (tmp/failure_artifacts/). Without this a capture cannot be traced back to
	# the case that produced it -- which is why the v47 crash (HANDOVER.md §3)
	# sat unnoticed among 1,457 unlinked files until someone went looking by hand.
	CONCRETIZATION_DEBUG_DIR="$LOGDIR/v${i}_captures" \
	PYTHONPATH=framework python -u framework/scripts/run.py \
	      --aut "$CANON" --platform android \
	      --system-interface systems/foodyou/model/system_interface_foodyou_copy.lnt \
	      --concrete-domain systems/foodyou/properties/concrete_domain.yml \
	      --type-description systems/foodyou/properties/type_description.yml \
	      --disruption-mapping systems/foodyou/properties/disruption_mapping.yml \
	      --device-config "$DEV" --timeout "${TIMEOUT:-10}" \
	      --report --verbose > "$LOGDIR/v${i}.log" 2>&1
	rc=$?
	V=$(perl -pe 's/\e\[[0-9;]*m//g' < "$LOGDIR/v${i}.log" \
	    | grep -oE '(Verdict: (PASS|FAIL|INCONC)|Status: UNEXECUTABLE)' \
	    | head -1 | awk '{print $2}')
	# An unexecuted run is not a verdict and must not be scored as one. run.py
	# prints it on a "Status:" line and exits 2; without the alternation above
	# the grep found nothing and the row was recorded as ERROR -- which reads
	# like a failed test case rather than a case that never ran.

	# Exit 2 means the apparatus could not start the test case -- no verdict was
	# produced, and the run says nothing about the SUT. Three of those in a row
	# means the DEVICE is broken, not the test cases, and every remaining case
	# will fail the same way.
	#
	# On 2026-08-24 the emulator's system process hung during storage_media and
	# 138 consecutive cases failed on their first element, each recorded as
	# INCONCLUSIVE. Two hours of runtime, no information, and the real cause only
	# visible by opening a log by hand. Stop instead: partial results from a known
	# device beat a full table from a broken one.
	#
	# Two DIFFERENT things exit 2, and only one of them means the device is
	# broken. run.py prints "HARNESS FAILURE:" when the test case could not even
	# START (HarnessNotReady: the initial screen never came up after 3
	# relaunches) -- that is the 2026-08-24 case and the one worth aborting on.
	# It prints "Status: UNEXECUTABLE" when the walk started, ran real steps, and
	# then hit a stimulus the apparatus could not apply (an ANR mid-walk, a
	# fixture it cannot populate). On 2026-09-25 three of those in a row
	# (v36-v38, the app hanging after 4h of driving) aborted a sweep on a
	# perfectly healthy device; the next variant would have started fine.
	# So: only the startup kind counts toward the abort; the mid-walk kind is
	# recorded and the counter is reset, because a walk that started proves the
	# device can start one.
	#
	# The row says UNEXECUTABLE, run.py's own word for it, which is also what
	# eval_tables.py's row pattern accepts -- it silently dropped the old HARNESS
	# label, so those rows never reached the tables at all.
	if [ "$rc" -eq 2 ]; then
		if grep -q "HARNESS FAILURE:" "$LOGDIR/v${i}.log"; then
			HARNESS_RUN=$((${HARNESS_RUN:-0} + 1))
			echo "  (v${i}: could not start -- harness failure ${HARNESS_RUN}/3)"
		else
			HARNESS_RUN=0
			echo "  (v${i}: started, then a step could not be applied -- not counted toward abort)"
		fi
		printf "%-9s %8s %12s   %s\n" "$i" "$nstates" "$ntrans" "UNEXECUTABLE" | tee -a "$LOG"
		if [ "$HARNESS_RUN" -ge 3 ]; then
			echo "ABORT: 3 consecutive harness failures -- the device cannot start a" | tee -a "$LOG"
			echo "  test case. Remaining variants are NOT run and must not be counted." | tee -a "$LOG"
			echo "  Check for a system 'isn't responding' dialog, a crashed app, or an" | tee -a "$LOG"
			echo "  exhausted disk, then: bash systems/foodyou/run_variants_resume.sh $PURPOSE" | tee -a "$LOG"
			break
		fi
		continue
	fi
	HARNESS_RUN=0

	printf "%-9s %8s %12s   %s\n" "$i" "$nstates" "$ntrans" "${V:-ERROR}" | tee -a "$LOG"
done

restore
trap - INT TERM

echo "----------------------------------------------------------------" | tee -a "$LOG"
echo "canonical $CANON restored" | tee -a "$LOG"
echo "written to $LOG"
