#!/bin/sh
# generate_tc_all.sh -- per test purpose, extract EVERY controllable test case
# of the composed model, not just the one TESTOR picks on the fly.
#
# Builds the Complete Test Graph (-all) and then runs TESTOR's extract_all,
# which enumerates one test case per way of resolving the controllability
# conflicts. A purpose with no conflicts yields exactly one test case; where
# there are several, they are real alternative strategies the tester could
# follow, and dropping them silently understates what the purpose exercises.
#
# FLAT layout: expects ALL inputs in the CURRENT directory (the licensed CADP
# node's scratch directory). Files in subdirectories are NEVER read -- pushing
# an updated model into a model/ or Test_Purposes/ mirror is a silent no-op.
# Always verify a push landed with a content grep before trusting a run.
#
#   export CADP=/path/to/cadp
#   export PATH=$CADP/com:$CADP/bin.x64:$PATH
#   cd <flat scratch dir>
#   sh generate_tc_all.sh               # every purpose in $TPS
#   sh generate_tc_all.sh db_corrupt    # just one
#
# Per test purpose:
#   1. tp_X.lnt            -> tp_X.bcg              (TP_ACCEPT->ACCEPT, TP_REFUSE->REFUSE)
#   2. COMPOSED x tp_X -all -> mastodon_X.ctg.bcg    (complete test graph)
#   3. extract_all         -> TC.mastodon_X.<i>.bcg  (every controllable test case)
#   4. bcg_io              -> variants/X/tc_X.<i>.aut (+ tc_X.aut for variant 1)
# ----------------------------------------------------------------------------
set -e

SUT=mastodon

# The purposes to derive: every tp_<name>.lnt here, unless names are given.
# <name> is the target fault lower-cased (tc_<name>.aut -> <NAME> is how the
# concretizer finds the injection); nominal is the exception. Each purpose
# yields as many cases as extract_all resolves: variants/<name>/.
TPS="${*:-$(ls tp_*.lnt 2>/dev/null | sed -e 's/^tp_//' -e 's/\.lnt$//' | sort)}"

if [ -z "$CADP" ] || [ ! -d "$CADP" ]; then
  echo "ERROR: \$CADP must point to the CADP install." >&2; exit 1
fi
ARCH=$("$CADP/com/arch")

# extract_all lives in the TESTOR distribution, not in CADP proper. It reads
# $TESTOR_DIR/com/common.sh, so TESTOR_DIR must be exported, not just set.
export TESTOR_DIR=${TESTOR_DIR:-$CADP}
if   [ -x "$TESTOR_DIR/com/extract_all" ]; then EXTRACT_ALL="$TESTOR_DIR/com/extract_all"
elif [ -x "$CADP/com/extract_all" ];       then EXTRACT_ALL="$CADP/com/extract_all"
else
  echo "ERROR: cannot find com/extract_all under \$TESTOR_DIR ($TESTOR_DIR) or \$CADP." >&2
  exit 1
fi

if   [ -r ./testor ]; then TESTOR=./testor
elif [ -r "$TESTOR_DIR/bin.$ARCH/testor.a" ]; then TESTOR="$TESTOR_DIR/bin.$ARCH/testor.a"
elif [ -r "$CADP/bin.$ARCH/testor.a" ]; then TESTOR="$CADP/bin.$ARCH/testor.a"
else echo "ERROR: cannot find testor.a" >&2; exit 1; fi
echo "using testor:      $TESTOR"
echo "using extract_all: $EXTRACT_ALL"

# Limit virtual memory to 80% of physical RAM. ONLY EVER LOWER IT: under a
# batch scheduler the wrapper has already capped the limit to the job's
# allocation, and raising it is refused by the kernel -- which with `set -e`
# kills the run two seconds in. Apply the target only if it is tighter than
# what is in force, and never let the call be fatal.
MEMORY_SIZE=$("$CADP/bin.$ARCH/cadp_memory" -physical)
MEMORY_LIMIT=$(echo "0.8 * $MEMORY_SIZE / 1024" | bc -l | sed 's/[.][0-9]*$//')
CURRENT_LIMIT=$(ulimit -v)
if [ "$CURRENT_LIMIT" = "unlimited" ] || [ "$MEMORY_LIMIT" -lt "$CURRENT_LIMIT" ]; then
  if ulimit -v "$MEMORY_LIMIT" 2>/dev/null; then
    echo "limiting virtual memory to $MEMORY_LIMIT kbytes"
  else
    echo "could not lower virtual memory limit; keeping $CURRENT_LIMIT kbytes" >&2
  fi
else
  echo "virtual memory already capped at $CURRENT_LIMIT kbytes -- keeping it"
fi

# Every module the composition or a purpose imports must be here, flat.
for f in ${SUT}_types.lnt ${SUT}_fixture.lnt specification_${SUT}.lnt \
         system_interface_${SUT}.lnt compose_${SUT}.lnt \
         ${SUT}.io accept.ren refuse.ren; do
  [ -r "$f" ] || { echo "ERROR: missing input '$f' in $(pwd)" >&2; exit 1; }
done

# Stale artefacts from a previous run look current to everything downstream.
# Clear only what is about to be rebuilt, so a single-purpose run does not
# wipe the other purposes' output. One directory per purpose keeps a partial
# re-extraction visible.
for name in $TPS; do
  mkdir -p "variants/${name}"
  rm -f "tp_${name}.bcg" "${SUT}_${name}.ctg.bcg" \
        "TC.${SUT}_${name}".*.bcg "variants/${name}/tc_${name}".*.aut
