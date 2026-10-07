#!/bin/sh
# watch_state.sh — live view of the SUT state a test case is driving.
#
# Shows, every 2s, the four things the oracles read plus whether a fault is
# actually installed. Run it in a second terminal beside a sweep.
#
# Scalar subqueries, not UNION over the tables: an empty table contributes no
# ROW to a union, so a clean fixture printed a short list and looked like a
# broken query rather than like "nothing submitted yet".
#
#   sh watch_state.sh          # refresh every 2s
#   INTERVAL=5 sh watch_state.sh
# ---------------------------------------------------------------------------
set -u

SUT=$(cd "$(dirname "$0")" && pwd)
DOCKER="$SUT/sut/moodle-docker"
INTERVAL="${INTERVAL:-2}"

MOODLE_DOCKER_WWWROOT="$SUT/sut/moodle"
MOODLE_DOCKER_DB=pgsql
export MOODLE_DOCKER_WWWROOT MOODLE_DOCKER_DB

SQL="
SELECT
  'submission status : ' || coalesce((SELECT status FROM m_assign_submission LIMIT 1), '(no submission)')
  || E'\n' ||
  'submission text   : ' || coalesce((SELECT onlinetext FROM m_assignsubmission_onlinetext LIMIT 1), '(no content row)')
  || E'\n' ||
  'quiz attempt      : ' || coalesce((SELECT id || ':' || state FROM m_quiz_attempts ORDER BY id DESC LIMIT 1), '(no attempt)')
  || E'\n' ||
  'answer steps      : ' || coalesce((SELECT string_agg(sequencenumber || ':' || state, '  ' ORDER BY sequencenumber) FROM m_question_attempt_steps), '(none)')
  || E'\n' ||
  'grade             : ' || coalesce((SELECT round(finalgrade,2)::text FROM m_grade_grades WHERE finalgrade IS NOT NULL LIMIT 1), '(none)')
  || E'\n' ||
  'INJECTED FAULT    : ' || coalesce((SELECT string_agg(tgname, ', ') FROM pg_trigger WHERE tgname LIKE 'storm%'), '(none)');
"

while true; do
  OUT=$(cd "$DOCKER" && bin/moodle-docker-compose exec -T db \
          psql -U moodle -d moodle -tAc "$SQL" 2>&1)
  clear
  echo "Moodle live state — $(date '+%H:%M:%S')   (Ctrl-C to stop)"
  echo "-------------------------------------------------------------"
  echo "$OUT"
  sleep "$INTERVAL"
done
