# MedTimer — Observed Behaviour (ground truth for the specification)

Written 2026-09-28 against the clone at `systems/medtimer/sut/medtimer`, commit
`abd1950` (2026-06-20), `versionName 1.24.0` / `versionCode 175`
(`app/build.gradle.kts:20-21`), built as `foss` `debug`
(`app/build/outputs/apk/foss/debug/MedTimer-foss-debug.apk`). Everything below
was established by READING THE SOURCE; nothing has run on a device yet. §14
lists what must be confirmed live before it is relied on.

Evidence marks: a `file:line` reference means those lines were read; `✓` marks a
claim re-checked against the file named after an earlier note had it differently
or less precisely. Paths are relative to the clone; `core/database/…` means
`core/database/src/main/java/com/futsch1/medtimer/database/…`, `feature/reminders/…`
means `feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/…`,
`feature/ui/…` means `feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/…`,
`core/ui/…` means `core/ui/src/main/java/com/futsch1/medtimer/core/ui/…`.

The earlier version of this note (schema v24, undated) is superseded. Its two
central claims are re-checked here: the dose action is indeed several separate
writes (§4.1 ✓), and `cannotBeSkipped` is indeed enforced only in the
notification (§9 ✓). What it did not say, and the source makes central, is in
§4.4–4.7 and §8.

---

## 1. What MedTimer is

A medication reminder and adherence-history app, Kotlin, Android only, Room on
SQLite, Hilt, a mix of Compose scaffold and View-based fragments. It has **no
network access at all**: the manifest removes `INTERNET` and
`ACCESS_NETWORK_STATE` (`app/src/main/AndroidManifest.xml:12-17`), and the
`foss` flavour has no Google services (`AGENTS.md`, flavour table). There are no
accounts. The only inputs from outside the app are the system clock and time
zone (`TimeChangeReceiver`, manifest `:72-80`) and, optionally, a user-chosen
backup directory that the app only writes to (§11).

Three tabs: **Overview** (the day's reminders and what happened to them),
**Medicine** (the list of medicines, each with its reminders and stock), and
**Analysis** (charts, table, calendar). The app's own labels: `tab_overview`
"Overview", `tab_medicine` "Medicine", `analysis` "Analysis"
(`core/ui/src/main/res/values/strings.xml:77,78,156`).

---

## 2. Domain and schema (the nouns)

Room database named `medTimer` (`core/database/di/DatabaseModule.kt:36-37`),
so the file is `/data/data/com.futsch1.medtimer/databases/medTimer`. No journal
mode is set, so Room's default applies (WAL on this class of device; `-wal` and
`-shm` siblings expected: confirm live, §14). Schema version 24
(`core/database/MedicineRoomDatabase.kt:21-23`). Five tables: `Medicine`,
`Reminder`, `ReminderEvent`, `Tag`, `MedicineToTag` (`:22`). Enum columns are
stored as their name in TEXT (Room's built-in enum conversion; the app's own
`Converters.kt` only handles lists). No foreign keys are declared on any entity.

### 2.1 `Medicine` — the medicine and its stock (`core/database/MedicineEntity.kt:9-26`)

| column | type / default | meaning |
|---|---|---|
| `medicineId` | INTEGER PK autoincrement (`:12`) | identity |
| `medicineName` | TEXT (`:11`) | the name shown everywhere |
| `amount` | REAL, default 0 (`:17`) | **the current stock** |
| `unit` | TEXT, default "" (`:19`) | stock unit, e.g. "pills" |
| `refillSizes` | TEXT JSON list (`:18`) | refill presets |
| `expirationDate` / `productionDate` | INTEGER epoch-day, 0 = unset (`:23-24`) | expiry |
| `cannotBeSkipped` | INTEGER bool, default false (`:25`) | see §9 |

There is no separate stock table: stock is the one scalar `Medicine.amount`.
Derived predicates on the domain model (`core/domain/.../model/Medicine.kt`):
`hasExpired()` = expiration set and before today (`:39-41`);
`isStockManagementActive()` = amount ≠ 0 **or** some reminder has an out-of-stock
type other than OFF (`:47-49`); `isOutOfStock()` = stock management active **and**
some reminder with out-of-stock type ≠ OFF has `threshold >= amount` (`:43-45`).
So a medicine whose stock has reached exactly 0 and that has no out-of-stock
reminder is neither "stock-managed" nor "out of stock" in the app's eyes (§8.2).

### 2.2 `Reminder` — the schedule and the dose (`core/database/ReminderEntity.kt:8-44`)

| column | type / default | meaning |
|---|---|---|
| `reminderId` | INTEGER PK (`:11`) | identity |
| `medicineRelId` | INTEGER (`:10`) | the medicine (no FK) |
| `timeInMinutes` | INTEGER (`:12`) | fire time, minutes since midnight |
| `createdTimestamp` | INTEGER, default 0 (`:13`) | when created; gates same-day scheduling (§7.2) |
| `amount` | TEXT, default `"?"` (`:18`) | **the dose, as typed**; parsed to a number only when stock is handled |
| `active` | INTEGER bool, default true (`:28`) | on/off |
| `days`, `periodStart/End`, `activeDaysOfMonth`, cycle fields | | schedule variants |
| `outOfStockThreshold` / `outOfStockReminderType` | REAL 0.0 / TEXT OFF (`:40-41`) | ONCE, ALWAYS, DAILY, OFF (`:52-57`) |
| `expirationReminderType` | TEXT OFF (`:42`) | ONCE, DAILY, OFF |
| `variableAmount`, `automaticallyTaken`, interval fields | | not used by the journeys below |

