# SimpleBaby — Observed Behaviour (ground truth for the behavioural model)

Written 2026-09-29. Source: the clone at `systems/simplebaby/sut/simplebaby`
(remote `adulbrich/SimpleBaby`, commit `a46e3cf`, 2026-06-04). Everything below
was established by READING THE SOURCE. Nothing has been run against a live
instance yet; §11 lists what must be confirmed live before it is relied on.

Evidence marks: `file:line` means those lines were read. `✓` means re-checked
against the file while writing this note. Paths are relative to the clone.

---

## 1. What SimpleBaby is

A mobile baby tracker: a parent records feedings, sleep, diapers, nursing,
health events and milestones for one or more children. React Native 0.81 on
Expo SDK 54 with Expo Router (`package.json` ✓), NativeWind styling. The
backend is Supabase (Postgres 17 behind the Kong gateway, GoTrue auth,
PostgREST, Storage), run locally by the Supabase CLI (`supabase/config.toml`:
API 54321, DB 54322, `enable_confirmations = false` at :176 ✓).

**Platform: Android** (Appium + UiAutomator2 + emulator). The app is written
for a phone: native date/time pickers (`DateTimePickerAndroid.open`, e.g.
`components/feeding-category.tsx:57-67` ✓), native `Alert` dialogs for every
report, `expo-secure-store` for the key. A web target exists in `package.json`
but SecureStore and the native pickers have no web implementation, so it is
not the app's real platform.

### 1.1 Two modes, two stores

| Mode | Entered by | Store | Code |
|---|---|---|---|
| Signed in | Sign Up / Sign In | Supabase tables, one per tracker | `library/log-functions.ts:116-165` ✓ |
| Guest | "Try as Guest" → Continue | AsyncStorage keys `sb:table:<name>`, each a JSON array | `library/local-store.ts:16-22, 152-176` ✓ |

`saveLog` picks the store from `isGuest` (`log-functions.ts:206-212` ✓). The
two modes share every screen; they differ in their write path, their failure
behaviour (§5) and one screen: the Calendar says "This feature is not
supported in Guest Mode" (`app/(modals)/calendar.tsx:97-108` ✓).

### 1.2 End-to-end encryption

Every free-text or category field is encrypted on the device before it is
stored, in both modes (`log-functions.ts:169-178` ✓: type `string` →
`encryptData`; `date`, `unencrypted`, `photo` are stored as-is).

- The key is 32 random bytes in SecureStore under `ENCRYPTION_KEY`, **created
  silently when absent** (`library/supabase-client.ts:79-98` ✓). It never
  leaves the device.
- `encryptData` prepends a hex IV and calls CryptoES AES with a SHA-256 of the
  key as a string (`library/crypto.ts:18-47` ✓). The stored value contains
  the OpenSSL marker `U2FsdGVkX1`, which `safeDecrypt` uses to decide whether
  a value is encrypted (`crypto.ts:73-74` ✓). (Whether CryptoES then ignores
  the passed IV because a string key selects passphrase mode does not change
  any behaviour below; not examined further.)
- `safeDecrypt` never throws. A value without the marker is returned as
  plain text; a value with the marker that fails to decrypt comes back as the
  string `"[Decryption Failed]: ❌ Decryption failed"`
  (`crypto.ts:75-80` ✓, `assets/stringLibrary.json` `errors.decryption` ✓).
  That string is then rendered as the field's value.

Consequence for the tester: Postgres holds ciphertext, so an SQL read-back
of what the store holds can count rows and read dates, never the values.

---

## 2. Schema (signed-in store)

`supabase/migrations/20251101234414_init_all_tables.sql` ✓, amended by
`20260121071904_remote_schema.sql` ✓.

