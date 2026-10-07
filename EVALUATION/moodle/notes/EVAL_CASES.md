Campaign: Moodle sweep of 2026-10-02 (03:03-06:20). It is the newest campaign and its test cases match the current model files by date and label evidence, but no hash proves it (§4). The DISRUPTOR `i` branch is still in the model, so these are not results from a model without quiescence everywhere. **No Moodle counterexample survives Rule 4.**

# Moodle: STORM evaluation cases

Sources: `EVALUATION/moodle/variants_<purpose>.log` (File 1, converted 2026-10-06 from `variant_results_<purpose>.log`), the per-case logs `EVALUATION/moodle/variant_logs/<purpose>/tc_<purpose>.<n>.log`, and the walked test cases `EVALUATION/moodle/Test_Cases/variants/<purpose>/tc_<purpose>.<n>.aut`. Totals come from `.venv/bin/python framework/scripts/eval_tables.py EVALUATION/moodle`, which reads only the `variants_*.log` files. Systems/moodle has no `RESULTS_campaign.md`, so this file has nothing to reconcile against.

## 1. Headline counterexamples

None survive. The walker returned 81 FAILs. In every one, the cause is the tester or the model: the oracle was read before the deadline it checks, the fault was injected before or after the step it targets, or the test case required an output before the action that would produce it. Each of these FAILs is listed in §6 and §7.

## 2. Other findings

- **Resilience: the write-failure controls hold.** `app1_write_fail` (2/2 PASS) and `db_attempt_step_loss` (2/2 PASS) inject a Postgres trigger fault. In each case Moodle showed "an error occurred while processing your responses (error writing to d…)" and the walk reached `:PASS:` (`variant_logs/app1_write_fail/tc_app1_write_fail.1.log:19,21,59`, `variant_logs/db_attempt_step_loss/tc_db_attempt_step_loss.1.log:18,20,58`).
- **A forecast miss: Moodle's non-atomic save is not visible.** The specification forecasts a partial submission: the status shows "submitted" while the content write failed (`model/specification_moodle.lnt:17-22`). In both cases that inject the fault right after the save (`app_partial_submission` .3 and .4), Moodle showed "error writing to database" and the status "no submissions have been made yet". Both PASS (`variant_logs/app_partial_submission/tc_app_partial_submission.3.log:15,17,19,49`).
- **Resilience: the client-side disruptions are reported.** `ue1_lose_conn.1` captured Moodle's banner "network connection lost. (autosave failed)" (`variant_logs/ue1_lose_conn/tc_ue1_lose_conn.1.log:14,16,45`). `ue2_session_expire.1` captured "your session has timed out. please log in again." (`variant_logs/ue2_session_expire/tc_ue2_session_expire.1.log:12,14,37`).
- **Nominal: the baselines PASS.** `happy` (1/1) and `happy_quiz` (2/2) both PASS. In `happy`, every status and text oracle matched (`variant_logs/happy/tc_happy.1.log:12,14,17,19,21`).
- **Tester and model defects that STORM exposed (81 FAILs, §7).** These fall into five groups:
  - (i) The specification allows `OPEN_GRADING` before any submission exists (`model/specification_moodle.lnt:509-511`). 31 cases.
  - (ii) The specification states the cron obligation without a deadline (`model/specification_moodle.lnt:575-591`). The fixture quiz has a 60 s time limit (`seed_moodle.php:285`), but each walk observed within 25-30 s. 41 cases.
  - (iii) `APP_PARTIAL_SUBMISSION` is pre-injected (`properties/disruption_mapping.yml:142`). In two cases this broke the save the test case expects to succeed. 2 cases.
  - (iv) `app_lazy_regrade` waits for the error before the fault is injected, or on a page loaded before the fault. 7 cases.
  - (v) `WAIT_FOR` is an input in `testor/moodle.io:5`. TESTOR therefore never places a `:DELTA:` at a `WAIT_FOR` state, yet the walker judges a `WAIT_FOR` timeout at a state without `:DELTA:` as a FAIL (`framework/concretization/algorithm.py:2429-2472`). 41 of the 81 FAILs come from this rule (§9).
