<?php
/**
 * seed_moodle.php — fixture seed for the Moodle case study.
 *
 * The moodle-docker volume was recreated at some point, so the database is a
 * fresh install: admin has no email (Moodle therefore pins every request to
 * /user/editadvanced.php titled "Installation"), the only course is the site
 * front page, and there are zero quizzes and zero assignments. Nothing the
 * System Interface needs exists.
 *
 * This rebuilds the minimum fixture the specification's two paths require:
 *
 *   quiz path   VIEW_QUIZ / START_ATTEMPT / SAVE_ATTEMPT / PROCESS_ATTEMPT /
 *               GRADE_PERSISTED  -> needs an attemptable quiz, so at least one
 *               question, and a grade to persist.
 *   assign path VIEW_ASSIGN / SUBMIT_DRAFT / UPDATE_SUBMISSION /
 *               GRADE_SUBMISSION / CONFIRMED_GRADE -> needs an online-text
 *               assignment that can be submitted, updated and graded, and a
 *               teacher distinct from the student.
 *
 * Run from the host (NOT from a browser -- CLI only):
 *
 *   cd systems/moodle/sut/moodle-docker
 *   bin/moodle-docker-compose exec -T webserver php /dev/stdin \
 *       < ../../seed_moodle.php
 *
 * Idempotent: re-running reuses the course/modules/users if already present,
 * so it is safe to run again after a partial failure.
 */

define('CLI_SCRIPT', true);

require_once('/var/www/html/config.php');
require_once($CFG->libdir . '/testing/generator/lib.php');
require_once($CFG->dirroot . '/mod/quiz/locallib.php');
require_once($CFG->dirroot . '/course/lib.php');
require_once($CFG->libdir . '/gradelib.php');

global $DB, $CFG;

function say(string $m): void {
    echo $m . "\n";
}

// ---------------------------------------------------------------------------
// 0. Finish the admin account.
//
// Moodle redirects every request to user/editadvanced.php while the primary
// admin has no email address -- that is the "Installation" page seen at
// http://localhost:8080/. Filling it in is what releases the site.
// ---------------------------------------------------------------------------
$admin = $DB->get_record('user', ['username' => 'admin']);
if (!$admin) {
    cli_error('No admin user found - the database is not installed.');
}
$dirty = false;
if (empty($admin->email)) {
    $admin->email = 'admin@example.com';
    $dirty = true;
}
if (empty($admin->city)) {
    $admin->city = 'Testville';
    $dirty = true;
}
if (empty($admin->country)) {
    $admin->country = 'GB';
    $dirty = true;
}
if ($dirty) {
    $DB->update_record('user', $admin);
    say("admin: profile completed (email={$admin->email})");
} else {
    say("admin: profile already complete (email={$admin->email})");
}
// Always reset the password so the credential is known and recorded.
update_internal_user_password($admin, 'Test1234!');
say('admin: password set to Test1234!');

// Site front page name, so the site is not nameless.
if (empty($SITE->fullname)) {
    $site = $DB->get_record('course', ['id' => SITEID]);
    $site->fullname  = 'Moodle SUT';
    $site->shortname = 'MOODLESUT';
    $DB->update_record('course', $site);
    say('site: front page named');
}

// ---------------------------------------------------------------------------
// 0b. Gradebook roles.
//
// $CFG->gradebookroles is core config, normally set during install to the
// student role id. On this database it was NULL — the same unfinished-install
// symptom as the missing admin email and the absent enrol_manual defaults.
// With it unset the gradebook cannot tell which roles count as graded users,
// so EVERY /grade/report/* route fails and APP_LAZY_REGRADE has no observable
// at all. Its oracle (COURSE_TOTAL) is unreachable rather than passing, which
// would have looked like a result.
// ---------------------------------------------------------------------------
$studentroleid = $DB->get_field('role', 'id', ['shortname' => 'student']);
if (empty($CFG->gradebookroles) && $studentroleid) {
    set_config('gradebookroles', $studentroleid);
    say("gradebook: gradebookroles set to student role id={$studentroleid}");
} else {
    say('gradebook: gradebookroles already set');
}

