#!/usr/bin/env bash
# Remove all generated .aut files under systems/spliit/model so they can be
# regenerated from scratch via lnt.open / tgv / bcg_io.
set -e

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MODEL="$ROOT/systems/spliit/model"

find "$MODEL" -name "*.aut" -type f | while read -r f; do
    echo "Deleting $f"
    rm "$f"
done

echo "Done."
