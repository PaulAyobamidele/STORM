#!/usr/bin/env bash
#
# seed_foods.sh — deterministic FoodYou state reset, via sqlite on the ALREADY
# ONBOARDED database. No `pm clear`, no UI onboarding.
# ----------------------------------------------------------------------------
# WHY NOT pm clear: it wipes onboarding, forcing a fragile re-dismissal of the
# "Agree & Continue"/"What's new" screens via `uiautomator dump` + coordinate
# taps — which is timing-sensitive and conflicts with a live Appium
# UiAutomator2 session. Instead we reset the DATA directly:
#   1. clear the diary/measurement rows  -> daily total starts EMPTY (0 kcal)
#   2. remove the retired synthetic foods; the foods under test are now real
#      Swiss Food Composition Database products the app imports itself
# The app's onboarding flag (in DataStore/prefs, not the DB) is left intact, and
# run.py's reset_sut relaunches with noReset:true so this seed survives the run.
#
# PRECONDITION: the DB must exist (app onboarded at least once). run.py's
# reset_sut keeps it onboarded; on a truly fresh install, launch FoodYou once
# (tap "Agree & Continue" x2, dismiss "What's new"), then re-run this seed.
#
# Usage:   systems/foodyou/seed_foods.sh          (adb on PATH)
#          ADB=/path/to/adb systems/foodyou/seed_foods.sh
# ----------------------------------------------------------------------------
set -euo pipefail

PKG=com.maksimowiczm.foodyou
DB=databases/open_source_database.db
ADB="${ADB:-adb}"

sql() { $ADB shell "run-as $PKG sqlite3 $DB \"$1\""; }

# --- 0. device + onboarded DB present --------------------------------------
if ! $ADB shell true >/dev/null 2>&1; then
  echo "ERROR: no adb device reachable (is the emulator booted?)." >&2
  exit 1
fi
if ! $ADB shell "run-as $PKG test -f $DB" >/dev/null 2>&1; then
  echo "ERROR: $DB not found — FoodYou isn't onboarded yet." >&2
  echo "  Launch the app once (Agree & Continue x2 + dismiss What's new), or run" >&2
  echo "  the happy path once (run.py's reset onboards it), then re-run this seed." >&2
  exit 1
fi

# --- 1. reset the diary so the daily total is EMPTY ------------------------
# Clear every logged-entry table (name contains Measurement, or starts Diary,
# plus FoodEvent). FKs off so deletion order doesn't matter.
DIARY_TABLES=$(sql "SELECT name FROM sqlite_master WHERE type='table' AND \
  (name LIKE '%Measurement%' OR name LIKE 'Diary%' OR name='FoodEvent');" | tr -d '\r')
echo "  clearing diary tables: $(echo $DIARY_TABLES | tr '\n' ' ')"
for T in $DIARY_TABLES; do
  sql "PRAGMA foreign_keys=OFF; DELETE FROM $T;" 2>/dev/null || true
done

# --- 2. remove the retired synthetic foods ---------------------------------
# This script used to CREATE TestApple/TestRice/TestEgg and the suite tested
# against them. It no longer does: the foods under test are real products from
# the Swiss Food Composition Database, which the app imports from a CSV bundled
# in its own APK. Nothing invents nutrition data any more, so a wrong value means
# the app disagrees with its own catalogue rather than with our bookkeeping.
#
# The old rows are deleted rather than left alone because they would still match
# a search for "Test" and could be tapped by mistake.
sql "DELETE FROM Product WHERE name IN ('TestApple','TestRice','TestEgg');"

# --- 3. verify the foods under test are present and correct ----------------
# These are NOT created here -- they arrive with the app's own Swiss import
# (Settings -> Databases -> Swiss Food Composition Database). If they are
# missing, that import has not been run on this device.
echo "  foods under test:"
sql "SELECT '    '||name||' = '||CAST(energy AS INT)||' kcal/100g' \
     FROM Product WHERE name IN ('Peanut butter','Cooking butter','Corn germ oil') \
     ORDER BY name;"
count=$(sql "SELECT COUNT(*) FROM Product \
     WHERE name IN ('Peanut butter','Cooking butter','Corn germ oil');" | tr -d '\r')
if [ "$count" = "3" ]; then
  echo "OK: diary cleared (daily total should read 0 / 2000 kcal); 3 foods present."
else
  echo "ERROR: expected the 3 foods under test, found $count." >&2
  echo "  The Swiss Food Composition Database has probably not been imported." >&2
  echo "  In the app: Settings -> Databases -> Swiss Food Composition Database." >&2
  exit 1
fi
