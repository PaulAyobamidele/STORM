# Mastodon — how the per-SUT template fitted

Started 2026-09-29 (phase A). One line per template hole (`notes/template_guide.md`,
"Holes, in the order to fill them") and per structural convention: **fitted
as-is**, **adjusted** (how), or **did not fit** (why). Filled in as the phases
proceed; holes not yet reached are marked *pending*.

## Structural conventions

| Convention | Fit | Detail |
|---|---|---|
| five primitives `navigate / tap / enter_text / wait_for / observe` | **adjusted** | web SUT: `navigate / click / type_into / wait_for / observe`, the forms the parser resolves through `selectors:` (`si_lnt_parser.py` paper-style `click` / `type_into` rules). `tap` and `enter_text` are Android-shaped |
| `Ch_Value` for tap / enter_text | **adjusted** | `Ch_Selector` for click, `Ch_TypeIn (Selector, InputValue)` for type_into |
| `SCR_HOME` = the app's home screen with an anchor | **adjusted** | `SCR_HOME` is where the browser sits before login (cookies cleared, nothing of the app on screen); it carries no anchor. The app's home column is a separate screen with its own anchor |
| prelude creates a fresh fixture so no id is captured | **adjusted** | registrations are closed and there is no mail; a fresh account per run is not possible through the UI. The prelude **logs in** as the fixture user `bob`; the fixture is reset between cases by `seed.sh` through the application's own removal service. Every post the walk reads is one the walk wrote, found by its own text, so no id is captured |
| `android:` platform block in `disruption_mapping.yml` | **adjusted** | web `mechanisms:` block (postgres via `docker exec … psql`, redis via `docker exec … redis-cli`, shell); every fault with both probes |
| `.io`: `TAP .*`, `ENTER_TEXT .*` | **adjusted** | `CLICK .*`, `TYPE_INTO .*` |
| DISRUPTOR with an `i` branch | **did not fit** | removed: an internal loop in every composed state makes TESTOR mark every state quiescent (binding rule in `PROMPT_next_session.md`) |
| `Scope` (LOCAL / EXTERNAL read) | **did not fit** | deleted: Mastodon has no external read; its one external dependency (the link preview) is on the write side and is a pre-armed fault |
| `Context` (bucket a write lands in) | **adjusted** | replaced by `Visibility` (PUBLIC / FOLLOWERS), the domain variant; the spec states identical obligations for both |
| SEARCH / INFO read journey | **did not fit** | there is no catalogue to search. Replaced by CHECK (fresh read) and PEEK (read without refresh), both answered by the DATABASE |
| DATABASE without per-record state | **adjusted** | DATABASE tracks which posts exist (`Presence`) and which text each carries (`Versions`), so CHECK after a loss and PEEK after a stale change have a definite answer |
| one fault, one purpose | **adjusted** | the Sidekiq catalogue types are two faults with different mechanisms: INFRA_SIDEKIQ_DEAD (container paused, before a post) and APP_LAZY_PROCESSING (Sidekiq quiet, before a delete) |

## Holes

