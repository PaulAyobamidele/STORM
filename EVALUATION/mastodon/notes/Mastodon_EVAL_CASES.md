# Mastodon: evaluation cases (campaign_2026-09-30b, current model)

Paths are relative to `EVALUATION/mastodon/`. `vN.log` = `generated/variant_logs/<purpose>/vN.log`;
`tc_x.N.aut` = `Test_Cases/variants/<purpose>/tc_x.N.aut`; app source = `sut/mastodon/` (v4.7.2).

## 1. Headline counterexamples

**H1. Antispam drops a post, and Mastodon tells the user it was published.** With an antispam
entry in Redis, the Post click shows "Post published." while no row is stored, and the error
the spec owes never comes (2 of 2 cases). The tester is ruled out: the fault is a confirmed Redis
entry set before the click, the failing state offers no `:DELTA:`, and the app source drops the
post without saving it and returns it as the result.

#### Mastodon-1  A dropped post is reported as published
    Purpose / test case : tp_app_write_fail / tc_app_write_fail.1.aut (also .2)
    Disruption          : APP_WRITE_FAIL (APP), Redis SADD antispam:all_time_spammy_texts, timing gate (properties/disruption_mapping.yml:63-72)
    Where it struck     : S2, after ADD post B, before the Post click (tc_app_write_fail.1.aut:21-23); .2 at S1
    Obligation          : O2, failed write reported, nothing moves (model/specification_mastodon.lnt:14-15, 157-160)
    What the app did    : no error report within the timeout (v1.log:16-17); live probe: "Post published." at 0.3 s, 0 rows (notes/observed_behaviour.md:536)
    Verdict and why     : FAIL, owed output missing at a state without δ (v1.log:19, 28)
    Counterexample      : (19, ADD !POST_B !PUBLIC !VALID) (20, APP_WRITE_FAIL) (21, CLICK !SEL_POST_BUTTON) (22, WAIT_FOR !EL_WRITE_ERROR) — tc_app_write_fail.1.aut:21-24
    Class               : SILENT
    Silent failure?     : yes
    Root cause in app   : app/lib/antispam.rb:29, 39-45 (raise SilentlyDrop before save); app/services/post_status_service.rb:76-77, 103, 108 (rescued, unsaved status returned)
    Data store evidence : 0 rows / 0 counter after restore, live probe before the sweep (notes/probe_faults_2026-09-29.log:30-35); not recorded per case
    Separate from nominal? : yes (S1/S2; nominal passes those steps, nominal/v1.log)
    Forecast            : FAIL on O2 in the frozen mapping (runs/campaign_2026-09-30b/snapshot/mastodon/properties/disruption_mapping.yml:24); held
    Reproduced          : 2 of 2 cases FAIL (variants_app_write_fail.log:3-4); each walked once
    Doubts              : first forecast named O3, not O2 (notes/observed_behaviour.md:581); strike at post C not extracted

**H2. With Sidekiq down, a post is "published", counted and on the profile, but missing from a
fresh home timeline.** All three strike points FAIL on O3: home is written only by a Sidekiq job,
so a committed post the user was told succeeded is absent from home. The tester is ruled out: the
read is a fresh navigation, the profile and count in the same read-back show the post, and the
source routes home delivery through `DistributionWorker`.

