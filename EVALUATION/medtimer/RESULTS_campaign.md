# MedTimer — campaign results

Case study six, built from `EVALUATION/template` (2026-09-28/29). Everything here
is read from the run logs in `generated/logs/`; a verdict the log does not
support is not reported. Model: `model/` (specification 208 states, composition
1470 states, no deadlock); purposes: `Test_Purposes/`; generation: narval,
`generated/generate_tc_all.log`, one controllable test case per purpose (no
variants); device: emulator `medtimer_test` (Pixel 6, API 34, arm64), MedTimer
1.24.0 foss debug; harness: Appium 3.5.2 / UiAutomator2 through the framework's
Android executor and the LNT System Interface adapter.

Obligations O1–O9 and the per-fault forecast: `notes/observed_behaviour.md` §13,
copied into `properties/disruption_mapping.yml` before any run. Fault mechanisms
proved on the device before the sweep: `notes/observed_behaviour.md` §15.

## Verdict matrix (first sweep, 2026-09-29; 13 cases, one per purpose)

Tally: 1 nominal PASS, 2 fault PASS (ue_kill, app_cache_stale), 10 FAIL. Every fault was confirmed active by its probe; every FAIL rests on a quoted oracle line and, for the write faults, on the database state after the run.

| case | target | expected (before the run) | verdict | evidence (log) |
|---|---|---|---|---|
| nominal | — | PASS | **PASS** | `logs/nominal.log:488` `CONFIRM oracle OK: StockBand, DoseState agree with 'CONFIRM !COMMITTED !S2 !TAKEN !MED_A' on [('el_state_button', 'taken'), ('el_med_card', 'vitamin c (2 pills left)')]`; 43 steps, every one `ok` |
| input_invalid | empty name (O9) | FAIL | **FAIL** | `logs/input_invalid.log:761` `OBSERVE !EL_NAME_ERROR … never appeared … CONFORMANCE FAILURE`; capture: the edit screen of the nameless medicine (field hint "Medicine name"), no error |
| cannot_skip | forbidden skip (O8) | FAIL | **FAIL** | `logs/cannot_skip.log:586` `CONFIRM mismatch — DoseState: AUT expects PENDING, observed 'skipped' classifies as SKIPPED` |
| delete_skipped | refund on delete (O5) | FAIL | **FAIL** | `logs/delete_skipped.log:524` first checkpoint OK (`S3 SKIPPED`, 3 pills); `:606` `CONFIRM mismatch — StockBand: AUT expects S3, observed 'vitamin c (4 pills left)' classifies as S4` |
| edit_flip | status without stock (O5) | FAIL | **FAIL** | `logs/edit_flip.log:528` first checkpoint OK (`S3 SKIPPED`); `:614` `CONFIRM mismatch — StockBand: AUT expects S2, observed 'vitamin c (3 pills left)' classifies as S3` |
| app_write_fail | record update fails (O4, O5) | FAIL | **FAIL** | rerun with the relaunch removed: `logs/app_write_fail.log:485` injection confirmed; `:764` `OBSERVE !EL_WRITE_ERROR … never appeared … CONFORMANCE FAILURE`; database after: **stock 2.0 with the event still RAISED, stockHandled 0**: the stock write committed, the record update was aborted, no message. The half-written state §4.1 predicted, now measured |
| db_abort | record insert fails (O4) | FAIL | **FAIL** | rerun `logs/db_abort.log:437` injection confirmed; `:720` `OBSERVE !EL_WRITE_ERROR … never appeared`; database after: stock 3.0, no event row: the first write aborted, nothing committed, nothing reported |
| infra_storage_full | partition full (O4) | FAIL | **FAIL** | rerun `logs/infra_storage_full.log:369` injection confirmed; `:632` `OBSERVE !EL_WRITE_ERROR … never appeared`; database after: stock 3.0, no event row: the insert hit ENOSPC, nothing reported |
| ue_kill | kill after the tap | PASS likely | **PASS** | rerun `logs/ue_kill.log:1098` `CONFIRM oracle OK … 'CONFIRM !COMMITTED !S2 !TAKEN !MED_A'`; database after: stock 2.0, event TAKEN, stockHandled 1: the kill landed after all three writes (the whole outcome). the first walk did not finish (apparatus, see threats) |
| app_cache_stale | list read before the write (O3) | PASS | **PASS** | `logs/app_cache_stale.log:517` `CONFIRM oracle OK: StockBand, DoseState agree with 'CONFIRM !COMMITTED !S2 !TAKEN !MED_A' on [('el_state_button', 'taken'), ('el_med_card', 'vitamin c (2 pills left)')]` |
| db_corrupt | record unreadable (O6) | FAIL | **FAIL** | `logs/db_corrupt.log:536` phase-1 checkpoint OK; `:673` injection confirmed; `:1050` `OBSERVE !EL_CORRUPT_ERROR … never appeared`; capture: only the system UI in the hierarchy, the app gone (it died on relaunch reading the bad status) |
| db_event_loss | record lost after the write (O5) | FAIL | **FAIL** | `logs/db_event_loss.log:979` phase-1 checkpoint OK (2 pills, Taken); `:982,984` loss injected twice, both confirmed; `:1174` `CONFIRM mismatch — StockBand: AUT expects S3, observed 'vitamin c (2 pills left)' classifies as S2` (the dose is due again, the stock stayed decremented) |
| infra_storage_media | store unreadable (O7) | FAIL | **FAIL** | `logs/infra_storage_media.log:528` phase-1 checkpoint OK; `:665` injection confirmed; `:1064` `OBSERVE !EL_STORAGE_ERROR … never appeared`; capture: the launcher on screen, the app gone (it died at the first query) |

