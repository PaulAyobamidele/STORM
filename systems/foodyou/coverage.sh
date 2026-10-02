#!/bin/sh
# coverage.sh — per-test-purpose ACTION/GATE coverage over the COMPOSED FoodYou
# model, plus each test case's size. Run in the flat testor dir on the CADP node
# (narval), AFTER generate_all.sh has produced the tc_*.aut:
#
#   export CADP=/home/paulad/cadp; export PATH=$CADP/com:$CADP/bin.x64:$PATH
#   cd /scratch/paulad/testor_foodyou
#   sh coverage.sh | tee coverage.txt
#
# Metric: the COMPOSED (spec x SI x disruptors) LTS is the baseline — every
# reachable action ("gate"). For each test case we report how many of those gates
# it exercises. This is ACTION coverage, not full transition coverage (see note).
set -e

# 0. Build the COMPOSED baseline LTS once (all reachable actions of the model).
if [ ! -r compose_full.aut ]; then
  echo "building COMPOSED baseline LTS (one-off)..." >&2
  lnt.open -main COMPOSED compose_foodyou_copy.lnt generator compose_full.bcg
  bcg_io compose_full.bcg compose_full.aut
fi

# distinct GATE names = first token of each label (drops parameters and the
# internal action i / tau), e.g.  "SEARCH_FOOD !FOOD_APPLE !LOCAL" -> SEARCH_FOOD
gates()   { grep -oE '"[^"]*"' "$1" | tr -d '"' | awk '{print $1}' | sed 's/;$//' \
            | grep -vE '^(i|tau)$' | sort -u ; }
# .aut header is:  des (init, transitions, states)
nstates() { head -1 "$1" | grep -oE '[0-9]+' | sed -n 3p ; }
ntrans()  { head -1 "$1" | grep -oE '[0-9]+' | sed -n 2p ; }

gates compose_full.aut > .model_gates
MODEL_N=$(wc -l < .model_gates | tr -d ' ')
echo "COMPOSED baseline: states=$(nstates compose_full.aut) transitions=$(ntrans compose_full.aut) gates=$MODEL_N"
echo
printf "%-16s %8s %12s %9s   %s\n" "TEST_PURPOSE" "STATES" "TRANSITNS" "GATE_COV" "GATES_HIT"

: > .suite_gates
TPS="happy ue1_kill input_invalid extapi_fail cache_stale disruption_db db_corrupt storage_full storage_media"
for name in $TPS; do
  aut="tc_${name}.aut"
  if [ ! -r "$aut" ]; then printf "%-16s   (missing tc)\n" "$name"; continue; fi
  gates "$aut" > .tc_gates
  cat .tc_gates >> .suite_gates
  HIT=$(comm -12 .tc_gates .model_gates | wc -l | tr -d ' ')
  PCT=$(awk "BEGIN{printf \"%.0f\", 100*$HIT/$MODEL_N}")
  HITLIST=$(comm -12 .tc_gates .model_gates | tr '\n' ' ')
  printf "%-16s %8s %12s %7s%%   %s\n" "$name" "$(nstates "$aut")" "$(ntrans "$aut")" "$PCT" "$HITLIST"
done

echo
UHIT=$(sort -u .suite_gates | comm -12 - .model_gates | wc -l | tr -d ' ')
UPCT=$(awk "BEGIN{printf \"%.0f\", 100*$UHIT/$MODEL_N}")
echo "UNION (whole suite): $UHIT / $MODEL_N model gates = ${UPCT}%"
echo "model gates NO test purpose covers (documentable gaps):"
sort -u .suite_gates | comm -13 - .model_gates | sed 's/^/  /'
rm -f .model_gates .tc_gates .suite_gates