// ---------------------------------------------------------------------------
// 0c. Plain-text editor.
//
// $CFG->texteditors defaults to "tiny,atto,tinymce,textarea", so TinyMCE wins
// and REPLACES the submission textarea with an iframe, hiding the original.
// sel_online_text_editor (//textarea[@id='id_onlinetext_editor']) is present in
// the served HTML — which is why it verified fine against raw HTML — but is
// never VISIBLE in a real browser, so wait_for times out and the run reports
// INCONCLUSIVE. Observed exactly that on the first clean run of tc_happy.
//
// Forcing the plain textarea does not weaken what is tested: the property is
// about the submission CONTENT and its persistence, not about which editor
// widget renders it. It also removes a large amount of JS from the path, which
// is a source of flakiness rather than of test power.
// ---------------------------------------------------------------------------
if (get_config(null, 'texteditors') !== 'textarea') {
    set_config('texteditors', 'textarea');
    say('editor: texteditors set to plain textarea (TinyMCE hides the real one)');
} else {
    say('editor: already plain textarea');
}

$generator = new testing_data_generator();

// ---------------------------------------------------------------------------
// 1. Course
// ---------------------------------------------------------------------------
$course = $DB->get_record('course', ['shortname' => 'MOD']);
if (!$course) {
    $course = $generator->create_course([
        'shortname'  => 'MOD',
        'fullname'   => 'Model Course',
        'format'     => 'topics',
        'numsections' => 3,
    ]);
    say("course: created id={$course->id} shortname=MOD");
} else {
    say("course: reusing id={$course->id} shortname=MOD");
}
$coursecontext = context_course::instance($course->id);

// ---------------------------------------------------------------------------
// 2. Users -- a student to act, a teacher to grade.
//
// The specification has STUDENT and TEACHER as separate processes, and the
// stale-read property (teacher grades the version the student did NOT end up
// with) is only expressible if they are genuinely different accounts.
// ---------------------------------------------------------------------------
function ensure_user(testing_data_generator $generator, string $username,
                     string $first, string $last, string $password): stdClass {
    global $DB;
    $u = $DB->get_record('user', ['username' => $username]);
    if (!$u) {
        $u = $generator->create_user([
            'username'  => $username,
            'firstname' => $first,
            'lastname'  => $last,
            'email'     => $username . '@example.com',
            'password'  => $password,
        ]);
        say("user: created {$username} id={$u->id}");
    } else {
        update_internal_user_password($u, $password);
        say("user: reusing {$username} id={$u->id} (password reset)");
    }
    return $u;
}

$student = ensure_user($generator, 'student1', 'Stu', 'Dent', 'Student1!');
$teacher = ensure_user($generator, 'teacher1', 'Tea', 'Cher', 'Teacher1!');

// Enrolment needs an explicit `manual' enrol INSTANCE on the course.
//
// create_course() only adds default enrol instances for the plugins listed in
// $CFG->enrol_plugins_enabled, and on this fresh install that produced none —
// m_enrol had zero rows for the course. enrol_user() then silently no-ops, so
// the first version of this script reported success while enrolling nobody and
// every course page answered require_login() with a Notice. Hence: create the
// instance, then VERIFY with is_enrolled() rather than trusting the call.
require_once($CFG->libdir . '/enrollib.php');

$enabled = explode(',', (string)get_config(null, 'enrol_plugins_enabled'));
if (!in_array('manual', $enabled, true)) {
    $enabled[] = 'manual';
    set_config('enrol_plugins_enabled', implode(',', array_filter($enabled)));
    say('enrol: enabled the manual enrolment plugin');
}

$manual = enrol_get_plugin('manual');
if (!$manual) {
    cli_error('The manual enrolment plugin is unavailable.');
}

// The enrol_manual plugin's default settings were never installed on this
// database, so get_config('enrol_manual','status') is null and
// add_default_instance() builds an INSERT with status=NULL — which the
// not-null constraint on m_enrol.status rejects. Install the defaults, then
// pass the fields explicitly rather than depending on them being read back.
$studentroleid = $DB->get_field('role', 'id', ['shortname' => 'student']);
$manualdefaults = [
    'status'                  => ENROL_INSTANCE_ENABLED,
    'roleid'                  => $studentroleid,
    'enrolperiod'             => 0,
    'expirynotify'            => 0,
    'expirythreshold'         => 0,
    'notifyall'               => 0,
    'sendcoursewelcomemessage' => 0,
];
foreach ($manualdefaults as $k => $v) {
    if (get_config('enrol_manual', $k) === false) {
        set_config($k, $v, 'enrol_manual');
    }
}

