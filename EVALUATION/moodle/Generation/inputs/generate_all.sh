#!/bin/sh
# generate_all.sh — regenerate every Moodle test-case AUT (happy path + the 8
# disruptions) in one pass.
#
# FLAT layout: expects all inputs in the CURRENT directory — the model .lnt,
# the tp_*.lnt, moodle.io, accept.ren, refuse.ren. Run on the licensed node.
#
#   export CADP=/home/paulad/cadp
#   export PATH=$CADP/com:$CADP/bin.x64:$PATH
#   cd /scratch/paulad/testor_moodle
#   sh generate_all.sh                        # all nine purposes
#   sh generate_all.sh happy                  # just tp_happy
#   OUTDIR=variants sh generate_all.sh happy  # output into variants/
#
# Per test purpose:
#   1. tp_X.lnt        -> tp_X.bcg   (TP_ACCEPT->ACCEPT, TP_REFUSE->REFUSE)
#   2. COMPOSED x tp_X -> tc_X.bcg   (test case on the fly, via testor)
#   3. tc_X.bcg        -> tc_X.aut   (what run.py walks)
#
# PURPOSE NAMES ARE LOAD-BEARING. The concretizer derives the target fault from
# the filename tc_<fault>.aut and uppercases it to look up FaultInjector.faults,
# so tp_app_partial_submission.lnt -> APP_PARTIAL_SUBMISSION. An abbreviated
# name (tp_partial_submission) resolves to nothing, the fault is never injected,
# and the run still reports a verdict — for a test that exercised no fault.
# ----------------------------------------------------------------------------
set -e

if [ -z "$CADP" ] || [ ! -d "$CADP" ]; then
  echo "ERROR: \$CADP must point to the CADP install (e.g. /home/paulad/cadp)." >&2; exit 1
fi
ARCH=$("$CADP/com/arch")

# testor plugin: local ./testor if present, else $TESTOR_DIR, else CADP's
if   [ -r ./testor ]; then TESTOR=./testor
elif [ -n "${TESTOR_DIR:-}" ] && [ -r "$TESTOR_DIR/bin.$ARCH/testor.a" ]; then TESTOR="$TESTOR_DIR/bin.$ARCH/testor.a"
elif [ -r "$CADP/bin.$ARCH/testor.a" ]; then TESTOR="$CADP/bin.$ARCH/testor.a"
else echo "ERROR: cannot find testor.a (set \$TESTOR_DIR)" >&2; exit 1; fi
echo "using testor: $TESTOR"

# moodle_types.lnt holds every channel and the L_* functions imported by the
# spec, the SI and each tp_*.lnt; without it step 1 fails with an opaque
# module-resolution error.
for f in moodle_types.lnt specification_moodle.lnt \
         system_interface_moodle.lnt compose_moodle.lnt \
         moodle.io accept.ren refuse.ren; do
  [ -r "$f" ] || { echo "ERROR: missing input '$f' in $(pwd)" >&2; exit 1; }
done

if [ "$#" -gt 0 ]; then
  TPS="$*"
else
  TPS="happy app1_write_fail app_partial_submission app_grade_stale_sub app_lazy_regrade db_attempt_step_loss infra_cron_dead ue1_lose_conn ue2_session_expire"
fi

OUT="${OUTDIR:-.}"
[ -d "$OUT" ] || mkdir -p "$OUT"
echo "purposes: $TPS"
echo "output dir: $OUT"

# Drop stale artefacts for the purposes being regenerated only, so a partial
# run cannot leave LAST run's tc_<name>.aut on disk looking current.
for name in $TPS; do
  rm -f "$OUT/tc_${name}.aut" "$OUT/tc_${name}.bcg" "$OUT/tp_${name}.bcg"
done

# --- the composed model, built once and checked before anything uses it -----
echo "======================================================================"
echo "==> composed model"
lnt.open -main COMPOSED compose_moodle.lnt generator "$OUT/compose_moodle.bcg"
echo "  $(bcg_info -size "$OUT/compose_moodle.bcg")"

