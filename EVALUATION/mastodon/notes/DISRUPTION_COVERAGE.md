# Mastodon — disruption coverage against the project catalogue

Started 2026-09-29 (phase A). For every disruption type used in the earlier
case studies: the Mastodon fault that mirrors it, the mechanism, and — where it
cannot be hosted — the reason. Evidence is in `observed_behaviour.md` (§ refs).
A type enters the specification only once its inject / restore /
verify_injected / verify_restored are written and proven in
`properties/disruption_mapping.yml` (phase D) and by `check_faults.sh`
(phase F). Status column: **hosted**, **decision**, **not hosted**.

| Category | Catalogue type | Mastodon fault | Mechanism (out of band unless SI) | Status | Notes |
|---|---|---|---|---|---|
| USER | client killed / leaves mid-write | `UE_KILL` | SI-realised: click Post, navigate to `/home` at once (timing `none`) | hosted | the request completes server-side (§4.1); the spec offers both consistent read-backs |
| USER | connectivity lost | — | Chrome DevTools offline exists (`executors.py`, `set_ue1_offline`) | **not hosted** | reached only by unmapped legacy gate names, and the read-back needs connectivity back mid-walk, which no mapped fault can do; left out of the spec by decision (2026-09-29). Earlier note: | the switch exists but is reached only by unmapped legacy gate names (`algorithm.py:2685-2709`). Needs a small config-driven hook: a mapped fault with `mechanism: connectivity` calls the executor's switch on inject and restore. SUT-agnostic, self-testable. Fallback without the hook: pause Caddy — but that is server-side and blurs with APP_UNAVAILABLE |
| USER | session expires | `UE_SESSION_EXPIRED` | SQL: delete `bob`'s `session_activations` and the linked `oauth_access_tokens` (§2, §6) | hosted | probe: count of rows = 0; restore: nothing (the next case logs in afresh) |
| USER | device storage full | — | — | not hosted | the browser is the only device-side store and no part of the write depends on it; the server-side analogue is INFRA_STORAGE_FULL below |
| APP | write fails inside the app | `APP_WRITE_FAIL` | Redis `SADD antispam:all_time_spammy_texts "<fixture text>"`; the fixture post mentions `@alice`, who does not follow `bob` (§8) | hosted | the app drops the post, files a report, and answers success (`post_status_service.rb:76-77`). Restore: `SREM`; the seed clears the system report. Requires every fixture post to carry the `@alice` mention so the write under fault is the same write as nominal |
| APP | stale cache / derived view | `APP_CACHE_STALE` | SQL: change the fixture post's `text` underneath the client store; the SI reads the home column **without** reload (§5) | hosted | the only purpose whose read-back is not a fresh fetch; every other purpose reloads first. The model carries the store's value (original → edited) so the oracle expects the edited text |
| APP | API unavailable | `APP_UNAVAILABLE` | `docker pause mastodon-web-1`, delayed unpause (upstream hangs) | hosted (mechanism under review) | measured: paused = no alert in 15 s, the write lands after the unpause; stopped = \"502\" at 0.1 s, nothing written. A stopped web cannot be walked: the read-back would meet Caddy's 502 page until puma is back (8 s). | live check in phase C: what the browser receives and how fast; puma's restart time. Forecast differs by mechanism (§13) |
| APP | external API fails | `APP_EXTAPI_FAIL` | `docker network disconnect mastodon_external_network mastodon-sidekiq-1` (§8, §11.7) | hosted | the only outbound call a plain post causes is the link-preview fetch; the fixture post for this purpose carries a URL; resilience shape (the post must still commit); the card is not an oracle. Restore: `docker network connect …` |
| APP | partial or lazy processing | `APP_LAZY_PROCESSING` | `docker kill -s TSTP mastodon-sidekiq-1` (quiet: no new jobs), restore by restart | hosted | the app's asynchronous half is entirely Sidekiq (§4); no distinct app-level mechanism exists. A paused streaming server was considered and dropped: the column merely stops updating and a reload is fresh, so under the fresh-read rule nothing is measured |
| DB | transaction aborted | `DB_ABORT` | `CREATE TRIGGER fault_abort_write BEFORE INSERT ON statuses … RAISE EXCEPTION` | hosted | probe: `pg_trigger` count; restore: `DROP TRIGGER`, `DROP FUNCTION` |
| DB | record corrupted | `DB_CORRUPT` | SQL: `UPDATE statuses SET text = ''` on the fixture post (violates `status.rb:121`) | hosted | rendered as an empty post (§10); probe: the row's text = ''; restore: nothing (the seed removes the post) |
| DB | data lost after write | `DB_EVENT_LOSS` | SQL: `DELETE FROM statuses WHERE id = <fixture post>` (cascades in place, §2) | hosted | leaves `statuses_count` and `feed:home` drifted (§7); probe: row count 0; restore: the seed re-counts / recreates `account_stats` |
| INFRA | database down | `INFRA_DB_DOWN` | `docker pause mastodon-db-1` across the Post, delayed unpause | hosted | probe: `docker inspect .State.Paused`; the write may land late (§13) |
| INFRA | scheduler / background-job worker dead | `INFRA_SIDEKIQ_DEAD` | `docker pause mastodon-sidekiq-1` | hosted | two placements: post (home feed never written) and delete (count never decremented); probe: `.State.Paused`; restore: unpause (the queued jobs then run — the seed must wait for them or clear) |
| INFRA | storage media degraded | — | — | not hosted | the only files are media attachments (none in the fixture); an unreadable file shows as a broken image, which no text oracle reads. Hosting it needs a media variant and an upload primitive |
| INFRA | (server) storage full | `INFRA_STORAGE_FULL` (analogue) | `ALTER SYSTEM SET default_transaction_read_only = on` + reload; restore with the default overridden for the session | hosted | filling a real disk is not safe on a bind-mounted volume; read-only Postgres is the honest "storage refuses writes" analogue. Distinct mechanism from DB_ABORT (cluster-wide vs one table). Include or record as analogue only |
| INPUT | invalid value | `INPUT_INVALID` | SI: blank text, click Post | hosted (parameter) | client alert "Post can't be blank." (§6) |
| INPUT | over limit | `INPUT_OVERLIMIT` | SI: 501 counted characters | hosted (parameter) | Post button withheld (§6); the refusal is checked in the unchanged count |
| INPUT | domain variant | (followers-only visibility) | SI branch exists: compose visibility button → dialog → Followers → Save | **not exercised, by decision** | 2026-09-29: one happy path only, and not every function is tested; a second visibility would be a second happy path | both are counted and appear in home; CW hides the text behind "Show more" (changes the observable); poll possible; scheduled post not exercisable (5-minute scheduler, §8) |
| ENV | sensor / environment | — | — | not hosted | a server-side web application has no sensors |
| — | federation | — | — | not hosted | single instance, no remote peer to deliver to or receive from (§8) |

## Rules this table respects

- One fault, one mechanism: no two rows share a command.
- A fault whose mechanism blocks a write is armed **before** the write's
  concrete steps (timing `pre`) or at a gate placed **before** the click it
  shares with the commit arm (Spliit's UE_KILL lesson, `PROMPT_next_session.md`).
- A fault that changes the store underneath the client (`APP_CACHE_STALE`,
  `DB_CORRUPT`, `DB_EVENT_LOSS`) fires at its gate, after the post exists.
- Every hosted row gets `verify_injected` and `verify_restored` probes in
  phase D; a row without both is not run.

All twelve injected faults were proven to bite and let go through the framework's DisruptionExecutor on 2026-09-29 (`notes/check_faults_2026-09-29.log`, `check_faults.py`).
