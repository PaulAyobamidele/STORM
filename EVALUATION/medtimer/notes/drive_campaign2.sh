#!/usr/bin/env bash
# drive_campaign2.sh -- pull each purpose's test cases from narval as soon as
# generate_tc_all.sh has finished it, then walk every variant on the emulator
# with run_variants.sh. A walk that runs past WALK_CAP seconds is stopped by a
# watchdog (it would otherwise block the sweep); run_variants.sh then records
# it UNEXECUTABLE, i.e. a walk to repeat, never a verdict.
#
#     source EVALUATION/medtimer/env.sh
#     bash EVALUATION/medtimer/notes/drive_campaign2.sh [purpose ...]
set -u
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SYS="$ROOT/EVALUATION/medtimer"
REMOTE=narval:/scratch/paulad/testor_medtimer
WALK_CAP="${WALK_CAP:-1800}"
PURPOSES="${*:-nominal ue_kill app_write_fail db_abort infra_storage_full app_cache_stale db_corrupt db_corrupt_stock db_event_loss infra_storage_media input_invalid cannot_skip delete_skipped edit_flip}"

watchdog() {
  while sleep 30; do
    for pid in $(pgrep -f "framework/scripts/run.py --aut $SYS/Test_Cases/"); do
      age=$(ps -o etime= -p "$pid" | awk -F'[-:]' '{ s = 0; for (i = 1; i <= NF; i++) s = s * 60 + $i; if (NF == 4) s = $1 * 86400 + $2 * 3600 + $3 * 60 + $4; print s }')
      if [ "${age:-0}" -gt "$WALK_CAP" ]; then
        echo "watchdog: walk pid $pid ran ${age}s > ${WALK_CAP}s, stopped" >&2
        kill "$pid"
      fi
    done
  done
}
watchdog & WD=$!
trap 'kill $WD 2>/dev/null' EXIT

for p in $PURPOSES; do
  # LOCAL=1: every purpose was already pulled (generation finished), so the
  # sweep needs no narval connection, which would otherwise ask for MFA.
  if [ -z "${LOCAL:-}" ]; then
    echo "=== $p: waiting for generation ($(date '+%H:%M'))"
    until ssh -o BatchMode=yes narval "grep -q '^$p	' /scratch/paulad/testor_medtimer/gen_times.tsv" 2>/dev/null; do sleep 120; done
    mkdir -p "$SYS/Test_Cases/variants/$p"
    rsync -a --delete "$REMOTE/variants/$p/" "$SYS/Test_Cases/variants/$p/" 2>/dev/null
  fi
  cp "$SYS/Test_Cases/variants/$p/tc_$p.1.aut" "$SYS/Test_Cases/tc_$p.aut"
  echo "=== $p: $(ls "$SYS/Test_Cases/variants/$p"/*.aut | wc -l | tr -d ' ') variants, walking ($(date '+%H:%M'))"
  bash "$SYS/run_variants.sh" "$p"
done
[ -z "${LOCAL:-}" ] && for f in gen_times.tsv generate_tc_all.log model_size.txt inputs.md5; do
  rsync -a "$REMOTE/$f" "$SYS/$f" 2>/dev/null
done
echo "=== sweep done ($(date '+%H:%M'))"
