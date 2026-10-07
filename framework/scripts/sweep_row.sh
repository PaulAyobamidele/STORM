#!/bin/sh
# sweep_row.sh -- the ONE row format every SUT's sweep driver (its own
# run_variants.sh) emits, so eval_tables.py can read any of them with zero
# SUT-specific code. Source it, don't execute it:
#
#     . "$(cd "$(dirname "$0")/../.." && pwd)/framework/scripts/sweep_row.sh"
#     sweep_row "$i" "$aut_file" "$elapsed_seconds" "$verdict" "$note"
#
# CANONICAL SCHEMA -- tab-separated, one row per variant, written to
# EVALUATION/<sut>/variants_<purpose>.log (and optionally
# variants_<purpose>.recheck.log for a subset re-run, which eval_tables.py
# layers on top of the base file by variant number):
#
#     VARIANT   STATES   TRANSITIONS   TIME_S   VERDICT   NOTE
#
# TIME_S and NOTE may be the empty string -- "not measured", never a
# placeholder word ("NA", "--", ...), so a missing field parses identically
# everywhere and can never be confused with a real value.
#
# VERDICT is exactly one of: PASS FAIL INCONC UNEXECUTABLE -- the same four
# words regardless of which SUT or executor produced the row. UNEXECUTABLE
# means "no verdict was produced" (run.py exit code 2, a crash, an unconfirmed
# fault: an apparatus problem, not SUT evidence). It is reported in its own
# column and never summed with INCONC, which IS a genuine ioco outcome the
# walk reasoned its way to. No other word (HARNESS, ERROR, MISSING) is written.
#
# STATES/TRANSITIONS are read directly from the .aut file's own CADP header
# (`des (0, transitions, states)`), the same way every generate_tc_all.sh-
# style script already prints them -- this function does not invent that
# parsing, it centralizes it so two SUTs' sweep drivers do not each carry
# their own slightly-different copy.

sweep_row() {
	# $1 variant index    $2 path to this variant's .aut file
	# $3 elapsed seconds, or "" if not timed
	# $4 verdict (PASS/FAIL/INCONC/UNEXECUTABLE)
	# $5 free-text note, or "" (e.g. Moodle's "UNCONFIRMED")
	_sr_variant="$1"; _sr_aut="$2"; _sr_time="$3"; _sr_verdict="$4"; _sr_note="${5:-}"
	_sr_hdr=$(head -1 "$_sr_aut" 2>/dev/null | tr -dc '0-9,')
	_sr_trans=$(echo "$_sr_hdr" | cut -d, -f2)
	_sr_states=$(echo "$_sr_hdr" | cut -d, -f3)
	printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
		"$_sr_variant" "$_sr_states" "$_sr_trans" "$_sr_time" "$_sr_verdict" "$_sr_note"
}

sweep_header() {
	# $1 SUT name   $2 purpose   $3 optional provenance (e.g. "rev abc1234 (dirty)")
	printf '# %s tc variants -- purpose: %s -- %s%s\n' "$1" "$2" "$(date '+%Y-%m-%d %H:%M')" "${3:+ -- $3}"
	printf 'VARIANT\tSTATES\tTRANSITIONS\tTIME_S\tVERDICT\tNOTE\n'
}

sweep_verdict() {
	# $1 run.py exit code   $2 the walk's log
	# Exit code 2 is run.py's "no verdict was produced"; otherwise the LAST
	# `Verdict: X` line the walk printed. No verdict line at all is also
	# UNEXECUTABLE: the walk ended before the SUT was put to the question.
	if [ "$1" = 2 ]; then echo UNEXECUTABLE; return; fi
	_sv=$(sed 's/\x1b\[[0-9;]*m//g' "$2" | grep -oE 'Verdict: (PASS|FAIL|INCONC)' | tail -1 | cut -d' ' -f2)
	echo "${_sv:-UNEXECUTABLE}"
}