The reminder type is derived, not stored: LINKED, CONTINUOUS_INTERVAL,
WINDOWED_INTERVAL, OUT_OF_STOCK, EXPIRATION_DATE, else TIME_BASED
(`core/domain/.../model/Reminder.kt:36-44`). Only TIME_BASED is modelled.

### 2.3 `ReminderEvent` — a fired (or logged) reminder and its outcome (`core/database/ReminderEventEntity.kt:15-46`)

| column | type / default | meaning |
|---|---|---|
| `reminderEventId` | INTEGER PK (`:17`) | identity |
| `reminderId` | INTEGER (`:25`), −1 for manual doses and refills | the reminder |
| `medicineName`, `amount` | TEXT (`:18-19`) | snapshot at creation |
| `status` | TEXT enum (`:22`): RAISED, TAKEN, SKIPPED, DELETED, ACKNOWLEDGED (`:39-45`) | **the outcome** |
| `remindedTimestamp` | INTEGER epoch-s (`:23`) | when it fired / was scheduled |
| `processedTimestamp` | INTEGER epoch-s (`:24`) | when the user acted |
| `stockHandled` | bool, default false (`:29`) | whether this event has consumed stock |
| `stockBefore` / `stockAfter` | REAL, default −1.0 (`:35-36`) | stock around the action; −1 = stock not tracked |
| `stockUnit` | TEXT (`:37`) | |
| `reminderType` | TEXT, default TIME_BASED (`:34`) | TIME_BASED, OUT_OF_STOCK, EXPIRATION_DATE, REFILL, … |

ACKNOWLEDGED is the terminal state of out-of-stock, expiration and refill
events, never of a dose (`feature/reminders/NotificationProcessor.kt:119-124`).
DELETED rows stay in the table and are filtered out of every view (§6).

---

## 3. Screens and the controls the tester will use

**Overview** (`feature/ui/overview/OverviewFragment.kt`; layout
`feature/ui/src/main/res/layout/fragment_overview.xml`): a week strip
(`overviewWeek`, `:24`), filter chips Taken / Skipped / Raised / Scheduled
(`:55-83`), the list `reminders` (`:89`) and the button `logManualDose` "Log
additional dose" (`:103-111`, `strings.xml:128`). Each row
(`layout/overview_item.xml`) is a round **state button** `stateButton`
(`:37-52`) plus the text `reminderText` (`:66-78`). The state button's content
description is the row's state (`feature/ui/overview/ReminderViewHolder.kt:193-197`):
"Please wait…" (PENDING), "Taken", "Skipped", "Reminded" (RAISED)
(`feature/ui/overview/model/OverviewState.kt:14-22`; `strings.xml:64,25,24,259`).
Tapping the state button opens a circular popup
(`ReminderViewHolder.kt:126-147`) whose buttons are `takenButton` "Taken",
`skippedButton` "Skipped", `rescheduleButton`, `deleteButton` "Delete",
`reraiseButton`, `acknowledgedButton` (`layout/circular_menu_overview_event.xml:71-135`);
which of them are visible is decided per row (§4.2, §4.3). Tapping the row text
opens the **edit-event sheet** for a Taken/Skipped row and the medicine sheet
otherwise (`ReminderViewHolder.kt:104-117`).

The row text is built by `core/ui/ReminderStringFormatter.kt`. For a past
event (`:31-59`): the reminder-type icon, the reminded time, "` ➡ `taken time"
when TAKEN and the preference `showTakenTimeInOverview` is on (default true,
`core/domain/.../model/UserPreferences.kt:79`), then, **only if
`stockBefore != stockAfter`**, "`, ` 📦 `<stockAfter> <unit>`" (`:191-208`),
a newline, the medicine name in bold, and "` (<amount>)`". For a scheduled
(not yet raised) reminder (`:61-77`): the time, "`, ` 📦 `<current stock>`"
when stock management is active (`:158-189`), the name, "` (<dose>)`".

**Medicine** (`feature/ui/medicine/MedicinesFragment.kt`): a card per medicine
(`layout/card_medicine.xml`, `medicineName` `:43`, `remindersSummary` `:49`)
and a FAB `addMedicine` (`MedicinesFragment.kt:145`). The card's title is the
name in bold followed by "` (<amount> <unit> left`[` ⚠`][` 🚫`]`)`"
(`core/ui/MedicineStringFormatter.kt:22-55`; "%1$s left" is
`strings.xml:19`), with the stock text present **only while
`isStockManagementActive()`** (`:44`), ⚠ only when `isOutOfStock()` and 🚫 only
when `hasExpired()` (`core/common/.../helpers/MedicineHelper.kt:34-55`). Tapping a
card opens **edit medicine** (`feature/ui/medicine/EditMedicineFragment.kt`), which
holds the name field `editMedicineName` (`:176`), the reminders list, a FAB that
opens the new-reminder type dialog (`:279`), and sub-menus including **stock
settings** (`feature/ui/medicine/medicineSettings/StockSettingsFragment.kt`,
preferences `amount`, `stock_unit`, `stock_refill_size`, `stock_refill_now`,
`expiration_date`, …).

**Analysis** (`feature/ui/statistics/*`): charts of taken vs skipped, a per-day
bar chart of TAKEN per medicine, a reminder table and a calendar. Counts come
from `StatisticsProvider.kt:20-24` (TAKEN and SKIPPED counted by status,
DELETED and ACKNOWLEDGED not counted) and `:64-85` (per-day TAKEN).

**Notification** (`feature/reminders/src/main/res/layout/notification.xml`): a
title and the buttons `takenButton` "Taken" (`:19-27`), `skippedButton`
"Skipped" (`:45-54`), `snoozeButton`. Not a screen the harness drives; it is
where §9 applies.

---