| Table | Fields that matter | Constraints |
|---|---|---|
| `children` (:5-10) | `id`, `user_id` → `auth.users` CASCADE (:158), `name` (ciphertext) | RLS: own rows only (:501-531) |
| `feeding_logs` (:29-39) | `child_id` → children CASCADE (:166), `category`, `item_name`, `amount`, `note` (ciphertext), `feeding_time` (clear), `created_at` | RLS via child (:577-614) |
| `diaper_logs` (:15-24) | `consistency`, `amount` (ciphertext), `change_time` | RLS via child |
| `sleep_logs` (:97-107) | `start_time`, `end_time`, `duration` (clear text "HH:MM:SS"), `note` | `CHECK (end_time > start_time)` (:190) |
| `nursing_logs` (:81-92) | four durations/amounts (ciphertext), `logged_at` | — |
| `health_logs` (:44-60 + remote_schema :13-21) | `category` enum Growth/Activity/Meds/Vaccine/Other (clear), per-category ciphertext fields, `date` | category CHECK (remote_schema :21) |
| `milestone_logs` (:65-76) | `title` (ciphertext), `category` enum (clear), `achieved_at`, `photo_url` | — |

No foreign key is enforced from the app side on the child: `child_id` comes
from the user's metadata `activeChildId` (`library/remote-store.ts:27-45` ✓).
The storage bucket `milestone-photos` has policies
(`20260127054220_remote_schema.sql:1-25` ✓) but **no migration creates the
bucket**, and `config.toml` declares none (:112-113 are commented out ✓).
`config.toml:63` names `./seed.sql`, which does not exist in the repository ✓.

---

## 3. Journeys

Routes (Expo Router, `app/`): the welcome screen `index.tsx`; `(auth)/signin`,
`signup`, `guest`; tabs `(tabs)/index` (six tracker buttons), `logs` (six
history buttons), `about`, `settings`; trackers `(trackers)/<name>`; histories
`(logs)/<name>-logs`; modals `profile`, `active-child`, `calendar`, `tos`,
`privacy-policy`.

**First run.** Sign-up signs in immediately (`(auth)/signup.tsx:59-85` ✓;
confirmations off). The Trackers tab then shows the "Welcome to SimpleBaby /
Please add your first child's name" popup whenever the session metadata has
no active child (`(tabs)/index.tsx:90-117` ✓). Saving a child encrypts the
name, inserts it and writes `activeChildId` into the user metadata
(`remote-store.ts:87-131` ✓). Duplicate names are refused
("Child name already exists.", :104-106).

**Guest relaunch.** `index.tsx:15-20` ✓ redirects to the tabs only when there
is a Supabase **session**. A guest who relaunches the app lands on the welcome
screen again and must tap "Try as Guest" → Continue; the guest id and data are
kept (`local-store.ts:61-68` ✓). A signed-in user is restored from the
persisted session and redirected.

**Record a log** (every tracker has the same shape; feeding is quoted):
fill the form → "Add to log" → client validation (§6) → `saveLog` → on
success `router.dismissTo("/(tabs)")` and the native alert "Feeding log saved
successfully!"; on failure the alert "Failed to save feeding log: <error>"
and the form stays (`(trackers)/feeding.tsx:62-105` ✓). Double submission is
blocked by `isSaving` (:63-64 ✓).

**Read the history.** Logs tab → e.g. "Feeding Logs" → a list, newest first,
each card showing date, time, "Category: …", "Item: …", "Amount: …", and the
note (`(logs)/feeding-logs.tsx:122-146` ✓). Empty: "You don't have any
feeding logs for <child> yet!" (:155-159). Read error: "Error: <message>"
with testID `feeding-logs-loading-error` (:154).

**Edit / delete a log.** Each card has Edit and Delete
(`components/log-item.tsx:97-114` ✓). Delete asks "Are you sure you want to
delete this log?" (`log-functions.ts:333-336` ✓).

**Calendar** (signed in only): a month with a dot on each day that has any
log, and the day's logs of all six kinds below it (`library/calendar.ts`,
`app/(modals)/calendar.tsx` ✓).

**Profile / children.** Add, switch, rename, delete children (signed in);
guest mode shows the guest child only (`app/(modals)/profile.tsx` ✓).

---

## 4. Write paths

| Write | Code | Statements | Reported on failure? |
|---|---|---|---|
| create log, signed in | `log-functions.ts:116-165` ✓ | (1) `auth.getUser()` over the network, (2) `children` select for the active child, decrypt its name, (3) optional photo uploads, (4) one `insert` | yes, alert with the error text (`feeding.tsx:101-103`) |
| create log, guest | `log-functions.ts:91-112`, `local-store.ts:152-176` ✓ | read the whole table key, push, write the whole key back | yes, "Failed to save feeding log locally." |
| edit log, signed in | `feeding-logs.tsx:72-116` ✓ | one `update … eq(id)`, then a re-fetch | only if PostgREST returns an error |
| edit log, guest | same file, `local-store.ts:188-210` ✓ | read-modify-write of the whole key | yes ("Failed to update log") |
| delete log, signed in | `log-functions.ts:313-330` ✓ | one `delete … eq(id)` | only if PostgREST returns an error |
| delete log, guest | `local-store.ts:214-234` ✓ | read-modify-write | yes ("Error deleting log") |

