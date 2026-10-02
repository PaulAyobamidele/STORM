# Mastodon running example for Sec. III (STORM, ICSE 2027)

Scenario: `APP_WRITE_FAIL`. Mastodon's antispam drops a post without storing it, and the
specification owes an error report at that point. Test case
`generated/tc/variants/app_write_fail/tc_app_write_fail.1.aut`, walk log
`generated/variant_logs/app_write_fail/v1.log`, campaign `runs/campaign_2026-09-30b`.
All paths below are relative to `systems/mastodon/` unless they start with `framework/`.

## 1. LaTeX (ready to paste)

```latex
\paragraph{Walkthrough of Fig.~\ref{fig:pipeline} via the Mastodon running example.}
Figure~\ref{fig:pipeline} is best read as one end-to-end path through one
concrete scenario: a Mastodon user posts a status whose text matches an
antispam rule, and Mastodon drops the post without storing it. The
specification owes an error report at that point, and the test checks whether
Mastodon gives one.

\hl{start}
\begin{enumerate}
\item \textbf{Behavioural model template (LNT).}
% src: model/specification_mastodon.lnt:14-15, 42, 115, 157-160, 256, 319-320, 420-446, 453
We model Mastodon as seen by one local user, in four LNT processes under
\texttt{SPEC}: \texttt{USER}, \texttt{APP}, \texttt{DATABASE} and
\texttt{DISRUPTOR}. Obligation O2 states that a failed write is reported and
that nothing moves. In \texttt{APP}, a valid \texttt{ADD} either reaches the
store or meets a fault. The arm for \texttt{APP\_WRITE\_FAIL} owes
\texttt{WRITE\_ERROR\_SHOWN} and then \texttt{CONFIRM (ROLLED\_BACK, \ldots)}.
In \texttt{DATABASE}, the same fault leaves the post count, home timeline and
profile unmoved. This is the template's write-path shape: the fault is a
sibling of the commit. \texttt{DISRUPTOR} offers every fault and has no
internal step.

\item \textbf{System Interface model template (LNT).}
% src: model/system_interface_mastodon.lnt:75-84, 93-99, 101-103, 124-129; properties/concrete_domain.yml:83
The System Interface maps each abstract gate to Selenium steps. Its prelude
logs in as the fixture user: \texttt{navigate (rt\_login)}, two
\texttt{type\_into} steps and \texttt{click (sel\_login\_submit)}. The posting
branch picks the next unwritten post from its \texttt{has\_a}, \texttt{has\_b}
and \texttt{has\_c} state; it tracks a \texttt{screen} variable but does not
use it as a guard. It types the post text and offers \texttt{ADD}. In the
\texttt{APP\_WRITE\_FAIL} arm the fault gate comes before the Post click,
followed by \texttt{wait\_for (el\_write\_error)}, \texttt{observe
(el\_write\_error)} and \texttt{WRITE\_ERROR\_SHOWN}.

\item \textbf{Composition and alphabet check.}
% src: model/compose_mastodon.lnt:1-3, 10-61; model_size.txt:4-5, 10; framework/scripts/check_alphabet.py:2-11
\texttt{COMPOSED} is \texttt{SPEC}~$\parallel$~\texttt{SI}, synchronised on the
whole abstract alphabet: 23 gates, the 13 fault gates included. Nothing is
hidden, and the five concrete primitives stay visible so that test cases carry
them. The composed model has 1,175,066 states and 1,514,418 transitions, with
no hidden label. Composition does not check that the artefacts agree, and CADP
checks none of it. \texttt{check\_alphabet.py} does: it requires each fault
name to be identical in the specification, the SI, the composition, every
purpose, the \texttt{.io} file and the disruption mapping, and every SI
element to have a concrete interpretation.

\item \textbf{Test purpose.}
% src: test_purposes/tp_app_write_fail.lnt:3-10, 42-49; properties/disruption_mapping.yml:24; runs/campaign_2026-09-30b/SWEEP.txt:1, 20
The purpose \texttt{tp\_app\_write\_fail} follows the happy path, which posts
A, B and C, and lets the fault strike after the \texttt{ADD} of any of the
three. Its accept branch is \texttt{APP\_WRITE\_FAIL}, then
\texttt{WRITE\_ERROR\_SHOWN}, then \texttt{CONFIRM (ROLLED\_BACK, \ldots)},
ending in \texttt{TP\_ACCEPT}. It refuses a run in which the happy path
completes without the fault, and every fault or input it does not use. The
disruption mapping recorded the expected outcome, \textsc{Fail} on O2, in the
snapshot frozen before the sweep started.

\item \textbf{ioco test generation (TESTOR).}
% src: testor/generate_tc_all.sh:117-119; generated/tc/generate_tc_all.log:633-634; testor/mastodon.io:1-22; testor/README_io.md:3-6
For each purpose, TESTOR builds the complete test graph (CTG) of the composed
model and the purpose. For \texttt{app\_write\_fail}, the CTG has 70 states
and 98 transitions. The \texttt{.io} file lists the tester's inputs: the
concrete stimuli, the abstract requests such as \texttt{ADD}, and every fault
gate, \texttt{APP\_WRITE\_FAIL} included. Every other label, \texttt{WAIT\_FOR}
among them, is an output, and ioco verdicts are earned on outputs. Because the
fault is an input, TESTOR places it where the purpose asks: it is a choice the
tester makes, not an event the tester waits for.

\item \textbf{Test-case extraction (\texttt{extract\_all}).}
% src: testor/generate_tc_all.sh:141; generated/tc/generate_tc_all.log:636-644; generated/tc/variants/app_write_fail/tc_app_write_fail.1.aut:1-35, .2.aut:9-11; RESULTS_campaign.md:74, 106-108; gen_times.tsv:7
\texttt{extract\_all} splits the CTG into controllable test cases, one for
each way of resolving its controllability choices. Here it found four choices
and extracted two cases. Case~1 commits post A, reads it back, and lets the
fault strike post B; case~2 strikes post A. A strike at post C was not
extracted. The cases are concrete: because the SI is composed in, case~1
holds \texttt{NAVIGATE}, \texttt{TYPE\_INTO}, \texttt{CLICK},
\texttt{WAIT\_FOR} and \texttt{OBSERVE} steps between its abstract gates, 34
transitions in all. Generating this purpose took 28~s.

\item \textbf{Walker and oracle.}
% src: framework/concretization/algorithm.py:2779-2790, 2846-2849, 2077; generated/variant_logs/app_write_fail/v1.log:10-13; tc_app_write_fail.1.aut:19; properties/type_description.yml:57-59
The walker reads the test case as an automaton and executes its concrete
steps; nothing is translated at run time. Abstract gates between the steps are
checkpoints. At \texttt{ADD} the walker only advances. At
\texttt{CONFIRM !COMMITTED !N1 !IN\_HOME !ON\_PROFILE !POST\_A}, the type
oracle classifies the observed post count, profile list and home column and
compares each with the label; in case~1 all three agree. A mismatch would be a
\textsc{Fail}. The post count is declared in \texttt{type\_description.yml} as
a band read from \texttt{el\_post\_count}.

\item \textbf{Executor.}
% src: generated/variant_logs/app_write_fail/v1.log:5-9; properties/concrete_domain.yml:13, 27, 83; run_suite.sh:77; generated/variant_logs/app_write_fail/v1.seed.log:3-17, v2.seed.log:4-18
The executor is Selenium's \texttt{HTMLExecutor}, pointed at
\texttt{https://mastodon.localhost}. \texttt{concrete\_domain.yml} resolves
each symbolic name: \texttt{SEL\_POST\_BUTTON} is the submit button inside
\texttt{compose-form\_\_submit}, and \texttt{EL\_WRITE\_ERROR} is a
notification bar that contains neither ``Post published.'' nor ``Post
saved.''. The local TLS certificate is accepted by configuration, and the
password is read from the environment and never logged. Before each case,
\texttt{seed.sh} resets the fixture user and checks fourteen conditions. All
passed before both cases, including that the antispam entry is absent.

\item \textbf{Disruption injector.}
% src: tc_app_write_fail.1.aut:21-23; properties/disruption_mapping.yml:6-7, 63-72; generated/variant_logs/app_write_fail/v1.log:14-15, 20; framework/concretization/algorithm.py:2706-2719; sut/mastodon/app/services/post_status_service.rb:102-108
In case~1 the fault gate sits after \texttt{ADD !POST\_B} and
before the Post click. There the disruption executor runs the mapping's shell
command, adding \texttt{ioco note} to the Redis set
\texttt{antispam:all\_time\_spammy\_texts}; every fixture post contains that
text and mentions an account that does not follow the poster. A probe
confirms the entry, and the walker logs the fault as injected and confirmed.
The entry is therefore in place when Mastodon checks the post, before saving
it. Afterwards the entry and the system report are removed, and a
second probe confirms it. An unconfirmed injection would make the run
UNEXECUTABLE.

\item \textbf{Verdict.}
% src: tc_app_write_fail.1.aut:24; generated/variant_logs/app_write_fail/v1.log:19, 28; framework/concretization/algorithm.py:2429-2472; sut/mastodon/app/lib/antispam.rb:39-45; sut/mastodon/app/services/post_status_service.rb:76-77, 103, 108; notes/observed_behaviour.md:522-536; variants_app_write_fail.log:3-4
After the click, case~1 is at state 22, whose only transition is
\texttt{WAIT\_FOR !EL\_WRITE\_ERROR}: the state offers no quiescence
($\delta$). No error appeared within the timeout. Because silence is not
permitted at this state, the walker returns \textsc{Fail}; at a state that
offered $\delta$, the same silence would be \textsc{Inconclusive}. The
\textsc{Fail} is therefore a counterexample, not a timeout. The source shows
why: antispam raises \texttt{SilentlyDrop} before the post is saved, and the
service returns the unsaved post as its result. In a live probe before the
sweep, Mastodon showed ``Post published.'' and stored no row. Both extracted
cases \textsc{Fail}.
\end{enumerate}
\hl{end}
```

