#!/usr/bin/env bash
# TGV pipeline for FoodYou (mirrors build_spliit.sh):
#   model/compose_foodyou.lnt  -->  generated/compose_foodyou.bcg
#       the SPEC || SI composition. The internal APP<->DATABASE gates are
#       already hidden inside compose_foodyou.lnt; the visible alphabet is the
#       observable abstract gates (SEARCH_FOOD, FOOD_INFO, ADD_ENTRY,
#       CONFIRM_TOTAL) plus the concrete SI gates (NAVIGATE, TAP, WAIT_FOR,
#       OBSERVE). foodyou.io classifies them — no extra hiding needed.
#   Test_Purposes/tp_*.lnt  -->  generated/tp/tp_*.bcg  (ACCEPT/REFUSE renamed)
#   tgv(compose, tp, io)    -->  Test_Cases/tc_*.bcg + tc_*.aut
#
# Usage:
#   build_foodyou.sh           build everything (default TP: happy)
#   build_foodyou.sh happy     rebuild only the given test purpose(s)
#   build_foodyou.sh clean     delete all generated artifacts
set -e

CADP_COM="${CADP_COM:-$HOME/cadp/com}"
export PATH="$CADP_COM:$PATH"
export CADP="${CADP:-${CADP_COM%/com}}"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SYS="$ROOT/EVALUATION/foodyou"
MODEL="$SYS/model"
TP_SRC="$SYS/Test_Purposes"
GEN="$SYS/generated"
BUILD="$GEN/build"
IO="$MODEL/foodyou.io"

TPS="happy"

if [ "$1" = "clean" ]; then
    rm -rf "$BUILD" "$GEN/tp" "$GEN/compose_foodyou.bcg"
    rm -f "$GEN"/tc/tc_*.aut "$GEN"/tc/tc_*.bcg
    echo "Cleaned $GEN."
    exit 0
fi

[ $# -gt 0 ] && TPS="$*"

mkdir -p "$BUILD" "$GEN/tp" "$GEN/tc"
# CADP tools resolve imported modules and dump scratch files in cwd,
# so build inside generated/build with the sources linked in.
ln -sf "$MODEL"/*.lnt "$TP_SRC"/tp_*.lnt "$TP_SRC/tp.ren" "$BUILD/"
cd "$BUILD"

echo "[1/4] compose (SPEC || SI) -> compose_foodyou.bcg"
lnt.open -main COMPOSED compose_foodyou.lnt generator "$GEN/compose_foodyou.bcg"

for tp in $TPS; do
    TP_PROC="TP_$(printf '%s' "$tp" | tr 'a-z' 'A-Z')"
    echo "[2/4] tp_$tp.lnt -> tp_$tp.bcg ($TP_PROC)"
    lnt.open -main "$TP_PROC" "tp_$tp.lnt" generator "tp_$tp.raw.bcg"
    bcg_labels -rename tp.ren "tp_$tp.raw.bcg" "$GEN/tp/tp_$tp.bcg"

    echo "[3/4] tgv: compose_foodyou x tp_$tp -> tc_$tp.bcg"
    bcg_open "$GEN/compose_foodyou.bcg" tgv -io "$IO" "$GEN/tp/tp_$tp.bcg" "$GEN/tc/tc_$tp.bcg"

    echo "[4/4] tc_$tp.bcg -> tc_$tp.aut"
    bcg_io "$GEN/tc/tc_$tp.bcg" "$GEN/tc/tc_$tp.aut"
done

echo "Done:"
ls "$GEN"/tc/tc_*.aut