Facts to carry into the specification:

1. **A single insert per log.** The signed-in create is one statement, so a
   write lands whole or not at all. There is no activity log or second table
   that could disagree with it.
2. **Delete and edit trust "no error" as success.** Signed in, a `delete` or
   `update` that matches zero rows returns no error from PostgREST (RLS
   filtering, or a trigger that cancels the row). The delete path then
   removes the card from the list **from the client's own copy**
   (`log-functions.ts:323-324` ✓: `updateLogs(prev => prev.filter(...))`),
   never re-reading the store. The edit path re-fetches (`feeding-logs.tsx:109`
   ✓), so a silently cancelled edit shows the old values with no message.
3. **Guest writes rewrite the whole table.** `insertRow` reads the array with
   `getJson`, which **returns `[]` on any read or parse error**
   (`local-store.ts:43-51` ✓), then writes back that array plus the new row
   (:158-167). A table key that cannot be read or parsed is therefore
   replaced by a one-row array on the next save: every earlier log of that
   kind is gone, and the save is reported as a success.
4. **The key is recreated silently.** If `ENCRYPTION_KEY` is missing from
   SecureStore, a new one is generated (`supabase-client.ts:92-97` ✓). Every
   record written under the old key then renders as
   "[Decryption Failed]: ❌ Decryption failed", and the active child's name
   fails to decrypt, which makes `getActiveChildData` return
   "Could not decrypt child name." (`remote-store.ts:53-60` ✓), so no new
   log can be saved either (the save reports that error).
5. **Photo then row.** A milestone with a photo uploads first and inserts
   after (`log-functions.ts:139-157` ✓). An upload failure is reported
   ("Photo upload failed"); an insert failure after a successful upload
   leaves an orphan object in Storage.

---

## 5. What the UI shows on failure

Every tracker save that returns `{success:false}` raises a native alert
whose title is "Failed to save <kind> log: <error>" (feeding, sleep, diaper,
nursing, milestone) or "Error / Failed to save health log: …" (health,
`(trackers)/health.tsx:147-157` ✓). **A failed create is reported**, in both
modes, as long as the failure surfaces as an error. Three ways it does not:

- **A request that never answers.** supabase-js sets no request timeout
  (`createClient` options, `supabase-client.ts:122-129` ✓: none), so a
  gateway or database that holds the connection open leaves the button
  disabled (`isSaving`) and shows nothing until the socket gives up. For the
  tester this is quiescence.
- **Zero-row edits and deletes** (§4, fact 2): no error, so no report, and
  for delete a list that no longer matches the store.
- **Guest reads that fail** (§4, fact 3): `listRows` → `getJson` → `[]`, so
  the history shows the empty-state sentence instead of an error
  (`local-store.ts:180-184` ✓, `feeding-logs.tsx:155-159`). The signed-in
  read path, in contrast, shows "Error: <message>" (`log-functions.ts:299-302`
  ✓, `feeding-logs.tsx:154`).

Sign-in failure shows "Sign In Error" with the server's message
(`(auth)/signin.tsx:36-40` ✓).

---

## 6. Validation: client only

Each tracker has a `checkInputs` that raises the alert "Missing Information"
with a sentence naming the missing fields (`stringLibrary.json`
`errors.trackerMissingInfo` ✓):

| Tracker | Rejected | Code |
|---|---|---|
| Feeding | empty item name, empty amount | `feeding.tsx:40-59` ✓ |
| Sleep | no stopwatch time AND start ≥ end | `sleep.tsx:67-82` ✓ |
| Diaper | none reachable (both choices have defaults) | `diaper.tsx:41-59` ✓ |
| Nursing | all four fields zero/empty | `nursing.tsx:39-56` ✓ |
| Health | the category's fields, e.g. all three Growth fields | `health.tsx:53-96` ✓ |
| Milestone | empty name | `milestone.tsx:110-128` ✓ |