$instance = $DB->get_record('enrol', ['courseid' => $course->id, 'enrol' => 'manual']);
if (!$instance) {
    $instanceid = $manual->add_instance($course, [
        'status'          => ENROL_INSTANCE_ENABLED,
        'roleid'          => $studentroleid,
        'enrolperiod'     => 0,
        'expirynotify'    => 0,
        'expirythreshold' => 0,
        'notifyall'       => 0,
    ]);
    if (!$instanceid) {
        cli_error('Could not create a manual enrolment instance.');
    }
    $instance = $DB->get_record('enrol', ['id' => $instanceid], '*', MUST_EXIST);
    say("enrol: created manual enrol instance id={$instance->id}");
} else {
    say("enrol: reusing manual enrol instance id={$instance->id}");
}
if ((int)$instance->status !== ENROL_INSTANCE_ENABLED) {
    $manual->update_status($instance, ENROL_INSTANCE_ENABLED);
    $instance = $DB->get_record('enrol', ['id' => $instance->id], '*', MUST_EXIST);
    say('enrol: instance enabled');
}

function ensure_enrolled(enrol_plugin $manual, stdClass $instance, stdClass $user,
                         string $roleshortname, context_course $ctx): void {
    global $DB;
    $role = $DB->get_record('role', ['shortname' => $roleshortname], '*', MUST_EXIST);
    if (!is_enrolled($ctx, $user->id)) {
        $manual->enrol_user($instance, $user->id, $role->id, 0, 0, ENROL_USER_ACTIVE);
    }
    // Verify, do not assume — this is exactly what went wrong before.
    if (!is_enrolled($ctx, $user->id)) {
        cli_error("FAILED to enrol {$user->username} in course {$instance->courseid}");
    }
    say("enrol: {$user->username} -> {$roleshortname} (verified)");
}

ensure_enrolled($manual, $instance, $student, 'student', $coursecontext);
ensure_enrolled($manual, $instance, $teacher, 'editingteacher', $coursecontext);

// ---------------------------------------------------------------------------
// 3. Quiz, with one multichoice question so it is actually attemptable.
//
// A quiz with no questions cannot be started, so START_ATTEMPT would have no
// concrete counterpart and the whole quiz path of the model would be dead.
// ---------------------------------------------------------------------------
$quiz = $DB->get_record('quiz', ['course' => $course->id, 'name' => 'Model_Quiz']);
if (!$quiz) {
    $quiz = $generator->create_module('quiz', [
        'course'         => $course->id,
        'name'           => 'Model_Quiz',
        'grade'          => 100,
        'sumgrades'      => 1,
        'attempts'       => 0,          // unlimited: the sweep re-attempts often
        'preferredbehaviour' => 'deferredfeedback',
        // A TIME LIMIT IS REQUIRED FOR INFRA_CRON_DEAD TO BE REACHABLE AT ALL.
        // \mod_quiz\task\update_overdue_attempts only has work to do once an
        // attempt is past its deadline. With timelimit=0 no attempt can ever
        // become overdue, so disabling that task violates nothing and the
        // fault would report a vacuous pass rather than being unreachable —
        // which is worse, because it looks like a result.
        // 60s is long enough to complete an attempt normally and short enough
        // that a test case can deliberately leave one open.
        'timelimit'      => 60,
        'overduehandling' => 'autosubmit',
    ]);
    say("quiz: created id={$quiz->id} cmid={$quiz->cmid} timelimit=60s overdue=autosubmit");
} else {
    $cm = get_coursemodule_from_instance('quiz', $quiz->id, $course->id);
    $quiz->cmid = $cm->id;
    say("quiz: reusing id={$quiz->id} cmid={$quiz->cmid}");
}