# "No deadlock" is NOT evidence the gates are alive. A synchronised gate that
# one side never offers is SILENTLY DELETED from the composition — the build
# still succeeds and the state space just shrinks. That has bitten this model
# twice (six STUDENT-only gates left in a sync set, collapsing SPEC to 85
# states; and a value mismatch that removed CONFIRMED_GRADE entirely). Diff the
# alphabet before generating anything from it.
LBL=$(bcg_info -labels "$OUT/compose_moodle.bcg")
MISSING=""
# Keep this list in step with the model. SUBMISSION_STATE was split into
# SUBMISSION_STATUS + SUBMISSION_TEXT because the concretizer performs one
# observe and captures one parameter per gate, so a gate carrying both the
# status and the stored version could never have its version observed.
for g in APP1_WRITE_FAIL APP_PARTIAL_SUBMISSION APP_GRADE_STALE_SUB \
         APP_LAZY_REGRADE DB_ATTEMPT_STEP_LOSS INFRA_CRON_DEAD \
         UE1_LOSE_CONN UE2_SESSION_EXPIRE \
         SAVE_SUBMISSION UPDATE_SUBMISSION \
         SUBMISSION_STATUS SUBMISSION_TEXT CONFIRMED_GRADE GRADING_SHOWS \
         ATTEMPT_STATE COURSE_TOTAL GRADE_PERSISTED WRITE_ERROR_SHOWN \
         STALE_WARNING_SHOWN; do
  echo "$LBL" | grep -q "^$g" || MISSING="$MISSING $g"
done
if [ -n "$MISSING" ]; then
  echo "ERROR: gates absent from the composed alphabet:$MISSING" >&2
  echo "       Generating now would produce test cases for gates that cannot" >&2
  echo "       fire. Fix the composition first." >&2
  exit 1
fi
echo "  all 8 faults and all oracles present in the alphabet"

FAILED=""
for name in $TPS; do
  echo "======================================================================"
  echo "==> $name"
  [ -r "tp_${name}.lnt" ] || { echo "  SKIP: tp_${name}.lnt not found"; continue; }

  echo "  1. tp -> BCG"
  lnt.open -main MAIN -silent "tp_${name}.lnt" generator \
      -rename accept.ren -rename refuse.ren "$OUT/tp_${name}.bcg"

  echo "  2. COMPOSED x tp -> test case BCG"
  lnt.open -main COMPOSED compose_moodle.lnt "$TESTOR" \
      -io moodle.io "$OUT/tp_${name}.bcg" "$OUT/tc_${name}.bcg"

  echo "  3. BCG -> AUT"
  bcg_io "$OUT/tc_${name}.bcg" "$OUT/tc_${name}.aut"

  # An EMPTY test case is the failure mode to catch: when a purpose
  # over-constrains the spec the product is empty, testor still exits 0, and
  # bcg_io still writes a well-formed .aut with 0 transitions. run.py then walks
  # nothing and the purpose silently contributes no coverage.
  # Header is:  des (init, transitions, states)
  NTRANS=$(head -1 "$OUT/tc_${name}.aut" | tr -dc '0-9,' | cut -d, -f2)
  if [ "${NTRANS:-0}" -eq 0 ]; then
    echo "  ERROR: $OUT/tc_${name}.aut is EMPTY (0 transitions)." >&2
    echo "         tp_${name} selects no trace of the composed model — it is" >&2
    echo "         over-constrained. Relax it or fix the spec; do NOT ignore." >&2
    FAILED="$FAILED ${name}(empty)"
    continue
  fi

  # A NON-empty case can still be about the wrong thing. Every disruption
  # purpose must actually contain its fault; tp_happy deliberately has none.
  if [ "$name" != "happy" ]; then
    FAULT=$(echo "$name" | tr 'a-z' 'A-Z')
    if ! bcg_info -labels "$OUT/tc_${name}.bcg" | grep -q "^$FAULT"; then
      echo "  WARNING: $FAULT does not appear in tc_${name} — the case tests" >&2
      echo "           something other than the fault it is named for." >&2
      FAILED="$FAILED ${name}(no-fault)"
    fi
  fi
  echo "  done: $OUT/tc_${name}.aut ($NTRANS transitions)"
done

echo "======================================================================"
if [ -n "$FAILED" ]; then
  echo "PROBLEM PURPOSES:$FAILED" >&2
  echo "  An empty or mis-targeted test case is a finding about the model," >&2
  echo "  not a purpose to quietly drop from the sweep." >&2
fi
echo "all AUTs: $(ls "$OUT"/tc_*.aut 2>/dev/null | tr '\n' ' ')"
echo
echo "bring back tc_*.aut (and tc_*.bcg) to the mac repo under"
echo "EVALUATION/moodle/Test_Cases/"

rm -f *.o *.t *.f *.lotos *.lib *.h
