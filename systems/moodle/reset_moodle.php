<?php
/**
 * reset_moodle.php — return the fixture to a known state before a test case.
 *
 * WHY THIS EXISTS
 * ---------------
 * Every generated test case starts from the specification's initial state, in
 * which the student has NOT submitted anything: tp_happy's first concrete step
 * waits for the "Add submission" button. Moodle renders "Edit submission"
 * instead once a submission exists, so the second run of any assignment test
 * case stalls on a precondition and reports INCONCLUSIVE — not because the SUT
 * misbehaved, but because the run could not be set up.
 *
 * Observed exactly that: tc_happy reached VIEW_ASSIGN, then timed out waiting
 * for "Add submission" against a fixture left dirty by earlier probing.
 *
 * This is test isolation, not cleanup-for-tidiness. Without it a sweep's
 * verdicts depend on the order the cases happen to run in, which makes them
 * unattributable.
 *
 * WHAT IT DOES NOT TOUCH
 * ----------------------
 * The course, the users, the enrolments, the quiz, the assignment and the
 * question bank all survive. Only per-attempt and per-submission USER DATA is
 * cleared, so seed_moodle.php does not need re-running.
 *
 * Run from the host before each test case:
 *   cd systems/moodle/sut/moodle-docker
 *   bin/moodle-docker-compose exec -T webserver php /dev/stdin < ../../reset_moodle.php
 */

define('CLI_SCRIPT', true);

require_once('/var/www/html/config.php');
require_once($CFG->dirroot . '/mod/quiz/locallib.php');
require_once($CFG->dirroot . '/mod/assign/locallib.php');
require_once($CFG->libdir . '/gradelib.php');

global $DB, $CFG;

function say(string $m): void { echo $m . "\n"; }

$course = $DB->get_record('course', ['shortname' => 'MOD']);
if (!$course) {
    cli_error('Course MOD not found — run seed_moodle.php first.');
}

// ---------------------------------------------------------------------------
// 1. Quiz attempts.
//
// quiz_delete_all_attempts() is used rather than a DELETE, because an attempt
// owns rows in question_usages / question_attempts / question_attempt_steps
// and the quiz grade cache. Deleting only m_quiz_attempts would leave those
// orphaned, and DB_ATTEMPT_STEP_LOSS asserts on exactly that table — a stale
// orphan would make its verdict meaningless.
// ---------------------------------------------------------------------------
$quiz = $DB->get_record('quiz', ['course' => $course->id, 'name' => 'Model_Quiz']);
if ($quiz) {
    // quiz_delete_attempt() per attempt, NOT a DELETE and NOT
    // quiz_delete_all_attempts() -- the latter does not exist in 4.5
    // (verified: mod/quiz/locallib.php declares only quiz_delete_attempt).
    // It is the supported path because it also removes the question usage,
    // question_attempts and question_attempt_steps that the attempt owns.
    $attempts = $DB->get_records('quiz_attempts', ['quiz' => $quiz->id]);
    foreach ($attempts as $attempt) {
        quiz_delete_attempt($attempt, $quiz);
    }
    $DB->delete_records('quiz_grades', ['quiz' => $quiz->id]);
    say('quiz: deleted ' . count($attempts) . ' attempt(s), their question usages and grades');
}

// ---------------------------------------------------------------------------
// 2. Assignment submissions.
//
// Plugin rows first, then the submission rows they reference: the reverse
// order would orphan the onlinetext, which is the very table
// APP_PARTIAL_SUBMISSION targets.
// ---------------------------------------------------------------------------
$assign = $DB->get_record('assign', ['course' => $course->id, 'name' => 'Model_Assignment']);
if ($assign) {
    $subids = $DB->get_fieldset_select('assign_submission', 'id', 'assignment = ?', [$assign->id]);
    if ($subids) {
        list($insql, $params) = $DB->get_in_or_equal($subids);
        $DB->delete_records_select('assignsubmission_onlinetext', "submission $insql", $params);
        $DB->delete_records_select('assignsubmission_file',       "submission $insql", $params);
    }
    $ns = $DB->delete_records('assign_submission', ['assignment' => $assign->id]);
    $DB->delete_records('assign_grades',     ['assignment' => $assign->id]);
    $DB->delete_records('assign_user_flags', ['assignment' => $assign->id]);
    say('assign: cleared ' . count($subids) . ' submission(s), grades and user flags');
}

// ---------------------------------------------------------------------------
// 3. Gradebook.
//
// Clearing the raw grades is not enough: grade_items carries a needsupdate
// flag, and APP_LAZY_REGRADE injects by SETTING that flag. Leaving it set from
// a previous run would mean the fault was already active before injection, so
// the oracle could not distinguish injected from residual.
// ---------------------------------------------------------------------------
$items = $DB->get_records('grade_items', ['courseid' => $course->id]);
foreach ($items as $item) {
    $DB->delete_records('grade_grades', ['itemid' => $item->id]);
}
$DB->set_field('grade_items', 'needsupdate', 0, ['courseid' => $course->id]);
say('gradebook: cleared ' . count($items) . ' item(s) and reset needsupdate');

// ---------------------------------------------------------------------------
// 4. Any fault left latched by a crashed run.
//
// check_faults.py restores what IT injected, but a run killed mid-walk cannot.
// A trigger still in place would silently apply to the NEXT test case, whose
// verdict would then describe a fault it never asked for.
// ---------------------------------------------------------------------------
$triggers = ['storm_app1_write_fail'      => 'm_quiz_attempts',
             'storm_partial_submission'   => 'm_assignsubmission_onlinetext',
             'storm_attempt_step_loss'    => 'm_question_attempt_steps'];
$dropped = 0;
foreach ($triggers as $tg => $tbl) {
    $exists = $DB->get_field_sql("SELECT count(*) FROM pg_trigger WHERE tgname = ?", [$tg]);
    if ($exists) {
        $DB->execute("DROP TRIGGER IF EXISTS $tg ON $tbl");
        $dropped++;
    }
}
$DB->set_field('task_scheduled', 'disabled', 0,
               ['classname' => '\mod_quiz\task\update_overdue_attempts']);
say("faults: dropped {$dropped} latched trigger(s), re-enabled the overdue task");

// The submission text the oracle distinguishes revisions by. Reset so a
// leftover REVISION-FINAL cannot make a stale read look like a fresh one.
$DB->execute("UPDATE {assignsubmission_onlinetext} SET onlinetext = ''");

rebuild_course_cache($course->id, true);
purge_all_caches();

say('');
say('fixture reset: no submissions, no attempts, no grades, no latched faults');
say('course/users/enrolments/quiz/assignment left intact');
