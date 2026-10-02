#!/bin/sh
# new_system.sh -- instantiate the template as systems/<name>/.
#
#     sh systems/template/new_system.sh medtimer
#
# Copies every template file, renames `sutname` in file names and contents to
# <name> (and SUTNAME to <NAME>), creates the empty generated/ notes/ sut/
# directories every case study has, and prints the number of HOLE markers
# left to fill. It refuses to overwrite an existing system.
set -e

NAME="${1:-}"
if [ -z "$NAME" ]; then
  echo "usage: sh systems/template/new_system.sh <name>   (lowercase, e.g. medtimer)" >&2
  exit 1
fi
case "$NAME" in
  *[!a-z0-9_]*) echo "ERROR: name must be lowercase letters, digits or '_' (it becomes an LNT module name)" >&2; exit 1 ;;
esac

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/systems/template"
DST="$ROOT/systems/$NAME"
if [ -e "$DST" ]; then
  echo "ERROR: refusing to overwrite $DST" >&2
  exit 1
fi
UPPER=$(printf '%s' "$NAME" | tr 'a-z' 'A-Z')

mkdir -p "$DST"
( cd "$SRC" && find . -type f \
    -not -name 'new_system.sh' \
    -not -name 'TEMPLATE_ANALYSIS.md' \
    -not -name '.DS_Store' ) | while read -r f; do
  rel=$(printf '%s' "$f" | sed -e 's#^\./##' -e "s/sutname/$NAME/g")
  # the fill-in guide travels with the system, under notes/
  case "$rel" in README.md) rel="notes/template_guide.md" ;; esac
  out="$DST/$rel"
  mkdir -p "$(dirname "$out")"
  sed -e "s/sutname/$NAME/g" -e "s/SUTNAME/$UPPER/g" "$SRC/$f" > "$out"
done

mkdir -p "$DST/generated/tc" "$DST/generated/tp" "$DST/generated/build" \
         "$DST/notes" "$DST/sut" "$DST/properties" "$DST/test_purposes"
touch "$DST/generated/tc/.gitkeep" "$DST/generated/tp/.gitkeep" "$DST/generated/build/.gitkeep"
chmod +x "$DST/testor/generate_tc_all.sh" 2>/dev/null || true

echo "created $DST"
echo "holes to fill: $(grep -rn 'HOLE' "$DST" --include='*.lnt' --include='*.yml' --include='*.sh' --include='*.io' | wc -l | tr -d ' ') markers"
echo "next: open $DST/notes/template_guide.md and work through the checklist"