## 4. Writes: the complete write alphabet, in the order the statements run

There is **no user-initiated write that spans a transaction over more than one
table**. The only `@Transaction` methods are `MedicineDao.decreaseStock`
(`core/database/dao/MedicineDao.kt:16-22`: fetch, `amount = max(0, amount −
dose)`, update, re-read) and `ReminderEventDao.decreaseRepeats` (`:58-65`).
Every other write is a single `@Insert` / `@Update` (`ReminderEventDao.kt:40-50`,
`MedicineDao.kt:43-50`) called from a repository that adds nothing
(`core/database/ReminderEventRepositoryImpl.kt:64-67, 85-91`,
`MedicineRepositoryImpl.kt:46-48`).

### 4.1 Marking a dose Taken or Skipped — the central journey ✓

Whatever the entry point (§4.2, §4.3, notification), the action ends in
`NotificationProcessor.setReminderEventStatus`
(`feature/reminders/NotificationProcessor.kt:115-151`), which, per event:

1. cancels the event's pending alarms (`:134`);
2. **writes the stock first**: `doStockHandling` (`:135`, body `:155-168`) —
   for TAKEN with `!stockHandled`, or SKIPPED with `stockHandled` (an undo),
   it parses the dose from the event's `amount` string (`:160`; an unparsable
   dose means **no stock change and no error**), negates it for SKIPPED
   (`:161-163`), and calls `StockHandlingProcessor.processStock`
   (`feature/reminders/StockHandlingProcessor.kt:21-26`) →
   `decreaseStock` (**UPDATE Medicine**, its own transaction) → threshold check
   (`:28-52`, §8.3). A fresh SKIP (`stockHandled` false) changes nothing.
3. builds the updated event: `status`, `processedTimestamp`, `stockHandled :=
   (status == TAKEN)`, `stockAfter` from the stock change (`:136-145`);
4. clears pending location snoozes (`:148`, DataStore, not Room);
5. **writes the event second**: `reminderEventRepository.updateAll` (`:149`,
   **UPDATE ReminderEvent**);
6. removes the reminder from any notification (`:150`).

So a Taken is **UPDATE Medicine, then UPDATE ReminderEvent**, two statements,
two transactions, in that order. A failure between them leaves the stock
decremented and the event still RAISED. The event row is the thing the
history, the Analysis counts and the overview show; the stock is what the
Medicine tab shows. That gap is the write-abort injection surface.

### 4.2 The entry point that needs no alarm: acting on a scheduled reminder

The overview lists, for the selected day, both the events already in the table
and the **scheduled reminders that have not fired yet**
(`feature/ui/overview/OverviewViewModel.kt:98-101`, scheduled rows from the
simulation §6.2). A scheduled row's popup offers TAKEN, SKIPPED and RESCHEDULE
(`feature/ui/overview/actions/ScheduledReminderActions.kt:33-42`).
Choosing Taken or Skipped (`:79-82`):

1. `ReminderEventCreator.getOrCreateReminderEvent`
   (`feature/ui/overview/actions/ReminderEventCreator.kt:22-33`): fetch the
   event for (reminderId, timestamp) or **INSERT ReminderEvent** with status
   RAISED, `stockBefore = stockAfter = current stock` if stock management is
   active, else −1 (`feature/reminders/ReminderNotificationProcessor.kt:107-163`,
   `:147, :159-160`);
2. `ReminderProcessorBroadcastReceiver.requestReminderAction`
   (`feature/reminders/ReminderProcessorBroadcastReceiver.kt:171-183`) sends a
   Taken / Skipped **broadcast**, received in the same process (`:62-117`,
   `goAsync` `:64`, `applicationScope.launch` `:65`), which runs §4.1 and then
   reschedules (`:77-83`, `:69-75`).

Hence a Taken on a scheduled row is **INSERT ReminderEvent (RAISED) → UPDATE
Medicine → UPDATE ReminderEvent (TAKEN)**, three statements, three transactions.
This is the journey the tester can drive at any time of day with a reminder
whose time is still ahead, no alarm and no notification involved.

### 4.3 Acting on a raised event

When the reminder has fired, the row is a past event in state RAISED
("Reminded"); its popup offers TAKEN, SKIPPED and RESCHEDULE
(`feature/ui/overview/actions/ReminderEventActions.kt:53-64`). Taken / Skipped
send the same broadcast (`:106-108`, note the `null` reminder argument, so the
variable-amount prompt is bypassed here, `ReminderProcessorBroadcastReceiver.kt:175`)
and run §4.1 without the insert.

### 4.4 Deleting or re-raising a Taken / Skipped event — stock is refunded unconditionally

For a Taken or Skipped row the popup offers, besides the other status, RERAISE
and DELETE (`ReminderEventActions.kt:60-63`). Both first call `undoStock`
(`:120-124`): parse the dose and `decreaseStock(medicine, −dose)`, i.e. **add
the dose back**, **without checking `stockHandled`**. Then DELETE writes the
event with status DELETED and `stockHandled = false` (`:126-133`); RERAISE
deletes the row and asks for a reschedule (`:110-118`).

Consequence: deleting (or re-raising) a **Skipped** event, which never consumed
stock, **increases the stock by one dose**. On a medicine with stock 0 and no
stock reminder this also flips `isStockManagementActive()` on, so "N left"
appears on the Medicine card where nothing was shown before. This is a
source-proven divergence between the events and the stock (obligation
candidate, §13).

### 4.5 Editing an event — status changes without stock handling