Word counts (item text, without the `\item` heading and the `% src` line): 1: 94 · 2: 82 ·
3: 94 · 4: 80 · 5: 92 · 6: 84 · 7: 83 · 8: 77 · 9: 99 · 10: 100.

## 2. Evidence table

| Item | Claim | Source |
|---|---|---|
| Scenario | antispam drops the post without storing it | `sut/mastodon/app/lib/antispam.rb:29, 44`; `sut/mastodon/app/services/post_status_service.rb:103, 108` |
| 1 | USER, APP, DATABASE, DISRUPTOR, SPEC | `model/specification_mastodon.lnt:42, 115, 256, 423, 453` |
| 1 | O2: "a failed write (post or delete) is reported, and nothing moves — WRITE_ERROR_SHOWN" | `model/specification_mastodon.lnt:14-15` |
| 1 | APP arm: `APP_WRITE_FAIL; WRITE_ERROR_SHOWN; CONFIRM (ROLLED_BACK, …)` beside the commit `CONFIRM` | `model/specification_mastodon.lnt:150-151, 157-160` |
| 1 | DATABASE: `APP_WRITE_FAIL; CONFIRM (ROLLED_BACK, band, home_of (posted, id), prof_of (posted, id), id)` | `model/specification_mastodon.lnt:315, 319-320` |
| 1 | write-path shape = fault as sibling of the commit | `STORM_approach_review.md:129` (template shapes); spec lines above |
| 1 | DISRUPTOR offers every fault, "NO `i` branch" | `model/specification_mastodon.lnt:420-446` |
| 2 | prelude `navigate (rt_login)` … `click (sel_login_submit)`; `screen := SCR_TIMELINE` | `model/system_interface_mastodon.lnt:78-84` |
| 2 | arm chosen by `has_a` / `has_b` / `has_c` | `model/system_interface_mastodon.lnt:93-97` |
| 2 | `screen` assigned (75, 84, 163, …), never tested; no `if screen ==` in the file | `grep -n "if screen ==" model/system_interface_mastodon.lnt` → only the comment at line 10 |
| 2 | `type_into (sel_compose_text, L_text (id)); ADD (id, PUBLIC, VALID)` | `model/system_interface_mastodon.lnt:98-99` |
| 2 | fault arm: `APP_WRITE_FAIL; click (sel_post_button); wait_for (el_write_error); observe (el_write_error); WRITE_ERROR_SHOWN` | `model/system_interface_mastodon.lnt:124-129` |
| 3 | sync set = 23 abstract gates incl. 13 faults; no `hide`; primitives visible | `model/compose_mastodon.lnt:1-3, 40-59` |
| 3 | 1,175,066 states / 1,514,418 transitions; "no transition with a hidden label" | `model_size.txt:4-5, 10` |
| 3 | what `check_alphabet.py` checks; "None of this is checked by CADP" | `framework/scripts/check_alphabet.py:2-11` |
| 4 | strikes after ADD of A, B or C; owed WRITE_ERROR_SHOWN then CONFIRM (ROLLED_BACK) | `test_purposes/tp_app_write_fail.lnt:3-9` |
| 4 | accept branch ending in `loop TP_ACCEPT end loop` | `test_purposes/tp_app_write_fail.lnt:44-49` |
| 4 | expectation "APP_WRITE_FAIL x3 FAIL O2" in the frozen mapping; snapshot frozen 15:15:05, sweep started 15:25:04 | `runs/campaign_2026-09-30b/snapshot/mastodon/properties/disruption_mapping.yml:24`; `runs/campaign_2026-09-30b/SWEEP.txt:1, 20` |
| 5 | `testor … -io mastodon.io -all tp_X.bcg …ctg.bcg` | `testor/generate_tc_all.sh:117-119` |
| 5 | CTG 70 states, 98 transitions | `generated/tc/generate_tc_all.log:633-634` |
| 5 | `ADD .*` and `APP_WRITE_FAIL` are inputs; `WAIT_FOR` is not listed | `testor/mastodon.io:5, 12` (whole file 1-22) |
| 5 | unlisted labels are outputs; ioco verdicts are earned on outputs | `testor/README_io.md:3-6` |
| 6 | `extract_all -check -copy -io …` | `testor/generate_tc_all.sh:141` |
| 6 | "4 choices found" … "2 test cases extracted" (34 and 22 transitions) | `generated/tc/generate_tc_all.log:636-644` |
| 6 | case 1 commits A, strikes B; case 2 strikes A | `tc_app_write_fail.1.aut:9, 19, 21-22`; `tc_app_write_fail.2.aut:9-10` |
| 6 | post C not extracted | `RESULTS_campaign.md:74` (struck at "posts A, B"); mechanism `RESULTS_campaign.md:106-108` (threat 1 explains why; it does not name APP_WRITE_FAIL) |
| 6 | generation 28 s | `gen_times.tsv:7` |
| 7 | concrete steps are executed (typed structural transitions) | `framework/concretization/algorithm.py:2779-2790` |
| 7 | "checkpoint ADD — advance (concrete steps done)" | `v1.log:10, 13`; code `algorithm.py:2849` |
| 7 | CONFIRM oracle OK: CountBand, HomeState, ProfileState agree | `v1.log:11`; label `tc_app_write_fail.1.aut:19`; code `algorithm.py:2077, 2846` |
| 7 | count band: `role: band`, `observed_from: el_post_count` | `properties/type_description.yml:57-59` |
| 8 | `HTMLExecutor initialized with base URL: https://mastodon.localhost` | `v1.log:6` |
| 8 | untrusted TLS accepted by configuration | `v1.log:5`; `properties/concrete_domain.yml:13` |
| 8 | password `@env:MASTODON_PW`, "not logged" | `v1.log:8-9` |
| 8 | Post button and write-error selectors | `properties/concrete_domain.yml:27, 83` |
| 8 | seed before each walk; sweep stops if not clean | `run_suite.sh:77-79` |
| 8 | 14 seed checks ok, incl. "antispam entry = 0" | `v1.seed.log:4-17`; `v2.seed.log:5-18` |
| 9 | order ADD → APP_WRITE_FAIL → CLICK !SEL_POST_BUTTON | `tc_app_write_fail.1.aut:21-23`; `v1.log:51-53`; "each label stands BEFORE the click it disrupts" `properties/disruption_mapping.yml:6-7` |
| 9 | inject `SADD antispam:all_time_spammy_texts 'ioco note'`; probe `SISMEMBER … equals 1` | `properties/disruption_mapping.yml:69, 71` |
| 9 | fixture texts mention @alice and contain "ioco note" | `properties/disruption_mapping.yml:64-66` |
| 9 | "Disruption activated and confirmed" / "APP_WRITE_FAIL injected and confirmed" | `v1.log:14-15` |
| 9 | restore `SREM` + delete the system report; probe equals 0; "restored and confirmed cleared" | `properties/disruption_mapping.yml:70, 72`; `v1.log:20` |
| 9 | unconfirmed injection → UNEXECUTABLE, walk stopped | `framework/concretization/algorithm.py:2706-2719` |
| 9 | the check runs before the save | `sut/mastodon/app/services/post_status_service.rb:102-103` (check) vs `:107-109` (`save!`) |
| 10 | state 22's only transition is `WAIT_FOR !EL_WRITE_ERROR`; no `:DELTA:` in the file | `tc_app_write_fail.1.aut:24` |
| 10 | "State 22 waits for WAIT_FOR !EL_WRITE_ERROR — it never appeared and this state does NOT permit quiescence … CONFORMANCE FAILURE." | `v1.log:19` |
| 10 | `Verdict: FAIL` | `v1.log:28` |
| 10 | δ rule: FAIL without δ, INCONCLUSIVE with δ | `framework/concretization/algorithm.py:2429-2472` (δ branch 2454-2462); `:DELTA:` is the sentinel, `algorithm.py:171` |
| 10 | the log also shows "stimulus could not be applied -> UNEXECUTABLE (not a verdict)" (`v1.log:18`): that is the executor's provisional result for the timed-out WAIT_FOR, which the walker re-judges by the δ rule | `framework/concretization/algorithm.py:2783-2790` |
| 10 | `raise SilentlyDrop, @status` when `considered_spam?`; the status is deleted, not persisted | `sut/mastodon/app/lib/antispam.rb:29, 39-45` |
| 10 | `rescue Antispam::SilentlyDrop … => e; e.status` | `sut/mastodon/app/services/post_status_service.rb:76-77` |
| 10 | controller renders the returned status as JSON | `sut/mastodon/app/controllers/api/v1/statuses_controller.rb:31, 50` |
| 10 | live probe, not the counted walk: "Post published." at 0.3 s; rows/counter 0/0 after restore | `notes/observed_behaviour.md:522-527, 536`; `notes/probe_faults_2026-09-29.log:30-35` |
| 10 | both cases FAIL, 15 s each (walk 30 s) | `variants_app_write_fail.log:3-4` |

