# Mastodon — campaign results (campaign_2026-09-30b)

Mastodon v4.7.2 (Rails + React, PostgreSQL 14, Redis 7, Sidekiq), one local instance behind
Caddy at https://mastodon.localhost, fixture user `bob`. 16 test purposes, 31 test cases, each
walked once from a seeded and verified clean stack. Verdicts are the ioco verdicts only.
**Every number below is regenerable** from files in this directory:

    .venv/bin/python framework/scripts/eval_tables.py EVALUATION/mastodon --baseline nominal

reads `variants_<purpose>.log` (one row per case), `gen_times.tsv` and `model_size.txt`; its
output for this campaign is `runs/campaign_2026-09-30b/eval_tables.txt`. Per-case evidence:
`generated/variant_logs/<purpose>/v<N>.log`, `.seed.log`, `_captures/`. Provenance:
`runs/campaign_2026-09-30b/SWEEP.txt` (revision, dirty flag, frozen snapshot, `framework.diff`),
`Test_Cases/inputs_md5.txt` (every generator input identical on the Mac and the CADP node).

## The design in one paragraph

One happy path H — post A, post B, post C, read C without refresh, fresh check of C, delete C —
and 15 disruptions of it, each allowed to strike at every step of H where the specification
states what is owed. The test cases are what TESTOR's `extract_all` resolves from those choices
(31 from 16 purposes). Obligations (specification header): O1 a rejected input is reported ·
O2 a failed post or delete is reported and nothing moves · O3 a post the user was told
succeeded is what a fresh read shows · O4 the post count follows the committed rows · O6 a
deleted post is gone everywhere and the count follows · O7 a view read without refresh shows
the committed text · O8 a corrupt record is flagged · O9 leaving mid-write leaves a whole
write or none.

## Results

Composed model SPEC ‖ SI: 1 175 066 states, 1 514 418 transitions (`model_size.txt`).

| Purpose | Cases | Pass | Fail | Inc. | Unexec. | Pass rate | TC size | Min variant | Max variant | Gen. s | Walk s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nominal | 1 | 0 | 1 | 0 | 0 | 0% | 85–85 | .1 (85/121) | .1 (85/121) | 15 | 8 |
| app_cache_stale | 1 | 0 | 1 | 0 | 0 | 0% | 49–49 | .1 (49/49) | .1 (49/49) | 21 | 5 |
| app_extapi_fail | 2 | 2 | 0 | 0 | 0 | 100% | 20–32 | .2 (20/20) | .1 (32/32) | 27 | 8 |
| app_lazy_processing | 1 | 0 | 1 | 0 | 0 | 0% | 86–86 | .1 (86/123) | .1 (86/123) | 12 | 18 |
| app_unavailable | 3 | 0 | 3 | 0 | 0 | 0% | 22–46 | .3 (22/22) | .1 (46/46) | 36 | 46 |
| app_write_fail | 2 | 0 | 2 | 0 | 0 | 0% | 22–34 | .2 (22/22) | .1 (34/34) | 28 | 30 |
| db_abort | 3 | 3 | 0 | 0 | 0 | 100% | 22–46 | .3 (22/22) | .1 (46/46) | 41 | 11 |
| db_corrupt | 1 | 0 | 1 | 0 | 0 | 0% | 56–56 | .1 (56/82) | .1 (56/82) | 15 | 19 |
| db_event_loss | 1 | 0 | 1 | 0 | 0 | 0% | 55–55 | .1 (55/55) | .1 (55/55) | 24 | 5 |
| infra_db_down | 3 | 0 | 3 | 0 | 0 | 0% | 22–46 | .3 (22/22) | .1 (46/46) | 43 | 51 |
| infra_sidekiq_dead | 3 | 0 | 3 | 0 | 0 | 0% | 20–44 | .3 (20/20) | .1 (44/44) | 40 | 12 |
| infra_storage_full | 3 | 3 | 0 | 0 | 0 | 100% | 22–46 | .3 (22/22) | .1 (46/46) | 44 | 20 |
| input_invalid | 1 | 1 | 0 | 0 | 0 | 100% | 71–71 | .1 (71/100) | .1 (71/100) | 17 | 3 |
| input_overlimit | 1 | 1 | 0 | 0 | 0 | 100% | 71–71 | .1 (71/100) | .1 (71/100) | 16 | 3 |
| ue_kill | 2 | 2 | 0 | 0 | 0 | 100% | 21–33 | .2 (21/22) | .1 (33/34) | 32 | 55 |
| ue_session_expired | 3 | 3 | 0 | 0 | 0 | 100% | 28–52 | .3 (28/28) | .1 (52/52) | 39 | 12 |
| **Total** | **31** | **15** | **16** | **0** | **0** | **48%** | 20–86 | | | 450 | 306 |

