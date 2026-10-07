#!/usr/bin/env bash
# investigate_variants.sh -- re-run the FAIL variants of one test purpose with
# full diagnostics kept, and classify each FAIL.
#
#     source EVALUATION/foodyou/env.sh
#     bash EVALUATION/foodyou/investigate_variants.sh happy            # every FAIL in variants_happy.log
#     bash EVALUATION/foodyou/investigate_variants.sh happy 2 4 6      # only these
#     REPEATS=3 bash EVALUATION/foodyou/investigate_variants.sh happy  # determinism check
#
# run_variants.sh answers "what verdict", discarding stderr and the execution
# report; that is why a FAIL there cannot be told apart from a driver hiccup.
# This keeps everything: each run's stdout+stderr lands in
# generated/investigate/<purpose>/v<N>.run<K>.log, and classify_failure.py reads
# the failing step out of it.
#
# REPEATS > 1 is the decisive test. The variant AUT is fixed, so two runs of the
# SAME variant differing in verdict cannot be an ioco property of that test case
# -- it is the emulator, the timeouts, or leftover SUT state. A variant that
# fails identically on every repeat is a stable observation about the SUT.
#
# Like run_variants.sh, each variant is copied over the canonical
# tc_<purpose>.aut for its run (run.py derives the target fault from the file
# NAME), and the canonical file is restored at the end, including on Ctrl-C.
set -u

PURPOSE="${1:-}"
if [ -z "$PURPOSE" ]; then
	echo "usage: bash EVALUATION/foodyou/investigate_variants.sh <purpose> [variant ...]" >&2
	exit 1
fi
shift || true
: "${DEV:?source EVALUATION/foodyou/env.sh first}"

# Refuse to run against an environment that cannot support the test. The external
# source is expected to work, so a search that fails is a conformance FAIL -- which
# is only sound if the device could have reached it. Set SKIP_ENV_CHECK=1 to
# override, but understand that external-source verdicts then describe the
# environment rather than the SUT.
if [ "${SKIP_ENV_CHECK:-0}" != "1" ]; then
	bash EVALUATION/foodyou/check_env.sh || exit 1
fi

REPEATS="${REPEATS:-2}"
TIMEOUT="${TIMEOUT:-10}"

TC=EVALUATION/foodyou/Test_Cases
CANON="$TC/tc_${PURPOSE}.aut"
OUT="EVALUATION/foodyou/generated/investigate/${PURPOSE}"
SUMMARY="EVALUATION/foodyou/investigate_${PURPOSE}.log"
mkdir -p "$OUT"

# --- which variants -------------------------------------------------------
# Explicit list wins; otherwise take every FAIL from the sweep log, so the
# investigation is driven by the evidence rather than a hand-copied list.
if [ "$#" -gt 0 ]; then
	# Keep only numeric arguments. zsh does not strip trailing `# comments` from
	# an interactive command line, so a pasted "... 2 4 6   # FAILs" arrives here
	# as two extra "variants" named "#" and "FAILs".
	WANT=""
	for a in "$@"; do
		case "$a" in
			''|*[!0-9]*) : ;;
			*)           WANT="$WANT $a" ;;
		esac
	done
	if [ -z "$WANT" ]; then
		echo "no numeric variant given: $*" >&2
		exit 1
	fi
else
	SWEEP="EVALUATION/foodyou/variants_${PURPOSE}.log"
	if [ ! -f "$SWEEP" ]; then
		echo "no sweep log at $SWEEP -- run run_variants.sh $PURPOSE first," >&2
		echo "or name the variants explicitly." >&2
		exit 1
	fi
	WANT=$(awk '$4 == "FAIL" || $4 == "ERROR" { print $1 }' "$SWEEP")
fi
if [ -z "$WANT" ]; then
	echo "nothing to investigate: no FAIL/ERROR rows found." >&2
	exit 1
fi

BACKUP=$(mktemp)
cp "$CANON" "$BACKUP" 2>/dev/null || true
restore() { [ -s "$BACKUP" ] && cp "$BACKUP" "$CANON" ; rm -f "$BACKUP" ; }
trap 'echo; echo "interrupted -- restoring $CANON"; restore; exit 130' INT TERM

{
	echo "# FoodYou FAIL investigation -- purpose: $PURPOSE -- $(date '+%Y-%m-%d %H:%M')"
	echo "# repeats=$REPEATS timeout=${TIMEOUT}s   logs in $OUT"
	printf "%-8s %-4s %-8s %-14s %-6s %-26s %s\n" \
	       "VARIANT" "RUN" "VERDICT" "CLASS" "ARITH" "GATE" "ERROR"
} | tee "$SUMMARY"