#### Mastodon-2  Home timeline misses a committed post while Sidekiq is down
    Purpose / test case : tp_infra_sidekiq_dead / tc_infra_sidekiq_dead.1.aut (also .2, .3)
    Disruption          : INFRA_SIDEKIQ_DEAD (INFRA), docker pause mastodon-sidekiq-1, timing gate (properties/disruption_mapping.yml:154-158)
    Where it struck     : before post C (S3), ahead of TYPE_INTO (tc_infra_sidekiq_dead.1.aut:32); .2 before B, .3 before A
    Obligation          : O3, a post the user was told succeeded is what a fresh read shows, home and profile (model/specification_mastodon.lnt:16-18)
    What the app did    : newest post in fresh home was the previous one (v1.log:19); live probe: "Post published." at 1.0 s, home written only after unpause (notes/observed_behaviour.md:539)
    Verdict and why     : FAIL, CONFIRM HomeState expected IN_HOME, observed NOT_IN_HOME (v1.log:19, 28)
    Counterexample      : (30, INFRA_SIDEKIQ_DEAD) (32, ADD !POST_C …) (33, CLICK !SEL_POST_BUTTON) (34, WAIT_FOR !EL_PUBLISHED) … (39, NAVIGATE !RT_HOME) … (42, CONFIRM !COMMITTED !N3 !IN_HOME !ON_PROFILE !POST_C) — tc_infra_sidekiq_dead.1.aut:32-44
    Class               : STALE
    Silent failure?     : yes (success shown; home delivery never ran during the read)
    Root cause in app   : app/services/post_status_service.rb:176 (DistributionWorker.perform_async); home is read from Redis, app/models/feed.rb:17-28
    Data store evidence : rows/counter/home 1/1/3 after the unpause (notes/observed_behaviour.md:539)
    Separate from nominal? : yes (S1–S3; nominal fails only at S6)
    Forecast            : FAIL O3 at S1–S3 (properties/disruption_mapping.yml:31); held
    Reproduced          : 3 of 3 cases FAIL (variants_infra_sidekiq_dead.log:3-5); each walked once
    Doubts              : home is eventually consistent by design; the FAIL holds for the read-back, not after recovery

**H3. With the web process paused, the post click hangs with no report, and the write lands
later.** All three strike points FAIL on O2 by missing output; live probes show the hung write
stored after the unpause (1 row). The tester is ruled out for the verdict (confirmed pause, no
`:DELTA:` at the waiting state); whether a delayed write is a "failed write" is a modelling doubt.

#### Mastodon-3  A hung post gives no report
    Purpose / test case : tp_app_unavailable / tc_app_unavailable.1.aut (also .2, .3)
    Disruption          : APP_UNAVAILABLE (APP), docker pause mastodon-web-1, auto-unpause after 20 s, timing gate (properties/disruption_mapping.yml:74-80)
    Where it struck     : S3, after ADD post C, before the Post click (tc_app_unavailable.1.aut:34-35); .2 at S2, .3 at S1
    Obligation          : O2 (model/specification_mastodon.lnt:14-15)
    What the app did    : no alert while the web process hung (v1.log:22); live probe: no alert in 15 s, write stored after unpause (notes/observed_behaviour.md:533)
    Verdict and why     : FAIL, owed output missing at state 34, no δ (v1.log:22, 31)
    Counterexample      : (32, APP_UNAVAILABLE) (33, CLICK !SEL_POST_BUTTON) (34, WAIT_FOR !EL_WRITE_ERROR) — tc_app_unavailable.1.aut:34-36
    Class               : MISSING-REPORT
    Silent failure?     : yes (nothing shown)
    Root cause in app   : NOT ESTABLISHED (no client request timeout located)
    Data store evidence : rows/counter/home 1/1/3 after restore (notes/observed_behaviour.md:533)
    Separate from nominal? : yes (S1–S3)
    Forecast            : FAIL O2 by quiescence (properties/disruption_mapping.yml:26); held
    Reproduced          : 3 of 3 FAIL (variants_app_unavailable.log:3-5); each walked once
    Doubts              : the write eventually succeeds, so O3/O9 may fit better than O2; a stopped (not paused) web is reported at once with "502" (notes/observed_behaviour.md:534, 543-544)

## 2. Other findings