// The question step is INDEPENDENT of the quiz step on purpose. A previous run
// created the quiz and then died here, so keying this off `if (!$quiz)` would
// skip it forever and leave an unattemptable quiz behind.
//
// core_question_generator is NOT usable here: question/tests/generator/lib.php
// requires question/engine/tests/helpers.php -> lib/phpunit/lib.php, which
// needs PHPUnit\Framework\TestCase, and composer has never been run in this
// container. Moodle XML import is the supported non-test path and does not
// touch the phpunit tree.
$slots = $DB->count_records('quiz_slots', ['quizid' => $quiz->id]);
if ($slots == 0) {
    require_once($CFG->dirroot . '/question/format.php');
    require_once($CFG->dirroot . '/question/format/xml/format.php');
    require_once($CFG->dirroot . '/lib/questionlib.php');

    $qcat = $DB->get_record('question_categories', [
        'contextid' => $coursecontext->id,
        'name'      => 'Model Questions',
    ]);
    if (!$qcat) {
        $qcat = (object)[
            'name'       => 'Model Questions',
            'contextid'  => $coursecontext->id,
            'info'       => 'Fixture questions for the STORM Moodle case study',
            'infoformat' => FORMAT_HTML,
            'parent'     => 0,
            'sortorder'  => 999,
            'stamp'      => make_unique_id_code(),
        ];
        $qcat->id = $DB->insert_record('question_categories', $qcat);
        say("question: created category id={$qcat->id}");
    }

    $xml = <<<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<quiz>
  <question type="multichoice">
    <name><text>Capital of England</text></name>
    <questiontext format="html"><text><![CDATA[<p>What is the capital of England?</p>]]></text></questiontext>
    <generalfeedback format="html"><text></text></generalfeedback>
    <defaultgrade>1.0000000</defaultgrade>
    <penalty>0.3333333</penalty>
    <hidden>0</hidden>
    <single>true</single>
    <shuffleanswers>false</shuffleanswers>
    <answernumbering>abc</answernumbering>
    <correctfeedback format="html"><text>Correct.</text></correctfeedback>
    <partiallycorrectfeedback format="html"><text>Partially correct.</text></partiallycorrectfeedback>
    <incorrectfeedback format="html"><text>Incorrect.</text></incorrectfeedback>
    <answer fraction="100" format="html">
      <text><![CDATA[<p>London</p>]]></text>
      <feedback format="html"><text>Correct.</text></feedback>
    </answer>
    <answer fraction="0" format="html">
      <text><![CDATA[<p>Paris</p>]]></text>
      <feedback format="html"><text>No.</text></feedback>
    </answer>
    <answer fraction="0" format="html">
      <text><![CDATA[<p>Berlin</p>]]></text>
      <feedback format="html"><text>No.</text></feedback>
    </answer>
    <answer fraction="0" format="html">
      <text><![CDATA[<p>Madrid</p>]]></text>
      <feedback format="html"><text>No.</text></feedback>
    </answer>
  </question>
</quiz>
XML;

    $tmp = make_request_directory() . '/model_question.xml';
    file_put_contents($tmp, $xml);

    $qformat = new qformat_xml();
    $qformat->setCategory($qcat);
    $qformat->setContexts([$coursecontext]);
    $qformat->setCourse($course);
    $qformat->setFilename($tmp);
    $qformat->setRealfilename('model_question.xml');
    $qformat->setMatchgrades('error');
    $qformat->setCatfromfile(false);
    $qformat->setContextfromfile(false);
    $qformat->setStoponerror(true);

    if (!$qformat->importpreprocess() || !$qformat->importprocess() || !$qformat->importpostprocess()) {
        cli_error('Question import failed.');
    }

    $question = $DB->get_record('question', ['name' => 'Capital of England'], '*', IGNORE_MULTIPLE);
    if (!$question) {
        cli_error('Question imported but could not be found by name.');
    }
    quiz_add_quiz_question($question->id, $quiz, 0, 1);
    quiz_update_sumgrades($quiz);
    say("quiz: added question id={$question->id} (multichoice, London correct)");
} else {
    say("quiz: already has {$slots} question slot(s)");
}

