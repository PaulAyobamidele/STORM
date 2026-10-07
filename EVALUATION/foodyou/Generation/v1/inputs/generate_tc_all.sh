#!/bin/sh
# generate_tc_all.sh — per test purpose, extract EVERY controllable test case,
# not just the one testor picks on the fly.
#
# generate_all.sh runs testor WITHOUT -all, so it yields a single test case per
# purpose: testor resolves each controllability conflict itself. This script
# instead builds the complete test graph (-all) and then runs TESTOR's
# extract_all, which enumerates one test case per way of resolving those
# conflicts. For a purpose with no conflicts you get exactly one test case and
# the two scripts agree; where they disagree, the extra test cases are real
# alternative strategies the tester could follow, and dropping them silently
# understates what the purpose can exercise.
#
# FLAT layout: expects all inputs in the CURRENT directory, as on narval3's
# /scratch/paulad/testor_foodyou. Run it on the licensed node.
#
#   export CADP=/home/paulad/cadp
#   export PATH=$CADP/com:$CADP/bin.x64:$PATH
#   cd /scratch/paulad/testor_foodyou
#   sh generate_tc_all.sh              # all purposes
#   sh generate_tc_all.sh cache_stale  # just one
#
# Per test purpose:
#   1. tp_X.lnt              -> tp_X.bcg              (TP_ACCEPT->ACCEPT, TP_REFUSE->REFUSE)
#   2. COMPOSED x tp_X -all  -> foodyou_X.ctg.bcg     (complete test graph)
#   3. extract_all           -> TC.foodyou_X.<i>.bcg  (every controllable test case)
#   4. bcg_io                -> variants/X/tc_X.<i>.aut (+ tc_X.aut for variant 1)
# ----------------------------------------------------------------------------
set -e

if [ -z "$CADP" ] || [ ! -d "$CADP" ]; then
  echo "ERROR: \$CADP must point to the CADP install (e.g. /home/paulad/cadp)." >&2; exit 1
fi
ARCH=$("$CADP/com/arch")

# extract_all lives in the TESTOR distribution, not in CADP proper. It reads
# $TESTOR_DIR/com/common.sh, so TESTOR_DIR must be exported, not just set.
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

# Limit virtual memory to 80% of physical RAM (as in testor.sh) -- the CTG is
# much larger than a single test case, so this matters more here.
#
# ONLY EVER LOWER IT. Under Slurm the batch wrapper has already capped the limit
# to the cgroup allocation (e.g. 30 GB of a 32 GB job), while `cadp_memory
# -physical` reports the whole compute node (hundreds of GB). Raising a limit
# above the current hard limit is refused by the kernel, and with `set -e` that
# refusal killed the entire run two seconds in:
#
#   generate_tc_all.sh: line 58: ulimit: virtual memory: cannot modify limit:
#   Operation not permitted
#
# So: compute the target, apply it only if it is TIGHTER than what is already in
# force, and never let the call be fatal. On a login node nothing has been set,
# so the target applies as before; under Slurm the allocation's tighter limit is
# kept, which is the one that actually matters.
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
  echo "virtual memory already capped at $CURRENT_LIMIT kbytes (tighter than \
$MEMORY_LIMIT) -- keeping it"
fi

for f in foodyou_types.lnt specification_foodyou_copy.lnt \
         system_interface_foodyou_copy.lnt compose_foodyou_copy.lnt \
         foodyou.io accept.ren refuse.ren; do
  [ -r "$f" ] || { echo "ERROR: missing input '$f' in $(pwd)" >&2; exit 1; }
done

TPS="${*:-happy ue1_kill input_invalid extapi_fail cache_stale disruption_db db_corrupt storage_full storage_media}"

# Stale artefacts from a previous run look current to everything downstream.
# Only clear what we are about to rebuild, so a single-purpose run does not
# wipe the other purposes' output.
# One directory per purpose: variants/<purpose>/tc_<purpose>.<i>.aut. The names
# alone would disambiguate, but nine purposes in one flat directory is hundreds
# of files with no visual grouping, and a partial re-extraction of one purpose
# is impossible to see. A directory per purpose makes "what do I have for
# storage_full" a single `ls`.
for name in $TPS; do
  mkdir -p "variants/${name}"
  rm -f "tp_${name}.bcg" "foodyou_${name}.ctg.bcg" \
        "TC.foodyou_${name}".*.bcg "variants/${name}/tc_${name}".*.aut
done

SUMMARY=""
FAILED=""