- **Resilience.** DB_ABORT, INFRA_STORAGE_FULL and UE_SESSION_EXPIRED were reported at once ("500", "401") with count, home and profile unmoved: PASS 9 of 9 (RESULTS_campaign.md:73, 76, 78). UE_KILL left whole writes (PASS ×2, :72); APP_EXTAPI_FAIL did not block the post (PASS ×2, :79).
- **Nominal defect (RQ1).** After deleting post C the profile still reads "Posts 3" where 2 is owed, in 2 of 3 walks (Mastodon-4). The controller hides the post at once; the count drops only when Sidekiq destroys the row (app/controllers/api/v1/statuses_controller.rb:84-88; app/models/status.rb:161, 487-492).
- **Forecast miss.** 15 of 16 purposes came out as forecast; nominal was forecast PASS (RESULTS_campaign.md:92-95; Test_Purposes/tp_nominal.lnt:10).
- **The fault mechanism decides the verdict.** A paused web process is silent; a stopped one answers "502" at 0.1 s (notes/observed_behaviour.md:533-534, 543-544). The same holds for INFRA_DB_DOWN (Mastodon-5).
- **Tester defects STORM exposed, fixed before this campaign:** oracles reading empty article shells, the login throttle stopping cases after the 25th login, and non-matching selectors; three runs are archived uncounted (RESULTS_campaign.md:127-132).
- **No INCONCLUSIVE and no UNEXECUTABLE** in this campaign (runs/campaign_2026-09-30b/eval_tables.txt, TOTAL row).

## 3. System and obligations

**Scope.** Mastodon v4.7.2 (Rails, React web client, PostgreSQL 14, Redis 7, Sidekiq), one
local instance behind Caddy at https://mastodon.localhost, driven through Selenium as fixture
user `bob` (RESULTS_campaign.md:3-5). The model covers posting, reading with and without refresh,
a fresh check and deleting (model/specification_mastodon.lnt:5-9). Left out: federation, the
connectivity-lost fault (RESULTS_campaign.md:136-137) and edits (no case contains `EDIT`).

**Normal run** (Test_Purposes/tp_nominal.lnt:4, 9; Test_Cases/tc_nominal.aut):
1. S1 log in, type post A, `ADD`, Post → "Post published."; read-back `CONFIRM COMMITTED N1 IN_HOME ON_PROFILE` (:14, :28)
2. S2 post B, `CONFIRM … N2` (:32, :45)
3. S3 post C, `CONFIRM … N3` (:49, :62)
4. S4 read C without refresh: `PEEK`, `SHOW V_ORIG` (:67, :72)
5. S5 fresh check: `CHECK`, `CONFIRM … N3` (:80, :89)
6. S6 delete C: `REMOVE`, `CONFIRM COMMITTED N2 NOT_IN_HOME OFF_PROFILE` → `:PASS:` (:111, :121-122)

| ID | Plain words | Witnessing gate(s) | path:line |
|---|---|---|---|
| O1 | a rejected input is reported, nothing written | REJECT_SHOWN | specification_mastodon.lnt:13 |
| O2 | a failed post/delete is reported, nothing moves | WRITE_ERROR_SHOWN | :14-15 |
| O3 | a post shown as succeeded is on home and profile after a fresh read | IN_HOME, ON_PROFILE | :16-18 |
| O4 | the post count follows the committed rows | count band | :19 |
| O5 | an edit is what a fresh read shows | V_EDITED (not exercised) | :20 |
| O6 | a deleted post is gone everywhere; count follows | NOT_IN_HOME, band | :21-22 |
| O7 | a view read without refresh shows the committed text | SHOW after APP_CACHE_STALE | :23 |
| O8 | a corrupt record is flagged | DB_CORRUPT_DETECTED | :24 |
| O9 | leaving mid-write leaves a whole write or none | after UE_KILL | :25 |

## 4. Campaign identity