- **INCONCLUSIVE, with a lesson.** All 14 INCONCLUSIVE results are a missing `OBSERVE` at a state that offers `:DELTA:`. That `:DELTA:` exists because of the `i` branch (`model/specification_moodle.lnt:615,634`). 860 of the 864 output states across the 109 test cases offer `:DELTA:` (a count over the .aut files). So the INCONCLUSIVE results show what `EVALUATION/template/CAPTURING_METRICS.md:51` predicts: a missing observable cannot FAIL. In `app_grade_stale_sub` .1-.5 the fault is also injected after the grade-save click (`tc_app_grade_stale_sub.1.aut:77,79`). Removing `i` would therefore not, by itself, turn these cases into a valid test of O3.

## 3. System and obligations

**Scope.** Moodle 4.5.12 (Build 20260608) (`sut/moodle/version.php:35`), a PHP LMS on Postgres, run with moodle-docker at `http://localhost:8080` and driven through Selenium (`run_variants.sh:35,52-53,110-121`). The model covers:
- one course with a quiz (60 s limit, autosubmit, `seed_moodle.php:285-286`) and an online-text assignment;
- a student who enrols, attempts the quiz, submits and revises;
- a teacher who grades;
- the course total.

It covers eight disruptions (`model/specification_moodle.lnt:7-15`). It leaves out multiple users, files, other activity types, and time itself: no deadline is modelled.

**Normal run** (`tc_happy.1.aut`, `tc_happy_quiz.1.aut`):
- S1 The student logs in (`WAIT_FOR !SEL_USER_MENU`) and sees the dashboard.
- S2 `VIEW_ASSIGN`: the student sees the assignment page and its submission status.
- S3 `SAVE_SUBMISSION … PLACEHOLDER`: the student adds online text and saves.
- S4 `SUBMISSION_STATUS !SUBMITTED_FG` ("submitted for grading"), then `SUBMISSION_TEXT !PLACEHOLDER`.
- S5 `UPDATE_SUBMISSION … FINAL`, then the status and the text `FINAL` again.
- S6 (quiz) `VIEW_QUIZ`, `START_ATTEMPT`, `SAVE_ATTEMPT`, `PROCESS_ATTEMPT`, then `GRADE_PERSISTED !GRADE_FULL`, read from the review page.
- S7 (teacher) `OPEN_GRADING`, `GRADING_SHOWS`, `GRADE_SUBMISSION`, `CONFIRMED_GRADE`. Then `VIEW_COURSE_TOTAL` and `COURSE_TOTAL`.

| ID | Plain words | Witnessing gate(s) | path:line |
|---|---|---|---|
| O1 | A failed write is reported (quiz finish, step loss) | `WRITE_ERROR_SHOWN` after APP1_WRITE_FAIL / DB_ATTEMPT_STEP_LOSS | model/specification_moodle.lnt:366-376 |
| O2 | A partial submission must not show "submitted" | `WRITE_ERROR_SHOWN; SUBMISSION_STATUS(NO_SUBMISSION)` | model/specification_moodle.lnt:17-22, 438-447 |
| O3 | A grade is confirmed only against the version the teacher saw, or a stale warning is shown | `CONFIRMED_GRADE` / `STALE_WARNING_SHOWN` | model/specification_moodle.lnt:34-38, 509-518 |
| O4 | A stale course total is not shown silently | `COURSE_TOTAL(GRADE_FULL)` or `WRITE_ERROR_SHOWN` | model/specification_moodle.lnt:40-43, 525-533 |
| O5 | An attempt past its deadline reaches a terminal state | `ATTEMPT_STATE(SUBMITTED / ABANDONED)` | model/specification_moodle.lnt:45-47, 575-591 |
| O6 | Lost connectivity is reported | `CONN_ERROR_SHOWN` | model/specification_moodle.lnt:178-185 |
| O7 | An expired session is reported | `SESSION_ERROR_SHOWN` | model/specification_moodle.lnt:178-185 |