for i in $WANT; do
	# Per-purpose directory, falling back to the older flat layout.
	SRC="$TC/variants/${PURPOSE}/tc_${PURPOSE}.${i}.aut"
	[ -f "$SRC" ] || SRC="$TC/variants/tc_${PURPOSE}.${i}.aut"
	if [ ! -f "$SRC" ]; then
		printf "%-8s %-4s %-8s %-14s %-6s %-26s %s\n" \
		       "$i" "-" "MISSING" "-" "-" "-" "$SRC" | tee -a "$SUMMARY"
		continue
	fi

	VERDICTS=""
	for k in $(seq 1 "$REPEATS"); do
		LOG="$OUT/v${i}.run${k}.log"
		cp "$SRC" "$CANON"
		bash EVALUATION/foodyou/seed_foods.sh >"$OUT/v${i}.run${k}.seed.log" 2>&1

		# -u so the interleaving of print() (stdout) and logging (stderr) in the
		# captured file matches the real order; --verbose keeps the walker trace,
		# which is the only record of a verdict returned without a logged step.
		# Scope failure captures to this run's own directory (see run_variants.sh
		# for why: an unlinked flat capture dir is how the v47 crash sat unnoticed).
		CONCRETIZATION_DEBUG_DIR="$OUT/v${i}_run${k}_captures" \
		PYTHONPATH=framework python -u framework/scripts/run.py \
		  --aut "$CANON" --platform android \
		  --system-interface EVALUATION/foodyou/model/system_interface_foodyou_copy.lnt \
		  --concrete-domain EVALUATION/foodyou/properties/concrete_domain.yml \
		  --type-description EVALUATION/foodyou/properties/type_description.yml \
		  --disruption-mapping EVALUATION/foodyou/properties/disruption_mapping.yml \
		  --device-config "$DEV" --timeout "$TIMEOUT" \
		  --report --verbose >"$LOG" 2>&1

		LINE=$(python framework/scripts/classify_failure.py "$LOG" --tsv)
		V=$(echo "$LINE"  | cut -f1)
		C=$(echo "$LINE"  | cut -f2)
		G=$(echo "$LINE"  | cut -f3)
		E=$(echo "$LINE"  | cut -f4 | cut -c1-70)
		# Arithmetic findings never end a walk, so they do not reach the verdict
		# and used to vanish from this table entirely -- a PASS could carry a
		# TOTAL MISMATCH and read as clean. `abst` means the exact-sum ledger
		# switched itself off partway, which is not the same as finding nothing.
		A=$(echo "$LINE"  | cut -f5)
		LD=$(echo "$LINE" | cut -f6)
		if [ "$LD" = "UNKNOWN" ]; then A="abst"
		elif [ "${A:-0}" = "0" ];  then A="-"
		fi
		VERDICTS="$VERDICTS $V"

		printf "%-8s %-4s %-8s %-14s %-6s %-26s %s\n" \
		       "$i" "$k" "$V" "$C" "$A" "${G:--}" "${E:--}" | tee -a "$SUMMARY"
	done

	# Stability: identical AUT, differing verdicts => not a property of the test
	# case. Reported per variant so the two questions stay separate.
	UNIQ=$(echo "$VERDICTS" | tr ' ' '\n' | grep -v '^$' | sort -u | tr '\n' '/' | sed 's|/$||')
	case "$UNIQ" in
		*/*) printf "%-8s %-4s %-8s %-14s %s\n" \
		            "$i" "=" "$UNIQ" "FLAKY" \
		            "same AUT, different verdicts -- environment, not ioco" | tee -a "$SUMMARY" ;;
		*)   printf "%-8s %-4s %-8s %-14s %s\n" \
		            "$i" "=" "$UNIQ" "STABLE" \
		            "reproducible across $REPEATS runs" | tee -a "$SUMMARY" ;;
	esac
done

restore
trap - INT TERM

{
	echo "----------------------------------------------------------------"
	echo "canonical $CANON restored"
	echo
	echo "class counts (per run):"
	awk 'NF>=4 && $2 ~ /^[0-9]+$/ { c[$4]++ } END { for (k in c) printf "  %-14s %d\n", k, c[k] }' "$SUMMARY"
	echo
	# A sweep of PASSes is only a clean bill of health if the ARITH column is
	# clean too. Report it separately so it cannot be read past.
	awk 'NF>=5 && $2 ~ /^[0-9]+$/ && $5 != "-" {
	         if ($5 == "abst") a++ ; else { f++ ; k += $5 }
	         rows = rows sprintf("    variant %s run %s: %s\n", $1, $2, $5)
	     }
	     END {
	         if (f) printf "ARITHMETIC: %d run(s) carry %d finding(s) the verdict does not show\n", f, k
	         if (a) printf "LEDGER:     %d run(s) abstained -- the exact-sum check switched off partway\n", a
	         if (f || a) printf "%s", rows
	         if (!f && !a) print "arithmetic: none -- every run kept its exact-sum ledger and agreed with the device"
	     }' "$SUMMARY"
	echo
	echo "  IOCO        real counter-example: the SUT contradicted the spec"
	echo "  QUIESCENCE  SUT silent where an output was required -- confirm the"
	echo "              observation was reachable and TIMEOUT was long enough"
	echo "              (re-run with TIMEOUT=30 to separate slow from silent)"
	echo "  ARTIFACT    the tester's own stimulus failed -- NOT an ioco verdict"
	echo "  FLAKY       verdict not reproducible for a fixed AUT"
	echo
	echo "per-run detail:  python framework/scripts/classify_failure.py $OUT/v<N>.run<K>.log --trace 20"
} | tee -a "$SUMMARY"

echo "written to $SUMMARY"
