#!/bin/bash
# extract_happy.sbatch -- run generate_tc_all.sh under Slurm instead of on a
# login node.
#
#     sbatch --account=def-marssol extract_happy.sbatch            # all nine purposes
#     sbatch --account=def-marssol extract_happy.sbatch happy      # just one
#
# The --time in the SBATCH block below is sized for ONE purpose. Extracting all
# nine needs more: pass --time=24:00:00 on the command line to override it.
#
# Why: extract_all on the FoodYou happy CTG runs for hours and writes one BCG
# per extracted test case. On a login node the Alliance kills it for resource
# use, and an SSH drop kills it regardless. A batch job survives both, and its
# output lands in slurm-<jobid>.out whether or not you are still connected.
#
# Find your account with:  sacctmgr -nP show user "$USER" format=defaultaccount
#
#SBATCH --job-name=extract_happy
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --output=%x_%j.out

set -u

# No argument means EVERY purpose: generate_tc_all.sh has its own nine-purpose
# default, so pass nothing through and let it apply. This used to default to
# "happy", which made the no-argument form silently extract one purpose out of
# nine -- and the job would exit 0 having done an eighth of the work.
PURPOSE="${1:-all}"
# Second argument, when given, is the directory to run in. Needed to extract
# several purposes CONCURRENTLY: generate_tc_all.sh runs lnt.open on the shared
# compose_foodyou_copy.lnt and ends with `rm -f *.o *.t *.f *.lotos *.lib *.h`,
# so two jobs in one directory delete each other's intermediates. One directory
# per purpose removes the race. Serial runs can omit it and keep the flat dir.
#
# NOTE: this `cd` overrides sbatch --chdir, which is why --chdir alone does not
# isolate the jobs. Pass the directory here instead.
WORKDIR="${2:-/scratch/paulad/testor_foodyou}"

export CADP=/home/paulad/cadp
export PATH="$CADP/com:$CADP/bin.x64:$PATH"
export TESTOR_DIR="${TESTOR_DIR:-$CADP}"

cd "$WORKDIR" || { echo "no $WORKDIR" >&2; exit 1; }

# generate_tc_all.sh caps virtual memory at 80% of the node's PHYSICAL RAM,
# which inside a Slurm allocation is far above what the cgroup actually permits
# -- the job would then be OOM-killed by Slurm rather than failing gracefully at
# the ulimit. Cap to the allocation instead, and let the script's own (higher)
# ulimit call be the no-op.
if [ -n "${SLURM_MEM_PER_NODE:-}" ]; then
	ulimit -v $(( SLURM_MEM_PER_NODE * 1024 * 90 / 100 ))
fi

echo "host:    $(hostname)"
echo "purpose: $PURPOSE"
echo "started: $(date)"
df -h . | tail -1

if [ "$PURPOSE" = "all" ]; then
	sh generate_tc_all.sh
else
	sh generate_tc_all.sh "$PURPOSE"
fi
rc=$?

echo "finished: $(date)  rc=$rc"
echo "test cases extracted, per purpose:"
ls -1 variants/tc_*.aut 2>/dev/null \
  | sed 's|.*/tc_\(.*\)\.[0-9][0-9]*\.aut|\1|' | sort | uniq -c \
  | sed 's/^/  /'
echo "total: $(ls -1 variants/tc_*.aut 2>/dev/null | wc -l)"
exit $rc
