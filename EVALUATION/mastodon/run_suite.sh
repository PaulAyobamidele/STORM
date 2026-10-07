#!/bin/sh
# run_suite.sh -- one campaign sweep over every generated Mastodon test case,
# recorded so that every column of the results table is regenerable from files
# (the "capturing the evaluation numbers" procedure).
#
#   export MASTODON_PW=...                       (never in the repo)
#   sh EVALUATION/mastodon/run_suite.sh CAMPAIGN [purpose ...]
#
# CAMPAIGN names runs/CAMPAIGN/. On its first start the sweep FREEZES a
# snapshot there -- framework/, the model, the properties, the cases -- and
# every walk of that campaign runs from the snapshot, never from the working
# tree, so other work cannot change a campaign mid-way. The header of
# runs/CAMPAIGN/SWEEP.txt records the git revision, the dirty flag and, when
# dirty, runs/CAMPAIGN/framework.diff.
#
# Per case (variant N of purpose P):
#   EVALUATION/mastodon/variants_P.log   one row, appended (File 1 of the shared
#   results format, header written once):
#       VARIANT  STATES  TRANSITIONS  TIME_S  VERDICT  NOTE
#     VERDICT is PASS, FAIL or INCONC from the walk; UNEXECUTABLE when the walk
#     produced no verdict (the harness under `verdicts: ioco` prints such a walk
#     as INCONC with "the walk could not be completed": that is NOT an ioco
#     INCONC and is recorded UNEXECUTABLE, so the two are never summed).
#   generated/variant_logs/P/vN.seed.log, vN.log, vN_captures/   kept for ever
# Resume: re-running the same CAMPAIGN appends, and skips every variant that
# already has a row. REPEAT=1 walks the named purposes AGAIN for
# reproducibility evidence, into runs/CAMPAIGN/repeats/ (rows and logs), which
# eval_tables.py never reads: a case counts once, by its first recorded walk. A seed that does not prove a clean stack stops the sweep.
set -u
cd "$(dirname "$0")/../.." || exit 1
ROOT=$(pwd); M=EVALUATION/mastodon
C=${1:?usage: run_suite.sh CAMPAIGN [purpose ...]}; shift
[ -n "${MASTODON_PW:-}" ] || { echo "MASTODON_PW is not set"; exit 1; }
ORDER="nominal input_invalid input_overlimit ue_kill ue_session_expired app_write_fail app_unavailable db_abort infra_db_down infra_storage_full app_extapi_fail infra_sidekiq_dead app_cache_stale db_event_loss db_corrupt app_lazy_processing"
PURPOSES="${*:-$ORDER}"
CD=$M/runs/$C; SNAP=$CD/snapshot
if [ ! -d "$SNAP" ]; then
  mkdir -p "$SNAP"
  cp -R framework "$SNAP/framework"
  mkdir -p "$SNAP/mastodon"
  cp -R $M/model $M/properties "$SNAP/mastodon/"
  cp -R $M/Test_Cases "$SNAP/mastodon/tc"
  { echo "# campaign $C, frozen $(date +%Y-%m-%dT%H:%M:%S)"
    echo "# git revision $(git rev-parse HEAD)"
    if [ -n "$(git status --porcelain -- framework EVALUATION/mastodon/model EVALUATION/mastodon/properties)" ]; then
      echo "# tree DIRTY: framework.diff and snapshot/ hold exactly what ran"
      git diff -- framework > "$CD/framework.diff"
      git status --porcelain -- framework > "$CD/framework.status"
    else echo "# tree clean"; fi
    echo "# inputs: $M/Test_Cases/inputs_md5.txt (Mac vs CADP node)"
  } > "$CD/SWEEP.txt"
  ( cd "$SNAP/framework" && PYTHONPATH=. "$ROOT/.venv/bin/python" -m pytest -q tests > "$ROOT/$CD/framework_selftest.txt" 2>&1 )
  echo "# framework self-test of the snapshot: $(tail -1 "$CD/framework_selftest.txt")" >> "$CD/SWEEP.txt"