What is NOT validated anywhere: the **content** of free-text amounts ("abc",
"-5", ten thousand characters are all accepted; the columns are `text`),
and **times in the future** (a feeding or diaper time later today is
accepted; there is no check in the tracker or the schema). The note field
has `maxLength={200}` (`components/note-entry.tsx:33` ✓): typing stops at
200 characters, with no message.

**Overnight sleep cannot be entered manually.** The manual pickers are
`mode: 'time'` on two dates that both start as "now"
(`sleep.tsx:26-27` ✓, `components/sleep-manual-entry.tsx:46-67` ✓), so
22:00 → 06:00 is start > end on the same day and is rejected with
"Please provide either a stopwatch time or valid manual start and end
times." A valid real-world input is refused.

The server re-checks only two things: `sleep_logs` end > start (:190) and the
health category rule (remote_schema :21), which is weaker than the client's
(Growth needs one of three fields on the server, all three on the client).

---

## 7. Derived views and caches

There are **no totals, charts or summaries** in the source; the About page's
"insights into developmental trends" has no code behind it. The derived
views are:

| View | Computed from | Freshness |
|---|---|---|
| History list per tracker | `fetchLogs` on mount (`feeding-logs.tsx:68-70` ✓), decrypted per field | fresh on every visit; not refreshed on focus; after **delete** it is the client's filtered copy (§4 fact 2) |
| Calendar day list | six queries for the local day window (`calendar.ts:17-153` ✓) | fetched on each day change |
| Calendar month dots | six queries for the month (`calendar.ts:155-220` ✓) | fetched on each month change |
| Empty-state sentence | the list length and the child name | same as the list |
| "Active child" everywhere | `auth.getUser()` metadata, fetched per call (`remote-store.ts:19-45` ✓) | fresh |

No query cache, no React Query, no local mirror of the remote store in
signed-in mode. The one place a view does not follow the store is the list
after a delete.

---

## 8. Timers and schedulers

- **No scheduler, no reminders, no notifications.** No `expo-notifications`
  or background-task dependency (`package.json` ✓), no alarm code.
- **The two stopwatches are in-memory counters.** `Stopwatch` adds 1 to the
  elapsed seconds on every `setInterval` tick (`components/stopwatch.tsx:25-34`
  ✓); the nursing stopwatch does the same per side
  (`components/nursing-stopwatch.tsx:33-54` ✓). Elapsed time is the number
  of ticks that ran, not the difference of two wall-clock times, and it is
  held only in the screen's state: leaving the screen or killing the app
  loses it with no warning. Whenever the JS timers are held back (the app in
  the background under Doze, a paused process) the stopwatch under-counts,
  and the sleep log it produces is dated from "now minus the counted
  seconds" (`sleep.tsx:40-44` ✓), so both its start and its duration are
  wrong. Whether Android holds the timers back for a backgrounded Expo app is
  a live question (§11).

---

## 9. Logs versus data

There is no application log or audit table. `console.log` prints every
ciphertext and every decrypted value (`crypto.ts:45, 67` ✓) to the device
log, which is a privacy observation, not an observable for the tester.

---

## 10. Disruptions the source admits, and the forecast

Obligations the forecast is written against (the specification header will
state them):

- **O1** a rejected input is reported.
- **O2** a record the user was told was saved is what the history then shows
  (present, and readable).
- **O3** the history follows the committed records (after a delete or an
  edit, the list shows what the store holds).
- **O4** a failed save is reported.
- **O5** a corrupt record is flagged, not shown as sound.
- **O6** a timer that could not run is visible (the stopwatch does not
  silently under-count).

