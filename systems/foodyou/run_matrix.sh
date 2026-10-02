#!/usr/bin/env bash
# run_matrix.sh — run every FoodYou test case against the live app, print the
# verdict matrix, and record it to systems/foodyou/results.log.
#
# Prereqs: emulator + Appium up, app installed & onboarded, $DEV set to the
# device-config path. Run from the repo root:  DEV=... bash systems/foodyou/run_matrix.sh
set -u

RESULTS=systems/foodyou/results.log
: "${DEV:?set DEV to your --device-config path}"

# See investigate_variants.sh. This matters more here than anywhere: EXTAPI_FAIL
# deliberately takes the radios down and restores them only on the normal path, so
# an interrupted matrix run leaves the device offline and every subsequent sweep
# reports failures caused by that, not by the app. SKIP_ENV_CHECK=1 overrides.
if [ "${SKIP_ENV_CHECK:-0}" != "1" ]; then
	bash systems/foodyou/check_env.sh || exit 1
fi

# disruption | layer | basis (descriptive metadata for the matrix columns)
ROWS=(
  "happy|baseline|nominal happy path"
  "ue1_kill|User/Env|kill+relaunch, authoritative read-back"
  "input_invalid|User/Env|invalid amount unreachable (numeric field)"
  "extapi_fail|App|Open Food Facts disabled (local-first config)"
  "cache_stale|App|stale stored energy, no revalidation"
  "disruption_db|Database|write abort, authoritative read-back"
  "db_corrupt|Database|NULL required field detected"
  "storage_full|Infra|write abort, authoritative read-back"
  "storage_media|Infra|forced re-open of a chmod-0000 DB -- error boundary shown"
)

hdr() { printf "%-16s %-10s %-9s %s\n" "$@"; }
{
  echo "# FoodYou disruption verdict matrix — $(date '+%Y-%m-%d %H:%M')"
  hdr "DISRUPTION" "LAYER" "VERDICT" "BASIS"
} | tee "$RESULTS"

# Keep every run's stdout AND stderr. This used to be `2>/dev/null` with only the
# verdict word kept, which made each row unfalsifiable: an audit of a 54-FAIL sweep
# found that ALL of them were the tester failing to act rather than the SUT
# misbehaving -- and none of that was recoverable from the log, because the log did
# not exist. A verdict nobody can check is a verdict nobody should quote.
LOGDIR=systems/foodyou/generated/matrix_logs
mkdir -p "$LOGDIR"

for row in "${ROWS[@]}"; do
  IFS='|' read -r tc layer basis <<< "$row"
  bash systems/foodyou/seed_foods.sh > "$LOGDIR/${tc}.seed.log" 2>&1
  # -u so print() (stdout) and logging (stderr) interleave in the real order.
  # Scope failure captures to this case's own directory (see run_variants.sh
  # for why: an unlinked flat capture dir is how the v47 crash sat unnoticed).
  CONCRETIZATION_DEBUG_DIR="$LOGDIR/${tc}_captures" \
  PYTHONPATH=framework python -u framework/scripts/run.py \
        --aut systems/foodyou/generated/tc/tc_${tc}.aut --platform android \
        --system-interface systems/foodyou/model/system_interface_foodyou_copy.lnt \
        --concrete-domain systems/foodyou/properties/concrete_domain.yml \
        --type-description systems/foodyou/properties/type_description.yml \
        --disruption-mapping systems/foodyou/properties/disruption_mapping.yml \
        --device-config "$DEV" --timeout "${TIMEOUT:-10}" \
        --report --verbose > "$LOGDIR/${tc}.log" 2>&1
  V=$(perl -pe 's/\e\[[0-9;]*m//g' < "$LOGDIR/${tc}.log" \
      | grep -oE '(Verdict: (PASS|FAIL|INCONC)|Status: UNEXECUTABLE)' \
      | head -1 | awk '{print $2}')
  # See run_variants.sh: UNEXECUTABLE arrives on a "Status:" line, not a
  # "Verdict:" line, precisely so it cannot be counted as a verdict by accident.
  hdr "$tc" "$layer" "${V:-ERROR}" "$basis" | tee -a "$RESULTS"
  # Why this verdict, in one line, from the same taxonomy the happy-purpose
  # investigation uses -- so a FAIL that is really an execution artifact is
  # visible in the matrix itself rather than only under later scrutiny.
  python framework/scripts/classify_failure.py "$LOGDIR/${tc}.log" --tsv 2>/dev/null \
    | awk -F'\t' '$2 != "NONE" {printf "%-16s %-10s %-9s %s\n", "", "", "\\_ "$2, $4}' \
    | tee -a "$RESULTS"
done

echo "----------------------------------------------------------------" | tee -a "$RESULTS"
echo "matrix written to $RESULTS" | tee -a "$RESULTS"