Tapping a Taken / Skipped row opens the edit sheet
(`feature/ui/overview/EditEventSheetDialogFragment.kt`), whose Taken / Skipped
toggle sets `viewModel.status` (`:135-144`) and whose dismissal calls
`updateEvent` (`:146-149`). `EditEventViewModel.updateEvent`
(`feature/ui/overview/EditEventViewModel.kt:124-141`) copies name, amount, notes,
both timestamps and the chosen status into the row and does a plain UPDATE
(`:139`). **No stock handling and no `stockHandled` update.** Flipping Skipped →
Taken here records a dose that was never subtracted; Taken → Skipped leaves the
subtraction in place. Second source-proven divergence (§13).

### 4.6 Logging an additional dose ("Log additional dose")

`feature/ui/overview/ManualDose.kt`: the user picks a medicine, an amount and a
time; `getTimeAndLog` (`:147-169`) then, in the activity's coroutine scope,
**INSERT ReminderEvent** with status TAKEN and `reminderId = −1` (`:98-106,
151-158`), and, independently, sends a StockHandling **broadcast** that runs
`decreaseStock` (`:164-167`, receiver `ReminderProcessorBroadcastReceiver.kt:134-139`).
Two writes with no ordering between them. The manual-dose event carries
`stockBefore = stockAfter = −1` (defaults), so its row never shows a stock text.

### 4.7 Refill

`feature/reminders/RefillProcessor.kt:46-52`: `amount := amount + refillSize`
(UPDATE Medicine, no upper bound) then INSERT an ACKNOWLEDGED REFILL event
whose amount text reads "`<before> ➡ <after>`" (`:54-75`). Reached from stock
settings ("Refill now", `StockSettingsFragment.kt:198-200`) or from an
out-of-stock notification.

### 4.8 Creating the fixture

- **Add medicine**: the FAB opens a one-field dialog; OK trims the text and
  INSERTs `Medicine.default()` with that name (`MedicinesFragment.kt:166-181`).
  **No check for an empty name** (`:171-176`): "" is accepted. Then it navigates
  to edit medicine (`:183-189`).
- **Edit medicine** saves on `onStop`, in the application scope: every changed
  reminder, then the medicine if it changed (`EditMedicineFragment.kt:156-169`).
  Leaving the screen is the commit.
- **Stock**: the `amount` preference's edit text has a numeric keyboard and a
  watcher that deletes any character making the value unparsable or negative
  (`StockSettingsFragment.kt:220-248`, `:234`), so a negative or textual stock
  is unreachable through the UI; an emptied field stores nothing
  (`feature/ui/medicine/medicineSettings/MedicineDataStore.kt:66-67`).
- **Add reminder**: the new-reminder dialog (`feature/ui/medicine/dialogs/NewReminderDialog.kt`)
  takes a time and the dose text. Create (`:172-213`) copies the dose **as
  typed** (`:174-177`); only the time is validated (`:197`), a bad time gives a
  toast "Invalid input" (`:206-210`, `strings.xml:220`). While stock management
  is active, a non-numeric dose shows the inline error "The amount has to
  contain a number to enable medicine stock tracking for this reminder"
  (`:80-85`, `feature/ui/helpers/AmountTextWatcher.kt:28-33`, `strings.xml:255`)
  **but the reminder is still created**; taking it later changes no stock
  (§4.1 step 2). A reminder created at a time earlier than now is not scheduled
  today (§7.2).

### 4.9 Reads that write

None. Unlike a materialising read, every read here is a Room query or Flow. The
future-reminder simulation (§6.2) computes in memory and writes nothing.

---

## 5. What the UI reports when a write fails: nothing, then a crash

No repository write anywhere in the dose path is wrapped in a `try`. The
`catch` sites in the main sources are navigation, parsing, export and biometric
helpers only (`grep -rn 'catch (' feature/reminders/src/main
feature/ui/src/main/java/.../overview core/database/src/main`: the two hits in
`overview` are a date-picker `IllegalStateException` and the simulation's own
guard, `FutureRemindersRepository.kt:60`). The broadcast receiver wraps its
work in `try … finally` with no `catch` (`ReminderProcessorBroadcastReceiver.kt:66-115`).
The application scope it launches into is `CoroutineScope(SupervisorJob() +
dispatcher)` with **no `CoroutineExceptionHandler`**
(`core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:16-21`),
and `MedTimerApplication` installs no default handler
(`app/src/main/java/com/futsch1/medtimer/MedTimerApplication.kt`). The UI-side
launches (`lifecycleScope`, `viewModelScope`) are the same.

Therefore a Room exception during a write (constraint failure, injected
trigger, `SQLITE_FULL`, unreadable file) propagates to the thread's default
handler and **kills the process**; the system shows its "MedTimer keeps
stopping" dialog. Nothing in the app reports the failure, and what was
committed before the throw stays committed (§4.1: the stock, if the event
update is the statement that fails). On relaunch, `MainActivity.checkForceStopped`
(`app/src/main/java/com/futsch1/medtimer/MainActivity.kt:284-294`) re-posts
notifications for RAISED events of the last day (`AutostartService.kt:28-51`);
it does not reconcile anything.

For an ioco tester this means: **a failed write is observed as quiescence at
the app level, with a system crash dialog on screen**; there is no app-level
error element to wait for.

Only two write-adjacent failures are handled: the auto-backup's file write is
caught and logged (`app/src/main/java/com/futsch1/medtimer/database/backup/BackupManager.kt:335-346`,
never shown), and a scheduling simulation error is logged (`FutureRemindersRepository.kt:60-61`).

---

## 6. Derived views and their staleness

### 6.1 Reactive by construction