## 4. Campaign identity

| Field | Value |
|---|---|
| Name and date | Moodle variant sweep, 2026-10-02 03:03-06:20. Per-case logs are dated 03:03-06:20 (`variant_logs/happy/tc_happy.1.log`, `variant_logs/infra_cron_dead/tc_infra_cron_dead.39.log`). The driver log is `sweep_20261002.log`. |
| Matches current model? | **Probably, not hash-verified.** Evidence: (1) The test cases were generated 2026-10-01 15:18-15:34 (`gen_summary.txt` and .aut mtimes). (2) The spec (2026-09-25), purposes (09-25) and `moodle.io` (09-16) predate generation and equal HEAD in git. (3) The SI and types were modified 2026-10-01 19:15, after generation. However, the .aut files already contain labels that exist only in that uncommitted SI diff (`WAIT_FOR !SEL_FINISH_ATTEMPT_ANCHOR` ×14, `WAIT_FOR !SEL_USER_MENU` ×257). (4) Every walk logged `LNT SI invariants OK` against the current SI (e.g. `tc_infra_cron_dead.1.log:4`). (5) No model, property, purpose or testor file is newer than the first walk. The generator records no md5 (`testor/generate_tc_all.sh` has none). |
| Framework | No revision was recorded (`sweep_20261002.log` has no rev line), and `framework/` is uncommitted. `algorithm.py`, `executors.py`, `si_lnt_parser.py` and `run.py` have mtimes of 2026-10-01 23:27, before the first walk. The only framework files changed since then are `export_public.sh` and `ctg_cover.py`, and the walk does not use either. The log wording matches the current `_judge_missing_observable` (`algorithm.py:2454-2466`), so the sweep ran the current code. |
| Model size | NOT RECORDED. There is no `model_size.txt`, and the local `model/compose_moodle.bcg` dates from 2026-09-16. |
| Purposes | 11 |
| Cases | 109 (`gen_summary.txt:1-11`, all walked) |
| P/F/I/U | 12 / 81 / 14 / 2 |
| Generation time | 983 s in total, summed from `gen_summary.txt:1-11`. There is no `gen_times.tsv`, so `eval_tables.py` prints `--`. |
| Walk time | 3467 s, the sum of TIME_S over the last row per case (`eval_tables.py`). Earlier NONE attempts are not included. |

## 5. Results by purpose

| Purpose | Layer | Cases | P | F | I | U | One-line cause |
|---|---|---|---|---|---|---|---|
| happy | NOMINAL | 1 | 1 | 0 | 0 | 0 | All status and text oracles matched |
| happy_quiz | NOMINAL | 2 | 2 | 0 | 0 | 0 | Grade read as GRADE_FULL |
| app1_write_fail | APP | 2 | 2 | 0 | 0 | 0 | Write error shown (O1 held) |
| app_grade_stale_sub | APP | 36 | 0 | 31 | 5 | 0 | F: grading opened before any submission. I: stale warning absent at a `:DELTA:` state, fault injected after the save click |
| app_lazy_regrade | APP | 7 | 0 | 7 | 0 | 0 | Error waited for before the fault, or on a page loaded before the fault |
| app_partial_submission | APP | 4 | 2 | 2 | 0 | 0 | P: error shown and status NO_SUBMISSION. F: pre-injection broke the save the case expects to succeed |
| db_attempt_step_loss | DB | 2 | 2 | 0 | 0 | 0 | Write error shown (O1 held) |
| infra_cron_dead | INFRA | 42 | 0 | 41 | 0 | 1 | Attempt read as "in progress" within 30 s of start, deadline 60 s; 3 cases had no attempt at all |
| ue1_lose_conn | USER | 4 | 1 | 0 | 3 | 0 | I: fault injected before any request that could surface it; `:DELTA:` offered |
| ue1_lose_conn_midattempt | USER | 5 | 1 | 0 | 3 | 1 | Same as above; .2 is a Selenium read timeout |
| ue2_session_expire | USER | 4 | 1 | 0 | 3 | 0 | Session error not observed; `:DELTA:` offered |
| **Total** | | **109** | **12** | **81** | **14** | **2** | |

