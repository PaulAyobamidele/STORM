#!/bin/sh
# generate_tc_all.sh -- per test purpose, the complete test graph (-all) and
# every controllable test case (extract_all), on the licensed CADP node.
#
# FLAT layout: every input in the CURRENT directory; subdirectories are never
# read. Verify a push with the md5 list, not a grep.
#
#   sh generate_tc_all.sh               every purpose in $TPS
#   sh generate_tc_all.sh db_abort      just one
#
# Writes, for pulling back with the cases into EVALUATION/simplebaby/ (notes/TEST_PATH.md, CAPTURING_METRICS):
#   inputs.md5      md5 of every generator input, as read by this run
#   model_size.txt  bcg_info of compose_simplebaby.bcg, with the date
#   gen_times.tsv   purpose, seconds, cases (one row per purpose this run)
# ----------------------------------------------------------------------------
set -e

SUT=simplebaby
TPS="${*:-nominal_signed nominal_guest ue_kill ue_offline ue_storage_full app_unavailable app_key_lost app_cache_stale db_abort db_corrupt db_corrupt_local db_data_lost infra_db_down infra_storage_media infra_doze input_invalid input_overnight}"
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
INPUTS="${SUT}_types.lnt ${SUT}_fixture.lnt specification_${SUT}.lnt system_interface_${SUT}.lnt compose_${SUT}.lnt ${SUT}.io accept.ren refuse.ren generate_tc_all.sh"
for f in tp_*.lnt; do INPUTS="$INPUTS $f"; done
for f in $INPUTS; do
  [ -r "$f" ] || { echo "ERROR: missing input '$f' in $(pwd)" >&2; exit 1; }
done
md5sum $INPUTS > inputs.md5
echo "input hashes: inputs.md5 ($(wc -l < inputs.md5) files)"

# the composed model first, and its size (CAPTURING_METRICS: model size)
echo "==> compose_${SUT}.bcg"
lnt.open -main COMPOSED -silent "compose_${SUT}.lnt" generator "compose_${SUT}.bcg"
{ date '+%Y-%m-%d %H:%M:%S'; bcg_info "compose_${SUT}.bcg"; } > model_size.txt
if ! grep -q 'no transition with a hidden label' model_size.txt; then
  echo "ERROR: compose_${SUT}.bcg has hidden transitions (see model_size.txt)" >&2; exit 1
fi
[ -f gen_times.tsv ] || printf 'purpose\tseconds\tcases\n' > gen_times.tsv

# Stale artefacts from a previous run look current to everything downstream.
# Clear only what is about to be rebuilt, so a single-purpose run does not
# wipe the other purposes' output. One directory per purpose keeps a partial
# re-extraction visible.
for name in $TPS; do
  mkdir -p "variants/${name}"
  rm -f "tp_${name}.bcg" "${SUT}_${name}.ctg.bcg" \
        "TC.${SUT}_${name}".*.bcg "variants/${name}/tc_${name}".*.aut
done

SUMMARY=""
FAILED=""

for name in $TPS; do
  echo "======================================================================"
  echo "==> $name"
  SECONDS=0
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

  # The concretizer derives the TARGET fault from the filename tc_<fault>.aut.
  # A suffixed name like tc_db_corrupt.2.aut does NOT match, so the fault would
  # silently go untargeted. Keep variant 1 under the canonical name -- that is
  # the one run.py walks -- and leave the alternatives in variants/ for the
  # per-variant runner, which installs each one under the canonical name for
  # its run.
  cp "variants/${name}/tc_${name}.1.aut" "tc_${name}.aut"
  echo "     canonical: tc_${name}.aut (= variant 1)"
  printf '%s\t%s\t%s\n' "$name" "$SECONDS" "$N" >> gen_times.tsv
  SUMMARY="$SUMMARY
  ${name}: ${N} test case(s), ${SECONDS} s"
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
echo "and gen_times.tsv, model_size.txt, inputs.md5 to EVALUATION/${SUT}/"

rm -f *.o *.t *.f *.lotos *.lib *.h