done

# model_size.txt (File 2's companion): the composed model SPEC || SI, once per run
echo "==> model size (compose_${SUT}.bcg)"
lnt.open -main COMPOSED "compose_${SUT}.lnt" generator "compose_${SUT}.bcg" > compose_build.log 2>&1 \
  && { date '+%Y-%m-%d %H:%M:%S'; bcg_info "compose_${SUT}.bcg"; } > model_size.txt \
  || echo "  WARNING: could not build compose_${SUT}.bcg; see compose_build.log" >&2
# appended, never truncated: a single-purpose run must not wipe the others'
# rows (eval_tables.py takes the last row per purpose)
[ -f gen_times.tsv ] || printf 'purpose\tseconds\tcases\n' > gen_times.tsv

SUMMARY=""
FAILED=""

for name in $TPS; do
  echo "======================================================================"
  echo "==> $name"
  GEN_T0=$(date +%s)
  [ -r "tp_${name}.lnt" ] || { echo "  SKIP: tp_${name}.lnt not found"; continue; }

  echo "  1. tp -> BCG"
  lnt.open -main MAIN -silent "tp_${name}.lnt" generator \
      -rename accept.ren -rename refuse.ren "tp_${name}.bcg"

  echo "  2. COMPOSED x tp -all -> complete test graph"
  lnt.open -main COMPOSED "compose_${SUT}.lnt" "$TESTOR" \
      -io "${SUT}.io" -all "tp_${name}.bcg" "${SUT}_${name}.ctg.bcg"

  # An empty CTG means the purpose selects no trace of the composed model --
  # it is over-constrained. testor still exits 0, so this has to be checked.
  CTG_SIZE=$(bcg_info -size "${SUT}_${name}.ctg.bcg")
  echo "     ctg: $CTG_SIZE"
  # Is a verdict reachable at all? The question is whether :PASS: exists, NOT
  # whether :INCONCLUSIVE: does. An inconclusive branch is normal for any
  # purpose of the form FAULT; RESPONSE; ACCEPT (the fault fires and the
  # response never comes). Rejecting on it once discarded three satisfiable
  # purposes.
  if ! bcg_info -labels "${SUT}_${name}.ctg.bcg" | grep -q ':PASS:' ; then
    echo "  WARNING: CTG has no reachable :PASS: -- tp_${name} is unsatisfiable" >&2
    FAILED="$FAILED $name(no-pass)"
    continue
  fi

  echo "  3. extract_all -> controllable test cases"
  # -check  verify each extracted test case (prefix included, PASS reachable)
  # -copy   emit the CTG itself as TC.*.1.bcg when it is already controllable
  # (INCONCLUSIVE branches of the CTG are kept: extract_all builds each case
  #  with -refuse refuse_inconclusive; there is no -keep option)
  "$EXTRACT_ALL" -check -copy -io "${SUT}.io" \
      "${SUT}_${name}.ctg.bcg" "TC.${SUT}_${name}"

  echo "  4. BCG -> AUT"
  N=0
  for tc in $(ls -1 "TC.${SUT}_${name}".*.bcg 2>/dev/null | sort -t. -k3 -n); do
    I=$(echo "$tc" | sed -e 's/.*\.\([0-9][0-9]*\)\.bcg$/\1/')
    bcg_io "$tc" "variants/${name}/tc_${name}.${I}.aut"
    NTRANS=$(head -1 "variants/${name}/tc_${name}.${I}.aut" | tr -dc '0-9,' | cut -d, -f2)
    echo "     variants/${name}/tc_${name}.${I}.aut (${NTRANS} transitions)"
    N=$((N + 1))
  done
  if [ "$N" -eq 0 ]; then
    echo "  ERROR: extract_all produced no test case for $name" >&2
    FAILED="$FAILED $name(no-tc)"
    continue
  fi
  # the concretizer takes the fault from tc_<fault>.aut: variant 1 under the
  # canonical name; run_suite.sh installs each variant there for its walk
  cp "variants/${name}/tc_${name}.1.aut" "tc_${name}.aut"
  echo "     canonical: tc_${name}.aut (= variant 1)"

  # per purpose, appended (the last row per purpose wins): purpose, seconds, cases
  printf '%s\t%s\t%s\n' "$name" "$(( $(date +%s) - GEN_T0 ))" "$N" | tee -a gen_times.tsv   # File 2
  SUMMARY="$SUMMARY
  ${name}: ${N} test case(s)"
done

echo "======================================================================"
echo "test cases per purpose:$SUMMARY"
echo
if [ -n "$FAILED" ]; then
  echo "PROBLEM PURPOSES:$FAILED" >&2
  echo "  An unsatisfiable purpose or an empty extraction is a finding about" >&2
  echo "  the model, not a purpose to quietly drop from the sweep." >&2
fi
echo "canonical AUTs (walked by run.py): $(ls tc_*.aut 2>/dev/null | tr '\n' ' ')"
echo "alternatives:                      variants/<purpose>/tc_<purpose>.N.aut"
echo
echo "bring back tc_*.aut and variants/ to EVALUATION/${SUT}/Test_Cases/,"
echo "and gen_times.tsv and model_size.txt to EVALUATION/${SUT}/"

rm -f *.o *.t *.f *.lotos *.lib *.h
