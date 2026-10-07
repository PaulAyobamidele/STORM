#!/usr/bin/env bash
#
# generate_all.sh — regenerate every FoodYou test-case AUT (happy path + the 8
# disruptions) from the copy-set, in one pass.
#
# FLAT layout: expects all inputs in the CURRENT directory (as on narval3's
# /scratch/paulad/testor_foodyou) — the model .lnt, the tp_*.lnt, foodyou.io,
# accept.ren, refuse.ren. Run it on the licensed node (narval3), NOT pauls-macbook.
#
#   export CADP=/home/paulad/cadp
#   export PATH=$CADP/com:$CADP/bin.x64:$PATH
#   cd /scratch/paulad/testor_foodyou
#   sh generate_all.sh                  # all nine purposes, output in .
#   sh generate_all.sh happy            # just tp_happy
#   OUTDIR=variants sh generate_all.sh happy    # just tp_happy, output in variants/
#
# Inputs are always read from the CURRENT directory; only the generated
# tp_*.bcg / tc_*.bcg / tc_*.aut go to $OUTDIR (default "."). Naming a subset
# of purposes also limits the stale-artefact cleanup to those purposes, so a
# partial run cannot silently delete test cases it is not regenerating.
#
# Per test purpose it runs the ioco derivation:
#   1. tp_X.lnt        -> tp_X.bcg   (TP_ACCEPT->ACCEPT, TP_REFUSE->REFUSE)
#   2. COMPOSED x tp_X -> tc_X.bcg   (test case on the fly, via testor)
#   3. tc_X.bcg        -> tc_X.aut   (what run.py walks)
# ----------------------------------------------------------------------------
set -e

if [ -z "$CADP" ] || [ ! -d "$CADP" ]; then
  echo "ERROR: \$CADP must point to the CADP install (e.g. /home/paulad/cadp)." >&2; exit 1
fi
ARCH=$("$CADP/com/arch")

# testor plugin: local ./testor if present, else the one shipped with CADP
if [ -r ./testor ]; then TESTOR=./testor
elif [ -r "$CADP/bin.$ARCH/testor.a" ]; then TESTOR="$CADP/bin.$ARCH/testor.a"
else echo "ERROR: cannot find testor.a" >&2; exit 1; fi
echo "using testor: $TESTOR"

# required inputs must already be present in this flat dir
# (foodyou_types.lnt holds defaultF, imported by every tp_*.lnt;
#  without it lnt.open fails in step 1 with an opaque module-resolution error)
for f in foodyou_types.lnt specification_foodyou_copy.lnt \
         system_interface_foodyou_copy.lnt compose_foodyou_copy.lnt \
         foodyou.io accept.ren refuse.ren; do
  [ -r "$f" ] || { echo "ERROR: missing input '$f' in $(pwd)" >&2; exit 1; }
done

# test purposes to derive (must be present as tp_<name>.lnt).
# Names given on the command line win; otherwise derive the full set.
if [ "$#" -gt 0 ]; then
  TPS="$*"
else
  TPS="happy ue1_kill input_invalid extapi_fail cache_stale disruption_db db_corrupt storage_full storage_media"
fi

# where the generated artefacts land (inputs are still read from .)
OUT="${OUTDIR:-.}"
[ -d "$OUT" ] || mkdir -p "$OUT"
echo "purposes: $TPS"
echo "output dir: $OUT"

# Drop stale artefacts first. Without this, a purpose that fails to regenerate
# leaves LAST run's tc_<name>.aut on disk looking current -- and run.py would
# happily walk a test case derived from a superseded model. Only the purposes
# being regenerated are cleared, so `sh generate_all.sh happy` cannot wipe the
# other eight test cases.
for name in $TPS; do
  rm -f "$OUT/tc_${name}.aut" "$OUT/tc_${name}.bcg" "$OUT/tp_${name}.bcg"
done

for name in $TPS; do
  echo "======================================================================"
  echo "==> $name"
  [ -r "tp_${name}.lnt" ] || { echo "  SKIP: tp_${name}.lnt not found"; continue; }

  echo "  1. tp -> BCG"
  lnt.open -main MAIN -silent "tp_${name}.lnt" generator \
      -rename accept.ren -rename refuse.ren "$OUT/tp_${name}.bcg"

  echo "  2. COMPOSED x tp -> test case BCG"
  lnt.open -main COMPOSED compose_foodyou_copy.lnt "$TESTOR" \
      -io foodyou.io "$OUT/tp_${name}.bcg" "$OUT/tc_${name}.bcg"

  echo "  3. BCG -> AUT"
  bcg_io "$OUT/tc_${name}.bcg" "$OUT/tc_${name}.aut"

  # An EMPTY test case is the failure mode to catch here: when a test purpose
  # over-constrains the spec the product is empty, testor still succeeds, and
  # bcg_io still writes a well-formed .aut with 0 transitions. Nothing downstream
  # notices -- run.py just walks nothing and the purpose silently contributes no
  # coverage. The .aut header is:  des (init, transitions, states)
  NTRANS=$(head -1 "$OUT/tc_${name}.aut" | tr -dc '0-9,' | cut -d, -f2)
  if [ "${NTRANS:-0}" -eq 0 ]; then
    echo "  ERROR: $OUT/tc_${name}.aut is EMPTY (0 transitions)." >&2
    echo "         tp_${name} selects no trace of the composed model -- it is" >&2
    echo "         over-constrained. Relax it or fix the spec; do NOT ignore." >&2
    FAILED="$FAILED $name"
  else
    echo "  done: $OUT/tc_${name}.aut ($NTRANS transitions)"
  fi
done

echo "======================================================================"
if [ -n "$FAILED" ]; then
  echo "EMPTY TEST CASES:$FAILED" >&2
  echo "  These purposes selected no trace. Investigate before reporting any" >&2
  echo "  verdict for them -- an empty test case is a finding about the model," >&2
  echo "  not a purpose to quietly drop from the sweep." >&2
fi
echo "all AUTs: $(ls "$OUT"/tc_*.aut 2>/dev/null | tr '\n' ' ')"
echo "bring back the tc_*.aut (and tc_*.bcg) to the mac repo's EVALUATION/foodyou/Test_Cases/"
echo "and copy tc_happy.aut -> foodyou.tc.aut for the default run command."

# tidy intermediate compiler artefacts (keep .aut / .bcg)
rm -f *.o *.t *.f *.lotos *.lib *.h