Every view is a Room `Flow` re-collected on each committed change: the overview
events (`OverviewViewModel.kt:88-96`, `getAllFlowStartingFrom`, statuses without
DELETED `:90`), the medicine list (`feature/ui/MedicineViewModel.kt:39, 56-59`,
`getAllFlow`), the Analysis series
(`feature/ui/statistics/StatisticsScreenViewModel.kt:65-81`, `getAllFlow` over
TAKEN and SKIPPED, combined with the medicine flow). Nothing is cached by the
app between the store and the screen, and no timed cache exists. Whether the
tab's fragment re-collects when re-entered is a lifecycle fact to confirm live
(§14).

### 6.2 The one computed view: scheduled reminders

Scheduled (not yet raised) rows come from `FutureRemindersRepository`
(`feature/reminders/FutureRemindersRepository.kt`): a simulation of the next 28
days (`:107`) run on a trigger (`:71-79`, `:44-69`), whose result is a
`StateFlow` the overview consumes (`MedicineViewModel.kt:79-82`,
`OverviewViewModel.kt:98-101`). It is re-triggered when the next alarm is
(re)scheduled (`ScheduleNextReminderNotificationProcessor.kt:28`), i.e. after
every Taken / Skipped broadcast (`ReminderProcessorBroadcastReceiver.kt:74, 82`)
and on medicine changes (`ReminderSchedulerService.kt:20-28`), and by the
overview when the viewed day nears the simulated horizon
(`OverviewViewModel.kt:112-117`). Between the INSERT of a RAISED event (§4.2
step 1) and the re-simulation, the same reminder can be present twice: as a
past event and as a scheduled row. How long that lasts is to be measured live
(§14). The scheduler excludes days that already have an event
(`StandardScheduling.kt:57`), so after re-simulation the duplicate is gone.

### 6.3 What each view says about stock

- Medicine card: "N unit left" only while stock management is active (§3).
  **A medicine that reaches 0 with no out-of-stock reminder shows no stock text
  at all**, not "0 left" (`MedicineStringFormatter.kt:44`, `Medicine.kt:47-49`).
- Overview row: "📦 N unit" only when the event changed the stock (§3). A take
  at stock 0 (clamped, §8.1) has `stockBefore == stockAfter == 0` and shows
  nothing.
- ⚠ on the card and on a notification title require an out-of-stock reminder
  (`Medicine.kt:43-45`, `BigReminderNotificationFactory.kt:60-68`).
- Stock settings: the `amount` summary "N unit" with ⚠ when out of stock and 🚫
  on the expiration date when expired (`StockSettingsFragment.kt:103-116`).

---

## 7. Scheduling and notification

### 7.1 The path

`MainActivity.onResume` starts `ReminderSchedulerService` (`MainActivity.kt:296-306`),
which requests a reschedule on start and whenever the medicine flow changes
(`ReminderSchedulerService.kt:20-28, 35-39, 51-53`). The request is a broadcast
(`ReminderProcessorBroadcastReceiver.kt:144-147`, action `Schedule` `:110`)
handled by `ScheduleNextReminderNotificationProcessor.scheduleNextReminder`
(`:27-59`): read all medicines, read the last events per active reminder, run
`ReminderScheduler` (`feature/reminders/scheduling/ReminderScheduler.kt:10-31`,
one `Scheduling` per reminder type, `SchedulingFactory.kt:11-48`), take the
earliest, and hand it to `AlarmProcessor.setNextReminderAlarm`
(`feature/reminders/AlarmProcessor.kt:29-54`):

- if the due instant is **not after now**, the reminder is processed
  immediately (`:35-42`) — `ReminderNotificationProcessor.processReminders`
  (`:35-49`) creates the RAISED event **before** the notification
  (`feature/reminders/notificationData/ReminderNotificationFactory.kt:50-55`),
  then posts the notification if `POST_NOTIFICATIONS` is granted
  (`ReminderNotificationProcessor.kt:89-104`) and stores the notification id on
  the event (`:97`). Without the permission the event exists and no
  notification does; the overview then shows a "Reminded" row.
- otherwise an alarm is set (`:89-95`): `setExactAndAllowWhileIdle` when exact
  alarms are allowed, else `setAndAllowWhileIdle`. Exact needs the preference
  `exactReminders` (default **false**, `UserPreferences.kt:67`) and, on API 31+,
  `canScheduleExactAlarms()` (`:120-126`; permission `SCHEDULE_EXACT_ALARM`
  declared, manifest `:8-10`). With the defaults every alarm is
  **`setAndAllowWhileIdle`**: it fires in Doze, but may be deferred by the
  platform's inexact-alarm batching.

Force-stop and reboot: `checkForceStopped` re-posts RAISED events' notifications
(`MainActivity.kt:284-294`); `Autostart` does the same on `BOOT_COMPLETED` and
requests a reschedule (`app/src/main/java/com/futsch1/medtimer/Autostart.kt:36-54`).

### 7.2 When a time-based reminder is due

`StandardScheduling` (`feature/reminders/scheduling/StandardScheduling.kt`):
with no cycle, every day is possible except that **today is possible only if
the reminder was created before today's fire time and nothing was raised
today**, and tomorrow only if nothing was raised tomorrow (`:55-59`,
`:107-109`); weekday, period and day-of-month filters then apply (`:61-95`); the
earliest remaining day at the reminder's time is the answer (`:97-118`,
`Scheduling.kt:63-67`). So: a reminder created at 10:00 for 09:00 fires
**tomorrow** at 09:00, and appears in the overview under tomorrow; a reminder
created at 10:00 for 10:05 fires at 10:05 today and is a scheduled row on the
overview until then. Out-of-stock DAILY and expiration reminders have their own
schedulers (`OutOfStockScheduling.kt:15-20`, `ExpirationDateScheduling.kt:17-29`).

### 7.3 Doze