## 3. Checks a–j

| Check | Result | Evidence |
|---|---|---|
| a | **Pass.** The waiting state has one transition and neither case contains `:DELTA:` | `(22, "WAIT_FOR !EL_WRITE_ERROR", 23)` `tc_app_write_fail.1.aut:24`; `(10, "WAIT_FOR !EL_WRITE_ERROR", 11)` `tc_app_write_fail.2.aut:12`; `grep -c DELTA` = 0 in both |
| b | **Pass.** `framework.diff` is byte-identical to today's `git diff` of `framework/concretization` and `framework/scripts`. Every snapshot file (framework, model, properties, `generated/tc`) is identical to the working tree | `runs/campaign_2026-09-30b/SWEEP.txt:1-5, 20`; `cmp` per file |
| c | **Pass.** All four messages are present in both logs | v1: `:15`, `:19`, `:20`, `:28`; v2: `:12`, `:16`, `:17`, `:25` |
| c (TLS) | **Pass: no effect on the run.** `reset_sut()` POSTs `/admin/reset`, which Mastodon does not serve. Each walk opens its own browser, and the reset is done by `seed.sh`, whose 14 checks all passed | `framework/concretization/executors.py:812-834`; `framework/scripts/run.py:114`; `run_suite.sh:77-79`; `v1.seed.log:4-17`; `v2.seed.log:5-18` |
| d | **Pass.** Injection precedes the Post click, in the case and in the log | `tc_app_write_fail.1.aut:21-23`; `v1.log:13-15`, `:51-53`; `properties/disruption_mapping.yml:6-7` |
| e | **Pass.** WRITE-PATH shape in APP and DATABASE; O2 as quoted | `model/specification_mastodon.lnt:14-15, 157-160, 319-320` |
| f | **Pass after the brief's correction.** No `screen` guard; arms chosen by `has_*` | `model/system_interface_mastodon.lnt:93-99, 124-129`; `properties/concrete_domain.yml:27, 83` |
| g | **Pass.** `ADD .*` and `APP_WRITE_FAIL` are inputs; `WAIT_FOR` is unlisted, so it is an output | `testor/mastodon.io:5, 12`; `testor/README_io.md:3-4` |
| h | **Pass.** `local_preflight_check!` raises `SilentlyDrop` (`antispam.rb:39-45`) before `save!` (`post_status_service.rb:103` vs `:108`). The service rescues it and returns the unsaved status (`:76-77`), and the controller renders it (`statuses_controller.rb:50`). Clone is tag `v4.7.2` | as cited |
| i | **Pass.** 1,175,066 / 1,514,418; CTG 70 states / 98 transitions; 2 cases; generation 28 s; walk 15 s + 15 s = 30 s | `model_size.txt:4-5`; `generate_tc_all.log:634, 641`; `gen_times.tsv:7`; `variants_app_write_fail.log:3-4` |
| j | **Pass, with one discrepancy.** The frozen mapping, snapshotted at 15:15:05 before the sweep began at 15:25:04, holds "APP_WRITE_FAIL x3 FAIL O2". The purpose's "Expected FAIL on O2" is in an untracked file with mtime 2026-09-30 08:53, before `v1.log` (15:27). **But** the earliest forecast, `notes/observed_behaviour.md:581` (§13, "written before any run"), says "**FAIL** on **O3**", not O2. The predicted verdict predates the walk; the obligation it named changed from O3 to O2 before the sweep | `runs/campaign_2026-09-30b/snapshot/mastodon/properties/disruption_mapping.yml:24`; `SWEEP.txt:1, 20`; `test_purposes/tp_app_write_fail.lnt:10`; `notes/observed_behaviour.md:581` |