Verdicts are the ioco verdicts reached by walking the generated test case:
PASS (the walk reached `:PASS:`), FAIL (an output the case does not allow at
that state, silence included where no `:DELTA:` is offered) and INCONCLUSIVE
(the walk reached an `:INCONCLUSIVE:` state). A run that could not finish its
walk is an apparatus problem, fixed and walked again; it is not a verdict and
is not counted.

## How a verdict is earned here

The walk executes the generated case's concrete labels (TAP, TYPE_INTO,
WAIT_FOR, OBSERVE, NAVIGATE) against the emulator and advances through the
abstract checkpoints. At `CONFIRM` the observation oracle reads two values
back and compares them with the label's offers: the stock band from the
medicine card ("Vitamin C (N pills left)", one rung per dose, saturating at
four or more) and the dose row's state from its state button's content
description ("Please wait…", "Taken", "Skipped"). A checkpoint line of the
form `CONFIRM oracle OK: … agree with '…' on […]` is the proof that both were
checked; a bare `checkpoint CONFIRM — advance` would mean nothing was, and
no PASS below rests on one. Fault observables (`WRITE_ERROR_SHOWN`,
`REJECT_SHOWN`, `DB_CORRUPT_DETECTED`, `INFRA_STORAGE_ERROR`) are `observe`
steps on the element that message would have to occupy; their absence is a
FAIL by quiescence where the specification owes an output.

## Threats to validity

- **Owed observables that the app does not have.** The four error elements are
  the honest places a message would appear (the name field's error line, a
  toast or snackbar naming the failure). A FAIL on them says the app showed
  nothing there; it cannot say the app showed something elsewhere that a
  human would count. The screenshots captured at each such FAIL are the check.
- **One fixture, one medicine, one dose per day.** The band is valid only
  because every recorded dose is the same reminder's dose "1"; the fixture
  holds three units so that a refund the records do not justify classifies as
  a fourth rung. Nothing here speaks to multiple medicines, multiple
  reminders, or several doses a day.
- **The kill window.** UE_KILL is a force-stop issued by the relaunch step
  after the Taken tap; the three writes take milliseconds and the kill lands
  after them. A PASS there says the outcome read back was consistent, not
  that a kill between the writes was survived.
- **Read-back timing.** The dose row is read after the popup closes; the
  scheduled-row duplicate window of `notes/observed_behaviour.md` §6.2 was
  never captured live and is not measured by these runs.
- **Injection out of band.** Triggers, deletions, permission changes and the
  partition fill are applied through adb / sqlite3 as the app's own user.
  Each was proved to bite and let go before the sweep (§15); a run whose
  probe disagreed would have no verdict and would be walked again.
- **The record-loss obligation** (O5 as applied to DB_EVENT_LOSS) reads the
  stock as a function of the recorded doses; the app keeps the stock as a
  counter of its own. The specification states this as the weakest of its
  obligations, and the verdict is reported with that caveat.
- **Time of day.** The fixture's reminder is at 11:59 PM so the dose is
  scheduled today; a run that crosses midnight would find no row.
- **The second DB_EVENT_LOSS.** The generated case fires the loss gate twice
  in a row; the second deletion finds no row and its probe still agrees. It
  changes nothing observable and is noted for completeness.

## Deferred and noted (see `notes/DISRUPTION_COVERAGE.md`)

INPUT_OVERLIMIT (needs a second fixture reminder), the manual-dose journey,
the notification / alarm path, EXPIRED as an obligation; connectivity,
session, server and external-API faults have no analogue in an offline app.
- **Walks that did not finish, and were walked again.** Three first-sweep
  runs ended without a verdict for apparatus reasons and are not counted:
  ue_kill (an out-of-band force-stop issued before the tap dismissed the
  popup; the kill is now the SI's relaunch after the tap), infra_storage_full
  (the walker re-probed after the platform had trimmed its cache and judged
  the fault absent; the injector now keeps the probe answer taken at
  injection), and app_write_fail's first walk, which ended in a FAIL but with
  the fault never exercised (the SI relaunched before the dose was written;
  that relaunch is removed). A later batch of three found a different
  emulator on the device port and could not start the app; it was walked
  again on the MedTimer emulator. Every verdict in the matrix comes from a
  completed walk.