// ---------------------------------------------------------------------------
// 4. Assignment -- online text, so SUBMIT_DRAFT / UPDATE_SUBMISSION are real
//    edits to a text field rather than file uploads.
//
// submissiondrafts=0 is deliberate, and was CHANGED FROM 1 after measuring the
// SUT. The specification models one save that writes the status AND the
// content non-atomically -- that is the whole of APP_PARTIAL_SUBMISSION. With
// submissiondrafts=1 those are two separate, explicitly user-initiated actions
// (save, then "Submit assignment") with a write error already surfaced in
// between, so the modelled operation does not exist in the SUT: measured, a
// save leaves the status on 'Draft (not submitted)' and only the second action
// advances it. The status/content non-atomicity was therefore stated by the
// model but unreachable by any concrete path, and SUBMITTED_FG was never
// exercised by any test case.
//
// With submissiondrafts=0 a single save writes both, which is the operation
// the specification describes. Whether Moodle commits the status when the
// content write fails is then a real question with a real answer, rather than
// one the fixture had already decided.
// ---------------------------------------------------------------------------
$assign = $DB->get_record('assign', ['course' => $course->id, 'name' => 'Model_Assignment']);
if (!$assign) {
    $assign = $generator->create_module('assign', [
        'course'                             => $course->id,
        'name'                               => 'Model_Assignment',
        'assignsubmission_onlinetext_enabled' => 1,
        'assignsubmission_file_enabled'       => 0,
        'submissiondrafts'                    => 0,
        'grade'                               => 100,
    ]);
    say("assign: created id={$assign->id} cmid={$assign->cmid}");
} else {
    $cm = get_coursemodule_from_instance('assign', $assign->id, $course->id);
    $assign->cmid = $cm->id;
    say("assign: reusing id={$assign->id} cmid={$assign->cmid}");
}

// Enforce it on a REUSED assignment as well. The create_module() call above
// only runs when the assignment does not exist, so an assignment seeded before
// this setting changed would silently keep submissiondrafts=1 -- and every
// APP_PARTIAL_SUBMISSION verdict would then describe a workflow the model no
// longer models, with nothing in the output to say so.
if ((int)$assign->submissiondrafts !== 0) {
    $DB->set_field('assign', 'submissiondrafts', 0, ['id' => $assign->id]);
    $assign->submissiondrafts = 0;
    say('assign: submissiondrafts forced to 0 (one save writes status AND content)');
}

// An existing quiz from an earlier seed may predate the time limit, which
// INFRA_CRON_DEAD needs. Bring it up to date either way.
if ((int)$quiz->timelimit !== 60) {
    $DB->set_field('quiz', 'timelimit', 60, ['id' => $quiz->id]);
    $DB->set_field('quiz', 'overduehandling', 'autosubmit', ['id' => $quiz->id]);
    say('quiz: timelimit set to 60s, overduehandling=autosubmit (needed by INFRA_CRON_DEAD)');
}

// The two submission revisions the oracle distinguishes must be textually
// unmistakable — see concrete_domain.yml cv_assign_text / cv_assign_update.
// Nothing is seeded into the submission here: the test cases create it.

rebuild_course_cache($course->id, true);
purge_all_caches();

// ---------------------------------------------------------------------------
// 5. Report the ids the System Interface has to bind.
//
// concrete_domain.yml templates routes with {{...}} placeholders; these are the
// values those placeholders take for THIS database. They change whenever the
// volume is recreated, which is exactly how the previously recorded ids
// (course 2 / quiz cmid 2 / assign cmid 3) went stale.
// ---------------------------------------------------------------------------
say('');
say('================ BIND THESE IN concrete_domain.yml ================');
say("CRS_0        course id     = {$course->id}");
say("QUIZ_CMID    quiz cmid     = {$quiz->cmid}   (instance {$quiz->id})");
say("ASSIGN_CMID  assign cmid   = {$assign->cmid}   (instance {$assign->id})");
say('');
say("student      student1 / Student1!   (id {$student->id})");
say("teacher      teacher1 / Teacher1!   (id {$teacher->id})");
say("admin        admin    / Test1234!   (id {$admin->id})");
say('==================================================================');
