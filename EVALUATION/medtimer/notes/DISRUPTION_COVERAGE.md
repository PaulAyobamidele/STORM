# MedTimer — Disruption coverage

First draft, 2026-09-28, phase A. One row per disruption TYPE used in the
earlier case studies (the catalogue the study set out to mirror). Each row is
either **mirrored** (a real inject / restore mechanism exists on the emulator
and the fault will be in the specification, the System Interface, the
composition, every purpose, the `.io` and `disruption_mapping.yml`) or
**noted** (no analogue or no honest mechanism here; the reason, and the nearest
MedTimer-specific fault, are given). Mechanisms are stated from the source
reading in `observed_behaviour.md` and become binding only once
`check_faults` has shown each one bites and lets go on the device (phase D).

Gate names follow `<LAYER>_<WHAT>`; observables owed after a fault would be
`<STEM>_DETECTED | _WARNING | _ERROR`. Because MedTimer reports nothing on a
failed write (note §5), the observable owed by the write-failure faults is the
same `WRITE_ERROR_SHOWN`, expected absent, which is the point.

| # | category / type | MedTimer decision | mechanism (inject → verify → restore) | expected |
|---|---|---|---|---|
| 1 | USER: client killed / leaves mid-write | **mirrored** `UE_KILL` | `am force-stop com.futsch1.medtimer` right after the Taken tap, then `am start -n com.futsch1.medtimer/.MainActivity`; verify: `pidof` absent then present; restore = the relaunch | PASS likely (window not reachable deterministically; note §13) |
| 2 | USER: connectivity lost | **noted** | no network permission at all (`AndroidManifest.xml:12-17`): nothing to cut, nothing that would notice. Nearest MedTimer fault: none; the app is offline by design | — |
| 3 | USER: session expires | **noted** | no accounts, no sessions, no login. Nearest: the optional biometric lock (`appAuthentication`, off by default), which is an app gate, not a session | — |
| 4 | USER / INFRA: device storage full | **mirrored** `INFRA_STORAGE_FULL` | `run-as` ballast file in `files/` written with `dd` until ENOSPC (any headroom lets a 4 KB SQLite page through), armed at the `gate`, which the SI places before the commit tap; verify: `df` shows 0 available; restore: `rm` the ballast. Proved on the device 2026-09-29: 6 s to fill, 0 available, a SQLite write fails with "database or disk is full (13)", restore returns 4.7 GB and the app process survives | FAIL (SQLITE_FULL → crash, no report) |
| 5 | APP: write fails inside the app | **mirrored** `APP_WRITE_FAIL` | `run-as … sqlite3 databases/medTimer "CREATE TRIGGER fault_event_update BEFORE UPDATE ON ReminderEvent BEGIN SELECT RAISE(ABORT,'…'); END"`, armed at the `gate` before the commit tap (a `pre` arming would break the prelude, which creates the fixture inside the walk); verify: the trigger's name reads back from `sqlite_master`; restore: `DROP TRIGGER` | FAIL (stock moved, event RAISED, crash) |
| 6 | APP: stale cache / derived view | **mirrored** `APP_CACHE_STALE`, SI-driven (`timing: none`) | no cache exists (note §6.1); the honest reading of "stale derived view" here is cross-tab consistency: prime the Medicine tab (read the stock), take a dose on the overview, return to the Medicine tab and read the stock again without relaunching; the fault gate marks the priming visit | PASS expected (reactive flows); the scheduled-row duplicate (note §6.2) is the one place a stale view is possible and is checked on the overview itself |
| 7 | APP: unavailable / request never reaches the server | **noted** | no server, no request; the write is an in-process Room call. Nearest: `APP_WRITE_FAIL` (row 5), which is what "the request failed" reduces to in a local-only app | — |
| 8 | APP: external API fails | **noted** | fully offline, no external source (note §11). Nearest: none | — |
| 9 | APP: partial / lazy processing | **mirrored as a parameter-borne variant** `MANUAL_DOSE` (candidate) and covered by row 5 | the manual dose is two independent writes (event insert + stock broadcast, note §4.6): a kill between them (row 1 on that journey) or a trigger on `Medicine` update leaves the event without its stock effect. The notification path's "posted but not written" cannot happen: the event is inserted before the notification (note §7.1) | FAIL if the journey is included; decide in phase B whether the manual-dose journey is in scope |
| 10 | DB: transaction aborted | **mirrored** `DB_ABORT` | `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` trigger, armed at the `gate` before the commit tap of the scheduled-take journey (the insert is its first write, note §4.2); verify / restore as row 5 | FAIL (crash, no report; state consistent) |
| 11 | DB: record corrupted | **mirrored** `DB_CORRUPT` | after the take, `UPDATE ReminderEvent SET status='BOGUS' WHERE reminderEventId=(SELECT max(reminderEventId) FROM ReminderEvent)` (Room's enum read then throws), or `UPDATE Medicine SET amount=NULL` (NOT NULL column: use the enum route); verify: `SELECT status …` = BOGUS; restore: set it back to the value read before | FAIL (crash on read, nothing flagged) |
| 12 | DB: data loss after write | **mirrored** `DB_EVENT_LOSS` (candidate) | after CONFIRM, `DELETE FROM ReminderEvent WHERE reminderEventId=…` then re-read the overview and the stock; the stock stays decremented while the history has no dose | FAIL against O5 (stock drifts from events) — include only if it adds to row 11; decide in phase B |
| 13 | INFRA: database down | **mirrored** `INFRA_STORAGE_MEDIA` (see row 15); a "down" local store is an unreadable file | — | — |
| 14 | INFRA: scheduler dead | **noted, with a partial mirror** | alarms are `AllowWhileIdle` (note §7.3), so `dumpsys deviceidle force-idle` does not stop them and exact alarms are off by default; the tester-driven journeys never use the alarm. A mirror would need a notification journey (reminder due in +N min, force-idle, wait) and is slow and inexact. Nearest: rows 1 and 15, which kill or starve the process that would fire it | PASS by API choice if ever run |
| 15 | INFRA: storage media degraded | **mirrored** `INFRA_STORAGE_MEDIA` | `run-as … chmod 0000 databases/medTimer` (and `-wal`, `-shm`), `am force-stop`, relaunch; verify: `stat -c %a` = 0; restore: `chmod 660` (mode read before the first run), force-stop, relaunch | FAIL (crash at first query) (a walk that never reaches the screen is walked again, not counted) |
| 16 | INPUT: invalid value | **mirrored** `INPUT_INVALID` (`timing: none`) | the SI types an empty medicine name (accepted, note §4.8) or a non-numeric dose (accepted with a warning); negative or textual stock is unreachable (deleted as typed). Choose one in phase B; the empty name is the sharper case | FAIL (empty name accepted) |
| 17 | INPUT: over limit | **deferred** (decided 2026-09-28 in phase B) | a dose larger than the stock is clamped to 0 silently (note §8.1). The fixture's dose is the band's unit, so realising "over limit" needs either a second reminder with a larger dose in every prelude or a mid-journey stock edit with no gate to anchor it; neither is cheap or clean for the first sweep. Candidate for a second sweep as `INPUT_OVERLIMIT` (`timing: none`) with a second fixture reminder | FAIL expected when run |
| 18 | INPUT: domain variant | **mirrored** as parameter-borne variants (decided 2026-09-28) | `CANNOT_SKIP` (the cannot-be-skipped switch is set through the medicine settings, then the dose is skipped from the overview, note §9); `DELETE_SKIPPED` (a skipped event deleted: stock refunded, note §4.4); `EDIT_FLIP` (edit-sheet Skipped → Taken: no stock change, note §4.5). `EXPIRED` (a dose of an expired medicine recorded with no flag, note §10) is NOT an obligation: the card carries an expiry icon and flagging at the point of action is a design preference; recorded as an observation only | FAIL each, source-proven |
| 19 | SENSOR / ENV family (sensor timeout, sensor noise, environment obstacle, …) | **noted** | no sensors and no environment model; the only environmental input is the clock. Nearest: a clock jump (`date` / `TIMEZONE_CHANGED`, `TimeChangeReceiver`) which re-schedules but changes no recorded fact; not adopted | — |

## What this table commits to for phase B

Decided with the user on 2026-09-28. Fault gates in the specification (each
with a mechanism above): `UE_KILL`, `APP_WRITE_FAIL`, `DB_ABORT`,
`DB_CORRUPT`, `DB_EVENT_LOSS`, `INFRA_STORAGE_FULL`, `INFRA_STORAGE_MEDIA`,
`APP_CACHE_STALE` (SI-driven). Parameter-borne (no gate, `timing: none`):
`INPUT_INVALID` (the empty medicine name), and the domain variants
`CANNOT_SKIP`, `DELETE_SKIPPED`, `EDIT_FLIP`. Out for the first sweep:
`INPUT_OVERLIMIT` (row 17, deferred), the manual-dose journey (row 9, noted;
revisit if the first sweep finishes early), the notification journey (row 14,
noted), `EXPIRED` as an obligation (row 18, observation only).

Noted, with reasons: connectivity, session, server-unavailable, external API,
scheduler-dead (partial), sensor / environment.

## Rules this table follows

- A type enters the specification only with a working inject / restore /
  verify probe; a mechanism listed here is a proposal until `check_faults`
  has run it on the device (phase D).
- One fault, one mechanism: rows 5 and 10 use two different triggers on two
  different statements of the same journey; rows 4, 5, 10 and 15 fail the
  write at four different layers (filesystem, SQL update, SQL insert, file
  permissions) and are kept distinct for that reason.
- Every write-failure fault owes the same observable (`WRITE_ERROR_SHOWN`),
  which the source says the app does not have (note §5). The specification
  states the obligation; the verdict is what the app earns.

## Campaign two (2026-09-29): one happy path, faults at every point on it

The fixture grows to two medicines and four doses tonight (A "Vitamin C", 3
pills, doses 11:57 / 11:58 / 11:59 PM; B "Zinc", 2 pills, dose 11:56 PM). One
happy path (three orderings) walks every journey; each disruption follows
ordering 1 and may strike at each point where it applies, one test case per
point:

| fault | points on the happy path | cases |
|---|---|---|
| APP_WRITE_FAIL, INFRA_STORAGE_FULL, UE_KILL | the six writes (take a1, delete a1, skip a2, take a3, take b, edit a3) | 6 each |
| DB_ABORT | the four marks (only a mark inserts a record) | 4 |
| APP_CACHE_STALE | the five stock-moving writes | 5 |
| DB_CORRUPT, **DB_CORRUPT_STOCK** (new: the pill count set to -1, which no UI path can produce), INFRA_STORAGE_MEDIA | the five re-reads | 5 each |
| DB_EVENT_LOSS | after the four marks | 4 |
| INPUT_INVALID, CANNOT_SKIP, DELETE_SKIPPED, EDIT_FLIP | one each | 4 |

50 disruption cases plus 3 happy-path orderings. The zero-stock boundary
(a medicine whose last pill is taken shows no stock text at all, §6.3) is
deliberately NOT on the happy path: it would be a second forecast FAIL
before the edit and would cut the baseline of every point after it. It stays
deferred with INPUT_OVERLIMIT.