Every injected fault logged "injected and confirmed" and "restored and confirmed cleared"
(UE_KILL is realised by the System Interface; nothing to restore). The stack passed all 14
seed checks before every case and after the sweep.

## What each walk saw (the cause of every verdict, from its log)

**The happy path fails, intermittently, at its last step (O6).** Posts A, B, C, the read
without refresh and the fresh check all agreed with the oracle in every walk. After deleting
C, the post was gone from home and from the profile, but the profile still read "Posts 3"
where the specification requires 2. The controller hides a deleted post at once
(`statuses_controller.rb:84-86`); the count drops only when Sidekiq's RemovalWorker destroys
the row (`status.rb:161, 487-493`). Reproduced in 2 of 3 walks (the counted walk and one repeat,
`runs/campaign_2026-09-30b/repeats/`); the third read "Posts 2" and passed. A genuine ioco FAIL
of a timing-dependent obligation: it measures the count against the tester's read-back, not
against eventual convergence.

| Disruption | Where it struck | Verdict | What the walk saw |
|---|---|---|---|
| input_invalid (blank post) | post A | PASS | "Post can't be blank."; nothing written (count 0) |
| input_overlimit (501 chars) | post A | PASS | Post button withheld; nothing written |
| UE_KILL | posts A, B | PASS ×2 | the request completed after the user left: whole write, count, home and profile consistent |
| UE_SESSION_EXPIRED | posts A, B, C | PASS ×3 | "401 The access token was revoked"; after a fresh login, nothing written |
| APP_WRITE_FAIL (antispam) | posts A, B | **FAIL ×2** | "Post published." for a post Mastodon silently dropped; the owed error never came (O2) |
| APP_UNAVAILABLE (web paused) | posts A, B, C | **FAIL ×3** | no alert while the web process hung (O2 by quiescence) |
| DB_ABORT (trigger) | posts A, B, C | PASS ×3 | alert "500"; count, home, profile unmoved |
| INFRA_DB_DOWN (db paused) | posts A, B, C | **FAIL ×3** | no alert while the database hung (O2 by quiescence) |
| INFRA_STORAGE_FULL (read-only) | posts A, B, C | PASS ×3 | alert "500"; nothing moved |
| APP_EXTAPI_FAIL (preview fetch cut) | before posts A, B | PASS ×2 | the post landed normally; the link preview is async |
| INFRA_SIDEKIQ_DEAD | before posts A, B, C | **FAIL ×3** | "Post published.", counted, on the profile — but the newest post in a fresh home was the previous one: home is written only by Sidekiq (O3) |
| APP_CACHE_STALE | before the read without refresh | **FAIL** | the column still showed the original text after the stored text changed (O7) |
| DB_EVENT_LOSS | before the fresh check | **FAIL** | the row gone from home and profile, the count still "Posts 3" (O4) |
| DB_CORRUPT | during the fresh check | **FAIL** | the blanked post opened as an empty post, no notice (O8) |
| APP_LAZY_PROCESSING (Sidekiq quiet) | before the delete | **FAIL** | "Posts 3" after the delete — the same symptom as nominal's S6 FAIL |