Alarms use the `AllowWhileIdle` variants (§7.1), so forcing idle
(`dumpsys deviceidle force-idle`) does not suppress them; it may delay an
inexact one. The tester-driven journeys (§4.2, §4.3) do not depend on an alarm
at all, which is why a "scheduler dead" fault has a small observable surface
here (see DISRUPTION_COVERAGE.md).

---

## 8. Stock arithmetic

### 8.1 Saturation

`decreaseStock` clamps at zero: `amount = max(0.0, amount − dose)`
(`MedicineDao.kt:19`). Taking at stock 0, or a dose larger than the stock,
**is not blocked and produces no message**: the event is TAKEN, the stock is 0.
There is no upper bound; a refill (§4.7) or an unconditional refund (§4.4)
raises it without limit. Amounts are doubles; the UI formats with at most two
decimals (`MedicineHelper.kt:57-62`).

### 8.2 The zero-stock blind spot

Stock management is "active" only while `amount ≠ 0` or an out-of-stock
reminder exists (`Medicine.kt:47-49`). A medicine with stock exactly 0 and no
such reminder is displayed with no stock text (§6.3) and its new events carry
`stockBefore = stockAfter = −1` (`ReminderNotificationProcessor.kt:159-160`),
i.e. "untracked". The state "we ran out" is invisible unless an out-of-stock
reminder was configured.

### 8.3 Out-of-stock detection

After every stock decrease, `checkForThreshold` (`StockHandlingProcessor.kt:28-52`)
looks at each reminder of the medicine with an out-of-stock type: for ONCE it
fires only when the decrease **crosses** the threshold (`:35-37`), for ALWAYS on
every decrease at or below it (`:39`), DAILY is left to the scheduler
(`:40-42`, `OutOfStockScheduling.kt`). Firing means requesting a notification
(`:45-50`), which creates an OUT_OF_STOCK event whose amount text is the current
stock (`ReminderNotificationProcessor.kt:115-118`), acknowledged, never taken
(`NotificationProcessor.kt:119-124`). The notification text: "Only %2$s of %1$s
left!" (`strings.xml:67`).

### 8.4 The paths that can make the stock disagree with the events

| path | effect on stock | effect on events | source |
|---|---|---|---|
| Taken (normal) | −dose, clamped | TAKEN, stockHandled | §4.1 |
| Taken with non-numeric dose | none | TAKEN, stockHandled, stockAfter unchanged | `NotificationProcessor.kt:160` |
| Skipped (fresh) | none | SKIPPED | `:156-157` |
| Skipped after Taken | +dose | SKIPPED, stockHandled false | `:157, 161-163` |
| Delete / re-raise a Taken row | +dose | DELETED / row removed | `ReminderEventActions.kt:120-133` |
| **Delete / re-raise a Skipped row** | **+dose** | DELETED / row removed | same, no `stockHandled` check |
| **Edit sheet: Skipped → Taken** | **none** | TAKEN | `EditEventViewModel.kt:124-141` |
| **Edit sheet: Taken → Skipped** | **none** | SKIPPED | same |
| Manual dose | −dose (separate broadcast) | TAKEN, untracked | `ManualDose.kt:147-169` |
| Refill | +refillSize | REFILL ACKNOWLEDGED | `RefillProcessor.kt:46-52` |
| Crash between the two writes of §4.1 | −dose | still RAISED | §5 |

The bold rows are ordinary UI paths, not faults.

---

## 9. `cannotBeSkipped` ✓

Per medicine (`Medicine.kt:24`, `MedicineEntity.kt:25`), or globally through the
preference `cannotSkipReminders` ("Reminders cannot be skipped",
`strings.xml:331-332`, default false `UserPreferences.kt:75`). It is enforced
**only in the notification**: the skip intent is `null`
(`feature/reminders/notificationFactory/NotificationIntentBuilder.kt:67-71`) and
the big notification hides the Skipped button
(`BigReminderNotificationFactory.kt:51-53`); a swipe-dismiss then snoozes
instead of skipping (`NotificationIntentBuilder.kt:121-135`, default action
SKIP `UserPreferences.kt:74`). **The overview popup offers Skipped regardless**:
`ReminderEventActions.kt:57-59` and `ScheduledReminderActions.kt:39` never read
the flag, and the edit sheet's toggle (§4.5) does not either. So "this medicine
can only be taken" holds from the notification and nowhere else.

---

## 10. Expiry

`hasExpired()` (`Medicine.kt:39-41`) drives a 🚫 icon on the Medicine card
(`MedicineHelper.kt:49-55`, `MedicineStringFormatter.kt:43`) and on the
expiration-date row of the stock settings (`StockSettingsFragment.kt:112-116`),
and an optional expiration reminder (`ExpirationDateScheduling.kt:17-29`)
whose event text is the date (`ReminderNotificationProcessor.kt:120-122`,
`strings.xml:68`). **Nothing in the dose path reads `hasExpired()`**: the
overview row, the popup and `setReminderEventStatus` treat an expired
medicine's reminder like any other, and the row carries no expiry marker
(`ReminderStringFormatter.kt:31-59` has none). A dose of an expired medicine
is recorded TAKEN with no warning at the point of action.

---

## 11. Anything read from outside the app

None for the journeys. No network permission (§1). The auto-backup writes JSON
to a directory the user chose (`BackupManager.kt`, on every `onResume`,
`MainActivity.kt:308`) and swallows failures (§5); it never reads the directory
back except on a user-initiated restore. Biometric app lock is off by default
(`UserPreferences.kt:83`). Time and zone come from the system.

---

## 12. The debug build, first launch and permissions