| Fault (catalogue type) | Mechanism | Mode | Forecast | Why |
|---|---|---|---|---|
| UE_KILL (client killed mid-write) | `am force-stop` right after "Add to log", relaunch | both | **PASS** (consistent) | one insert, whole or nothing (§4.1); the guest relaunch lands on the welcome screen, the data survives |
| UE_OFFLINE (connectivity lost) | `svc wifi disable; svc data disable` before the tap | signed in | **PASS** (O4) | fetch fails fast, supabase-js returns the error, the alert shows it (§5); message may read "No authenticated user found" |
| UE_SESSION_EXPIRED | delete the user's rows in `auth.sessions` / refresh tokens | signed in | **PASS** (O4), to confirm | `getUser` fails, the save reports the error; the session may be dropped mid-screen |
| UE_STORAGE_FULL (device storage full) | ballast file on `/data` | guest | **PASS** (O4) | AsyncStorage write rejects, `insertRow` returns false, reported |
| APP_WRITE_FAIL (write fails inside the app) | the encryption key removed from SecureStore | signed in | **FAIL** (O2) | the key is recreated silently (§4.4); earlier records render "[Decryption Failed]" and new saves fail on the child name |
| APP_CACHE_STALE (derived view stale) | BEFORE DELETE trigger that returns NULL (the row stays, no error) | signed in | **FAIL** (O3) | the list drops the card from its own copy (§4.2); reopening shows the log again, nothing said |
| APP_UNAVAILABLE (API unavailable) | stop the PostgREST container behind Kong | signed in | **PASS** (O4) | Kong answers an error status at once; the insert returns it; reported |
| APP_EXTAPI_FAIL (external API fails) | stop the Storage container, save a milestone with a photo | signed in | **PASS** (O4) | "Photo upload failed" is reported; costly to drive (gallery picker) |
| APP_PARTIAL (partial processing) | photo uploads, then the insert aborts | signed in | **PASS** on the verdict, orphan object in the data | reported, but Storage keeps the file; a data finding, not a verdict |
| DB_ABORT (transaction aborted) | BEFORE INSERT trigger raising on `feeding_logs` | signed in | **PASS** (O4) | PostgREST returns the exception; the alert names it |
| DB_CORRUPT (record corrupted) | overwrite a stored ciphertext's tail, keeping the marker | signed in | **PASS** (O5) | the history shows "[Decryption Failed]: …" in that field; flagged, though crudely |
| DB_CORRUPT, guest variant | corrupt the `sb:table:feeding_logs` JSON in RKStorage | guest | **FAIL** (O5, then O2) | the read returns `[]`: the empty-state sentence, no flag; the next save wipes every earlier log (§4.3) |
| DB_DATA_LOST (lost after write) | covered by the two rows above (key loss; guest table rewrite) | — | FAIL | — |
| INFRA_DB_DOWN (database down) | `docker pause` the Postgres container across the tap | signed in | **FAIL** (O4) | the request hangs with no client timeout; silence in the window (§5) |
| INFRA_DOZE (scheduler dead) | start the sleep stopwatch, background the app, `dumpsys deviceidle force-idle`, return | both | **FAIL** (O6), to confirm | tick counter, not wall clock (§8) |
| INFRA_STORAGE_MEDIA (media degraded) | `chmod 000` the AsyncStorage database, force-stop, relaunch | guest | **FAIL** (O5) | reads fail into `[]`, the history looks empty (§5) |
| INPUT_INVALID | empty item name / empty amount | both | **PASS** (O1) | "Missing Information" alert (§6) |
| INPUT_OVERLIMIT | note of 250 characters | both | unknown | typing stops at 200 with no message; whether that is a report depends on what the SI can observe |
| INPUT_OVERNIGHT (domain variant) | manual sleep 22:00 → 06:00 | both | **FAIL** (O1 inverted: a valid input refused) | same-day time pickers (§6) |
| INPUT_FUTURE (domain variant) | feeding time later today | both | PASS only if the spec allows future times | nothing rejects it; the spec must decide, not the tester |
| ENV (sensors) | — | — | not applicable | the app reads no sensor |

---

## 10a. Confirmed live (2026-09-29, emulator simplebaby_test, notes/ui/)

