# Mastodon — Observed Behaviour (ground truth for the behavioural model)

Written 2026-09-29. Source: the local clone at `EVALUATION/mastodon/sut/mastodon`,
tag `v4.7.2` (`lib/mastodon/version.rb:7-16`), the same version as the running
images (`docker-compose.yml:62,86,105`). Everything in §1–§11 was established by
READING THE SOURCE; every `file:line` was read in this session (✓). The only
things executed were read-only: HTTP GETs of `/about` and `/api/v2/instance`,
`SELECT`s against the database, `SCAN`/`DBSIZE` against Redis, and a keychain
lookup. They are listed in §12 and marked `(measured)`.

Sections 1–9 describe the application as deployed here. Section 10 summarises
what is silent and what is reported. Section 11 lists the disruptions the
source admits, with a mechanism each. Section 12 is the live checklist.
Section 13 gives the honest forecast per fault, to be copied into
`properties/disruption_mapping.yml` before any run.

---

## 1. What Mastodon is, and how it is deployed here

A federated microblogging server: Ruby on Rails API + server-rendered login,
a React single-page web client, PostgreSQL 14, Redis 7, Sidekiq background
workers, and a Node streaming server that pushes timeline events to the
browser over WebSocket (`docker-compose.yml:5-118` ✓: services `db`, `redis`,
`web`, `streaming`, `sidekiq`; the `web` and `sidekiq` containers share the
bind mount `./public/system` for media).

**Reachability.** The user's `docker-compose.override.yml` moves `web` to
`127.0.0.1:3100`, `streaming` to `127.0.0.1:4100`, and adds a Caddy container on
`127.0.0.1:443` serving `mastodon.localhost` with an internal (self-signed) CA
(`Caddyfile` ✓). Rails host authorisation admits only `LOCAL_DOMAIN`
(`config/initializers/1_hosts.rb:31-34` ✓, `/health` excepted), so
`http://127.0.0.1:3100/` answers **403** and only `https://mastodon.localhost/`
answers **200** (measured). `config.force_ssl = true`
(`config/environments/production.rb:38` ✓). The Caddy root certificate is at
`caddy_data/caddy/pki/authorities/local/root.crt` and is **not** in the System
or login keychain (measured), so a Selenium Chrome must either trust it or be
started with certificate errors ignored (§12).

**Environment** (`.env.production`, non-secret keys only): `LOCAL_DOMAIN=
mastodon.localhost`, `S3_ENABLED=false` (media on local disk under
`public/system`, `config/initializers/paperclip.rb:163` ✓), `ES_ENABLED=false`,
`SMTP_SERVER=` (empty: no mail leaves the box), `EMAIL_DOMAIN_ALLOWLIST=
mastodon.localhost`, `DEFAULT_LOCALE=en`.

**Accounts.** Registrations are closed (`config/settings.yml:12`
`registrations_mode: 'none'` ✓; `/api/v2/instance` → `registrations.enabled:
false`, measured). Two local users exist (measured, read-only SQL):

| account id | username | role | confirmed | approved | last sign-in | statuses_count |
|---|---|---|---|---|---|---|
| 117353415418602758 | alice | Owner | yes | yes | 2026-09-29 08:41 | 3 |
| 117353415630680785 | bob | (none) | yes | yes | 2026-09-29 08:43 | 0 |

`bob` follows `alice`; `alice` does not follow `bob` (measured). Both have a
`feed:home:<id>` key in Redis (measured). Accounts are created and modified
with `tootctl accounts create USERNAME --email … --confirmed --approve --role`
and `tootctl accounts modify USERNAME --reset-password …`
(`lib/mastodon/cli/accounts.rb:43-49, 121-129` ✓).

**Rate limits that a sweep can hit.** Per account, 300 statuses per 3 hours
(`app/lib/rate_limiter.rb:12-15` ✓; applied because the controller passes
`with_rate_limit: true`, `app/controllers/api/v1/statuses_controller.rb:47` ✓
→ `post_status_service.rb:280`). Per user, **30 status deletions per 30
minutes** (`config/initializers/rack_attack.rb:100-106` ✓). Authenticated API
1 500 requests per 5 minutes (`:69`). Consequence: the fixture must be reset
between cases through the application's own service, never through API
deletes.

---

## 2. Domain and schema (the nouns)

`db/schema.rb` ✓, `app/models/*.rb` ✓.

