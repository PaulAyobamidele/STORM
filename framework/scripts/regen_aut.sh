#!/usr/bin/env bash
# Regenerate tc_*.aut files from the corresponding BCGs.
# Looks in model/ first, then test_purpose/, and writes every .aut to model/.
set -e

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MODEL="$ROOT/systems/spliit/model"
TP_DIR="$MODEL/test_purpose"

echo "Regenerating .aut files under $MODEL ..."

# Collect unique tc_* BCG basenames (model/ takes precedence over test_purpose/).
PROCESSED=""

for DIR in "$MODEL" "$TP_DIR"; do
    for BCG in "$DIR"/tc_*.bcg; do
        [ -f "$BCG" ] || continue
        BASE="$(basename "$BCG" .bcg)"
        # Skip if already processed
        echo "$PROCESSED" | grep -qw "$BASE" && continue
        PROCESSED="$PROCESSED $BASE"
        AUT="$MODEL/${BASE}.aut"
        echo "  bcg_io $BCG -> $AUT"
        bcg_io "$BCG" "$AUT"
    done
done

echo "Done. Generated .aut files:"
ls "$MODEL"/tc_*.aut 2>/dev/null | sed 's|.*/||'