| Field | Value |
|---|---|
| Name and date | campaign_2026-09-30b, frozen 2026-09-30T15:15:05, sweep 15:25–15:33 (runs/campaign_2026-09-30b/SWEEP.txt:1, 20-21) |
| Matches current model | yes: snapshot model, properties and cases byte-identical to the working tree (`cmp`, 2026-10-01); generator inputs identical on Mac and CADP node (Test_Cases/inputs_md5.txt) |
| Model size | 1,175,066 states / 1,514,418 transitions (model_size.txt:4-5) |
| Purposes / cases | 16 / 31 |
| P / F / I / U | 15 / 16 / 0 / 0 |
| Generation / walk | 450 s / 306 s (runs/campaign_2026-09-30b/eval_tables.txt, TOTAL) |

## 5. Results by purpose

| Purpose | Layer | Cases | P | F | I | U | Cause |
|---|---|---|---|---|---|---|---|
| nominal | NOMINAL | 1 | 0 | 1 | 0 | 0 | "Posts 3" after the delete (variants_nominal.log:3) |
| app_write_fail | APP | 2 | 0 | 2 | 0 | 0 | success shown, post dropped (Mastodon-1) |
| app_unavailable | APP | 3 | 0 | 3 | 0 | 0 | no report while web hung (Mastodon-3) |
| app_cache_stale | APP | 1 | 0 | 1 | 0 | 0 | open column shows old text (Mastodon-6) |
| app_lazy_processing | APP | 1 | 0 | 1 | 0 | 0 | nominal's S6 symptom; counted under nominal |
| app_extapi_fail | APP | 2 | 2 | 0 | 0 | 0 | preview fetch is async |
| db_abort | DB | 3 | 3 | 0 | 0 | 0 | "500", nothing moved |
| db_corrupt | DB | 1 | 0 | 1 | 0 | 0 | blank post shown, no notice (Mastodon-7) |
| db_event_loss | DB | 1 | 0 | 1 | 0 | 0 | row gone, count still 3 (Mastodon-8) |
| infra_db_down | INFRA | 3 | 0 | 3 | 0 | 0 | no report while db hung (Mastodon-5) |
| infra_sidekiq_dead | INFRA | 3 | 0 | 3 | 0 | 0 | home misses committed post (Mastodon-2) |
| infra_storage_full | INFRA | 3 | 3 | 0 | 0 | 0 | "500", nothing moved |
| input_invalid | INPUT | 1 | 1 | 0 | 0 | 0 | "Post can't be blank." |
| input_overlimit | INPUT | 1 | 1 | 0 | 0 | 0 | Post button withheld |
| ue_kill | USER | 2 | 2 | 0 | 0 | 0 | whole write |
| ue_session_expired | USER | 3 | 3 | 0 | 0 | 0 | "401", nothing written |
| **Total** | | **31** | **15** | **16** | **0** | **0** | agrees with RESULTS_campaign.md:50 |

## 6. Case cards

#### Mastodon-4  The post count does not drop after a delete (nominal)
    Purpose / test case : tp_nominal / tc_nominal.1.aut
    Disruption          : none
    Where it struck     : S6, read-back after the delete (tc_nominal.1.aut:111-121)
    Obligation          : O6, count follows the delete (specification_mastodon.lnt:21-22)
    What the app did    : post gone from home and profile; count "Posts 3" (nominal/v1.log:26)
    Verdict and why     : FAIL, CONFIRM CountBand expected N2, observed N3 (v1.log:26, 34)
    Counterexample      : (75, REMOVE !REC_C) … (78, OBSERVE !EL_POST_COUNT) … (83, CONFIRM !COMMITTED !N2 !NOT_IN_HOME !OFF_PROFILE !POST_C) — tc_nominal.1.aut:111-121
    Class               : NOMINAL + TIMING
    Silent failure?     : no
    Root cause in app   : statuses_controller.rb:84-88 (hide now, RemovalWorker later); status.rb:161, 487-492 (count drops on destroy)
    Data store evidence : NOT RECORDED
    Separate from nominal? : n/a
    Forecast            : PASS forecast (tp_nominal.lnt:10); missed
    Reproduced          : 2 FAIL of 3 walks (variants_nominal.log:3; runs/campaign_2026-09-30b/repeats/variants_nominal.log:3-4)
    Doubts              : measures the count against the read-back, not eventual convergence (RESULTS_campaign.md:64-66). APP_LAZY_PROCESSING (app_lazy_processing/v1.log:28) has the same symptom and is counted here

