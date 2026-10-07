#!/usr/bin/env bash
# run_variants_resume.sh -- finish a run_variants.sh sweep without redoing it.
#
#     source EVALUATION/foodyou/env.sh
#     bash EVALUATION/foodyou/run_variants_resume.sh storage_media          # every variant with no row yet
#     bash EVALUATION/foodyou/run_variants_resume.sh storage_media 7 9 12   # only these
#
# run_variants.sh stops after 3 consecutive harness failures (rc=2) and, when
# re-invoked, starts the log over from variant 1. This runs ONLY the variants
# that have no verdict row in variants_<purpose>.log (or the ones named) and
# APPENDS their rows in the same schema, so the log ends up complete without
# repeating work. Same per-variant body as run_variants.sh, same abort guard.
set -u

PURPOSE="${1:-}"; shift || true
if [ -z "$PURPOSE" ]; then
	echo "usage: bash EVALUATION/foodyou/run_variants_resume.sh <purpose> [variant ...]" >&2
	exit 1
fi
: "${DEV:?source EVALUATION/foodyou/env.sh first}"
cd "$(dirname "$0")/../.." || exit 1

if [ "${SKIP_ENV_CHECK:-0}" != "1" ]; then
	bash EVALUATION/foodyou/check_env.sh || exit 1
fi

TC=EVALUATION/foodyou/Test_Cases
CANON="$TC/tc_${PURPOSE}.aut"
LOG="EVALUATION/foodyou/variants_${PURPOSE}.log"
LOGDIR="EVALUATION/foodyou/generated/variant_logs/${PURPOSE}"
VDIR="$TC/variants/${PURPOSE}"
[ -d "$VDIR" ] || VDIR="$TC/variants"
mkdir -p "$LOGDIR"

if [ -z "$LOG" ] || [ ! -f "$LOG" ]; then
	echo "no $LOG to resume -- use run_variants.sh for a fresh sweep" >&2
	exit 1
fi

# Variants that already have a verdict row (first field numeric, verdict word last).
DONE=$(awk '$1 ~ /^[0-9]+$/ && $NF ~ /^(PASS|FAIL|INCONC|UNEXECUTABLE|HARNESS|ERROR)$/ {print $1}' "$LOG" | sort -n | uniq)

if [ $# -gt 0 ]; then
	TODO="$*"
else
	ALL=$(ls -1 "$VDIR"/tc_"${PURPOSE}".*.aut 2>/dev/null |
	      sed 's/.*\.\([0-9][0-9]*\)\.aut$/\1/' | sort -n)
	TODO=$(comm -23 <(echo "$ALL" | sort) <(echo "$DONE" | sort) | sort -n | tr '\n' ' ')
fi
if [ -z "$(echo "$TODO" | tr -d ' ')" ]; then
	echo "nothing to do: every variant in $VDIR has a row in $LOG"
	exit 0
fi
echo "resuming $PURPOSE: $(echo "$TODO" | wc -w | tr -d ' ') variant(s): $TODO"

BACKUP=$(mktemp)
cp "$CANON" "$BACKUP" 2>/dev/null || true
restore() { [ -s "$BACKUP" ] && cp "$BACKUP" "$CANON" ; rm -f "$BACKUP" ; }
trap 'echo; echo "interrupted -- restoring $CANON"; restore; exit 130' INT TERM

echo "# resumed $(date '+%Y-%m-%d %H:%M'): $TODO" | tee -a "$LOG"
HARNESS_RUN=0
for i in $TODO; do
	v="$VDIR/tc_${PURPOSE}.${i}.aut"
	if [ ! -f "$v" ]; then
		echo "skip: $v not found" >&2
		continue
	fi
	hdr=$(head -1 "$v" | tr -dc '0-9,')
	ntrans=$(echo "$hdr" | cut -d, -f2)
	nstates=$(echo "$hdr" | cut -d, -f3)

	cp "$v" "$CANON"
	bash EVALUATION/foodyou/seed_foods.sh > "$LOGDIR/v${i}.seed.log" 2>&1

	CONCRETIZATION_DEBUG_DIR="$LOGDIR/v${i}_captures" \
	PYTHONPATH=framework python -u framework/scripts/run.py \
	      --aut "$CANON" --platform android \
	      --system-interface EVALUATION/foodyou/model/system_interface_foodyou_copy.lnt \
	      --concrete-domain EVALUATION/foodyou/properties/concrete_domain.yml \
	      --type-description EVALUATION/foodyou/properties/type_description.yml \
	      --disruption-mapping EVALUATION/foodyou/properties/disruption_mapping.yml \
	      --device-config "$DEV" --timeout "${TIMEOUT:-10}" \
	      --report --verbose > "$LOGDIR/v${i}.log" 2>&1
	rc=$?
	V=$(perl -pe 's/\e\[[0-9;]*m//g' < "$LOGDIR/v${i}.log" \
	    | grep -oE '(Verdict: (PASS|FAIL|INCONC)|Status: UNEXECUTABLE)' \
	    | head -1 | awk '{print $2}')

	if [ "$rc" -eq 2 ]; then
		# Same rule as run_variants.sh: only a run that could not START
		# ("HARNESS FAILURE:" from run.py) counts toward the abort.
		if grep -q "HARNESS FAILURE:" "$LOGDIR/v${i}.log"; then
			HARNESS_RUN=$((HARNESS_RUN + 1))
		else
			HARNESS_RUN=0
		fi
		printf "%-9s %8s %12s   %s\n" "$i" "$nstates" "$ntrans" "UNEXECUTABLE" | tee -a "$LOG"
		if [ "$HARNESS_RUN" -ge 3 ]; then
			echo "ABORT: 3 consecutive harness failures -- the device cannot start a" | tee -a "$LOG"
			echo "  test case. Remaining variants are NOT run. Check the device, then" | tee -a "$LOG"
			echo "  re-run: bash EVALUATION/foodyou/run_variants_resume.sh $PURPOSE" | tee -a "$LOG"
			break
		fi
		continue
	fi
	HARNESS_RUN=0
	printf "%-9s %8s %12s   %s\n" "$i" "$nstates" "$ntrans" "${V:-ERROR}" | tee -a "$LOG"
done

restore
trap - INT TERM
echo "# resume finished $(date '+%Y-%m-%d %H:%M')" | tee -a "$LOG"