| n | file | decision | fit |
|---|---|---|---|
| 1 | types | `ItemId` | **adjusted**: post_a..c, posts the walk writes, told apart by fixed texts. Mastodon ships no catalogue, so the "real entries" bullet does not apply |
| 2 | types | `Scope` | **did not fit**: deleted |
| 3 | types | `Context` | **adjusted**: `Visibility` |
| 4 | types | `RecordId` | **fitted as-is**: rec_a..c, one per item |
| 5 | types | `Value` | **adjusted**: V_ORIG / V_EDITED, the text version, not a per-item figure |
| 6 | types | `StateBand` | **fitted as-is**: `CountBand` N0..N_MORE, the profile's "{n} posts", one rung per post |
| 7 | types | `value_of` / `item_of` | **adjusted**: `item_of` kept; `value_of` replaced by the DATABASE's `Versions` state |
| 8 | types | SUT-initiated journeys | **did not fit**: none on the tester's side (the mention notifies alice) |
| 9 | types | `Route` | **fitted as-is**: rt_login, rt_home, rt_profile |
| 10 | types | `Element` | **fitted as-is**: 14 elements, all from `notes/dom/`; oracles are containers (the Home feed, the profile column) so an absent post is a reading, not a timeout |
| 11 | types | `ConcreteValue` | **adjusted**: split as on the web path into `Selector` (click targets) and `InputValue` (typed strings) |
| 12–14 | fixture | defaults | **adjusted**: defaultItem post_c, defaultRecord rec_c, defaultVisibility PUBLIC; no context |
| 15–18 | spec | USER / APP / DATABASE / DISRUPTOR | **adjusted**: five journeys, thirteen faults, obligations O1..O9 in the header; DISRUPTOR without `i` |
| 19 | purposes | one per fault | **adjusted**: 19 purposes generated from one table (`test_purposes/make_purposes.py`): nominal, 13 faults, 3 input variants, nominal edit and delete. Negative closure is computed: every unused fault and input variant is refused, and each phase of a multi-phase purpose refuses the other phases' inputs. The template's `tp_infra_storage_media` was removed (no such fault here) |
| 20 | .io | patterns | **fitted as-is**: web primitives, five abstract requests, thirteen exact fault names |
| 21 | script | purpose list | **fitted as-is**: the 19 names |
| 22–26 | SI | screens, search, value location, return-home, refusal | **adjusted**: screens SCR_HOME (pre-login), SCR_TIMELINE, SCR_PROFILE; no search; the value is read from the Home feed; every write's read-back ends on a fresh /home; refusal: blank = client alert, over-limit = Post button withheld |
| 27–30 | concrete_domain | routes, elements, values, anchors | **fitted as-is**: all from the live dumps; SCR_HOME unanchored by design |
| 31–33 | type_description | enums, authoritative values, band unit | **adjusted**: no authoritative per-item figure (Mastodon has no catalogue); four read-back types with roles: CountBand `band` (unit 1), HomeState and ProfileState `names`, Value `enum` |
| 34–37 | disruption_mapping | platform, faults, cache, expectations | **adjusted**: web `mechanisms:` (postgres argv, shell for everything else: redis-cli must not receive its command as one argument); all twelve injected faults with both probes, proven live; the stale-view fault targets the browser's store, not a server cache; forecasts copied into the header |

## Framework changes this case study needed (config-driven, SUT-agnostic, self-tested)

| Need | Why | Proposed hook |
|---|---|---|
| a typed value from the environment | the fixture password must not live in the repo | **done**: `"@env:NAME"` in `_materialise_value` (algorithm.py); self-test `framework/tests/test_env_value_and_insecure_certs.py` |
| a browser that accepts a local CA | the app answers only on `https://mastodon.localhost` behind Caddy's internal CA | **done**: `browser.accept_insecure_certs` in concrete_domain.yml, read by the web executor, off by default, logged when on; same self-test |
| a gate with only a `wait_for` | the parser's invariant rejects it | not a framework change: PEEK and CHECK carry a harmless click on the Home column title |

The framework suite has the same 7 failures before and after these changes (stale expectations about other case studies' files; not touched).

alphabet check 2026-09-29: 0 FAIL, 6 warn (five pre-armed faults end a phase and are followed by `by`, not `;`, which the checker's heuristic does not see; SCR_HOME unanchored by design).

### Widened suite, 2026-09-29

One happy path H (post A, B, C; read without refresh; fresh check; delete C) and 15
disruptions of it, each allowed to strike at every step where the specification states
what is owed: 16 purposes, 44 strike points, one generated case per point. To get there:
the SI's post branches choose a not-yet-written post (A, B or C) instead of pinning
defaultItem; the delete branch has five fault arms before the confirm click and a
Sidekiq-before-delete branch; the specification states what a failed delete owes (O2) and
makes the stale-view and loss faults strike the newest committed post (a parameterless fault
choosing "any existing post" would have let a stale C pass as "the change hit A");
DB_ABORT's trigger also fires on UPDATE (a delete is a soft delete); the antispam entry is
"ioco note", common to every fixture text. Purposes are generated with explicit per-point
refusals, not per-phase disrupts, so the nested strike points stay deterministic.

### The suite grows in extraction, not in purposes (2026-09-29/30)

16 purposes: the happy path and 15 disruptions of it. The number of test cases is what
TESTOR's extract_all resolves from the choices a purpose leaves the tester, as in FoodYou.
Two conservative loosenings give it those choices: a disruption may strike at any step
where the specification states what is owed, and the two reads of H (read without
refresh, fresh check) may come in either order. Target: more than 50 and fewer than 100
cases in all. A split into one file per strike point (tp_<fault>_p<k>, 44 files) was tried
and withdrawn: it grew the number of purposes, which is not what was wanted.
