#!/bin/bash
# run_all.sh -- walk every purpose, nominal baselines first, one run_variants.sh
# per purpose, then prove the stack and the device are clean again.
#
#     source EVALUATION/simplebaby/env.sh
#     bash EVALUATION/simplebaby/run_all.sh                 all 17
#     bash EVALUATION/simplebaby/run_all.sh ue_kill db_abort  just these
#
# A purpose whose walk produced no verdict is an apparatus problem; it is
# listed at the end and the sweep continues with the next purpose.
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SYS="$ROOT/EVALUATION/simplebaby"
: "${DEV:?source EVALUATION/simplebaby/env.sh first}"
ALL="nominal_signed nominal_guest ue_kill ue_offline app_unavailable db_abort db_corrupt db_data_lost app_cache_stale app_key_lost infra_db_down infra_doze input_invalid input_overnight ue_storage_full db_corrupt_local infra_storage_media"
PURPOSES="${*:-$ALL}"
SUMMARY="$SYS/generated/logs/run_all_$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$(dirname "$SUMMARY")"
echo "sweep $(date '+%F %T') revision $(git -C "$ROOT" rev-parse --short HEAD): $PURPOSES" | tee "$SUMMARY"
BAD=""
for p in $PURPOSES; do
  bash "$SYS/run_variants.sh" "$p" 2>&1 | tee -a "$SUMMARY"
  [ "${PIPESTATUS[0]}" = "0" ] || BAD="$BAD $p"
done
echo "=== verdict rows" | tee -a "$SUMMARY"
for p in $PURPOSES; do
  [ -f "$SYS/variants_$p.log" ] && tail -n +2 "$SYS/variants_$p.log" | awk -v p="$p" -F'\t' '{printf "%-22s v%s\t%s\t%ss\t%s\n", p, $1, $5, $4, $6}' | tee -a "$SUMMARY"
done
echo "=== stack after the sweep" | tee -a "$SUMMARY"
bash "$SYS/seed.sh" 2>&1 | tee -a "$SUMMARY"
bash "$SYS/check_env.sh" 2>&1 | tee -a "$SUMMARY"
[ -z "$BAD" ] || echo "NO VERDICT (apparatus, rerun):$BAD" | tee -a "$SUMMARY"
