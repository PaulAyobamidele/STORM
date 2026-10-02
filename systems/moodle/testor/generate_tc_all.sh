#!/bin/sh
# generate_tc_all.sh — per test purpose, extract EVERY controllable test case,
# not just the one testor picks on the fly.
#
# generate_all.sh runs testor WITHOUT -all, so it yields a single test case per
# purpose: testor resolves each controllability conflict itself. This script
# instead builds the complete test graph (-all) and then runs TESTOR's
# extract_all, which enumerates one test case per way of resolving those
# conflicts. Where the two agree the purpose had no conflict; where they differ,
# the extra cases are real alternative strategies the tester could follow.
#
# FLAT layout: expects all inputs in the CURRENT directory. Run on the node.
#
#   export CADP=/home/paulad/cadp
#   export PATH=$CADP/com:$CADP/bin.x64:$PATH
#   cd /scratch/paulad/testor_moodle
#   sh generate_tc_all.sh                        # all purposes
#   sh generate_tc_all.sh app_partial_submission # just one
#
# Per test purpose:
#   1. tp_X.lnt              -> tp_X.bcg             (TP_ACCEPT->ACCEPT, ...)
#   2. COMPOSED x tp_X -all  -> moodle_X.ctg.bcg     (complete test graph)
#   3. extract_all           -> TC.moodle_X.<i>.bcg  (every controllable case)
#   4. bcg_io                -> variants/X/tc_X.<i>.aut (+ tc_X.aut for #1)
# ----------------------------------------------------------------------------
set -e

if [ -z "$CADP" ] || [ ! -d "$CADP" ]; then
  echo "ERROR: \$CADP must point to the CADP install (e.g. /home/paulad/cadp)." >&2; exit 1
fi
ARCH=$("$CADP/com/arch")

# extract_all lives in the TESTOR distribution, not in CADP proper. It reads
# $TESTOR_DIR/com/common.sh, so TESTOR_DIR must be EXPORTED, not just set.
export TESTOR_DIR=${TESTOR_DIR:-$CADP}
if   [ -x "$TESTOR_DIR/com/extract_all" ]; then EXTRACT_ALL="$TESTOR_DIR/com/extract_all"
elif [ -x "$CADP/com/extract_all" ];       then EXTRACT_ALL="$CADP/com/extract_all"
else
  echo "ERROR: cannot find com/extract_all under \$TESTOR_DIR ($TESTOR_DIR) or \$CADP." >&2
  echo "       Point \$TESTOR_DIR at the TESTOR distribution root." >&2
  exit 1
fi

if   [ -r ./testor ]; then TESTOR=./testor
elif [ -r "$TESTOR_DIR/bin.$ARCH/testor.a" ]; then TESTOR="$TESTOR_DIR/bin.$ARCH/testor.a"
elif [ -r "$CADP/bin.$ARCH/testor.a" ]; then TESTOR="$CADP/bin.$ARCH/testor.a"
else echo "ERROR: cannot find testor.a" >&2; exit 1; fi
echo "using testor:      $TESTOR"
echo "using extract_all: $EXTRACT_ALL"

# Limit virtual memory to 80% of physical RAM -- the CTG is much larger than a
# single test case.
#
# ONLY EVER LOWER IT. Under Slurm the batch wrapper has already capped the limit
# to the cgroup allocation, while `cadp_memory -physical` reports the whole
# node. Raising above the current hard limit is refused by the kernel, and with
# `set -e` that refusal kills the run two seconds in.
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
  echo "virtual memory already capped at $CURRENT_LIMIT kbytes (tighter than $MEMORY_LIMIT) -- keeping it"
fi

for f in moodle_types.lnt specification_moodle.lnt \
         system_interface_moodle.lnt compose_moodle.lnt \
         moodle.io accept.ren refuse.ren; do
  [ -r "$f" ] || { echo "ERROR: missing input '$f' in $(pwd)" >&2; exit 1; }
done

TPS="${*:-happy app1_write_fail app_partial_submission app_grade_stale_sub app_lazy_regrade db_attempt_step_loss infra_cron_dead ue1_lose_conn ue2_session_expire}"