#### Mastodon-5  A post during a database pause gives no report
    Purpose / test case : tp_infra_db_down / tc_infra_db_down.1.aut (also .2, .3)
    Disruption          : INFRA_DB_DOWN (INFRA), docker pause mastodon-db-1, auto-unpause after 25 s, gate (disruption_mapping.yml:146-150)
    Where it struck     : after ADD, before the Post click (tc_infra_db_down.1.aut:34-35)
    Obligation          : O2 (specification_mastodon.lnt:14-15)
    What the app did    : no alert (v1.log:22); probe: write landed after unpause (observed_behaviour.md:535)
    Verdict and why     : FAIL, missing output at state 34, no δ (v1.log:22, 31)
    Class               : MISSING-REPORT
    Silent failure?     : yes
    Root cause in app   : NOT ESTABLISHED
    Data store evidence : 1/1/3 after restore (observed_behaviour.md:535)
    Separate from nominal? : yes
    Forecast            : FAIL O2 by quiescence (disruption_mapping.yml:28); held
    Reproduced          : 3 of 3 FAIL (variants_infra_db_down.log:3-5)
    Doubts              : as Mastodon-3: the write succeeds later

#### Mastodon-6  An open column keeps showing text that changed in the store
    Purpose / test case : tp_app_cache_stale / tc_app_cache_stale.1.aut
    Disruption          : APP_CACHE_STALE (APP), SQL UPDATE of post C's text, gate (disruption_mapping.yml:93-101)
    Where it struck     : S4, before the read without refresh (tc_app_cache_stale.1.aut:44-49)
    Obligation          : O7 (specification_mastodon.lnt:23)
    What the app did    : column still showed the original text (v1.log:22)
    Verdict and why     : FAIL, SHOW expected V_EDITED (v1.log:22, 31)
    Class               : STALE
    Silent failure?     : no
    Root cause in app   : NOT ESTABLISHED
    Separate from nominal? : yes (S4)
    Forecast            : FAIL O7 (disruption_mapping.yml:32); held
    Reproduced          : walked once
    Doubts              : the SQL change emits no event, so no web client could know; this shows the client never re-checks, not that Mastodon's own edits go stale (RESULTS_campaign.md:123-125)

#### Mastodon-7  A blanked post is shown as an empty post, without notice
    Purpose / test case : tp_db_corrupt / tc_db_corrupt.1.aut
    Disruption          : DB_CORRUPT (DB), SQL sets post C's text to '' (violates status.rb:121), gate (disruption_mapping.yml:129-134)
    Where it struck     : S5, during the fresh check (tc_db_corrupt.1.aut:70-78)
    Obligation          : O8 (specification_mastodon.lnt:24)
    What the app did    : no notice at state 51 (v1.log:23)
    Verdict and why     : FAIL, missing output, no δ at state 51 (v1.log:23, 32)
    Class               : INTEGRITY
    Silent failure?     : no
    Root cause in app   : NOT ESTABLISHED
    Separate from nominal? : yes (S5)
    Forecast            : FAIL O8 (disruption_mapping.yml:34); held
    Reproduced          : walked once
    Doubts              : Mastodon claims no corruption detection; O8 is an obligation the model imposes; the fault bypasses the app (RESULTS_campaign.md:123-125)