| Table / key | Fields that matter | Notes |
|---|---|---|
| `statuses` | `account_id NOT NULL` (:1244), `text NOT NULL DEFAULT ''` (:1262), `spoiler_text NOT NULL DEFAULT ''` (:1261), `sensitive` (:1260), `visibility integer NOT NULL DEFAULT 0` (:1267; 0 = public), `deleted_at` (:1248, **soft delete**), `edited_at` (:1249) | `default_scope { recent.kept }` (`app/models/status.rb:128` ✓): a row with `deleted_at` set is invisible to every ordinary query |
| `status_stats` | `replies_count`, `reblogs_count`, `favourites_count`, all `NOT NULL DEFAULT 0` | read through `[value, 0].max` (`app/models/status_stat.rb:26-36` ✓): a negative stored count is **silently shown as 0** |
| `account_stats` | `statuses_count`, `followers_count`, `following_count`, `last_status_at` | a **counter cache**, maintained by an `UPSERT … statuses_count = statuses_count + 1` (`app/models/concerns/account/counters.rb:53-75` ✓), never recounted |
| `status_edits` | one snapshot per edit, plus one for the original on the first edit | written inside the edit's transaction (`app/services/update_status_service.rb:26-32, 160-172` ✓) |
| `session_activations` | one per browser session, `access_token_id` | the web client's API token is the session's Doorkeeper token (`app/models/session_activation.rb:22` ✓, `dependent: :destroy`); a session is live iff its row exists (`:36-38` ✓) |
| Redis `feed:home:<account_id>` | sorted set of status ids, score = id, max 800 | the home timeline (`app/lib/feed_manager.rb:29-33, 10` ✓) |
| Redis `idempotency:status:<account>:<key>` | 1 h | duplicate-post guard (`post_status_service.rb:226-256` ✓) |
| Redis `antispam:all_time_spammy_texts`, `antispam:spammy_texts` | sets of substrings | the silent-drop rule of §8 (`app/lib/antispam.rb:61-67` ✓) |

Foreign keys **into** `statuses` cascade for `status_stats`, `status_edits`,
`favourites`, `mentions`, `polls`, `statuses_tags`, `bookmarks`, `status_pins`,
`quotes`, `tagged_objects`; `media_attachments` is nullified
(`db/schema.rb:1518-1627` ✓). A raw `DELETE FROM statuses` therefore succeeds
and takes the row's dependants with it — but runs **no Rails callback**, so
`account_stats.statuses_count` and the Redis feed are left as they were (§7).

---

## 3. Journeys: what a user can do, and where

Web client routes (React SPA, after login through the server-rendered Devise
form at `/auth/sign_in`):

| Route | What the user does | Read from |
|---|---|---|
| `/home` | the home column; the compose form is in the left column on wide screens | `GET /api/v1/timelines/home` (Redis ids → rows, §5) then streaming events |
| `/@bob` | profile: header with **"{n} post(s)"** (`app/javascript/mastodon/locales/en.json:143` ✓ `account.statuses_counter`), then the account's posts | `GET /api/v1/accounts/:id` (counter cache) and `…/statuses` (rows) |
| `/@bob/<id>` | one post with its context | `GET /api/v1/statuses/:id` |
| compose form | textarea, character counter, **"Post"** button; in edit mode **"Update"** (`features/compose/components/compose_form.jsx:41-42` ✓) | — |
| status menu | Edit; Delete → modal **"Delete post?" / "Are you sure you want to delete this status?" / "Delete"** (`features/ui/components/confirmation_modals/delete_status.tsx:27-35` ✓) | — |

The complete **user-initiated write alphabet** on a status (all through
`Api::V1::StatusesController` ✓ and its siblings):

| Write | HTTP | Service |
|---|---|---|
| create | `POST /api/v1/statuses` with `Idempotency-Key` | `PostStatusService` |
| edit | `PUT /api/v1/statuses/:id` | `UpdateStatusService` |
| delete | `DELETE /api/v1/statuses/:id` | controller soft-delete + `RemovalWorker` |
| favourite / boost | `POST …/favourite`, `…/reblog` | `FavouriteService`, `ReblogService` |
| media upload | `POST /api/v2/media` → 202 while processing | `PostProcessMediaWorker` (async) |

Optional inputs on create: visibility (public / unlisted / followers-only /
direct), content warning (`spoiler_text`, which also sets `sensitive`,
`post_status_service.rb:83` ✓), poll, scheduled_at, media.

---

## 4. Writes: what is synchronous and what goes through Sidekiq

This is the central fact of the system. **Every user-facing write commits its
row synchronously and is acknowledged from that row; every derived view except
the profile's own post list is maintained afterwards by Sidekiq.**

### 4.1 Create — `PostStatusService#call` (`app/services/post_status_service.rb` ✓)

| Step | Sync / async | Lines |
|---|---|---|
| Redis lock and idempotency lookup | sync, **Redis required before any DB write** | :246-256 |
| `validate_media!` | sync | :197-212 |
| build status, process mentions, `Antispam#local_preflight_check!` | sync | :94-103 |
| `@status.save!` inside `ApplicationRecord.transaction` | sync | :105-109 |
| `after_create_commit :increment_counter_caches` → `account_stats.statuses_count + 1` | sync (same request) | `status.rb:160, 479-485` → `counters.rb:23-24, 53-63` |
| `process_hashtags_service`, `Trends.tags.register` | sync | :173-174 |
| `LinkCrawlWorker` (preview card, **external HTTP fetch**) | async | :175 |
| `DistributionWorker` → `FanOutOnWriteService` | async | :176 |
| `ActivityPub::DistributionWorker` (federation; no peers here) | async | :178 |
| response: the saved status as JSON | — | `statuses_controller.rb:50` |

