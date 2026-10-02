#!/bin/bash
# run_variants.sh <purpose> -- walk every variant of a purpose and write ONE
# row per case to systems/simplebaby/variants_<purpose>.log:
#
#     VARIANT  STATES  TRANSITIONS  TIME_S  VERDICT  NOTE
#
# VERDICT is the ioco verdict the walk reached: PASS, FAIL or INCONC. A walk
# that could not be completed (no verdict line, exit 2, seed failure) is an
# APPARATUS problem: it is NOT a result row; it goes to
# variants_<purpose>.apparatus.log and the driver exits 1, so it is fixed and
# rerun. Rows are appended (header once), so a resumed run never truncates.
#
#     source systems/simplebaby/env.sh
#     bash systems/simplebaby/run_variants.sh nominal_signed
#     ONLY="1 3" bash systems/simplebaby/run_variants.sh app_key_lost
set -u
NAME="${1:?usage: run_variants.sh <purpose>}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SYS="$ROOT/systems/simplebaby"
VDIR="$SYS/generated/tc/variants/$NAME"
RESULTS="$SYS/variants_${NAME}.log"
APP_LOG="$SYS/variants_${NAME}.apparatus.log"
LOGS="$SYS/generated/variant_logs/$NAME"; mkdir -p "$LOGS" "$SYS/generated/provenance"
: "${DEV:?source systems/simplebaby/env.sh first}"
ls "$VDIR"/tc_"$NAME".*.aut >/dev/null 2>&1 || { echo "no variants under $VDIR" >&2; exit 1; }

if [ -f "$ROOT/framework/scripts/sweep_row.sh" ]; then
  . "$ROOT/framework/scripts/sweep_row.sh"
else
  sweep_row() {
    h=$(head -1 "$2" 2>/dev/null | tr -dc '0-9,')
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$1" "$(echo "$h" | cut -d, -f3)" "$(echo "$h" | cut -d, -f2)" "$3" "$4" "$5"
  }
fi

STAMP=$(date '+%Y%m%d-%H%M%S')
REV=$(git -C "$ROOT" rev-parse --short HEAD); DIRTY=$(git -C "$ROOT" status --porcelain -- framework | wc -l | tr -d ' ')
{
  echo "sweep $NAME  $STAMP  revision $REV  framework files changed: $DIRTY"
  echo "device $DEVICE  inputs.md5 $(md5 -q "$SYS/inputs.md5" 2>/dev/null)"
} >> "$SYS/generated/provenance/${NAME}.txt"
[ "$DIRTY" = "0" ] || git -C "$ROOT" diff -- framework > "$SYS/generated/provenance/${NAME}.${STAMP}.framework.diff"
[ -f "$RESULTS" ] || printf 'VARIANT\tSTATES\tTRANSITIONS\tTIME_S\tVERDICT\tNOTE\n' > "$RESULTS"

bash "$SYS/check_env.sh" || { echo "run_variants: environment not ready" >&2; exit 1; }
unfinished=0
for aut in $(ls "$VDIR"/tc_"$NAME".*.aut | sort -t. -k2 -n); do
  i=$(echo "$aut" | sed -e 's/.*\.\([0-9][0-9]*\)\.aut$/\1/')
  if [ -n "${ONLY:-}" ]; then echo " $ONLY " | grep -q " $i " || continue; fi
  echo "=============== $NAME variant $i"
  SECONDS=0
  AUT="$aut" LOGFILE="$LOGS/v$i.log" CAPDIR="$SYS/generated/captures/$NAME/v$i" bash "$SYS/run_case.sh" "$NAME" > /dev/null 2>&1
  elapsed=$SECONDS
  v=$(sed 's/\x1b\[[0-9;]*m//g' "$LOGS/v$i.log" | grep -E '^Verdict:' | tail -1 | sed -e 's/^Verdict:[[:space:]]*//' -e 's/[[:space:]].*//')
  case "$v" in
    PASS|FAIL|INCONC) ;;
    *) echo "$(date '+%F %T') $NAME v$i no verdict (see $LOGS/v$i.log)" >> "$APP_LOG"
       echo "  v$i: NO VERDICT -- apparatus problem, recorded in $(basename "$APP_LOG"); fix and rerun"
       unfinished=1; continue ;;
  esac
  clean=$(sed 's/\x1b\[[0-9;]*m//g' "$LOGS/v$i.log")
  note=$(echo "$clean" | grep -m1 -E 'CONFORMANCE FAILURE|mismatch' | sed -e 's/^[^A-Za-z]*//' | cut -c1-160 | tr '\t' ' ')
  [ -n "$note" ] || note="$(echo "$clean" | grep -c 'oracle OK') oracle checks OK"
  sweep_row "$i" "$aut" "$elapsed" "$v" "$note" | tee -a "$RESULTS"
done
exit $unfinished
