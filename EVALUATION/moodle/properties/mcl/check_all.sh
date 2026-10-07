#!/bin/sh
# check_all.sh — model-check the Moodle properties against the composed model.
#
# Run on the node, in the directory holding compose_moodle.bcg:
#
#   export CADP=/home/paulad/cadp
#   export PATH=$CADP/com:$CADP/bin.x64:$PATH
#   cd /scratch/paulad/testor_moodle
#   sh mcl/check_all.sh 2>&1 | tee mcl.log
#
# ---------------------------------------------------------------------------
# CALIBRATION IS ENFORCED, NOT SUGGESTED
# ---------------------------------------------------------------------------
# In MCL a double-quoted action is a LITERAL, not a regex, so a formula written
# with "GATE.*" matches nothing and returns FALSE -- indistinguishable in the
# output from a property that genuinely fails. Two findings were reported from
# this model on that basis and both were wrong.
#
# So this script refuses to report anything unless 00 returns TRUE and 01
# returns FALSE. If the notation cannot both match and fail to match, no other
# answer here means anything.
# ---------------------------------------------------------------------------
set -u

BCG="${1:-compose_moodle.bcg}"
DIR=$(cd "$(dirname "$0")" && pwd)

if [ ! -r "$BCG" ]; then
  echo "ERROR: cannot read '$BCG'. Run from the directory holding the composed" >&2
  echo "       model, or pass its path as the first argument." >&2
  exit 1
fi
command -v bcg_open >/dev/null 2>&1 || {
  echo "ERROR: bcg_open not on PATH (need \$CADP/com)." >&2; exit 1; }

echo "model: $BCG"
echo "       $(bcg_info -size "$BCG" 2>/dev/null)"
echo

# Answer one formula. Echoes TRUE/FALSE, or ERROR if evaluator4 itself failed.
#
# evaluator4 is an Open/Caesar plugin (evaluator4.a), not a standalone binary
# -- there is no such executable on $PATH, confirmed against this CADP
# install's com/ and bin.*/ directories. It only runs loaded through
# bcg_open, same as testor.a in generate_all.sh. Calling it bare, as this
# script did before, fails with "command not found" on every formula.
answer() {
  out=$(bcg_open "$BCG" evaluator4 "$1" 2>&1)
  if echo "$out" | grep -q "^TRUE"; then echo TRUE
  elif echo "$out" | grep -q "^FALSE"; then echo FALSE
  else echo "ERROR"; echo "$out" | tail -3 >&2
  fi
}

echo "== calibration =="
C_TRUE=$(answer "$DIR/00_calibration_true.mcl")
C_FALSE=$(answer "$DIR/01_calibration_false.mcl")
echo "  00_calibration_true   -> $C_TRUE   (must be TRUE)"
echo "  01_calibration_false  -> $C_FALSE  (must be FALSE)"

if [ "$C_TRUE" != "TRUE" ] || [ "$C_FALSE" != "FALSE" ]; then
  echo >&2
  echo "CALIBRATION FAILED. The action syntax is not matching this model as" >&2
  echo "written, so every other formula's answer is uninterpretable. Do not" >&2
  echo "record anything from this run. Check the label text against" >&2
  echo "  bcg_info -labels $BCG" >&2
  exit 1
fi
echo "  calibration OK — the notation both matches and fails to match"
echo

echo "== properties =="
printf "  %-42s %s\n" "formula" "result"
for f in "$DIR"/0[2-9]_*.mcl "$DIR"/[1-9][0-9]_*.mcl; do
  [ -r "$f" ] || continue
  b=$(basename "$f" .mcl)
  printf "  %-42s %s\n" "$b" "$(answer "$f")"
done

echo
echo "Expected, for the reshaped APP_PARTIAL_SUBMISSION property:"
echo "  02_fault_reachable                 TRUE   (else everything after is vacuous)"
echo "  03_property_status_never_advances  FALSE  (the spec forbids the counter-example)"
echo "  04_required_output_reachable       TRUE   (else 03's FALSE is vacuous)"
echo "  05_error_surfaced_after_fault      TRUE   (silence must not be conformant)"
echo
echo "A FALSE in 03 alongside a FALSE in 04 is NOT the property holding --"
echo "it means nothing is reachable after the fault at all. Read them together."