for name in $TPS; do
  echo "======================================================================"
  echo "==> $name"
  [ -r "tp_${name}.lnt" ] || { echo "  SKIP: tp_${name}.lnt not found"; continue; }

  echo "  1. tp -> BCG"
  lnt.open -main MAIN -silent "tp_${name}.lnt" generator \
      -rename accept.ren -rename refuse.ren "tp_${name}.bcg"

  echo "  2. COMPOSED x tp -all -> complete test graph"
  # Timed together with step 3 below as "extraction time" -- eval_tables.py's
  # GEN t column, and the paper's per-purpose extraction-time cell. POSIX sh
  # (this script's shebang), not bash, so no $SECONDS -- date +%s twice and
  # subtract, same portable approach as run_variants.sh's TIME(s) column.
  _EXTRACT_T0=$(date +%s)
  lnt.open -main COMPOSED compose_foodyou_copy.lnt "$TESTOR" \
      -io foodyou.io -all "tp_${name}.bcg" "foodyou_${name}.ctg.bcg"

  # An empty CTG means the purpose selects no trace of the composed model --
  # over-constrained. testor still exits 0, so this has to be checked.
  CTG_SIZE=$(bcg_info -size "foodyou_${name}.ctg.bcg")
  echo "     ctg: $CTG_SIZE"
  # Is a verdict reachable at all? The question is whether :PASS: exists, NOT
  # whether :INCONCLUSIVE: does.
  #
  # This used to test for the PRESENCE of :INCONCLUSIVE: and call that
  # "INCONCLUSIVE-only" -- two different claims. An inconclusive branch is
  # normal and usually correct: a purpose of the form
  #
  #     THE_FAULT; THE_RESPONSE; loop TP_ACCEPT end loop
  #
  # necessarily admits a branch where the fault fires and the response never
  # comes, and that branch IS inconclusive. Rejecting on it discarded three
  # perfectly satisfiable purposes (extapi_fail, db_corrupt, storage_media),
  # each of which had a reachable :PASS: -- while the purposes that observe
  # CONFIRM_TOTAL instead had no inconclusive branch and sailed through. The
  # guard was selecting on modelling style, not on satisfiability.
  if ! bcg_info -labels "foodyou_${name}.ctg.bcg" | grep -q ':PASS:' ; then
    echo "  WARNING: CTG has no reachable :PASS: -- tp_${name} is unsatisfiable" >&2
    FAILED="$FAILED $name(no-pass)"
    continue
  fi

  echo "  3. extract_all -> controllable test cases"
  # -check  verify each extracted test case (prefix included, PASS reachable)
  # -copy   emit the CTG itself as TC.*.1.bcg when it is already controllable
  "$EXTRACT_ALL" -check -copy -io foodyou.io \
      "foodyou_${name}.ctg.bcg" "TC.foodyou_${name}"
  _EXTRACT_T1=$(date +%s)
  _EXTRACT_SECS=$((_EXTRACT_T1 - _EXTRACT_T0))

  echo "  4. BCG -> AUT"
  N=0
  for tc in $(ls -1 "TC.foodyou_${name}".*.bcg 2>/dev/null | sort -t. -k3 -n); do
    I=$(echo "$tc" | sed -e 's/.*\.\([0-9][0-9]*\)\.bcg$/\1/')
    bcg_io "$tc" "variants/${name}/tc_${name}.${I}.aut"
    NTRANS=$(head -1 "variants/${name}/tc_${name}.${I}.aut" | tr -dc '0-9,' | cut -d, -f2)
    echo "     variants/${name}/tc_${name}.${I}.aut (${NTRANS} transitions)"
    N=$((N + 1))
  done

  # extraction_stats.tsv: purpose  ISO-timestamp  seconds  variants_extracted.
  # eval_tables.py reads this for Table 2's GEN t column. Appended (not
  # overwritten) -- eval_tables.py's reader keeps the LAST row per purpose,
  # so a re-run's fresh row naturally wins without needing this script to
  # dedupe its own output file.
  #
  # WRITTEN INTO THE CURRENT DIRECTORY, not `../`. This script's own FLAT
  # layout on narval (cd /scratch/paulad/testor_foodyou; sh generate_tc_all.sh)
  # means `..` is /scratch/paulad -- the shared PARENT of every SUT's scratch
  # dir, not this SUT's own. `../extraction_stats.tsv` collided directly with
  # Moodle's identical script doing the same thing from testor_moodle/, into
  # the SAME file, one purpose name (`happy`) shared by both -- caught before
  # it ever actually ran, 2026-09-11. The Mac-side rsync (not this script) is
  # what maps this file up into EVALUATION/foodyou/, matching the local repo's
  # nested testor/ layout; this script no longer assumes that nesting exists.
  printf '%s\t%s\t%s\t%s\n' "$name" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      "$_EXTRACT_SECS" "$N" >> extraction_stats.tsv
  echo "     extraction: ${_EXTRACT_SECS}s -> ${N} test case(s)"

  if [ "$N" -eq 0 ]; then
    echo "  ERROR: extract_all produced no test case for $name" >&2
    FAILED="$FAILED $name(no-tc)"
    continue
  fi

  # The concretizer derives the TARGET fault from the filename tc_<fault>.aut
  # and looks <fault> up (uppercased) in FaultInjector.faults. A suffixed name
  # like tc_cache_stale.2.aut does NOT match, so the fault would silently go
  # untargeted. Keep variant 1 under the canonical name -- that is the one
  # run.py walks -- and leave the alternatives in variants/ for manual runs.
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
echo "bring back tc_*.aut and variants/ to the mac repo under"
echo "EVALUATION/foodyou/Test_Cases/ ; copy tc_happy.aut -> foodyou.tc.aut"
echo "for the default run command."

rm -f *.o *.t *.f *.lotos *.lib *.h