## 6. Case cards

Cases that share the same walked prefix, the same failing state type and the same log cause share one card. The card lists their variant numbers. None of these cards is a counterexample (Rule 4).

#### moodle-1  Grading form opened before any submission exists (31 FAILs)
    Purpose / test case : tp_app_grade_stale_sub / tc_app_grade_stale_sub.{6..36}.aut
    Disruption          : none walked (no injection line in any of the 31 logs)
    Where it struck     : S7, OPEN_GRADING walked with no SAVE_SUBMISSION before it
                          (checkpoints "OPEN_GRADING" or "VIEW_ASSIGN OPEN_GRADING")
    Obligation          : none of O1-O7; the spec offers GRADING_SHOWS(PLACEHOLDER) after OPEN_GRADING
                          even with no submission (model/specification_moodle.lnt:509-511)
    What the app did    : rendered no online-text div, because there is no submission
                          (variant_logs/app_grade_stale_sub/tc_app_grade_stale_sub.6.log:16)
    Verdict and why     : FAIL by algorithm.py:2463-2472. State 19 offers only WAIT_FOR (tc_…6.aut:21);
                          WAIT_FOR is an input (testor/moodle.io:5), so no :DELTA: can exist there
    Counterexample      : VIEW_ASSIGN; NAVIGATE !RT_LOGOUT; … ; OPEN_GRADING !CRS_0 !ASN_0;
                          NAVIGATE !RT_ASSIGN_GRADER; WAIT_FOR !SEL_GRADING_SUBMISSION_TEXT (timeout)
    Class               : none (model defect)
    Silent failure?     : no
    Root cause in app   : not an app defect. sut/moodle/mod/assign/submission/onlinetext/locallib.php:374
                          renders the text only when a submission row exists
    Data store evidence : NOT RECORDED
    Separate from nominal? : n/a
    Forecast            : yes, documented as an accepted coverage gap (model/specification_moodle.lnt:~490-508)
    Reproduced          : 31 of 31 cases, 1 walk each (.13 has 2 NONE rows before its FAIL)
    Doubts              : none about the cause

#### moodle-2  Stale-grade fault injected after the grade was saved (5 INCONCLUSIVE)
    Purpose / test case : tp_app_grade_stale_sub / tc_app_grade_stale_sub.{1..5}.aut
    Disruption          : APP_GRADE_STALE_SUB (APP), gate timing, injected and confirmed (tc_…1.log:21)
    Where it struck     : S7, after CLICK !SEL_GRADE_SAVE_BTN (tc_…1.aut:77) → APP_GRADE_STALE_SUB (:79)
    Obligation          : O3 (model/specification_moodle.lnt:509-518)
    What the app did    : no "has been modified" warning appeared (tc_…1.log:22)
    Verdict and why     : INCONCLUSIVE. State 67 offers :DELTA: (tc_…1.aut:82), "PERMITS quiescence" (tc_…1.log:23)
    Counterexample      : … GRADING_SHOWS !PLACEHOLDER; TYPE_INTO !SEL_GRADE_INPUT; CLICK !SEL_GRADE_SAVE_BTN;
                          APP_GRADE_STALE_SUB; OBSERVE !SEL_STALE_WARNING (absent)
    Class               : none
    Silent failure?     : not established
    Root cause in app   : NOT ESTABLISHED
    Data store evidence : NOT RECORDED
    Separate from nominal? : yes
    Forecast            : yes (O3)
    Reproduced          : 5 cases; .3 and .4 walked twice (NONE, then INCONC)
    Doubts              : The fault lands after the save it should race, so even without `i` this case
                          does not test O3