The **home feed is written only by the async path**: `FanOutOnWriteService#
deliver_to_self!` (`app/services/fan_out_on_write_service.rb:28-29, 58-60` ✓) →
`FeedManager#push_to_home` (`feed_manager.rb:76-83` ✓): returns without
writing unless `account.user.signed_in_recently?` (:77; "recently" = signed in
within `USER_ACTIVE_DAYS`, default 7 days, `app/models/concerns/user/activity.
rb:12-20` ✓), then `ZADD feed:home:<id>`, trim to 800, and a `PushUpdateWorker`
to the streaming server if that account has a subscriber (:81). Followers'
feeds go through one `FeedInsertWorker` each (`fan_out_on_write_service.rb:
101-107`, `app/workers/feed_insert_worker.rb` ✓). `DistributionWorker` takes a
Redis lock `distribute:<status_id>` (`app/workers/distribution_worker.rb:9` ✓).

Two exceptional exits, both **rescued and answered as success**
(`post_status_service.rb:76-77` ✓): `IdempotencyError` returns the earlier
status for the same key; `Antispam::SilentlyDrop` returns an **unsaved** status
object (`app/lib/antispam.rb:19-33, 39-45` ✓: `status.delete` "make sure this is
not persisted", wrapped in a `DummyStatus`) after filing a system report
(:74-80). The controller renders it with HTTP 200 like any other post. §8
gives the rule that triggers it.

### 4.2 Edit — `UpdateStatusService#call` (`app/services/update_status_service.rb` ✓)

One `Status.transaction` (:26-32): snapshot of the original if this is the
first edit (:160-168), media / poll changes, `update_immediate_attributes!`
(:113-128: text, `edited_at = now`, `save!`), and the new snapshot (:170-172).
`NoChangesSubmittedError` rolls back silently and the response is the reloaded
status (:40-45). Then, **async**: `DistributionWorker.perform_async(id,
{'update' => true})` (:143-146) → `push_to_home(update: true)` → `PushUpdateWorker`
→ streaming `status.update` to every subscribed client. The editing browser
does **not** depend on that: it takes the edited status from the PUT response
(`actions/compose.js:276-278` ✓).

### 4.3 Delete — `Api::V1::StatusesController#destroy` (`:76-91` ✓) and `RemoveStatusService` ✓

| Step | Sync / async | Lines |
|---|---|---|
| JSON of the status rendered first | sync | :82 |
| `discard_with_reblogs` → `UPDATE statuses SET deleted_at = now` (soft delete; reblogs too) | sync | :84 → `status.rb:400-404` |
| pin removed | sync | :85 |
| `@status.account.statuses_count - 1` | **in memory only** (the account is not saved) | :86 |
| `RemovalWorker` → `RemoveStatusService` | async | :88 → `app/workers/removal_worker.rb:6-7` |
| — `unpush_from_home` for the author: `ZREM feed:home`, publish `delete` | async | `remove_status_service.rb:27, 62-64` → `feed_manager.rb:90-95` |
| — followers, lists, mentions, hashtags, public streams | async | :28-46 |
| — `@status.destroy!` if `permanently?` (true for an ordinary delete) | async | :53, 162-164 |
| — `after_destroy_commit :decrement_counter_caches` → `statuses_count - 1` | async (inside the worker) | `status.rb:161, 487-493` |

So, the moment the API answers, the post is **hidden** everywhere (default
scope `kept`, §2) but `account_stats.statuses_count` still counts it and its id
is still in `feed:home` until the worker runs.

### 4.4 Favourite — synchronous row and counter

`Favourite.create!` (`app/services/favourite_service.rb:18` ✓) with
`after_create :increment_cache_counters` → `status_stats.favourites_count + 1`
(`app/models/favourite.rb:31-39` ✓); only the notification is async (:30-38).

### 4.5 Media

`POST /api/v2/media` creates the attachment with `delay_processing: true` and
answers **202** while `PostProcessMediaWorker` (Sidekiq) processes it
(`app/controllers/api/v2/media_controller.rb:4-22` ✓). A post that references an
unprocessed attachment is refused with 422 "not ready"
(`post_status_service.rb:211`). Media is therefore the one place where a dead
Sidekiq turns into a **reported** failure. Not used by this campaign's
fixture (no upload primitive in the System Interface; `public/system` is
empty, measured).

---

## 5. Reads: what each view is served from

| View | Source | Freshness |
|---|---|---|
| home timeline API | `HomeFeed#get` → `Feed#from_redis`: `ZREVRANGEBYSCORE feed:home:<id>` then `Status.where(id: ids)` (`app/models/feed.rb:22-32` ✓) | ids from Redis, **rows from the database at request time**, through the default scope: a soft-deleted or hard-deleted row is silently dropped from the page; an id with no row disappears. No Rails cache: `preload_collection` only preloads associations (`app/controllers/concerns/preloading_concern.rb:6-12` ✓, `app/models/concerns/cacheable.rb:17-19` ✓). HTTP 206 while the feed is being regenerated (`api/v1/timelines/home_controller.rb:22` ✓) |
| profile post list | `Api::V1::Accounts::StatusesController` → database query paginated by id ✓ | fresh |
| "{n} posts" | `account_stats.statuses_count` through the account serializer | a **counter cache** (§2), not a count |
| favourite / boost counts | `status_stats`, clamped at 0 on read | counter caches |
| public endpoints (unauthenticated) | `render_with_cache`, 3 minutes (`app/controllers/concerns/cache_concern.rb:28-47` ✓) | not on the authenticated home read |

**The web client is itself a cache.** The home column is filled once from the
API and then only changed by (a) streaming events — `update` → `updateTimeline`,
`status.update` → `updateStatus`, `delete` → `deleteFromTimelines`
(`actions/streaming.js:101-110` ✓) — and (b) the client's own actions: after a
successful post it **inserts the API response into the home column itself**,
provided the column is loaded and its stream is online (`actions/compose.js:
266-282` ✓, `insertIfOnline('home')`), and after a successful delete it removes
the post locally (`actions/statuses.js:167-169` ✓). Nothing in the client
re-reads the home timeline on its own; only a navigation / reload does.
Consequence for the tester: a read **with** reload measures Redis + database; a
read **without** reload measures the client store.

---

## 6. What the UI shows: success, failure, refusal (the observables)

All alerts are rendered by one controller into the live region
`div.notification-list` (`components/alerts_controller.tsx:83` ✓).

| Event | What appears | Source |
|---|---|---|
| post committed | toast **"Post published."** with an **"Open"** action, dismissed after 10 s; the form clears | `actions/compose.js:87-88, 292-300` ✓; reducer `COMPOSE_SUBMIT_SUCCESS → clearAll` (`reducers/compose.js:459-460` ✓) |
| edit committed | toast **"Post saved."**; the post re-renders with **"Edited {date}"** | `compose.js:89, 293`; `components/status.jsx:45` ✓ |
| any failed action | every Redux action whose type ends in `FAIL` is turned into an alert by `errorsMiddleware` (`store/middlewares/errors.ts:36-54` ✓) → `showAlertForError` (`actions/alerts.ts:40-78` ✓): **with a response**: title = the HTTP status code as text, message = `data.error` if the body has one, else the HTTP status text; **429** with a reset header: "Rate limited / Please retry after …"; **no response** (network failure): **"Oops!" / "An unexpected error occurred."**; the compose text is kept and the button re-enables (`reducers/compose.js:461-462`) | |
| blank post | client-side alert **"Post can't be blank."**, nothing sent | `compose.js:90, 201-211` ✓ |
| over the limit | the **Post button is disabled** and the keyboard shortcut is ignored (`canSubmit` false when the counted length exceeds `maxChars`); the counter shows a negative number | `compose_form.jsx:124-140, 337` ✓; `maxChars` from the instance configuration, default 500 (`compose_form_container.js:60` ✓ ← `serializers/rest/instance_serializer.rb:86` ✓ ← `StatusLengthValidator::MAX_CHARS = 500`, URLs count 23, `app/validators/status_length_validator.rb:4-5` ✓) |
| favourite | the star fills **optimistically** on request and is reverted on failure | `reducers/statuses.js:109-112` ✓ |
| delete | the post leaves the column on success; failure → alert | `actions/statuses.js:167-181` ✓ |
| session gone | no special handling of 401 in the client (`api.ts` has none ✓) → alert **"401"** with Doorkeeper's description (`api/base_controller.rb:23-25` ✓) | |

Server-side error bodies the alert can carry (`app/controllers/concerns/api/
error_handling.rb:7-50` ✓): 422 with the model's own message for
`RecordInvalid` / `Mastodon::ValidationError`, 422 "Duplicate record", 404
"Record not found", 503 "There was a temporary problem serving your request,
please try again" (`RaceConditionError`), 429 the i18n `errors.429` text.
**An exception outside that table — a database error such as
`ActiveRecord::StatementInvalid` from a raised trigger, or a connection
error — is unhandled: Rails answers 500.** There is no `public/500.json`
(only `500.html`, ✓), so the JSON body is Rails' default; what the alert's
message reads is a §12 item. `database.yml` sets `connect_timeout: 15` and no
`statement_timeout` (✓): a query against a **paused** database hangs.

Server-side validation of a post (`app/models/status.rb:120-124` ✓): `text`
present unless media / reblog / quote (:121); length (:122); no disallowed
hashtags (:123). The client refuses blank and over-limit **before** sending
(above), so these two server rules are never reached from the web UI.

---

## 7. Logs versus data

There is no activity log. Three pairs can disagree:

1. **`account_stats.statuses_count` vs rows.** Incremented in the create
   request, decremented only when the removal worker destroys the row (§4.3);
   never touched by anything outside Rails callbacks. A row deleted or a
   worker that never runs leaves the profile saying "1 post" over an empty
   list.
2. **`feed:home` vs rows.** Ids are added and removed asynchronously; the
   read joins them against the database and drops the missing ones (§5), so
   this drift is invisible as posts and visible only through the count.
3. **`status_edits` vs `statuses`.** Written in the same transaction; cannot
   drift by the application's own action.

The `favourites_count` clamp (`status_stat.rb:34-36`) is the one place where a
corrupt stored value is deliberately masked on read.

---

## 8. Background jobs, the streaming server, antispam, federation

**Queues** (`config/sidekiq.yml` ✓): `default`, `push`, `ingress`, `mailers`,
`pull`, `scheduler`, `fasp`; `ScheduledStatusesScheduler` every **5 minutes**
(a scheduled post is published by the scheduler, not by the request) —
too coarse for a walk with a 10 s observation window.

**Jobs that matter here**: `DistributionWorker` (home feeds), `RemovalWorker`
(permanent delete + counter), `LinkCrawlWorker` (preview card: the only
outbound HTTP a plain post causes; failures are rescued and the job ends
quietly, `app/workers/link_crawl_worker.rb:8-10` ✓), `PushUpdateWorker`
(streaming), `LocalNotificationWorker`, `ActivityPub::*` (no remote inbox to
reach on a single instance), `PostProcessMediaWorker` (media only).

**Streaming.** The Node server subscribes to `timeline:<account_id>` for the
home column (`streaming/index.js:1058-1061` ✓). On disconnect the client marks
the column offline (`actions/streaming.js:90-91` ✓), which also disables the
local insert after a post (§5).

**Antispam, the silent drop** (`app/lib/antispam.rb` ✓). A local post is
`considered_spam?` (:49-51) when its text contains a member of the Redis set
`antispam:all_time_spammy_texts` (or of `antispam:spammy_texts` for an account
younger than a week) **and** it replies to or mentions only accounts that do
not follow the author (:69-72). Then `local_preflight_check!` files a system
report and raises `SilentlyDrop` (:39-45), which `PostStatusService` rescues
and answers with the unsaved status (§4.1). The client shows "Post
published." and inserts the phantom into the home column; a reload shows no
such post. This is deliberate product behaviour (do not tell a spammer he was
caught) and a genuine app-layer failed write that reports success.

**Federation** cannot be exercised on one machine: there is no second
instance, `alice` and `bob` are local, `ActivityPub::DistributionWorker` has
no inbox to deliver to. Out of scope; recorded in `DISRUPTION_COVERAGE.md`.

---

## 9. Validation: client versus server

| Rule | Client | Server |
|---|---|---|
| blank text (no media, no quote) | alert "Post can't be blank.", not sent | 422 `text` presence (`status.rb:121`) |
| more than 500 counted characters | Post button withheld | 422 "over character limit" (`status_length_validator.rb:11`) |
| duplicate submission | `Idempotency-Key` (a UUID regenerated when the compose state changes, `reducers/compose.js:134-231` ✓) | the earlier status is returned (`post_status_service.rb:250`) |
| more than 4 media, mixed types, unprocessed media | — | 422 (`post_status_service.rb:203-211`) |
| rate | — | 429 after 300 posts / 3 h |

---

## 10. Failure and edge behaviour: what is silent, what is reported

| Situation | Reported? | Where |
|---|---|---|
| server answers an error (4xx/5xx) to a write | **yes**: alert with the code and the body's `error` | §6 |
| network unreachable from the browser | **yes**: "Oops! An unexpected error occurred." | `alerts.ts:72-77` |
| database hung (paused) during a write | **no output** within any reasonable window: the query blocks, the request does not return | `database.yml` (no statement timeout) |
| Sidekiq not running | **no**: the post is acknowledged and shown; the home feed is never written; a delete leaves the count | §4 |
| antispam silent drop | **no**: success is reported for a write that did not happen | §8 |
| a row edited or deleted outside the application | **no**: the client store keeps what it has until an event or a reload; counters keep their value | §5, §7 |
| a corrupt row (blank text, negative count) | **no**: rendered as an empty post (`app/lib/text_formatter.rb:34` ✓ returns `''` for blank text) or as 0 | §2 |
| session revoked | **yes**: 401 alert on the next API call; login page on the next full load | §6 |

---

## 11. Disruptions the source admits (mechanism and what a specification must state)

Each names a real mechanism against the running stack, out of band, and the
observable the specification would have to demand. No verdicts here; §13
forecasts them. Container names: `mastodon-db-1`, `mastodon-redis-1`,
`mastodon-web-1`, `mastodon-sidekiq-1`, `mastodon-streaming-1`,
`mastodon-caddy-1`; Postgres user `postgres`, database `mastodon_production`,
trust auth (`docker-compose.yml:16`).

1. **User leaves right after Post** (UE_KILL). Realised by the System
   Interface: click Post, navigate to `/home` at once. The request completes
   server-side; the idempotency key is lost with the page. Owed: a consistent
   read-back — the post everywhere, or nowhere.
2. **Browser loses connectivity** (UE_CONN_LOST). Chrome DevTools
   `Network.emulateNetworkConditions offline`; the framework's web executor
   has the switch (`framework/concretization/executors.py:761-777` ✓). Owed:
   the failed write is reported, nothing written. Note: today only an
   *unmapped* legacy gate name reaches that switch (`algorithm.py:2685-2709`
   ✓); a mapped fault needs a `mechanism: connectivity` hook (config-driven,
   see `DISRUPTION_COVERAGE.md`).
3. **Session expires** (UE_SESSION_EXPIRED). SQL: delete `bob`'s
   `session_activations` rows and their `oauth_access_tokens`. Owed: the
   rejected write is reported, nothing written.
4. **App refuses the write silently** (APP_WRITE_FAIL). `SADD
   antispam:all_time_spammy_texts "<substring of the fixture text>"` in
   Redis, with the fixture post mentioning `@alice` (who does not follow
   `bob`). Owed: either the failure is reported, or what the user was told
   succeeded is what a fresh read shows. Restore: `SREM`; the system report
   it files must be resolved or deleted by the seed.
5. **Client cache stale** (APP_CACHE_STALE). SQL: change the fixture post's
   `text` underneath the client store (no fan-out, no event), then read the
   home column **without** reload. Owed: the value shown is the committed
   one.
6. **API unavailable** (APP_UNAVAILABLE). `docker stop mastodon-web-1`
   (Caddy answers 502 at once) or `docker pause mastodon-web-1` (Caddy's
   upstream accepts the connection and never answers). Owed: the failed
   write is reported, nothing written. Which one, after a live check (§12).
7. **External lookup fails** (APP_EXTAPI_FAIL). `docker network disconnect
   mastodon_external_network mastodon-sidekiq-1`: the link crawler cannot
   fetch the preview card; the database and Redis stay reachable on the
   internal network. Owed: the post with a link still commits (resilience);
   the card is not part of any oracle.
8. **Transaction aborted** (DB_ABORT). `CREATE TRIGGER … BEFORE INSERT ON
   statuses … RAISE EXCEPTION`. Owed: reported, nothing written, count
   unchanged.
9. **Record corrupted** (DB_CORRUPT). SQL: `UPDATE statuses SET text = ''`
   on the fixture post: a row that violates the model's own invariant
   (`status.rb:121`). Owed: flagged when read, not rendered as a sound empty
   post.
10. **Data lost after write** (DB_EVENT_LOSS). SQL: `DELETE FROM statuses`
    the fixture post after it was acknowledged (cascades are in place, §2).
    Owed: a fresh read is consistent — the post absent **and** the count
    following.
11. **Database down** (INFRA_DB_DOWN). `docker pause mastodon-db-1` across
    the Post, unpaused afterwards. Owed: reported within the window,
    nothing written (or written whole).
12. **Background worker dead** (INFRA_SIDEKIQ_DEAD). `docker pause
    mastodon-sidekiq-1`. Two placements: around a **post** (the home feed is
    never written; profile and count move) and around a **delete** (post
    hidden, count not decremented). Owed: what the user was told is what a
    fresh read shows; counts follow.
13. **Storage refuses writes** (INFRA_STORAGE_FULL, analogue). The only file
    writes are media (none in the fixture). The server-storage analogue with
    a real mechanism is Postgres in read-only mode (`ALTER SYSTEM SET
    default_transaction_read_only = on; SELECT pg_reload_conf()`): every
    write fails with a statement error. Owed: reported, nothing written.
    Decision pending (see `DISRUPTION_COVERAGE.md`).
14. **Input**: blank post (INPUT_INVALID, client message); 501 characters
    (INPUT_OVERLIMIT, control withheld); domain variants: followers-only
    visibility (counted, in home, not public), content warning (text hidden
    behind "Show more"), poll. Scheduled post: not exercisable (5-minute
    scheduler).

Not admitted with an observable: media file made unreadable (a broken image
only), streaming server paused (the column simply stops updating; a reload is
fresh), device storage (nothing of the write depends on browser storage),
federation, sensors.

---

## 12. To confirm live before any of this is relied on

Already measured, read-only, 2026-09-29 (§1): `:3100` → 403 and
`https://mastodon.localhost/about` → 200; `/api/v2/instance` (v4.7.2,
registrations closed, `max_characters` 500); the two accounts, their roles,
sign-in dates and counts; `bob → alice` follow; `feed:home` keys; empty
`public/system`; Caddy root certificate present in `caddy_data`, absent from
both keychains.

Still to confirm, in phase C, against the running app:

- **Credentials**: `bob`'s password is not known to this session. Needed
  for the System Interface's login prelude. `tootctl accounts modify bob
  --reset-password` prints a new one if it is lost.
- **TLS**: whether Chrome under Selenium accepts `mastodon.localhost` once
  `caddy_data/caddy/pki/authorities/local/root.crt` is added to the login
  keychain; otherwise the executor needs an ignore-certificate-errors option
  (a generic, config-driven flag — framework change to record).
- The login form's field names and the landing route after sign-in; whether
  the compose form is present on `/home` at 1280×900.
- The exact DOM of: the compose form and Post button (enabled / disabled),
  the character counter, the `.notification-list` alerts (title and message
  nodes), the home column's status articles and their text, the profile
  header's "{n} posts", the status action menu, Edit → "Update", the delete
  modal, "Edited {date}".
- The **alert text on a 500** (DB_ABORT): Rails' default JSON body for an
  API request — is `error` "Internal Server Error", or absent (then the
  message is the HTTP status text, which is empty over HTTP/2 through Caddy)?
- **Antispam drop**: that the SADD + mention rule fires for `bob` posting to
  `@alice`; that the client shows "Post published." and the phantom row; that
  a reload shows nothing; what the system report needs for cleanup.
- **Paused database**: that the request hangs past the 10 s window and
  completes after unpause (or times out); the alert, if any.
- **Paused vs stopped web**: what the browser receives through Caddy in each
  case and how fast; puma's restart time after `docker start`.
- **Paused Sidekiq**: that "Post published." is shown, that `/home` after
  reload lacks the post while `/@bob` shows it with "1 post"; that after a
  delete the count stays.
- **Session revocation**: which rows to delete (`session_activations` and
  the linked `oauth_access_tokens`) and the exact 401 message.
- **Stale client**: that a SQL text change is not reflected without reload
  and is reflected after one.
- **Fixture reset**: a `seed.sh` that removes `bob`'s statuses through
  `RemoveStatusService` (`bin/rails runner` in the `web` container), clears
  system reports and the antispam set, and asserts `statuses_count = 0`,
  `feed:home:<bob>` free of `bob`'s ids, no trigger, database unpaused,
  `default_transaction_read_only = off`, Sidekiq and web unpaused.
- Whether `alice`'s three existing posts in `bob`'s home column disturb
  any anchor (they make the column non-empty, which is welcome).

---

### 12.1 Confirmed live, 2026-09-29 (`notes/probe_dom.py`, dumps in `notes/dom/`)

Headless Chrome with `--ignore-certificate-errors` (probe only), as `bob`.

- ✓ Sign-in at `/auth/sign_in`: `input[name='user[email]']`, `input[name='user[password]']`,
  `button[type=submit]` "Log in"; lands on `/home` (`01_sign_in`, `02_home`).
- ✓ Home at 1280×900 carries the compose form (`form.compose-form`, textarea
  `.autosuggest-textarea__textarea`, submit in `.compose-form__submit`, label "Post"),
  and the column `div[role=region][aria-label=Home].column`; posts are `<article data-id>`
  with text in `.status__content__text`. The column is non-empty (alice's "Hello 1",
  "Hello 2"; none contains the fixture text).
- ✓ Blank post: `div.notification-bar > span.notification-bar__content` "Post can't be
  blank." within 0.5 s, nothing sent (a one-shot dump at 1.2 s missed it; a poll caught it).
  Alerts auto-dismiss after 5 s + 1 s per stacked alert (`alerts_controller.tsx:88`).
- ✓ 501 characters: counter `.character-counter--over` shows `-1`; the Post button has
  the `disabled` attribute (`06_overlimit`).
- ✓ Post: the column shows the post at once, toast "Post published. | OPEN" (`11`);
  profile `/@bob` shows **"Posts | 1"** in `li._comp_number_fields__item` (not "1 post":
  the header uses the number-fields list) and the post in the account feed (`12`); home
  after reload (≈6 s later) contains it: fan-out ran (`13`). The URL renders as
  `https://` + `example.com` spans and a preview card "example.com | Example …" appeared
  on the profile: the link crawler reached the internet.
- ✓ Own post's "More" menu (`button[aria-label=More].status__action-bar__button`) lists
  `li.dropdown-menu__item` "Edit", "Delete", "Delete & re-draft" (`14`). Edit loads the
  text into the compose form and relabels the button **"Update"** (`15`). After Update the
  column shows the revised text at once and marks the timestamp with
  `<abbr title="Last edited …"> *</abbr>`, not "Edited {date}" (`16`, `17`). The
  "Post saved." toast was not caught by the dump (unverified).
- ✓ Delete: modal `.safety-action-modal` with `button[type=submit]` "Delete" (`18`);
  the post leaves the column (`19`); profile "Posts | 0" and
  `.empty-column-indicator` "No posts here!" (`20`). Database afterwards: no bob rows at
  all (hard-deleted by the worker), `statuses_count` 0, `feed:home:<bob>` = alice's two ids.

### 12.2 Fault behaviour measured live, 2026-09-29 (`notes/probe_faults.py`, log `notes/probe_faults_2026-09-29.log`)

One post per fault from a seeded fixture, the fault injected and confirmed through
the framework's DisruptionExecutor just before the Post click, the alert area
polled for 15 s, then the fault restored and the store read 8 s later. Every
injection and restore was confirmed by its probe; `notes/check_faults_2026-09-29.log`
proves all twelve bite and let go.

| Fault | Alert within 15 s | Store after restore (rows / counter / home feed) | Reading |
|---|---|---|---|
| DB_ABORT (trigger) | "500" at 0.3 s (title only, no message) | 0 / 0 / 2 | reported; nothing written |
| APP_UNAVAILABLE (web **paused**) | none | 1 / 1 / 3 | silent; the request hung and **completed after the unpause** |
| web **stopped** (not a fault of the spec) | "502" at 0.1 s | 0 / 0 / 2; web back after 8 s | reported; nothing written |
| INFRA_DB_DOWN (db paused) | none | 1 / 1 / 3 | silent; the write **landed after the unpause** |
| APP_WRITE_FAIL (antispam) | **"Post published."** at 0.3 s; form cleared | 0 / 0 / 2 | success claimed for a post that was never stored |
| UE_SESSION_EXPIRED | "401 The access token was revoked" at 0.4 s | 0 / 0 / 2 | reported; nothing written |
| INFRA_STORAGE_FULL (read-only) | "500" at 0.3 s | 0 / 0 / 2 | reported; nothing written |
| INFRA_SIDEKIQ_DEAD (paused) | "Post published." at 1.0 s | 1 / 1 / 3 after the unpause | the home write ran only once Sidekiq came back |

Consequences for the forecast (§13): DB_ABORT's report is a bare "500", which
`el_write_error` (any alert that is not a success toast) counts as a report.
APP_UNAVAILABLE's verdict depends on the mechanism: a paused web process is
silent (FAIL), a stopped one is reported at once (would PASS). Still unconfirmed:
that `/auth/sign_in` shows the form after the session is revoked (the SI's
re-login), and the home read *during* a Sidekiq pause.

### 12.3 The delete under each fault, measured live, 2026-09-29 (`notes/probe_delete_faults.py`, log alongside)

Posts A, B, C made through PostStatusService; the delete of C started in the browser; the fault
armed just before the modal's Delete click (Sidekiq: before the delete starts); alerts polled 15 s;
store read 8 s after the restore (live rows / C live / counter; before: 3 / 1 / 3).

| Fault | Alert within 15 s | C in the open column | Store after restore | Reading |
|---|---|---|---|---|
| DB_ABORT (trigger now also on UPDATE: a delete is a soft delete) | "500" at 0.3 s | still there | 3 / 1 / 3 | reported; nothing moved |
| INFRA_STORAGE_FULL | "500" at 0.6 s | still there | 3 / 1 / 3 | reported; nothing moved |
| UE_SESSION_EXPIRED | "401 The access token was revoked" at 0.3 s | still there | 3 / 1 / 3 | reported; nothing moved |
| APP_UNAVAILABLE (web paused) | none | still there | 2 / 0 / 2 | silent; the delete completed after the unpause |
| INFRA_DB_DOWN (db paused) | none | still there | 2 / 0 / 2 | silent; the delete completed after the unpause |
| INFRA_SIDEKIQ_DEAD | "Post deleted" at 0.3 s | gone | 2 / 0 / 2 once Sidekiq ran | hidden at once; the count drops only when the worker runs |

## 13. Forecast per fault (written before any run; to be copied into `disruption_mapping.yml`)

Obligations the specification will state (final wording in phase B):
O1 a rejected input is reported and nothing is written · O2 a failed write is
reported and nothing is written · O3 a post the user was told succeeded is
what a fresh read shows, on the home timeline and on the profile · O4 the
post count follows the committed rows · O5 an edit the user was told saved is
what a fresh read shows · O6 a deleted post is gone everywhere and the count
follows · O7 a view read without refresh shows the committed value · O8 a
corrupt record is flagged, not rendered as sound · O9 the write completes
when an external lookup fails.

| Fault | Mechanism | Expected | Why (source) |
|---|---|---|---|
| nominal | — | **PASS** | toast, synchronous count, fan-out to `feed:home` within the window |
| UE_KILL | SI: reload right after Post | **PASS** | the request completes; both consistent outcomes are offered |
| UE_CONN_LOST | Chrome offline (CDP) | **PASS** on O2 | network error → "Oops!" alert (`alerts.ts:72-77`); nothing sent |
| UE_SESSION_EXPIRED | delete session + token rows | **PASS** on O2 | 401 → alert with Doorkeeper's message; nothing written |
| APP_WRITE_FAIL | antispam SADD + mention | **FAIL** on O3 | success reported for an unsaved status (`post_status_service.rb:76-77`, `antispam.rb:29`) |
| APP_CACHE_STALE | SQL text change, read without reload | **FAIL** on O7 | the client store is never invalidated without an event (§5) |
| APP_UNAVAILABLE | web stopped (502) | **PASS** on O2 | alert "502"; nothing reaches the server |
| APP_UNAVAILABLE | web paused (hang) | **FAIL** on O2 by quiescence | Caddy's upstream never answers; no alert in the window |
| APP_EXTAPI_FAIL | sidekiq off the external network | **PASS** on O9 | `LinkCrawlWorker` is async and rescues; the post committed before it ran |
| DB_ABORT | BEFORE INSERT trigger | **PASS** on O2 (message text uncertain) | unhandled `StatementInvalid` → 500 → alert; `after_create_commit` never runs, count unchanged |
| DB_CORRUPT | `text = ''` | **FAIL** on O8 | blank text renders as an empty post (`text_formatter.rb:34`); no integrity check on read |
| DB_EVENT_LOSS | `DELETE` the row | **FAIL** on O4 | the post vanishes from every list (default scope), the counter cache still counts it (§7) |
| INFRA_DB_DOWN | pause db across Post | **FAIL** on O2 by quiescence | no statement timeout; the request hangs; the write may land after unpause |
| INFRA_SIDEKIQ_DEAD (post) | pause sidekiq | **FAIL** on O3 | "Post published." but `feed:home` never written (§4.1); profile shows it |
| INFRA_SIDEKIQ_DEAD (delete) | pause sidekiq | **FAIL** on O6 / O4 | hidden at once, count decremented only by the worker (§4.3) |
| INFRA_STORAGE_FULL (analogue) | Postgres read-only | **PASS** on O2 | statement error → 500 → alert; nothing written — if hosted |
| INPUT_INVALID | blank post | **PASS** on O1 | client alert, nothing sent |
| INPUT_OVERLIMIT | 501 characters | **PASS** on O1 | Post withheld, count unchanged |
| domain variants (followers-only, CW) | — | **PASS** | same write path; counted; in home |

Every FAIL above is a forecast, not a result. The verdict is what the
application earns in phase F.
