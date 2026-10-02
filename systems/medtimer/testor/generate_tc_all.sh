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
# an updated model into a model/ or test_purposes/ mirror is a silent no-op.
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
#   2. COMPOSED x tp_X -all -> medtimer_X.ctg.bcg    (complete test graph)
#   3. extract_all on the full CTG (count logged; it is one case here)
#   4. per accepting branch k: tp_X_a<k> (other ACCEPTs -> REFUSE) -> CTG ->
#      extract_all -> variants/X/tc_X.<i>.aut, mapped in variants/X/arms.tsv
#      (+ tc_X.aut for variant 1)
# ----------------------------------------------------------------------------
set -e

SUT=medtimer

# The purposes to derive, as tp_<name>.lnt. The name MUST be the
# target fault gate lower-cased (tc_<name>.aut -> <NAME> is how the
# concretizer finds the injection); the nominal purpose is the exception.
TPS="${*:-nominal ue_kill app_write_fail db_abort infra_storage_full app_cache_stale db_corrupt db_corrupt_stock db_event_loss infra_storage_media input_invalid cannot_skip delete_skipped edit_flip}"

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
        "TC.${SUT}_${name}".*.bcg "variants/${name}/tc_${name}".*.aut "variants/${name}/arms.tsv"
done

SUMMARY=""
FAILED=""

# Provenance and sizes, written beside the outputs and pulled back with them
# (never /tmp: it is cleared on the node).
#   inputs.md5      md5 of every generator input, to diff against the Mac's
#   model_size.txt  bcg_info of the composed SPEC || SI
#   gen_times.tsv   purpose, seconds, cases -- appended, never truncated
md5sum ${SUT}_types.lnt ${SUT}_fixture.lnt specification_${SUT}.lnt \
       system_interface_${SUT}.lnt compose_${SUT}.lnt ${SUT}.io accept.ren refuse.ren \
       generate_tc_all.sh tp_*.lnt > inputs.md5
if [ ! -r "compose_${SUT}.bcg" ] || [ "compose_${SUT}.lnt" -nt "compose_${SUT}.bcg" ] \
   || [ "system_interface_${SUT}.lnt" -nt "compose_${SUT}.bcg" ] \
   || [ "specification_${SUT}.lnt" -nt "compose_${SUT}.bcg" ]; then
  echo "building compose_${SUT}.bcg"
  lnt.open -main COMPOSED "compose_${SUT}.lnt" generator "compose_${SUT}.bcg"
fi
{ date '+%Y-%m-%d %H:%M:%S'; bcg_info "compose_${SUT}.bcg"; } > model_size.txt
[ -r gen_times.tsv ] || printf 'purpose\tseconds\tcases\n' > gen_times.tsv

for name in $TPS; do
  echo "======================================================================"
  echo "==> $name"
  T0=$(date +%s)
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

  echo "  3. extract_all on the full CTG (reported only)"
  # In this model every tester choice is between two STIMULI (the fault gate
  # stands before the commit tap), which TESTOR does not count as a
  # controllability conflict: the full CTG extracts as ONE test case holding
  # every branch, and the walker follows one of them. So the suite is built
  # per accepting branch, step 4; this count is logged for the record.
  rm -rf "xa_${name}"; mkdir -p "xa_${name}"
  "$EXTRACT_ALL" -copy -io "${SUT}.io" "${SUT}_${name}.ctg.bcg" "xa_${name}/TC" > "xa_${name}.log" 2>&1 || true
  echo "     extract_all on full CTG: $(ls xa_${name}/TC.*.bcg 2>/dev/null | wc -l) test case(s)"
  rm -rf "xa_${name}"

  echo "  4. one TESTOR test case per accepting branch of the purpose"
  # Copy k of the purpose keeps its k-th TP_ACCEPT and turns every other one
  # into TP_REFUSE; TESTOR then derives the CTG of that branch alone and
  # extract_all its controllable test case(s). variants/<name>/arms.tsv maps
  # each test case to its branch.
  ARMS=$(grep -c 'loop TP_ACCEPT end loop' "tp_${name}.lnt")
  echo "     $ARMS accepting branch(es)"
  printf 'variant\tarm\tctg_states\tctg_transitions\n' > "variants/${name}/arms.tsv"
  N=0
  K=1
  while [ "$K" -le "$ARMS" ]; do
    ARM="tp_${name}_a${K}"
    awk -v k="$K" '{ if (index($0, "loop TP_ACCEPT end loop")) { n++; if (n != k) sub(/loop TP_ACCEPT end loop/, "loop TP_REFUSE end loop") } print }' \
        "tp_${name}.lnt" | sed -e "s/^module tp_${name} /module ${ARM} /" > "${ARM}.lnt"
    lnt.open -main MAIN -silent "${ARM}.lnt" generator \
        -rename accept.ren -rename refuse.ren "${ARM}.bcg" > /dev/null 2>&1
    lnt.open -main COMPOSED "compose_${SUT}.lnt" "$TESTOR" \
        -io "${SUT}.io" -all "${ARM}.bcg" "${ARM}.ctg.bcg" > "${ARM}.log" 2>&1
    if ! bcg_info -labels "${ARM}.ctg.bcg" | grep -q ':PASS:' ; then
      echo "     branch $K: no reachable :PASS: (the specification refuses it)"
      FAILED="$FAILED $name/a$K(no-pass)"
      K=$((K + 1)); continue
    fi
    ACTG=$(bcg_info -size "${ARM}.ctg.bcg" | sed -e 's/ states, /\t/' -e 's/ transitions//')
    rm -f "TC.${ARM}".*.bcg
    "$EXTRACT_ALL" -check -copy -io "${SUT}.io" "${ARM}.ctg.bcg" "TC.${ARM}" > "${ARM}.xa.log" 2>&1
    for tc in $(ls -1 "TC.${ARM}".*.bcg 2>/dev/null | sort -t. -k3 -n); do
      N=$((N + 1))
      bcg_io "$tc" "variants/${name}/tc_${name}.${N}.aut"
      printf '%s\t%s\t%s\n' "$N" "$K" "$ACTG" >> "variants/${name}/arms.tsv"
    done
    rm -f "${ARM}.lnt" "${ARM}.bcg" "${ARM}.ctg.bcg" "TC.${ARM}".*.bcg
    K=$((K + 1))
  done
  echo "     ${N} test case(s) from ${ARMS} branch(es)"

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
  printf '%s\t%s\t%s\n' "$name" "$(( $(date +%s) - T0 ))" "$N" >> gen_times.tsv
  cp "variants/${name}/tc_${name}.1.aut" "tc_${name}.aut"
  echo "     canonical: tc_${name}.aut (= variant 1)"

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
echo "bring back tc_*.aut and variants/ to systems/${SUT}/generated/tc/"
echo "bring back gen_times.tsv, model_size.txt and generate_tc_all.log (CTG sizes) to systems/${SUT}/"

rm -f *.o *.t *.f *.lotos *.lib *.h