#### moodle-3  Course-total error awaited before the fault (5 FAILs)
    Purpose / test case : tp_app_lazy_regrade / tc_app_lazy_regrade.{2,3,4,5,7}.aut
    Disruption          : APP_LAZY_REGRADE, never reached (no injection line)
    Where it struck     : after VIEW_COURSE_TOTAL; the case waits for SEL_WRITE_ERROR before the fault gate
                          (tc_app_lazy_regrade.4.aut:9-12; fault comes later)
    Obligation          : O4
    What the app did    : showed the course total with no error (correct without a fault)
    Verdict and why     : FAIL, "State 8 waits for WAIT_FOR !SEL_WRITE_ERROR … does NOT permit quiescence"
                          (variant_logs/app_lazy_regrade/tc_app_lazy_regrade.4.log:14)
    Counterexample      : NAVIGATE !RT_COURSE_TOTAL; WAIT_FOR !SEL_COURSE_TOTAL_CELL; VIEW_COURSE_TOTAL;
                          WAIT_FOR !SEL_WRITE_ERROR (timeout)
    Class               : none (test case orders the SI's error wait, system_interface_moodle.lnt:938, before the fault)
    Silent failure?     : no
    Root cause in app   : not an app defect
    Data store evidence : NOT RECORDED
    Separate from nominal? : n/a
    Forecast            : no
    Reproduced          : 5 cases, 1 walk each
    Doubts              : none

#### moodle-4  Course-total fault injected after the page was loaded (2 FAILs)
    Purpose / test case : tp_app_lazy_regrade / tc_app_lazy_regrade.{1,6}.aut
    Disruption          : APP_LAZY_REGRADE (APP), SQL `needsupdate = 1` (properties/disruption_mapping.yml:204-206)
                          — note: the same SQL set is used for verification (:210-212),
                          gate timing, injected and confirmed (tc_…1.log:19)
    Where it struck     : after VIEW_COURSE_TOTAL had already loaded the page (tc_…1.aut:41,43); there is no reload
    Obligation          : O4
    What the app did    : the page already on screen showed no error (tc_…1.log:20-23)
    Verdict and why     : FAIL by algorithm.py:2463-2472, at a WAIT_FOR state (input, moodle.io:5)
    Counterexample      : VIEW_COURSE_TOTAL; APP_LAZY_REGRADE; WAIT_FOR !SEL_WRITE_ERROR (timeout)
    Class               : none (late injection; TIMING)
    Silent failure?     : not established; the total was never re-read after the fault
    Root cause in app   : NOT ESTABLISHED
    Data store evidence : injection verified by SQL (disruption_mapping.yml:210-212); the total was not probed
    Separate from nominal? : yes
    Forecast            : the mapping says Moodle "may recompute on report VIEW" (disruption_mapping.yml:201-203)
    Reproduced          : 2 cases, 1 walk each
    Doubts              : The page cannot change without a request, so this measures nothing about Moodle

#### moodle-5  Attempt read before its deadline, no fault (16 FAILs)
    Purpose / test case : tp_infra_cron_dead / tc_infra_cron_dead.{1..16}.aut
    Disruption          : none (the fault gate comes after the failing state, tc_…1.aut:26)
    Where it struck     : S6, right after START_ATTEMPT; the student leaves and reads the attempt state
    Obligation          : O5. The spec offers only SUBMITTED or ABANDONED, with no deadline guard
                          (model/specification_moodle.lnt:575-587)
    What the app did    : "in progress" (variant_logs/infra_cron_dead/tc_infra_cron_dead.1.log:15)
    Verdict and why     : FAIL, value mismatch (a). State 19 offers SUBMITTED, ABANDONED and :DELTA: (tc_…1.aut:23-25)
    Counterexample      : VIEW_QUIZ; START_ATTEMPT !ATT_0; NAVIGATE !RT_QUIZ_VIEW; WAIT_FOR !SEL_ATTEMPT_STATE_CELL;
                          OBSERVE !SEL_ATTEMPT_STATE_CELL → 'in progress'
    Class               : none (oracle timing; TIMING)
    Silent failure?     : no
    Root cause in app   : not an app defect. The quiz time limit is 60 s (seed_moodle.php:285), and each whole walk
                          took 25-27 s (variants_infra_cron_dead.log rows 1-16)
    Data store evidence : NOT RECORDED
    Separate from nominal? : this is the no-fault path
    Forecast            : no
    Reproduced          : 16 cases, 1 walk each
    Doubts              : none

#### moodle-6  Cron disabled, attempt read before its deadline (22 FAILs)
    Purpose / test case : tp_infra_cron_dead / tc_infra_cron_dead.{17..31,33,36,37,38,40,41,42}.aut
    Disruption          : INFRA_CRON_DEAD (INFRA), the scheduled-task row disabled (disruption_mapping.yml:264-276),
                          gate timing, injected and confirmed (tc_…17.log:14)
    Where it struck     : S6, after START_ATTEMPT (tc_…17.aut:19)
    Obligation          : O5. After the fault the spec offers only ABANDONED (model/specification_moodle.lnt:589-590)
    What the app did    : "in progress" (tc_…17.log:15)
    Verdict and why     : FAIL, value mismatch (a), at a state offering :DELTA: (tc_…17.aut:22-23)
    Counterexample      : START_ATTEMPT !ATT_0; NAVIGATE !RT_QUIZ_VIEW; WAIT_FOR !SEL_ATTEMPT_STATE_CELL;
                          INFRA_CRON_DEAD; OBSERVE → 'in progress'; expected ATTEMPT_STATE !ABANDONED
    Class               : none (oracle before the deadline; TIMING)
    Silent failure?     : not established
    Root cause in app   : NOT ESTABLISHED. update_overdue_attempts (sut/moodle/mod/quiz/classes/task/update_overdue_attempts.php:45)
                          could not have acted before the 60 s limit, with or without the fault
    Data store evidence : NOT RECORDED
    Separate from nominal? : no. moodle-5 shows the same symptom with no fault (Rule 5)
    Forecast            : yes (O5); untestable at this timing
    Reproduced          : 22 cases, 1 walk each
    Doubts              : A run that waits beyond 60 s is needed before anything can be claimed

#### moodle-7  Attempt state read with no attempt (3 FAILs)
    Purpose / test case : tp_infra_cron_dead / tc_infra_cron_dead.{32,34,35}.aut
    Disruption          : none (.32, .35); INFRA_CRON_DEAD confirmed in .34
    Where it struck     : after NAVIGATE !RT_QUIZ_VIEW, with no START_ATTEMPT (tc_…32.aut:7-8)
    Obligation          : O5 (no attempt exists, so the obligation does not apply)
    What the app did    : no attempt table
    Verdict and why     : FAIL, "State 6 waits for WAIT_FOR !SEL_ATTEMPT_STATE_CELL" (tc_…32.log:13); input state
    Counterexample      : login; NAVIGATE !RT_QUIZ_VIEW; WAIT_FOR !SEL_ATTEMPT_STATE_CELL (timeout)
    Class               : none (model admits ATTEMPT_STATE with no attempt, model/specification_moodle.lnt:164)
    Silent failure?     : no
    Root cause in app   : not an app defect
    Data store evidence : NOT RECORDED
    Separate from nominal? : n/a
    Forecast            : no
    Reproduced          : 3 cases
    Doubts              : none

#### moodle-8  Partial-submission fault pre-injected before the first save (2 FAILs)
    Purpose / test case : tp_app_partial_submission / tc_app_partial_submission.{1,2}.aut
    Disruption          : APP_PARTIAL_SUBMISSION, timing pre (properties/disruption_mapping.yml:142),
                          "pre-injected before the walk" (tc_…1.log:11)
    Where it struck     : S3. The case expects the first save to succeed (tc_…1.aut:22) and places the fault later (:31)
    Obligation          : O2
    What the app did    : "no submissions have been made yet" (tc_…1.log:14). This is Moodle's correct
                          response to a failed save
    Verdict and why     : FAIL, value mismatch (a): AUT expects SUBMITTED_FG
    Counterexample      : SAVE_SUBMISSION !PLACEHOLDER; OBSERVE !SEL_SUBMISSION_STATUS → NO_SUBMISSION; expected SUBMITTED_FG
    Class               : none (early injection; TIMING)
    Silent failure?     : no
    Root cause in app   : not an app defect
    Data store evidence : NOT RECORDED
    Separate from nominal? : n/a
    Forecast            : no
    Reproduced          : 2 cases
    Doubts              : none

#### moodle-9  Connection or session fault with no request to surface it (9 INCONCLUSIVE)
    Purpose / test case : ue1_lose_conn.{2,3,4}, ue1_lose_conn_midattempt.{3,4,5}, ue2_session_expire.{2,3,4}
    Disruption          : UE1_LOSE_CONN or UE2_SESSION_EXPIRE, injected and confirmed (e.g. tc_ue1_lose_conn.2.log:12),
                          except midattempt.3, which observed before the fault
    Where it struck     : before login (tc_ue1_lose_conn.4.aut:2), after VIEW_QUIZ, or after a navigate
    Obligation          : O6 / O7
    What the app did    : no banner (tc_ue1_lose_conn.2.log:14; tc_ue2_session_expire.2.log:15)
    Verdict and why     : INCONCLUSIVE: the state offers :DELTA:
    Counterexample      : VIEW_QUIZ; UE1_LOSE_CONN; OBSERVE !SEL_CONNECTION_ERROR (absent)
    Class               : none
    Silent failure?     : not established. No browser action follows the fault
    Root cause in app   : NOT ESTABLISHED
    Data store evidence : NOT RECORDED
    Separate from nominal? : yes
    Forecast            : yes; held in .1 of each purpose
    Reproduced          : 9 cases, 1 walk each
    Doubts              : These are expected under the `i` branch

#### moodle-10  PASS, write failure surfaced (app1_write_fail.1)
    Purpose / test case : tp_app1_write_fail / tc_app1_write_fail.1.aut
    Disruption          : APP1_WRITE_FAIL (APP), Postgres trigger, timing pre (disruption_mapping.yml:95)
    Where it struck     : S6, PROCESS_ATTEMPT
    Obligation          : O1
    What the app did    : "an error occurred while processing your responses (error writing to d…" (tc_…1.log:59)
    Verdict and why     : PASS (tc_…1.log:21,30)
    Class / Silent?     : none / no
    Reproduced          : .2 PASS as well

#### moodle-11  PASS, partial save reported, status not advanced (app_partial_submission.3)
    Purpose / test case : tp_app_partial_submission / tc_app_partial_submission.3.aut
    Disruption          : APP_PARTIAL_SUBMISSION (APP), timing pre, injected and confirmed (tc_…3.log:15)
    Obligation          : O2
    What the app did    : showed "error writing to database"; status "no submissions have been made yet" (tc_…3.log:17,49,53)
    Verdict and why     : PASS (tc_…3.log:19,28)
    Forecast            : the spec forecasts a possible "submitted" with no content (model/specification_moodle.lnt:17-22). Did not occur
    Reproduced          : .4 PASS as well

## 7. Tester-side and UNEXECUTABLE runs

| Case | What went wrong | Evidence | Fixed? |
|---|---|---|---|
| app_grade_stale_sub .6-.36 (31 F) | The spec allows OPEN_GRADING before any submission; the WAIT_FOR timeout is judged FAIL | specification_moodle.lnt:509-511; tc_…6.log:16; moodle.io:5 | No |
| app_lazy_regrade .2,.3,.4,.5,.7 (5 F) | The test case waits for the error before the fault | tc_app_lazy_regrade.4.aut:9-12; .4.log:14 | No |
| app_lazy_regrade .1,.6 (2 F) | Fault injected after the page loaded, no reload | tc_…1.aut:41,43; tc_…1.log:19,23 | No |
| infra_cron_dead .1-.16 (16 F) | Oracle read before the 60 s deadline; no deadline in the spec | tc_…1.log:15; specification_moodle.lnt:575-587; seed_moodle.php:285 | No |
| infra_cron_dead 22 cases (F) | Same as above, with cron disabled | tc_…17.log:14-15 | No |
| infra_cron_dead .32,.34,.35 (3 F) | Attempt state read with no attempt | tc_…32.log:13; tc_…32.aut:7-8 | No |
| app_partial_submission .1,.2 (2 F) | Pre-injection broke the save the case expects to succeed | tc_…1.log:11,14; disruption_mapping.yml:142 | No |
| infra_cron_dead .39 (U) | INFRA_CRON_DEAD fired between typing the password and the login click; the user menu never appeared; run.py exit 2. NONE in all 4 attempts | tc_infra_cron_dead.39.aut:5-7; tc_…39.log:11,13,23; variant_results_infra_cron_dead.log | No |
| ue1_lose_conn_midattempt .2 (U) | run.py crashed: Selenium `ReadTimeoutError` (120 s) in `driver.get` (framework/concretization/executors.py:364) after CONN_ERROR_SHOWN; exit 1, no verdict line. NONE in all 4 attempts (145-156 s) | tc_…2.log:14-15,83; variant_results_ue1_lose_conn_midattempt.log | No |

## 8. Aggregates

- Counterexamples by class: 0 in every class (SILENT, MISSING-REPORT, WRONG-REPORT, STALE, INTEGRITY, NOMINAL).
- By layer: 0 in every layer.
- Silent failures: exactly 0.
- Walker verdicts: 12 PASS, 81 FAIL, 14 INCONCLUSIVE, plus 2 UNEXECUTABLE, which are not a verdict. This agrees with §4, §5 and `eval_tables.py`.
- FAIL causes in Task A terms:
  - (a) value mismatch at a checkpoint: 40 (16 + 22 infra_cron_dead, 2 app_partial_submission).
  - (b) missing output at a state with no `:DELTA:`: 41 (31 app_grade_stale_sub, 7 app_lazy_regrade, 3 infra_cron_dead). All 41 are WAIT_FOR states.
  - (c) other: 0.

## 9. Do not claim

- **Any Moodle counterexample from this campaign.** All 81 FAILs are tester-side or model-side (§6, §7).
- **That the FAILs contradict the `i` branch, or that they confirm it.** The `i` branch puts `:DELTA:` on 860 of 864 output states, so a missing `OBSERVE` can only be INCONCLUSIVE, as `CAPTURING_METRICS.md:51` says. All 41 missing-output FAILs come from a second path. The walker's `_judge_missing_observable` (`algorithm.py:2429-2472`) treats a `WAIT_FOR` timeout as a missing output. But `WAIT_FOR` is declared as an input (`testor/moodle.io:5`), so TESTOR never places `:DELTA:` at a `WAIT_FOR` state. These FAILs do follow the walker rule literally. However, the missing `:DELTA:` there comes from how `WAIT_FOR` is classified, not from the specification requiring an output. "No missing observable can FAIL" therefore does not hold for this suite, and these FAILs are not ioco evidence.
- **The earlier `app_grade_stale_sub` FAIL** (Aug 31; `PRESENTATION_moodle.md`). In this campaign, the five cases that reach the stale-warning oracle are INCONCLUSIVE, and their fault lands after the save click.
- **O5 (cron) in either direction.** No walk waited beyond the 60 s deadline.
- **O4 (lazy regrade) in either direction.** The total was never re-read after the fault.
- **That the results come from a hash-verified model.** No md5, no revision and no `model_size.txt` were recorded (§4).
- **Generation and walk timings as table values.** `gen_times.tsv` is absent. The 983 s figure comes from `gen_summary.txt`, and walk time excludes the retried NONE attempts.