| Prediction | Seen | Dump |
|---|---|---|
| a saved feeding is reported | alert title "Feeding log saved successfully!", button OK | 10 |
| the history names the item | card "Item: Apple sauce", list id `feeding-logs` | 13 |
| the store holds ciphertext | `item_name` begins with the IV hex then `U2FsdGVk` | db |
| an empty amount is refused | "Missing Information" / "…missing the following fields: amount." | 14 |
| delete asks, then empties the list | "Delete Entry" CANCEL / DELETE; "You don't have any feeding logs for Robin yet!" | 15, 16 |
| a same-day manual sleep saves | "Sleep log saved successfully!"; row 12:00–13:00 UTC, "01:00:00" | 25 |
| an overnight manual sleep is refused | 10:00 PM → 6:00 AM: "…Please provide either a stopwatch time or valid manual start and end times."; 0 rows | 23, 24 |
| the stopwatch under-counts in the background | 62 s wall clock, reads 00:00:05 | 26, 27 |
| guest mode writes to the device store | `catalystLocalStorage` in `databases/RKStorage`: keys `sb:isGuest`, `sb:guestId`, `sb:children`, `sb:activeChildId`, `sb:table:feeding_logs` (a JSON array) | 32, 33, db |
| a guest relaunch lands on the welcome screen | after terminate + activate: Sign In / Sign Up / Try as Guest | 35 |
| the device key is one SecureStore entry | `shared_prefs/SecureStore.xml`, entry `key_v1-ENCRYPTION_KEY` (read as root) | — |

Alert titles carry the app's own id `com.anonymous.bt_sdk53:id/alert_title`,
messages `android:id/message`. The history shows no card count anywhere and
no node carries the list's text, so the history is read from the first
"Item:" line or the empty-state sentence.

Apparatus, not the app: a release build refuses plain HTTP (targetSdk 36;
the debug manifest alone sets `usesCleartextTraffic`), so sign-up failed with
"Network request failed" against `http://10.0.2.2:54321` (2026-10-01, first
nominal walk, no verdict). The local test backend is HTTP, so the release
manifest of the clone (`android/app/src/main/AndroidManifest.xml`, ignored
by git, generated by prebuild) now sets `android:usesCleartextTraffic="true"`.
Not a finding about SimpleBaby; it changes how the tester reaches the backend,
not what the app does with a response.

The dev build shows a LogBox banner over the bottom
of the screen (it covers "Try as Guest", "Continue" and "Sign Out"), and a
cleared dev build opens the Expo dev launcher instead of the app. The emulator
image allows `adb root`, so a release build (no LogBox, no Metro, bundle
embedded) keeps every injection path while removing both.

## 11. To confirm live

1. The Android package name: prebuild chose `com.anonymous.bt_sdk53`
   (`android/app/build.gradle:90-92`, 2026-09-29). Confirmed live the same
   day: the build is DEBUGGABLE and `run-as` lists `databases/RKStorage`,
   `files/`, `shared_prefs/`.
2. ~~That the emulator reaches Supabase at `10.0.2.2:54321`.~~ Confirmed:
   sign-up, the first child and a feeding all landed in the local store.
   Still to confirm: that `svc wifi/data disable` cuts that route.
3. The failure alert texts for DB_ABORT, APP_UNAVAILABLE and UE_OFFLINE, and
   whether they are the native `android:id/alertTitle` / `message` nodes.
4. Whether a paused Postgres makes the save hang past the tester's window,
   or Kong / PostgREST answers first.
5. That a zero-row delete returns no error and the card disappears (the
   trigger returning NULL), and that reopening the history shows it again.
6. The rendered "[Decryption Failed]: ❌ Decryption failed" on a corrupted
   ciphertext, and where on the card it appears.
7. ~~AsyncStorage's on-device file.~~ `databases/RKStorage` confirmed. Still
   to confirm: that
   corrupting the JSON value produces the empty-state sentence, then the
   wipe on the next save.
8. ~~Whether the stopwatch under-counts in the background.~~ Confirmed
   2026-09-29 (notes/ui/26, 27): started, app sent HOME, 60 s, app back.
   Wall clock 62 s; the stopwatch read 00:00:05 both with a forced Doze
   (`dumpsys deviceidle force-idle`) and with no Doze at all. The JS timer
   does not run while the app is in the background, so Doze is not needed
   for the fault to bite; INFRA_DOZE keeps the Doze injection as the
   catalogue's mechanism, and the note says plain backgrounding does the same.
9. The session-expiry mechanism: which GoTrue table removal makes `getUser`
   fail for a live access token.
10. ~~That the milestone photo bucket must be created by hand.~~ Confirmed
    2026-09-29 on the local stack: `storage.buckets` holds 0 rows after the
    three migrations. The seven public tables exist, and an anonymous REST
    read of `feeding_logs` through Kong returns `[]` with HTTP 200 (RLS).
