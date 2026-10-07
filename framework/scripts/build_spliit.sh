#!/usr/bin/env bash
# Full TGV pipeline for Spliit:
#   model/*.lnt + Test_Purposes/tp_*.lnt --> generated/composed_spliit.bcg
#   --> generated/tp/tp_*.bcg (ACCEPT/REFUSE renamed)
#   --> Test_Cases/tc_*.bcg + tc_*.aut
#
# The behaviour model is the composition SPEC || SI built from
# compose_spliit.lnt, not the SPEC alone.
#
# Usage:
#   build_spliit.sh            build everything
#   build_spliit.sh a1 u1      rebuild only the given test cases
#   build_spliit.sh clean      delete all generated artifacts
#
# All CADP scratch files (*.o, generator, tgv, ...) stay in generated/build.
set -e

CADP_COM="${CADP_COM:-$HOME/cadp/com}"
export PATH="$CADP_COM:$PATH"
export CADP="${CADP:-${CADP_COM%/com}}"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SYS="$ROOT/EVALUATION/spliit"
MODEL="$SYS/model"
TP_SRC="$SYS/Test_Purposes"
GEN="$SYS/generated"
BUILD="$GEN/build"
IO="$MODEL/spliit.io"

TPS="a1 a2 a3 a4 u1"

if [ "$1" = "clean" ]; then
    rm -rf "$BUILD" "$GEN/tp" "$GEN/composed_spliit.bcg"
    rm -f "$GEN"/tc/tc_a*.aut "$GEN"/tc/tc_u*.aut "$GEN"/tc/tc_a*.bcg "$GEN"/tc/tc_u*.bcg
    echo "Cleaned $GEN (kept tc_spliit_1.aut legacy)."
    exit 0
fi

[ $# -gt 0 ] && TPS="$*"

mkdir -p "$BUILD" "$GEN/tp" "$GEN/tc"
# CADP tools resolve imported modules and dump scratch files in cwd,
# so build inside generated/build with the sources linked in.
ln -sf "$MODEL"/*.lnt "$TP_SRC"/tp_*.lnt "$TP_SRC/tp.ren" "$BUILD/"
cd "$BUILD"

echo "[1/4] compose (SPEC || SI) -> composed_spliit.bcg"
lnt.open compose_spliit.lnt generator "$GEN/composed_spliit.bcg"

for tp in $TPS; do
    TP_PROC="TP_$(printf '%s' "$tp" | tr 'a-z' 'A-Z')"
    echo "[2/4] tp_$tp.lnt -> tp_$tp.bcg ($TP_PROC)"
    lnt.open -main "$TP_PROC" "tp_$tp.lnt" generator "tp_$tp.raw.bcg"
    bcg_labels -rename tp.ren "tp_$tp.raw.bcg" "$GEN/tp/tp_$tp.bcg"

    echo "[3/4] tgv: composed x tp_$tp -> tc_$tp.bcg"
    bcg_open "$GEN/composed_spliit.bcg" tgv -io "$IO" "$GEN/tp/tp_$tp.bcg" "$GEN/tc/tc_$tp.bcg"

    echo "[4/4] tc_$tp.bcg -> tc_$tp.aut"
    bcg_io "$GEN/tc/tc_$tp.bcg" "$GEN/tc/tc_$tp.aut"
done

echo "Done:"
ls "$GEN"/tc/tc_*.aut