# One directory per purpose, so "what do I have for app_partial_submission" is a
# single ls. Only clear what is about to be rebuilt.
for name in $TPS; do
  mkdir -p "variants/${name}"
  rm -f "tp_${name}.bcg" "moodle_${name}.ctg.bcg" \
        "TC.moodle_${name}".*.bcg "variants/${name}/tc_${name}".*.aut
done

SUMMARY=""
FAILED=""

# Sizes and times, written beside the outputs and pulled back with them
# (never under /tmp: it is cleared on this node):
#   model_size.txt  bcg_info of the composed SPEC || SI, dated
#   gen_times.tsv   purpose, seconds, cases -- appended, header once, the
#                   last row per purpose wins
echo "  composed model: compose_moodle.bcg -> model_size.txt"
lnt.open -main COMPOSED compose_moodle.lnt generator compose_moodle.bcg > /dev/null
{ date '+%Y-%m-%d %H:%M:%S'; bcg_info compose_moodle.bcg; } > model_size.txt
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
  lnt.open -main COMPOSED compose_moodle.lnt "$TESTOR" \
      -io moodle.io -all "tp_${name}.bcg" "moodle_${name}.ctg.bcg"

  CTG_SIZE=$(bcg_info -size "moodle_${name}.ctg.bcg")
  echo "     ctg: $CTG_SIZE"

  # Is a verdict reachable at all? The question is whether :PASS: exists, NOT
  # whether :INCONCLUSIVE: does. An inconclusive branch is normal and usually
  # correct: a purpose of the form  FAULT; RESPONSE; TP_ACCEPT  necessarily
  # admits a branch where the fault fires and the response never comes, and
  # that branch IS inconclusive. Rejecting on it selects on modelling style,
  # not on satisfiability.
  if ! bcg_info -labels "moodle_${name}.ctg.bcg" | grep -q ':PASS:' ; then
    echo "  WARNING: CTG has no reachable :PASS: -- tp_${name} is unsatisfiable" >&2
    FAILED="$FAILED ${name}(no-pass)"
    continue
  fi

  echo "  3. extract_all -> controllable test cases"
  # -check  verify each extracted case (prefix included, PASS reachable)
  # -copy   emit the CTG itself as TC.*.1.bcg when it is already controllable
  "$EXTRACT_ALL" -check -copy -io moodle.io \
      "moodle_${name}.ctg.bcg" "TC.moodle_${name}"

  echo "  4. BCG -> AUT"
  N=0
  for tc in $(ls -1 "TC.moodle_${name}".*.bcg 2>/dev/null | sort -t. -k3 -n); do
    I=$(echo "$tc" | sed -e 's/.*\.\([0-9][0-9]*\)\.bcg$/\1/')
    bcg_io "$tc" "variants/${name}/tc_${name}.${I}.aut"
    NTRANS=$(head -1 "variants/${name}/tc_${name}.${I}.aut" | tr -dc '0-9,' | cut -d, -f2)
    echo "     variants/${name}/tc_${name}.${I}.aut (${NTRANS} transitions)"
    N=$((N + 1))
  done

  if [ "$N" -eq 0 ]; then
    echo "  ERROR: extract_all produced no test case for $name" >&2
    FAILED="$FAILED ${name}(no-tc)"
    continue
  fi

  # The concretizer derives the TARGET fault from the filename tc_<fault>.aut.
  # A suffixed name like tc_app_lazy_regrade.2.aut does NOT match, so the fault
  # would silently go untargeted. Keep variant 1 under the canonical name --
  # that is the one run.py walks -- and leave alternatives in variants/.
  cp "variants/${name}/tc_${name}.1.aut" "tc_${name}.aut"
  echo "     canonical: tc_${name}.aut (= variant 1)"
  printf '%s\t%s\t%s\n' "$name" "$(( $(date +%s) - T0 ))" "$N" >> gen_times.tsv

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
echo "bring back gen_times.tsv and model_size.txt to systems/moodle/"
echo "bring back tc_*.aut and variants/ to the mac repo under"
echo "systems/moodle/generated/tc/"

rm -f *.o *.t *.f *.lotos *.lib *.h