### Not established from the files

- **No recorded `check_alphabet.py` run for Mastodon.** Item 3 therefore says what the checker
  checks, not that Mastodon passed it. To cite a pass, run
  `python framework/scripts/check_alphabet.py systems/mastodon` and keep the output.
- **The committed mapping does not hold the forecast.** The only commit touching the mapping
  (`ac9d46e`, 2026-09-29 09:48) predates `APP_WRITE_FAIL`, and the purpose file is untracked.
  The proof that the forecast came before the walk is the frozen snapshot (`SWEEP.txt:1`),
  not git.

## 4. Excerpt of `tc_app_write_fail.1.aut` (states 14–25)

```latex
\begin{lstlisting}
(14, "NAVIGATE !RT_HOME", 15)
(15, "WAIT_FOR !EL_HOME_LOADED", 16)
(16, "OBSERVE !EL_HOME_COLUMN", 17)
(17, "CONFIRM !COMMITTED !N1 !IN_HOME !ON_PROFILE !POST_A", 18)
(18, "TYPE_INTO !SEL_COMPOSE_TEXT !CV_TEXT_B", 19)
(19, "ADD !POST_B !PUBLIC !VALID", 20)
(20, APP_WRITE_FAIL, 21)
(21, "CLICK !SEL_POST_BUTTON", 22)
(22, "WAIT_FOR !EL_WRITE_ERROR", 23)
(23, "OBSERVE !EL_WRITE_ERROR", 24)
(24, WRITE_ERROR_SHOWN, 25)
\end{lstlisting}
```

Source: `generated/tc/variants/app_write_fail/tc_app_write_fail.1.aut:16-26`. It shows, in
eleven labels: the concrete read-back of post A, the oracle checkpoint, the next post, the
fault at its position before the click, and the state (22) that offers only the owed error.