fi
cat "$CD/SWEEP.txt"
# the shared row format (framework/scripts/sweep_row.sh), from the snapshot
. "$SNAP/framework/scripts/sweep_row.sh"
PROV="rev $(git rev-parse --short HEAD)$( [ -n "$(git status --porcelain -- framework)" ] && echo ' (dirty)'), campaign $C"
VL=$M/generated/variant_logs; RUN=$CD/run; mkdir -p "$RUN"
echo "# sweep start $(date +%Y-%m-%dT%H:%M:%S) purposes: $PURPOSES" >> "$CD/SWEEP.txt"

REP=${REPEAT:-0}
for p in $PURPOSES; do
  LOG=$M/variants_$p.log
  if [ "$REP" = 1 ]; then mkdir -p "$CD/repeats"; LOG=$CD/repeats/variants_$p.log; fi
  [ -f "$LOG" ] || sweep_header mastodon "$p" "$PROV" > "$LOG"
  mkdir -p "$VL/$p"
  for v in $(ls $SNAP/mastodon/tc/variants/$p/tc_$p.*.aut 2>/dev/null | sort -t. -k2 -n); do
    i=$(echo "$v" | sed -e 's/.*\.\([0-9][0-9]*\)\.aut$/\1/')
    if [ "$REP" != 1 ] && grep -qE "^$i[[:space:]]" "$LOG"; then echo "== $p v$i: already recorded, skipped"; continue; fi
    tag=v$i
    if [ "$REP" = 1 ]; then
      n=$(grep -cE "^$i[[:space:]]" "$LOG" 2>/dev/null); [ -n "$n" ] || n=0
      tag=v$i.repeat$((n + 1))
    fi
    echo "== $p $tag"
    if ! sh $M/seed.sh > "$VL/$p/$tag.seed.log" 2>&1; then
      echo "   stack NOT clean before the walk -- sweep stopped; see $VL/$p/$tag.seed.log"
      echo "# sweep stopped $(date +%Y-%m-%dT%H:%M:%S) at $p v$i: seed failed" >> "$CD/SWEEP.txt"; exit 1
    fi
    cp "$v" "$RUN/tc_$p.aut"
    SECONDS=0
    CONCRETIZATION_DEBUG_DIR="$VL/$p/${tag}_captures" PYTHONPATH="$SNAP/framework" \
      .venv/bin/python "$SNAP/framework/scripts/run.py" --aut "$RUN/tc_$p.aut" \
      --platform html --url https://mastodon.localhost \
      --system-interface "$SNAP/mastodon/model/system_interface_mastodon.lnt" \
      --concrete-domain "$SNAP/mastodon/properties/concrete_domain.yml" \
      --type-description "$SNAP/mastodon/properties/type_description.yml" \
      --disruption-mapping "$SNAP/mastodon/properties/disruption_mapping.yml" \
      --timeout 10 --report > "$VL/$p/$tag.log" 2>&1
    rc=$?
    dt=$SECONDS
    verdict=$(sweep_verdict "$rc" "$VL/$p/$tag.log")
    # also no verdict: a walk the harness could not complete, which it prints
    # as INCONC under `verdicts: ioco` (not covered by sweep_verdict)
    if grep -q 'the walk could not be completed' "$VL/$p/$tag.log"; then verdict=UNEXECUTABLE; fi
    inj=$(grep -c 'injected and confirmed' "$VL/$p/$tag.log")
    res=$(grep -c 'restored and confirmed cleared' "$VL/$p/$tag.log")
    cause=$(grep -E 'mismatch|required an output|precondition for|not confirmed' "$VL/$p/$tag.log" | head -1 | sed -e 's/ on \[.*//' -e 's/\t/ /g' | cut -c1-120)
    sweep_row "$i" "$v" "$dt" "$verdict" "injected=$inj restored=$res $cause" >> "$LOG"
    echo "   $verdict  (${dt}s, injected $inj, restored $res)  $(tail -1 "$LOG" | cut -f2,3 | tr '\t' '/') states/transitions"
  done
done
echo "== after the sweep"; sh $M/seed.sh | tail -15
echo "# sweep end $(date +%Y-%m-%dT%H:%M:%S)" >> "$CD/SWEEP.txt"