#### Mastodon-8  A row lost from the store still counts
    Purpose / test case : tp_db_event_loss / tc_db_event_loss.1.aut
    Disruption          : DB_EVENT_LOSS (DB), SQL DELETE of post C, gate (disruption_mapping.yml:137-145)
    Where it struck     : S5, before the fresh check (tc_db_event_loss.1.aut:44-55)
    Obligation          : O4 (specification_mastodon.lnt:19)
    What the app did    : post gone from home and profile, count "Posts 3" (v1.log:22)
    Verdict and why     : FAIL, CONFIRM CountBand expected N2, observed N3 (v1.log:22, 31)
    Class               : INTEGRITY
    Silent failure?     : no
    Root cause in app   : the count is a counter cache changed only by callbacks (status.rb:160-161)
    Separate from nominal? : yes (S5; nominal passes S5, same count symptom at S6)
    Forecast            : FAIL O4 at S5 (disruption_mapping.yml:33); held
    Reproduced          : walked once
    Doubts              : the SQL delete bypasses the callbacks by construction (RESULTS_campaign.md:123-125)

#### Mastodon-9  PASS: an aborted insert is reported and nothing moves
    Purpose / test case : tp_db_abort / tc_db_abort.1.aut
    Disruption          : DB_ABORT (DB), Postgres trigger raises on write, gate (disruption_mapping.yml:113-121)
    Obligation          : O2
    What the app did    : "500" alert; count, home, profile unmoved (db_abort/v1.log:18-20; RESULTS_campaign.md:76)
    Verdict and why     : PASS (v1.log:22, 31)
    Reproduced          : 3 of 3 PASS (variants_db_abort.log:3-5)

#### Mastodon-10  PASS: leaving right after Post leaves a whole write
    Purpose / test case : tp_ue_kill / tc_ue_kill.1.aut
    Disruption          : UE_KILL (USER), realised by the SI (Post, then leave), timing none (disruption_mapping.yml:48)
    Obligation          : O9
    What the app did    : post committed, counted, on home and profile (ue_kill/v1.log:20)
    Verdict and why     : PASS (v1.log:21, 29)
    Reproduced          : 2 of 2 PASS (variants_ue_kill.log:3-4)

## 7. Tester-side and UNEXECUTABLE runs

| Case | What went wrong | Evidence | Fixed? |
|---|---|---|---|
| none in this campaign | every injection and restore confirmed; 14 seed checks before every case | RESULTS_campaign.md:52-54 | n/a |
| runs 1–3 (uncounted) | empty-shell oracle reads, login throttle, selector mismatches | RESULTS_campaign.md:127-132 | yes, before this campaign |
| all walks | `reset_sut()` TLS warning: posts to a route Mastodon lacks; reset is done by seed.sh | app_write_fail/v1.log:7; v1.seed.log:4-17 | no effect |

## 8. Aggregates

Counterexamples: 15 FAIL cases in 8 findings (16 FAILs minus app_lazy_processing, counted under nominal).

| Class | Findings | Cases |
|---|---|---|
| SILENT | 1 (Mastodon-1) | 2 |
| MISSING-REPORT | 2 (Mastodon-3, -5) | 6 |
| STALE | 2 (Mastodon-2, -6) | 4 |
| INTEGRITY | 2 (Mastodon-7, -8) | 2 |
| NOMINAL (+TIMING) | 1 (Mastodon-4) | 1 |

By layer (cases): APP 6, INFRA 6, DB 2, NOMINAL 1, USER 0, INPUT 0.
Silent failures (success or nothing shown, operation stopped): **11 cases** in 4 findings
(Mastodon-1 ×2, -2 ×3, -3 ×3, -5 ×3).

## 9. Do not claim

- That every strike point was tested: post C of APP_WRITE_FAIL, the delete placements of six faults, and post C of UE_KILL and APP_EXTAPI_FAIL were not extracted (RESULTS_campaign.md:106-113).
- That no row was stored *in the counted walks*: store contents come from live probes before the sweep (RESULTS_campaign.md:97-102).
- That `check_alphabet.py` passed: no run is recorded for Mastodon.
- Anything about edits (O5), federation or connectivity loss: not exercised.
- That Mastodon's own edits go stale (Mastodon-6), or that Mastodon detects corruption by design (Mastodon-7).
- A security finding: no obligation concerns security.
