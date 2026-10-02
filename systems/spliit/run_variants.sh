#!/usr/bin/env bash
# run_variants.sh -- walk EVERY extracted test case of one purpose and write
# one row per variant to systems/spliit/variants_<purpose>.log, the file
# framework/scripts/eval_tables.py builds the evaluation table from.
# (A copy of systems/medtimer/run_variants.sh; only the web specifics differ.)
#
#     bash systems/spliit/run_variants.sh db_abort
#     ONLY="1 3" bash systems/spliit/run_variants.sh db_abort
#
# Needs the stack up (docker compose up -d in systems/spliit/sut/spliit) and
# the fault proxy on :3002 (systems/spliit/sut/fault_middleware.py). For
# app_extapi_fail the hosts line must be in place first:
#     sudo sh -c "echo '127.0.0.1 api.frankfurter.app' >> /etc/hosts"
#
# Row schema (tab-separated, fixed for the whole campaign, written by
# framework/scripts/sweep_row.sh, the one format every SUT shares):
#     VARIANT  STATES  TRANSITIONS  TIME_S  VERDICT  NOTE
# STATES / TRANSITIONS come from the variant's own .aut header
# (`des (init, TRANSITIONS, STATES)`); TIME_S is bash's SECONDS around the
# walk; VERDICT is PASS, FAIL or INCONC as the walk printed it. run.py's exit
# code 2, or a walk that ended without a verdict, is recorded UNEXECUTABLE:
# not a verdict, a walk to repeat, kept out of every verdict total.
#
# Resuming APPENDS: variants already in the log are skipped, a finished row
# is never overwritten. The header records the git revision and a dirty flag;
# a dirty framework/ is saved as a diff beside the log. Each case creates its
# own group, so no seeding is needed between cases.
# Per variant: the walk log and the failure captures live in
# generated/variant_logs/<purpose>/ (v<N>.log, v<N>_captures/).
set -u
NAME="${1:?usage: run_variants.sh <purpose>}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
. "$ROOT/framework/scripts/sweep_row.sh"
SYS="$ROOT/systems/spliit"
VDIR="$SYS/generated/tc/variants/$NAME"
TC="$SYS/generated/tc/tc_${NAME}.aut"
LOGS="$SYS/generated/variant_logs/$NAME"; mkdir -p "$LOGS"
ROWS="$SYS/variants_${NAME}.log"
URL="${URL:-http://localhost:3002}"

ls "$VDIR"/tc_"$NAME".*.aut >/dev/null 2>&1 || { echo "no variants under $VDIR" >&2; exit 1; }
[ "$(curl -s -o /dev/null -w '%{http_code}' "$URL/groups")" = 200 ] || { echo "the proxy does not answer on $URL" >&2; exit 1; }
[ "$(docker exec -i spliit-db-1 psql -U postgres -d postgres -t -A -c "SELECT count(*) FROM pg_trigger WHERE tgname = 'fault_abort_write'")" = 0 ] \
  || { echo "a DB_ABORT trigger is installed: clear it before sweeping" >&2; exit 1; }

rev=$(git -C "$ROOT" rev-parse --short HEAD)
dirty=$(git -C "$ROOT" status --porcelain -- framework systems/spliit/model systems/spliit/properties | head -1)
if [ ! -s "$ROWS" ]; then
  sweep_header Spliit "$NAME" "rev $rev${dirty:+ (dirty)}" > "$ROWS"
else
  echo "# resumed $(date '+%Y-%m-%d %H:%M') -- rev $rev${dirty:+ (dirty)}" >> "$ROWS"
fi
[ -n "$dirty" ] && git -C "$ROOT" diff -- framework/ > "$LOGS/framework.$(date +%Y%m%d-%H%M).diff"

cp "$TC" "$TC.canonical.bak"
trap 'mv "$TC.canonical.bak" "$TC"' EXIT
for aut in $(ls "$VDIR"/tc_"$NAME".*.aut | sort -t. -k2 -n); do
  i=$(echo "$aut" | sed -e 's/.*\.\([0-9][0-9]*\)\.aut$/\1/')
  if [ -n "${ONLY:-}" ]; then echo " $ONLY " | grep -q " $i " || continue; fi
  if awk -F'\t' -v v="$i" '$1 == v { found = 1 } END { exit !found }' "$ROWS"; then
    echo "v$i already recorded, skipped"; continue
  fi
  # the walker derives the target fault from the canonical file name
  cp "$aut" "$TC"
  export CONCRETIZATION_DEBUG_DIR="$LOGS/v${i}_captures"
  SECONDS=0
  ( cd "$ROOT" && PYTHONPATH=framework .venv/bin/python -u framework/scripts/run.py \
      --aut "$TC" --platform html --url "$URL" \
      --system-interface "$SYS/model/system_interface_spliit.lnt" \
      --concrete-domain "$SYS/properties/concrete_domain.yml" \
      --type-description "$SYS/properties/type_description.yml" \
      --disruption-mapping "$SYS/properties/disruption_mapping.yml" \
      --timeout "${TIMEOUT:-10}" --report ) > "$LOGS/v$i.log" 2>&1
  rc=$?
  secs=$SECONDS
  {
    echo "--- fault state after the walk:"
    echo "trigger=$(docker exec -i spliit-db-1 psql -U postgres -d postgres -t -A -c "SELECT count(*) FROM pg_trigger WHERE tgname = 'fault_abort_write'" 2>&1)"
    echo "db_paused=$(docker inspect -f '{{.State.Paused}}' spliit-db-1 2>&1)"
    echo "proxy_faults=$(curl -s "$URL/admin/fault/status" 2>&1)"
  } >> "$LOGS/v$i.log"
  v=$(sweep_verdict "$rc" "$LOGS/v$i.log")
  note=""
  if [ "$v" = UNEXECUTABLE ]; then
    note=$(sed 's/\x1b\[[0-9;]*m//g' "$LOGS/v$i.log" | grep -m1 -oE '(UNEXECUTABLE \([^)]*\)|not confirmed[^.]*|Traceback.*|[A-Za-z]*Error: .*)' | tr '\t' ' ' | cut -c1-80)
    note="${note:-no verdict (exit $rc)}"
  fi
  sweep_row "$i" "$aut" "$secs" "$v" "$note" | tee -a "$ROWS"
done
