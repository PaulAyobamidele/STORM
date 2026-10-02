#!/usr/bin/env bash
# compile_stats.sh -- time the LNT -> BCG compile step for any SUT's formal
# model, record real states/transitions/labels via bcg_info, and append one
# row per target to <sut_dir>/compile_stats.tsv. eval_tables.py reads this
# file for Table 1's "Model" column. Nothing in it is ever typed in by hand,
# and nothing in this script knows any SUT's name -- that comes in as
# arguments.
#
#     export CADP=/path/to/cadp
#     export PATH="$CADP/com:$CADP/bin.mac64:$PATH"   # or bin.x64 on Linux
#
#     framework/scripts/compile_stats.sh <sut_dir> <model_dir> \
#         <target_name>:<lnt_file>:<root_process> [...]
#
#     # FoodYou:
#     framework/scripts/compile_stats.sh systems/foodyou systems/foodyou/model \
#         bare_spec:specification_foodyou_copy.lnt:SPEC \
#         composed:compose_foodyou_copy.lnt:COMPOSED
#
#     # Moodle:
#     framework/scripts/compile_stats.sh systems/moodle systems/moodle/model \
#         bare_spec:specification_moodle.lnt:SPEC \
#         composed:compose_moodle.lnt:COMPOSED
#
# Each row overwrites that target's PREVIOUS row for this SUT (last-one-wins
# per target, not an append-forever log) -- compile_stats.tsv characterises
# the CURRENT model, not its history.
set -u

: "${CADP:?export CADP=/path/to/cadp first}"

SUT_DIR="${1:?usage: compile_stats.sh <sut_dir> <model_dir> <name:lnt:process> [...]}"
MODEL_DIR="${2:?usage: compile_stats.sh <sut_dir> <model_dir> <name:lnt:process> [...]}"
shift 2
if [ "$#" -eq 0 ]; then
	echo "usage: compile_stats.sh <sut_dir> <model_dir> <name:lnt_file:root_process> [...]" >&2
	exit 1
fi

OUT="$SUT_DIR/compile_stats.tsv"
TMP=$(mktemp)
[ -f "$OUT" ] && cp "$OUT" "$TMP" || : > "$TMP"

run_one() {
	local target="$1" lnt_file="$2" root_process="$3"
	local bcg_out="/tmp/compile_stats_${target}.bcg"
	echo "=== $target ($lnt_file, root $root_process) ==="
	rm -f "$bcg_out"
	local start end secs
	start=$(date +%s)
	( cd "$MODEL_DIR" && lnt.open -root "$root_process" "$lnt_file" generator "$bcg_out" ) \
		> "/tmp/compile_stats_${target}.log" 2>&1
	local rc=$?
	end=$(date +%s)
	secs=$((end - start))
	if [ "$rc" -ne 0 ] || [ ! -s "$bcg_out" ]; then
		# -root failed (e.g. the target isn't the module's root process,
		# common for a composed model built via -main instead) -- retry once
		# with -main before giving up. Recording which one worked is not
		# itself part of the stat -- both mean "compiled from this LNT file".
		( cd "$MODEL_DIR" && lnt.open -main "$root_process" "$lnt_file" generator "$bcg_out" ) \
			> "/tmp/compile_stats_${target}.log" 2>&1
		rc=$?
		end=$(date +%s)
		secs=$((end - start))
	fi
	if [ "$rc" -ne 0 ] || [ ! -s "$bcg_out" ]; then
		echo "  FAILED (rc=$rc, ${secs}s) -- see /tmp/compile_stats_${target}.log"
		return 1
	fi
	local info states trans labels
	info=$(bcg_info "$bcg_out")
	states=$(echo "$info" | grep -oE '[0-9]+ states' | grep -oE '[0-9]+' | head -1)
	trans=$(echo "$info" | grep -oE '[0-9]+ transitions' | grep -oE '[0-9]+' | head -1)
	labels=$(echo "$info" | grep -oE '[0-9]+ labels' | grep -oE '[0-9]+' | head -1)
	echo "  ${secs}s -> ${states} states, ${trans} transitions, ${labels} labels"
	grep -v "^${target}	" "$TMP" > "${TMP}.new" 2>/dev/null || true
	mv "${TMP}.new" "$TMP"
	printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
		"$target" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$secs" "$states" "$trans" "$labels" >> "$TMP"
}

for spec in "$@"; do
	name=$(echo "$spec" | cut -d: -f1)
	lnt_file=$(echo "$spec" | cut -d: -f2)
	root_process=$(echo "$spec" | cut -d: -f3)
	run_one "$name" "$lnt_file" "$root_process"
done

mv "$TMP" "$OUT"
echo
echo "written to $OUT"
column -t -s"$(printf '\t')" "$OUT" 2>/dev/null || cat "$OUT"
