# Spliit — Observed Behaviour (ground truth for the behavioural model)

Written 2026-09-25. Source: the local clone at `EVALUATION/spliit/sut/spliit`
(remote `spliit-app/spliit`, commit `d3b151e`, 2025-12-06, "Upgrade
dependencies (#479)"). Everything below was established by READING THE SOURCE.
Nothing was executed against a running instance in this session; §12 lists
what must be confirmed live before it is relied on.

Evidence marks. A file:line reference means I read those lines. Items marked
`(survey)` come from a systematic read of the UI layer done for this note;
the ones marked `✓` were re-checked against the file named. Two paths the
survey had wrong are given correctly here: the create-expense form is
`src/app/groups/[groupId]/expenses/create-expense-form.tsx` and the
reimbursement list is `src/app/groups/[groupId]/reimbursement-list.tsx`.

Sections 2 to 9 describe the application. Section 10 checks the repository's
existing behavioural model (`model/specification_spliit.lnt`) against it.
Section 11 lists the disruptions the source actually admits, with no
expected verdicts. Section 12 is the live checklist.

---

## 1. What Spliit is

An expense-sharing web app: a **group** of **participants** records
**expenses**, each paid by one participant for some of them, and the app
derives who owes whom. Next.js 16 (App Router), tRPC 11, Prisma 6 on
PostgreSQL, zod validation, next-intl with 23 locales over an `en-US` base
(`package.json`). MIT licence.

There are **no accounts and no authentication**. A group is identified by a
random id in its URL, and anyone holding the URL can read and write it. The
app says so itself (`messages/en-US.json`, `Share.warningHelp`: "Every
person with the group URL will be able to see and edit expenses."). Every
tRPC procedure is `baseProcedure` with an empty context (`src/trpc/init.ts`,
survey); there is no middleware to bypass.

---

## 2. Domain and schema (the nouns)

`prisma/schema.prisma`. Ids are **application-generated** `nanoid()` strings
(`src/lib/api.ts:11-13`), not database defaults, so a group's id is minted by
the server at creation and only then appears in the URL.

| Model | Fields that matter | Relations and cascade |
|---|---|---|
| `Group` (`:14-24`) | `id`, `name`, `information?`, `currency` (display symbol, default `"$"`), `currencyCode?` (ISO-4217), `createdAt` | owns `participants[]`, `expenses[]`, `activities[]` |
| `Participant` (`:26-33`) | `id`, `name`, `groupId` | `group` **onDelete: Cascade** (`:29`) |
| `Category` (`:35-40`) | `id Int autoincrement`, `grouping`, `name` | read-only at runtime; rows come from migrations (id 0 = General, id 1 = Payment; survey) |
| `Expense` (`:42-66`) | `id`, `groupId`, `expenseDate` (DATE, default `CURRENT_DATE`), `title`, `categoryId` (default 0), **`amount Int` in minor units**, `originalAmount?`, `originalCurrency?`, `conversionRate Decimal?`, `paidById`, `isReimbursement` (default false), `splitMode` (default `EVENLY`), `createdAt`, `notes?`, `recurrenceRule?` (default `NONE`) | `group` Cascade (`:44`); **`paidBy` Cascade (`:53`)**; `paidFor ExpensePaidFor[]`; `documents ExpenseDocument[]`; `recurringExpenseLink?` |
| `ExpensePaidFor` (`:107-115`) | `expenseId`, `participantId`, `shares Int` (default 1); composite id | both FKs Cascade (`:108-109`) |
| `ExpenseDocument` (`:68-75`) | `id`, `url`, `width`, `height`, `expenseId?` | optional relation, no action declared: deleting the expense **sets `expenseId` to NULL** (survey: `migrations/20240128193431_update_documents`) |
| `RecurringExpenseLink` (`:84-98`) | `id`, `groupId` (no FK), `currentFrameExpenseId` (unique), `nextExpenseCreatedAt?`, `nextExpenseDate` | `currentFrameExpense` Cascade (`:87`) |
| `Activity` (`:117-126`) | `id`, `groupId`, `time` (default now), `activityType`, `participantId?`, `expenseId?`, `data?` | `group` Cascade (`:119`); **`participantId` and `expenseId` are plain strings with no FK** (`:123-124`), so they dangle after a delete |

Enums: `SplitMode` = EVENLY, BY_SHARES, BY_PERCENTAGE, BY_AMOUNT (`:77-82`);
`RecurrenceRule` = NONE, DAILY, WEEKLY, MONTHLY (`:100-105`); `ActivityType`
= UPDATE_GROUP, CREATE_EXPENSE, UPDATE_EXPENSE, DELETE_EXPENSE (`:128-133`).

**The cascade that matters.** Deleting a participant deletes their
`ExpensePaidFor` rows AND **every expense they paid** (`Expense.paidById`,
`onDelete: Cascade`, `:53`), which in turn deletes those expenses' shares and
recurrence links and orphans their documents. §8.3 says when this can happen.

---

## 3. Journeys: what a user can do, and where

Page routes under `src/app` (survey; the five files named in §8 were
resolved and read):

| Route | Kind | What the user does |
|---|---|---|
| `/` | read-only | links to `/groups` |
| `/groups` | read-only + localStorage | recent / starred / archived groups; "Add by URL"; link to create |
| `/groups/create` | **form** | create a group (`GroupForm`) |
| `/groups/[groupId]` | redirect | to `/expenses` |
| `/groups/[groupId]/expenses` | read-only | search, infinite scroll, export, "+" to create |
| `/groups/[groupId]/expenses/create` | **form** | create an expense; also the "Mark as paid" reimbursement flow via query params |
| `/groups/[groupId]/expenses/[expenseId]/edit` | **form + delete** | edit; delete behind a confirm dialog |
| `/groups/[groupId]/balances` | read-only | balance bars; suggested reimbursements with "Mark as paid" |
| `/groups/[groupId]/information` | read-only | the group's free text |
| `/groups/[groupId]/stats` | read-only | totals |
| `/groups/[groupId]/activity` | read-only | the activity log |
| `/groups/[groupId]/edit` | **form** | "Settings": rename group, add / rename / delete participants, pick the local active user |

Non-page routes: `/api/trpc/[trpc]` (GET and POST), `/api/s3-upload`,
`/api/health{,/readiness,/liveness}`, and CSV / JSON export under
`/groups/[groupId]/expenses/export/` (survey).

**There is no way to delete a group.** No `prisma.group.delete` exists
anywhere in `src/lib/api.ts` (✓, the whole file was read); "Remove from
recent" and "Archive" only edit localStorage (survey).

### 3.1 The two forms

`GroupForm` (create and edit): `name`, `currencyCode`, `currency`,
`information`, `participants[].name`; create pre-fills three participants
John / Jane / Jack (survey). A participant row without an `id` is created,
with an `id` is renamed, and one missing from the submitted list is
**deleted** (`api.ts:305-323`).

`ExpenseForm` (create and edit): `expenseDate`, `title`, `category`,
`amount`, optional original amount / currency / conversion rate, `paidBy`,
`paidFor[]` with a share per participant, `splitMode`, `isReimbursement`,
`recurrenceRule`, `notes`, `documents[]` (feature-flagged). Validation is in
§6. A negative amount is accepted and rendered as income (survey).

The "Mark as paid" link on the balances page is not a separate write: it
opens the create-expense form with
`?reimbursement=yes&from=…&to=…&amount=…`
(✓ `src/app/groups/[groupId]/reimbursement-list.tsx:43`), which becomes an
ordinary expense with `isReimbursement = true`.

### 3.2 Per-device state (localStorage, cookie)

Not in the database, but observable and it changes what the tester sees
(survey): `recentGroups`, `starredGroups`, `archivedGroups`;
`${groupId}-activeUser` (who is preselected as payer, and the
`participantId` sent with every mutation, hence the activity author);
`${groupId}-defaultSplittingOptions`; the theme; the `NEXT_LOCALE` cookie.
A fresh browser profile starts with none of these.

---

## 4. Writes: the complete write alphabet

There are exactly **five** mutation procedures (✓ the router tree under
`src/trpc/routers/`). Each maps to one function in `src/lib/api.ts`.

| Procedure | Function | Prisma writes, in order | Atomic? |
|---|---|---|---|
| `groups.create` | `createGroup` (`api.ts:15-34`) | `group.create` with nested `participants.createMany` (`:16-31`) | one statement |
| `groups.update` | `updateGroup` (`:287-327`) | `activity.create` (UPDATE_GROUP, `:295`) then `group.update` with nested participant `deleteMany` / `updateMany` / `createMany` (`:297-325`) | **no**: two round trips |
| `groups.expenses.create` | `createExpense` (`:36-110`) | `activity.create` (CREATE_EXPENSE, `:53-57`, with the expense id minted at `:52`) then `expense.create` with nested shares, documents, recurrence link (`:67-109`) | **no** |
| `groups.expenses.update` | `updateExpense` (`:154-285`) | `activity.create` (UPDATE_EXPENSE, `:174-178`) then `expense.update` with a diffed nested `paidFor` create / update / deleteMany (`:220-249`), recurrence link ops, documents (`:207-284`) | **no** |
| `groups.expenses.delete` | `deleteExpense` (`:112-128`) | `activity.create` (DELETE_EXPENSE, `:118-122`) then `expense.delete` (`:124-127`) | **no** |

Three facts to carry into any specification:

1. **The activity row is written before the domain write, and outside any
   transaction**, in all four logging procedures (`:53`, `:118`, `:174`,
   `:295`). An activity row can therefore exist for a write that then
   failed. `createGroup` logs nothing at all.
2. **No user-initiated write runs in `prisma.$transaction`.** The only
   transaction in the application is the recurring-expense materialiser
   (`:498-552`), see §7.
3. **The `groupId` argument is not enforced on expense reads and writes.**
   `getExpense`, `updateExpense` and `deleteExpense` take a `groupId` but
   their `where` is `{ id: expenseId }` alone (`:383-384`, `:208`, `:125`).
   An expense of group A can be read, edited or deleted through group B's
   endpoints, and the activity row is then logged against B.

Server-side validation is the same zod schema the client uses
(§6), applied by tRPC on the procedure input
(✓ `src/trpc/routers/groups/expenses/create.procedure.ts`,
`update.procedure.ts`). `updateGroup` performs **no check on which
participants it deletes** (✓ `update.procedure.ts`, whole body; `api.ts:305-307`).

---

## 5. Derived state the user observes

### 5.1 Balances (`src/lib/balances.ts`)

`getBalances` (`:16-65`), per expense: the payer's `paid` grows by
`amount` (`:27`); each `paidFor` participant's `paidFor` grows by a share
chosen by split mode (`:39-44`): EVENLY uses `1 / count` and **ignores the
stored shares**; BY_SHARES, BY_PERCENTAGE and BY_AMOUNT all use
`amount × shares / Σshares`. The **last** `paidFor` entry absorbs the
remainder (`:46-49`), so each expense splits exactly before rounding.
Rounding is applied once per participant at the end (`:57-59`), then
`total = paid − paidFor` (`:61-62`). **Reimbursement expenses are included**
(nothing filters `isReimbursement` here).

`getSuggestedReimbursements` (`:101-132`) sorts non-zero balances,
creditors first then by participant id (`:90-99`, deliberately stable so
paying one suggestion does not reshuffle the rest), and pairs the largest
creditor with the last debtor greedily; amounts that round to zero are
dropped (`:131`).

**The balances endpoint returns settlement amounts, not gross figures.**
`groups.balances.list` computes `getBalances`, then the suggestions, then
`getPublicBalances(reimbursements)` and returns THAT as `balances`
(✓ `src/trpc/routers/groups/balances/list.procedure.ts`). A participant
whose net is zero is absent from the map and rendered as 0 (survey). So
"what the Balances tab shows" is a function of the suggestion algorithm,
not only of the expenses.

### 5.2 Split modes, storage versus arithmetic

| Mode | Stored `shares` | `getBalances` | `calculateShare` (`totals.ts:46-65`) |
|---|---|---|---|
| EVENLY | 100 each (string share × 100, `schemas.ts:199-204`), ignored | `amount / count` | `amount / count` |
| BY_SHARES | user value × 100 | `amount·shares/Σ` | `amount·shares/Σ` |
| BY_PERCENTAGE | percent × 100, must total 10000 | `amount·shares/Σ` | `amount·shares/10000` (agrees only because validation forces Σ = 10000) |
| BY_AMOUNT | minor units, must total `amount` | `amount·shares/Σ` | the stored value |

### 5.3 Totals (`src/lib/totals.ts`)

`getTotalGroupSpending` sums `amount` **excluding reimbursements** (`:3-11`);
`getTotalActiveUserPaidFor` likewise for the active user (`:13-24`);
`getTotalActiveUserShare` sums `calculateShare` (`:68-78`), which returns 0
for reimbursements (`:35`) and for a participant not in `paidFor` (`:42`).
Balances include reimbursements; totals exclude them. That is the intended
semantics, not a bug, and a specification has to say which figure it means.

### 5.4 Currency (survey)

Amounts are stored in minor units; the display symbol comes from
`currency`, the formatting from `currencyCode` when set. Per-expense
conversion pulls a rate from `api.frankfurter.app`; if that call fails the
form shows an error with a Refresh link and the expense can still be saved
with the original amount.

### 5.5 The activity log

`logActivity` (`api.ts:425-438`). Rows carry the acting participant (from
localStorage, may be absent), the expense id (pre-minted for creates,
dangling after deletes) and the title as `data`. The list re-joins rows to
expenses and marks a row clickable only if its expense still exists
(`api.ts:395-423`; survey for the rendering).

---

## 6. Validation: what "malformed" means (`src/lib/schemas.ts`)

Group (`:6-33`): `name` 2..50 chars; `currency` 1..5; `currencyCode` three
letters or empty; at least one participant, each name 2..50, **no duplicate
names** (`duplicateParticipantName`).

Expense (`:50-192`):

| Rule | Key | Text shown (survey, `messages/en-US.json`) |
|---|---|---|
| title present, ≥ 2 chars | `titleRequired`, `min2` | "Please enter a title." / "Enter at least two characters." |
| amount present, numeric | `amountRequired`, `invalidNumber` | "You must enter an amount." / "Invalid number." |
| amount ≠ 0 | `amountNotZero` | "The amount must not be zero." |
| amount ≤ 10 000 000 00 | `amountTenMillion` | "The amount must be lower than 10,000,000." |
| conversion rate > 0 | `ratePositive` | "The rate must be strictly greater than zero." |
| a payer is selected | `paidByRequired` | "You must select a participant." |
| at least one paid-for | `paidForMin1` | "The expense must be paid for at least one participant." |
| every share > 0 | `noZeroShares` | "All shares must be higher than 0." |
| BY_AMOUNT: shares sum to amount | `amountSum` | "Sum of amounts must equal the expense amount." |
| BY_PERCENTAGE: shares sum to 100 % | `percentageSum` | "Sum of percentages must equal 100." |

Two things the rules do NOT say: a **negative** amount is valid (only zero
is rejected, `:71`), and the same schema runs twice, client-side on major
units and server-side on minor units (survey), so the ten-million bound
means different things on the two sides and the server is the binding one.

Validation errors are shown inline under the field (survey). This is the
one failure the UI reports in words.

---

## 7. Read-time side effects: recurring expenses

There is no scheduler. `getGroupExpenses` calls
`createRecurringExpenses()` as its first statement (`api.ts:344`), and
`getGroupExpenses` backs the expense list, the balances and the stats
(✓ `balances/list.procedure.ts`; survey for stats). So:

- **Reads mutate the database.** Opening any group's expense list can create
  expenses.
- The materialiser is **global**: its `findMany` has no `groupId` filter
  (`:454-460`); one user's read materialises every group's due expenses.
- Each due link spawns a chain in a `while` loop, one expense plus one new
  link per missed period (`:479-568`), inside the only `$transaction` in
  the app (`:498-552`), guarded against double creation by
  `where: { id, nextExpenseCreatedAt: null }` (`:541-545`).
- Documents are `connect`-ed to the new expense (`:513-519`): since the FK is
  single-valued, that **moves** them off the original.
- A failed transaction is caught, logged to the console, and breaks the
  chain silently (`:553-562`). The user sees nothing.
- Monthly recurrence on the 29th to 31st drifts permanently to the smallest
  day encountered; the source says so (`:592-597`).

---

## 8. Failure and edge behaviour

### 8.1 A failed write is silent

There is **no `error.tsx` anywhere under `src/app`** (✓ `find`). The forms
call `await mutateAsync(...)` with no `catch` and no toast (✓
`src/app/groups/create/create-group.tsx:15`,
`src/app/groups/[groupId]/expenses/create-expense-form.tsx:21-40`). On
rejection the submit button simply re-enables and the page stays put; the
only success signal is the navigation to the group and the row appearing in
the refetched list (survey). Delete goes through `AsyncButton`, whose
`catch` swallows the error (✓ `src/components/async-button.tsx:24`). For an
ioco tester this means: **a failed create, update or delete is observed as
quiescence**, not as an error output.

### 8.2 No client-side optimism

Every flow is mutate → invalidate → navigate; the create-expense form does
not even await the invalidation before navigating (✓
`create-expense-form.tsx:39-40`). The expense list and balances
re-invalidate on mount; stats and activity do not and can serve a cached
value for up to 30 s after an edit (survey, `src/trpc/query-client.ts`).

Measured live (2026-09-28, headless Chrome through the proxy, fresh group):
the create-expense form invalidates only `groups.expenses` (✓
`create-expense-form.tsx:39`), never `groups.stats.get`, and the query
client's `staleTime` is 30 s (✓ `query-client.ts:8`). Open Stats on the
empty group (`$0.00`), create a $40.00 expense, reopen Stats: the total
reads `$0.00` at once and is still `$0.00` six seconds later; a reload
shows `$40.00`. Open Stats for the first time only after the write: the
skeleton is shown until the fetch lands and the first value rendered is
`$40.00`, no placeholder. So the stale total is seen exactly when the
Stats query was warmed before the write, which is what the SI's
APP_CACHE_STALE branch does, and never on the nominal order.

Activity behaves the same (measured 2026-09-28, same probe): open Activity on
the empty group ("There is not yet any activity in your group."), create the
expense, reopen Activity: still the empty sentence; a reload shows
"Expense “Dinner C” created by Someone." at once. `groups.activities` is not
in the create form's invalidation either.

### 8.3 Deleting a participant who has expenses

Through the UI it is blocked: the settings form receives
`participantsWithExpenses` (✓ `src/trpc/routers/groups/getDetails.procedure.ts:17-18`,
`src/app/groups/[groupId]/edit/edit-group.tsx:22`) and disables the trash
button for those rows. Through the API it is allowed: `groups.update` has no
such check (✓ `update.procedure.ts`), `updateGroup` deletes every participant
missing from the payload (`api.ts:305-307`), and Postgres cascades to every
expense they paid (§2). No activity rows are written for the vanished
expenses; only one UPDATE_GROUP row.

### 8.4 Not found

`groups.get` returns `{ group: null }` rather than throwing; the group
layout then raises a destructive toast "This group does not exist." and
stays in its loading branch forever (✓ `layout.client.tsx:15-31`).
`groups.getDetails` and `groups.expenses.get` throw `NOT_FOUND` (survey);
the edit-group page then falls back to the create defaults and the
edit-expense page renders blank (survey). Export routes return 404 (survey).

### 8.5 Concurrency

No optimistic locking, no version column, no transaction on user writes.
`updateExpense` and `updateGroup` compute their nested diffs from a
snapshot read before the write (`api.ts:163`, `:292`), so two concurrent
edits can try to create the same `(expenseId, participantId)` share or
delete each other's additions. Last write wins otherwise.

### 8.6 External dependencies (survey)

Environment is parsed at import time, so a missing required variable
crashes at boot rather than degrading. Documents (S3), receipt extraction
and category extraction (OpenAI) are behind flags that default to **off**;
when off, their UI does not render at all. When on and failing: uploads
show a toast with Retry; the title-blur category guess has no error
handling and leaves the selector spinning. The currency-rate API failing is
shown in the form. Database failure makes `/api/health` return 503 while
`/api/health/liveness` still returns 200.

---

## 9. Alphabet summary: entity → observable states → the write that changes it

| Entity | Observable | Changed by |
|---|---|---|
| Group | exists (URL resolves) / "This group does not exist."; name in the header; information tab; currency on every amount | `groups.create` → `group.create`; `groups.update` → `group.update`. No delete. |
| Participant set | names in settings, payer select, paid-for checkboxes, balance rows; protected vs deletable | only `groups.update` → nested createMany / updateMany / deleteMany; deletion cascades to expenses paid |
| Expense | present / absent in the list; title, amount, date, category, reimbursement style, paperclip count | `expenses.create` → `expense.create`; `expenses.update` → `expense.update`; `expenses.delete` → `expense.delete`; auto-create by the materialiser on any read; cascade-delete via participant removal |
| Shares (`ExpensePaidFor`) | per-participant amount on the form; every balance | nested in create / update; cascade |
| Documents | thumbnails, count badge | nested in create / update; orphaned on expense delete; moved by the materialiser |
| Activity | the activity tab; clickable iff the expense exists | `activity.create` before every logged write; never for group creation |
| Balances (derived) | bars; "X owes Y" suggestions; "Your balance:" on a card | no write; a pure function of expenses, shares and split mode, then of the suggestion algorithm |
| Totals (derived) | "Total group spendings", "Your total spendings", "Your total share" | no write; excludes reimbursements |
| Category table | the picker | read-only; migrations |
| localStorage / cookie | recent, starred, archived; active user; default split; theme; locale | client only, never the database |

---

## 10. The existing behavioural model, checked against the source

`model/specification_spliit.lnt` (processes USER, APP, DATABASE, DISRUPTOR,
INFRA_DISRUPTOR, SPEC) and `model/spliit_types.lnt`, composed with the
System Interface in `model/compose_spliit.lnt`.

### 10.1 Gate by gate

| Gate in the model | In the source | Assessment |
|---|---|---|
| `CREATE_GROUP (grp)` → `GROUP_CREATED (grp, created)` | `groups.create`; the id is minted server-side and captured from the URL | Real. The model never produces `failed` (APP always answers `created`, `spec:73-74`). |
| `ADD_MEMBER (grp, member)` ×2, then hidden in the composition | there is no "add member" write; participants are created with the group (three defaults) or by `groups.update` | Invented as a separate step. In the app it is either part of `CREATE_GROUP` or an `UPDATE_GROUP`. |
| `CREATE_EXPENSE (grp, id, Amount (50))` | `groups.expenses.create` | Real. The model pins one amount; `Amount (val : Nat)` is otherwise unbounded (`types:29-32`). |
| `WRITE_DB` → `DATA_PERSISTED (id, PERSISTED \| FAILED)` (hidden) | two writes, activity then expense, no transaction | The abstraction hides the pre-write activity row and merges two statements into one. `FAILED` is a status the app never reports: a failed write is silence (§8.1). |
| `BALANCE_SAVED (id, status)` | the balances page, which shows settlement amounts (§5.1) | The observable is a page, not a status; what the page shows depends on the suggestion algorithm, which the model does not describe. |
| `CONFIRM_SPLIT` → `SPLIT_ACCEPTED` | "Mark as paid" = create a reimbursement expense (§3.1) | Real but mis-typed: it is a `CREATE_EXPENSE` with `isReimbursement`, and "accepted" is the suggestion disappearing. |
| `UE2_MALFORMED` → `VALIDATION_ERROR` | zod, inline messages (§6) | Real, and the only failure the UI reports in words. |
| `UE1_OFFLINE` | none: the fault proxy has one mechanism, 503 on every `/api/trpc/*` while ANY fault is active (`sut/fault_middleware.py:103-109`) | Not distinguishable from `APP_TIMEOUT`. |
| `APP_TIMEOUT (grp)` | the same 503 | Real mechanism; what the UI owes in response is nothing (§8.1), which the specification must decide is acceptable or not. |
| `APP2_CONFLICT`, `DB1_ROLLBACK`, `DB2_SLOW_QUERY`, `NET_CONGESTION`, `HIGH_LATENCY` | no injection exists; not in the System Interface; not in `model/spliit.io` | Spec-only nondeterminism, never exercised. |

### 10.2 What the model does not say that the source makes central

Participants as state (creation, renaming, deletion and its cascade); split
modes and shares; reimbursements as ordinary expenses; edit and delete;
the activity log and its pre-write timing; recurring materialisation on
read; the cross-group scope hole (§4, item 3); the absence of any error
output on a failed write; balances as settlement amounts.

### 10.3 The fault artefacts do not belong to this model

`properties/disruption_mapping.yml` is keyed on
`"DISRUPTION_OCCURS !SENSOR_TIMEOUT (AMOUNT_INPUT)"` and eight siblings.
`DISRUPTION_OCCURS` is not a gate of `specification_spliit.lnt` (✓, whole
file read). The file describes a different system's taxonomy; the only
thing every entry does is POST to the proxy, which then blocks all tRPC.

### 10.4 What has actually been measured

`generated/logs/spliit_taxonomy_matrix.log` (2026-06-09) and
`generated/spliit_results.json` record the normal trace `tc_a4.aut` as
PASS ten times: once as "NORMAL" and nine times under a disruption key. In
all ten runs the report line reads `Fault : none` (✓, ten occurrences),
the log contains **no activation call** to the proxy (✓, zero matches), and
`tc_a4.aut` contains no `DISRUPTION_OCCURS` label for the key to match
(✓, its labels are `NAVIGATE_TO`, `WAIT_FOR`, `CLICK`, `TYPE_INTO`,
`OBSERVE`, `CREATE_EXPENSE`, `WRITE_DB`, `DATA_PERSISTED`, `BALANCE_SAVED`,
`LOCK`). **The nine "disruption" results are nine repetitions of the
normal run; no fault has ever been applied to Spliit through this
pipeline.** What stands is: the normal trace passes against the real app
through the proxy on port 3002.

---

## 11. Disruptions the source actually admits

Each entry names a real mechanism and what a specification would have to
state. No expected verdict is given; the verdict is what the app earns.

1. **Write aborted at the store.** A Postgres trigger `BEFORE INSERT ON
   "Expense"` that raises. Because the activity row is written first
   (§4), the observable consequence is specific: the Activity tab shows
   "Expense _title_ created by …" as a non-clickable row while the expense
   list does not contain it, and the form gives no error. The
   specification must say whether an activity entry for a write that did
   not happen is acceptable.
2. **Service unavailable during a write** (the proxy's 503, or the
   database down). The UI owes, today, nothing: the button re-enables.
   Distinguishing "the SUT reported the failure" from "the SUT said
   nothing" is exactly the quiescence question.
3. **Participant removed while they have expenses**, through the API. Not
   reachable from the UI (§8.3), so it is a fault of the tester's own
   making unless the model admits API-level actors. If admitted, the
   observable is expenses vanishing with no activity entries.
4. **Stale derived views.** Edit an expense, then open Stats or Activity
   within 30 s (§8.2). Observable as a total that has not moved.
5. **Recurring materialisation failing silently** (§7). Observable only as
   an expected expense that is absent on a later day; needs clock control.
6. **Cross-group expense id** (§4, item 3). An edit or delete addressed to
   the wrong group succeeds; observable in the wrong group's activity log.
7. **Currency-rate API unreachable.** The one external failure the UI
   reports in words (§8.6); a natural `X_WARNING`-style observable.
8. **Concurrent edits of one expense** (§8.5). Needs two sessions; the
   observable is a unique-key error, which the UI swallows (§8.1).

---

## 12. To confirm live before any of this is relied on

- That a rejected `groups.expenses.create` really produces no visible
  message (§8.1): submit with a trigger armed, capture the page.
- That the activity row survives an aborted expense insert (§4, §11.1).
- The exact strings and elements the tester will anchor on: the "owes"
  line, the balance bars, the empty states, the not-found toast.
- ~~The stale window for Stats and Activity (§8.2), measured.~~ Stats
  measured 2026-09-28 (§8.2): stale for the whole 30 s `staleTime` once
  warmed before the write. Activity not yet measured.
- Whether server-rendered pages still load while `/api/trpc/*` returns
  503, i.e. what the proxy's single mechanism actually blocks.
- Which of the three feature flags the running container has on
  (`container.env`; the example ships them off).
- The materialiser's global reach across groups on a shared database
  (§7), if two groups will ever coexist in a test run.