**Against the baseline** (the procedure: a disruption failure on functionality the nominal
run already fails is counted once, under nominal): APP_LAZY_PROCESSING fails at S6 on exactly
nominal's symptom, so it is not separate evidence about lazy processing. Every other
disruption strikes before S6, on steps nominal passed, so its verdict is attributable to its
disruption.

**Forecast against outcome.** The forecasts in `properties/disruption_mapping.yml` were
written before any sweep. 15 of 16 purposes came out as forecast. The miss is **nominal**,
forecast PASS: the source reading placed the count's asynchrony in the delete path
(observed_behaviour.md §4.3) but did not expect the fresh read-back to beat the worker.

**What the data store held** (live probes before the sweep, observed_behaviour.md §12.2–12.3,
logs in `notes/`): under APP_UNAVAILABLE and INFRA_DB_DOWN the hung write **landed after the
fault was lifted** (rows 1, counter 1), so the silence hid a write that later succeeded;
under APP_WRITE_FAIL no row was ever stored although success was shown; under DB_ABORT,
INFRA_STORAGE_FULL and UE_SESSION_EXPIRED nothing was stored. The sweep itself does not record
the store per case (the seed resets it before each).

## Threats to validity

1. **Coverage the extraction did not produce.** `extract_all` emits one case per point where
   the tester chooses between striking and carrying on, not one per strike point: the strike
   point reached only by carrying on past all others was never generated. So the delete
   placement of UE_SESSION_EXPIRED, APP_UNAVAILABLE, DB_ABORT, INFRA_DB_DOWN,
   INFRA_STORAGE_FULL and INFRA_SIDEKIQ_DEAD, and post C of UE_KILL and APP_EXTAPI_FAIL, are
   specified and probed live (observed_behaviour.md §12.3) but not walked. The blank and
   over-limit purposes each came out as one case holding three alternatives; the walk took
   post A.
2. **Seven purposes extract a single case.** By design (single strike point, or a choice
   between two ordinary inputs, which extraction does not split); the `.io` is identical on
   both machines by md5.
3. **Timing.** The quiescence window is 10 s; the nominal S6 verdict depends on Sidekiq's
   latency against the read-back. Other sweeps (FoodYou on an emulator, a Spliit session) ran
   on the same Mac during parts of the campaign.
4. **Test-environment resets.** The seed clears Mastodon's own rate-limit counters (login
   throttle 25/h per e-mail, 300 posts per 3 h) before each case; they are counters, not
   behaviour under test, but a real user would hit them.
5. **Mechanisms that bypass the application.** APP_CACHE_STALE, DB_CORRUPT and DB_EVENT_LOSS
   change the store by SQL, so no event reaches the client: the stale FAIL says the client
   never re-checks on its own, not that Mastodon's own edits go stale.
6. **The count band saturates at "4 or more"**; this campaign stays at ≤ 3 posts.
7. **Tester defects found and fixed before this campaign** (none affects its verdicts): home
   and profile oracles read while the feed still showed empty article shells; the login
   throttle stopped cases after the 25th login; the column-title and menu selectors did not
   match (a `<li>` whose handler is on its `<button>`). Three earlier runs are archived,
   uncounted, under `runs/2026-09-30_run1_discarded`, `runs/2026-09-30_run2_unfrozen`,
   `runs/2026-09-30_run3_smoke_delete_selector`, each with a README.
8. **Framework state.** The tree was dirty; the exact framework that ran is the campaign's
   `snapshot/` and `framework.diff`. Its self-test: 14 failures, all pre-existing or caused by
   running the suite inside the snapshot (SWEEP.txt), none in code a Mastodon walk uses.
9. **Federation not exercised** (single instance); no connectivity-lost fault
   (DISRUPTION_COVERAGE.md).