`BuildConfig.DEBUG` changes three things the tester would otherwise hit:
the intro slideshow is skipped (`MainActivity.kt:114-122`, `:115`), and the
battery-optimisation and exact-reminder warning cards are never shown
(`:266-273`, `:275-282`). The `POST_NOTIFICATIONS` request still runs on first
launch (`:144-152`) on API 33+, so a **system permission dialog** ("Allow
MedTimer to send you notifications?") appears once; granting it out of band
(`pm grant com.futsch1.medtimer android.permission.POST_NOTIFICATIONS`) before
the first launch avoids it. The launcher activity is `.MainActivity`
(`launchMode singleInstance`, manifest `:46-57`). The debug build also exposes a
test-data generator (`app/src/main/java/com/futsch1/medtimer/GenerateTestData.kt`)
that this study does not use: the fixture is created through the UI or by SQL so
that what the tester asserts was put there by a known path.

---

## 13. Obligations the source suggests, and what the app is expected to earn

Stated as what a user is owed, EU-AI-Act style, before any run. The verdict is
whatever the app earns; these are forecasts, not targets.

| # | obligation | source-based expectation |
|---|---|---|
| O1 | A dose marked Taken is recorded Taken (history) **and** the stock has moved by that dose. | nominal PASS (§4.1) |
| O2 | A dose marked Skipped is recorded Skipped and the stock is unchanged. | nominal PASS |
| O3 | What is displayed after a write is the committed state (overview, Medicine tab). | PASS: reactive flows (§6.1); the scheduled-row duplicate (§6.2) is the risk |
| O4 | A failed write is reported to the user (an app-level message, not a crash). | **FAIL** for every write-failure fault (§5) |
| O5 | The history never claims a dose that was not persisted with its stock effect, and the stock never drifts from the events. | **FAIL** on delete-skipped (§4.4), edit-sheet flip (§4.5), crash between the two writes (§4.1) |
| O6 | A corrupt record is flagged when read, not rendered as sound. | **FAIL** expected: a bad enum crashes the reader, a missing medicine is silently skipped (`ReminderNotificationFactory.kt:38-42`) |
| O7 | Taking more than the stock holds, or at zero, is flagged. | **FAIL** unless an out-of-stock reminder exists (§8.1-8.3) |
| O8 | A medicine that cannot be skipped cannot be skipped anywhere. | **FAIL** from the overview (§9) |
| O9 | An invalid input is rejected (empty name; non-numeric dose). | **FAIL** for the empty name (§4.8); non-numeric dose is accepted with a warning |
| O10 | A missed (raised, unprocessed) reminder stays visible. | PASS: RAISED rows persist and are re-notified (§7.1) |
| O11 | An expired medicine's dose is flagged at the point of action. | **FAIL** (§10) — a design choice to confirm with the user before it becomes an obligation |

Per-fault forecast (the same table goes into `properties/disruption_mapping.yml`'s
header in phase D):

| fault | expected | why |
|---|---|---|
| nominal | PASS | §4.1, §6.1 |
| UE_KILL (force-stop right after Taken) | PASS likely | the two writes take milliseconds; a kill from adb lands after them; the inconsistent window exists but is not reachable deterministically — say so in the results |
| APP_WRITE_FAIL (event update raises) | FAIL | stock moved, event RAISED, crash, no report (O4, O5) |
| DB_ABORT (event insert raises) | FAIL | crash, no report (O4); state stays consistent |
| DB_CORRUPT (event status made unreadable) | FAIL | crash on read, no flag (O6) |
| APP_CACHE_STALE | PASS expected | no cache; the derived views are flows (§6.1); the honest test is cross-tab consistency after a take |
| INFRA_STORAGE_FULL | FAIL | SQLITE_FULL raises, crash, no report (O4) |
| INFRA_STORAGE_MEDIA | FAIL | unreadable store: crash at first query; no honest error (O4) |
| INFRA_SCHED (Doze / inexact alarm) | PASS by API choice | `AllowWhileIdle` (§7.3); observable only on the notification path |
| INPUT_INVALID (empty name) | FAIL | accepted (§4.8) |
| INPUT_OVERLIMIT (dose > stock) | FAIL | clamped silently (§8.1) |
| CANNOT_SKIP (domain variant) | FAIL | overview skips it (§9) |
| DELETE_SKIPPED (domain variant) | FAIL | refund (§4.4) |
| EDIT_FLIP (domain variant) | FAIL | status without stock (§4.5) |

---

## 14. To confirm live before any of this is relied on

- The database file name, its journal mode (`PRAGMA journal_mode`) and the
  presence of `medTimer-wal` / `medTimer-shm`; that `run-as com.futsch1.medtimer
  sqlite3 databases/medTimer` works on the debug build; that enum columns hold
  the names (`SELECT DISTINCT status FROM ReminderEvent`).
- The exact rendered strings of the overview row, the Medicine card and the
  state button's content description, from a UiAutomator dump: "Taken",
  "Skipped", "Reminded", "Please wait…", "N pills left", the "📦 N pills" stock
  fragment, the "HH:MM ➡ HH:MM" time fragment.
- That a scheduled row for a reminder still ahead today is shown, that its
  popup offers Taken / Skipped, and that Taken yields the three writes of §4.2
  in that order (`adb logcat` tags `Reminder`, `StockHandling`).
- How long the scheduled-row duplicate of §6.2 lasts after a take.
- That the debug build shows no intro and only the notification permission
  dialog on first launch; whether `pm grant` before launch suppresses it.
- That a Room exception in the broadcast path really kills the process (inject
  a `BEFORE UPDATE` trigger on `ReminderEvent`, tap Taken, watch `logcat` and
  the crash dialog), and what the tables hold afterwards.
- That the Medicine tab re-collects on re-entry (stock text after a take on the
  overview), and what it shows while an external SQL update is made underneath
  a displayed list.
- That the empty medicine name is accepted and how such a card renders.
- That a non-numeric dose is created despite the inline error.
- That deleting a Skipped row raises the stock (§4.4) and that the edit-sheet
  flip leaves it (§4.5).
- That `cannotBeSkipped` leaves the overview popup's Skipped button in place.
- Whether an unreadable database file (chmod 0000 + force-stop + relaunch)
  crashes at launch or later, and what the screen shows.

---

## 15. Confirmed live (2026-09-29, emulator `medtimer_test`, API 34, foss debug 1.24.0)

Evidence: `notes/ui/*.txt|xml|png` (hierarchy dumps and screenshots from
`notes/probe_ui.py` and `notes/probe_variants.py`) and the database read-backs
they print (`run-as com.futsch1.medtimer sqlite3 databases/medTimer`).

| claim (§) | confirmed | evidence |
|---|---|---|
| store is `databases/medTimer`, WAL, enums stored by name (§2) | ✓ | `PRAGMA journal_mode` = wal; `-wal` / `-shm` present, mode 660 / 600; `status` reads `TAKEN` |
| debug build: no intro, only the notification dialog (§12) | ✓ | first launch landed on the overview with no dialog after `pm grant` |
| add medicine: empty name accepted (§4.8) | ✓ | `Medicine` row `2\|\|0.0\|\|0`; edit screen opened with the hint "Medicine name" as title; a nameless card on the list |
| stock settings: "Amount" / "Unit" dialogs, summary "3 pills" (§3) | ✓ | dump 09 |
| reminder dialog: dose and time fields; the time field ACCEPTS a typed locale string ("11:59 PM") and no picker appeared after a click (§4.8, TimeEditor) | ✓ | dumps 17, 18; `Reminder.timeInMinutes` = 1439 |
| scheduled row today: state "Please wait…", text "11:59 PM, 3 pills / Vitamin C (1)" (§3, §7.2) | ✓ | dump 21 |
| popup on a scheduled row: Taken / Skipped / Reschedule (§4.2) | ✓ | dump 22 |
| Taken: three writes, event TAKEN with stockBefore 3.0 / stockAfter 2.0 / stockHandled 1, stock 2.0 (§4.1, §4.2) | ✓ | read-back `1\|1\|TAKEN\|…\|1\|3.0\|2.0`; `Medicine.amount` 2.0 |
| row after Taken: state "Taken", "11:59 PM ➡ 8:27 AM, 2 pills" (§3) | ✓ | dump 23 |
| medicine card: "Vitamin C (2 pills left)" (§6.3) | ✓ | dump 29 |
| popup on a Taken row: Skipped / Re-raise event / Delete (§4.4) | ✓ | dump 27 |
| edit sheet: Taken / Skipped radio toggle, dismissed with BACK (§4.5) | ✓ | dumps 25, v_skip_edit_05-07 |
| **delete a Skipped dose refunds a unit** (§4.4) | ✓ | stock 3.0 → **4.0**, event DELETED with stockHandled 0 |
| **edit sheet Skipped → Taken moves no stock** (§4.5) | ✓ | event TAKEN, stockHandled 0, stock 3.0 |
| **cannot-be-skipped medicine is still skippable from the overview** (§9) | ✓ | `cannotBeSkipped` = 1, popup still offered Skipped, event SKIPPED |
| delete confirmation: dialog "Confirm", "Are you sure to delete the reminder event?", buttons Yes / Cancel | ✓ | dump v_skip_delete_06 |
| after delete: no row on the overview for the day (§6, DELETED filtered out) | ✓ | dump v_skip_delete_07: no `stateButton` |
| the cannot-be-skipped switch: row "Medicine cannot be skipped" in Medicine settings; tapping the row checks the second `switchWidget` | ✓ | dump v_noskip_skip_02 |

Two facts the source reading did not predict, both binding for the System
Interface:

- **Bottom tabs restore the last screen shown in that tab** (`MainActivity.kt:257-262`,
  `setRestoreState(true)`): after the prelude leaves the edit-medicine screen
  through the Overview tab, tapping the Medicine tab returns to the EDIT screen,
  not the list. Re-tapping the current tab pops to its root. The SI therefore
  ends the prelude on the list (Navigate up from the edit screen) and never
  leaves the list inside the Medicine tab without coming back to it.
- **The reminder time field takes typed text.** The executor's `enter_text`
  types into the first EditText on screen, which in the reminder dialog is the
  dose field, so the time is set with the element-targeted `type_into`.

Fault mechanisms proved on the device through the injector
(`framework/scripts/check_faults.py systems/medtimer`, 2026-09-29): UE_KILL,
APP_WRITE_FAIL, DB_ABORT, DB_CORRUPT, DB_EVENT_LOSS and INFRA_STORAGE_MEDIA each
inject and restore with their probes agreeing (the store's created modes are
660 for the database and 600 for `-wal` / `-shm`, restored as such);
INFRA_STORAGE_FULL fills the partition in 6 s, `df` then shows 0 available and
a SQLite write fails with "database or disk is full (13)". The first sweep
(RESULTS_campaign.md) then showed what the app does under them, with one
lesson for the System Interface: the two writes of a dose action run in a
background broadcast AFTER the tap, so a relaunch issued right after the tap
kills the app before they run, and a fault on the second write (§4.1) is then
never exercised; the write-failure arms now leave the app alone and let the
observe's timeout give it the time. Not yet observed: the §4.1 ordering under
APP_WRITE_FAIL (pending that rerun), and the scheduled-row duplicate window of §6.2 (the row switched to "Taken" within the
two-second settle of the probe; no duplicate was captured).
