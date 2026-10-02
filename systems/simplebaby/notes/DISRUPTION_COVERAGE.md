# SimpleBaby — disruption coverage

Every disruption type used so far, and whether SimpleBaby can host it with a
real mechanism. Grounded in `observed_behaviour.md` (section numbers below).
Status: **draft from source (phase A)**. "Mirror" means a mechanism exists;
a type enters the specification only once its inject / restore /
verify_injected / verify_restored work on the device.

Mode: S = signed in (Supabase), G = guest (AsyncStorage).

| Category | Type | Status | Mechanism, or why not | Mode |
|---|---|---|---|---|
| USER | client killed mid-write | mirror | `am force-stop` after "Add to log", relaunch (§4.1) | S, G |
| USER | connectivity lost | mirror | `svc wifi/data disable` (route to 10.0.2.2 to confirm, §11.2) | S |
| USER | session expires | mirror, NOT in the specification | revoking the session works, but the history read-back after it needs a fresh sign-in, which the walk cannot do without changing what it measures. Forecast PASS (O4) | S |
| USER | device storage full | mirror | ballast file on `/data`; only the guest store writes locally | G |
| APP | write fails inside the app | mirror as APP_KEY_LOST | the only app-side step of a save that can fail is encryption, and it fails only through the key: key removed from SecureStore, recreated silently (§4.4). The purpose checks the earlier record (O2) | S, G |
| APP | stale cache / derived view | mirror | zero-row delete (trigger returning NULL); the list is the client's copy (§4.2). There is no query cache | S |
| APP | API unavailable | mirror | stop the PostgREST container behind Kong | S |
| APP | external API fails | mirror, NOT in the specification | stop Storage, save a milestone with a photo; needs the bucket created by hand (live: 0 buckets) and the gallery picker driven, and it re-tests only O4. Forecast PASS | S |
| APP | partial or lazy processing | mirror, data only | photo uploaded, insert aborted: orphan object; the verdict is a plain O4 check | S |
| DB | transaction aborted | mirror | BEFORE INSERT trigger raising on the tracker's table | S |
| DB | record corrupted | mirror as DB_CORRUPT (S) and DB_CORRUPT_LOCAL (G) | S: ciphertext tail overwritten (flagged as "[Decryption Failed]"); G: table JSON corrupted (read as empty, §4.3) | S, G |
| DB | data lost after write | mirror as DB_DATA_LOST | the saved row deleted in Postgres after SAVED_SHOWN; the next history read owes a loss report (O2). The app keeps no local copy (observed_behaviour §7), so the forecast is FAIL. Key loss and the guest table rewrite also lose records | S |
| INFRA | database down | mirror | `docker pause` of the Supabase Postgres container | S |
| INFRA | scheduler / alarm dead (Doze) | partial | no scheduler exists (§8). The analog is the stopwatch tick counter under Doze; to confirm live | S, G |
| INFRA | storage media degraded | mirror | `chmod 000` on the AsyncStorage database, force-stop, relaunch | G |
| INPUT | invalid value | mirror | empty item name or amount (§6) | S, G |
| INPUT | over limit | NOT in the specification | the only limit is the note's 200 characters, enforced by the widget with no message | S, G |
| INPUT | domain variant | mirror | overnight manual sleep, SleepSpan = OVERNIGHT (owed: saved, O7). Future times and free-text amounts are accepted by design and not tested | S, G |
| ENV | sensor taxonomy | not applicable | the app reads no sensor, camera aside (photo picking only) | — |
