#!/bin/bash
# launch_sweep.sh [purposes...] -- start run_all.sh in a detached tmux session
# (sb_sweep) under caffeinate, with the environment sourced inside it.
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PURPOSES="${*:-ue_offline app_unavailable infra_doze input_invalid input_overnight ue_storage_full db_corrupt_local infra_storage_media}"
tmux kill-session -t sb_sweep 2>/dev/null
tmux new -d -s sb_sweep "cd $ROOT && source EVALUATION/simplebaby/env.sh && caffeinate -dimsu bash EVALUATION/simplebaby/run_all.sh $PURPOSES; sleep 600"
echo "started sb_sweep: $PURPOSES"
