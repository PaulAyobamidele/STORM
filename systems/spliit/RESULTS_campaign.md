# Spliit — campaign results (2026-09-28)

Eleven test purposes, sixteen generated cases, twelve walks that count (the eleven
canonical cases and two fault-first variants). Every
verdict below was earned by a walk whose log is in `run_*.out` and whose effect is
in the database (one fresh group per walk, name `ioco group`, newest first in
the queries quoted). Nothing here is inferred from a purpose's intent.

Stack: `spliit-app-1` (Next.js 16 / tRPC 11 / Prisma 6) + `spliit-db-1`
(Postgres 17), driven through the fault proxy on :3002 (`sut/fault_middleware.py`).
Model: `model/specification_spliit.lnt` (SPEC, 486 states) composed with
`model/system_interface_spliit.lnt` (COMPOSED: 3719 states, 4497 transitions,
no `i`), generated on narval with TESTOR `-all` + `extract_all`.

## Verdicts

| purpose (case walked) | verdict | obligation | what the walk saw | database after the walk |
|---|---|---|---|---|
| nominal | **PASS** | — | `CONFIRM oracle OK: SpendBand, LogState` on `$40.00`, `expense “dinner c” created by someone.` | 1 expense, 1 activity row |
| input_invalid | **PASS** | O1 met | zod message shown (`REJECT_SHOWN`), then `CONFIRM !REJECTED !S0 !UNLOGGED` on `$0.00`, `there is not yet any activity in your group.` | 0 / 0 |
| ue_kill | **PASS** | consistent | user left right after Create; on return `$40.00` + logged: the request had completed | 1 / 1 |
| app_extapi_fail (variant 4) | **PASS** | O6 met | hosts line pointed `api.frankfurter.app` at 127.0.0.1; form showed `oops, we could not get the most recent rates. enter a custom rate below.`; write committed, `CONFIRM` S1 + logged | 1 / 1 |
| input_overlimit | **FAIL** | **O1** | amount 20 000 000: no message at `WAIT_FOR !EL_REJECT_MESSAGE`; state offers no quiescence | 0 / 0 (server refused, said nothing) |
| app_unavailable | **FAIL** | **O4** | proxy 503 on `/api/trpc/*` (probe confirmed); no message at `WAIT_FOR !EL_WRITE_ERROR` | 0 / 0 |
| db_abort | **FAIL** | **O4** (O5 in the data) | BEFORE INSERT trigger confirmed (`pg_trigger` = 1); no message | **0 expenses, 1 activity row "Dinner C"** — the log claims a write that never happened |
| infra_db_down | **FAIL** | **O4** (see note) | `docker pause` confirmed; no message within the 10 s window | **1 / 1** — the request hung and completed after the 25 s unpause |
| weekly | **FAIL** | **O2** | write dated `@date-8` (2026-09-20) with recurrence Weekly; Stats `$80.00`; activity names the write once; `OBSERVE !EL_ACTIVITY_COPY` never appeared | 2 expenses (2026-09-20, 2026-09-27), **1 activity row** — the materialised copy is unlogged |
| app_cache_stale (variant 4) | **FAIL** | **O3** | Stats opened before the write (`$0.00`), then written, then read: `$0.00` → S0, model says S1 | 1 / 1 |
| app_cache_stale (canonical) | **FAIL** | **O3** | failed at the SECOND plain write, before the fault: `$40.00` → S1, model says S2 | 2 / 2 — the second write committed, Stats did not move |
| db_corrupt | **FAIL** | **O7** | first write fine (`CONFIRM` S1 + logged); split rows deleted by SQL (probe: 0 rows); the row opens with no notice (`OBSERVE !EL_CORRUPT_NOTICE` never appeared) | 1 / 1, 0 `ExpensePaidFor` rows |

4 PASS, 8 FAIL (7 purposes, one of them twice), 0 UNEXECUTABLE, 0 INCONCLUSIVE.
Forecasts written in `properties/disruption_mapping.yml` before the first run:
all eleven matched, except UE_KILL, which was left open and came out PASS.

### Notes on three verdicts

- **infra_db_down** is a FAIL against the specification as written (an output was
  owed within the tester's window and none came), but the write was not lost: it
  landed after the database returned. The violated obligation is "the user is
  told", not "the write is kept". A specification that admits a delayed commit
  would need a timeout observable Spliit does not have.
- **app_cache_stale, canonical case** never reached its fault. The SI's own
  read-back of Stats after a write warms the 30 s cache (`query-client.ts:8`,
  `staleTime: 30 * 1000`; `create-expense-form.tsx:39` invalidates only
  `groups.expenses`), so the next write within 30 s reads a stale total. Variants
  1–3 of this purpose and of app_extapi_fail begin with one to three plain writes
  and would fail the same way; only variant 4 (fault first) measures its fault.
  Activity has the same window (behaviour note §8.2).
- **db_abort** shows O5 in the data (activity row without the expense), but the
  walk stops at the first non-conformance (O4), so O5 was never reached by a
  CONFIRM. It is a finding of the database query, not a verdict.

## How a verdict was earned

- A PASS required the checkpoint oracle to agree on every declared type
  (`type_description.yml`: `SpendBand` role `band`, `LogState` role `names`),
  logged as `CONFIRM oracle OK: … agree with '<label>' on [...]`. A bare
  `checkpoint CONFIRM — advance` would have meant nothing was checked.
- A FAIL came either from the oracle (`CONFIRM mismatch — SpendBand: AUT expects
  S1, observed '$0.00'`) or from an owed observable that never appeared at a
  state whose generated case offers no `:DELTA:` (`the specification required an
  output here and none appeared`). Where a case offers quiescence, absence is
  INCONCLUSIVE; where the apparatus failed, UNEXECUTABLE. Neither occurred.
- Every injected fault was confirmed by its probe before the walk went on, and
  restored and re-probed after it (`Disruption restored and confirmed cleared`).
  DB_CORRUPT and APP_EXTAPI_FAIL declare no restore probe (nothing to restore:
  fresh group; hosts line removed by hand) and say so in the log.

## Threats to validity

1. **A first batch was discarded.** Its DB_ABORT trigger was never removed (the
   walker collected injected faults and restored none of them), so five later
   cases ran with every insert aborted; INFRA_DB_DOWN's pause was backgrounded by
   a shell precedence slip and reported FAIL unconfirmed; the activity selector
   `(//main//em)[1]` turned an empty list into a timeout. All three are fixed in
   the framework or the properties, and the batch above was run from a verified
   clean stack (trigger 0, db unpaused, proxy faults `{}`). The database rows of
   that batch remain (groups created 11:19–11:21 on the first pass are the
   trustworthy ones; earlier `ioco group` rows are not).
2. **Framework changes made during the campaign**, all SUT-agnostic and
   self-tested: the declared-type checkpoint oracle (`observation_oracle.py`);
   `timing: none` and per-probe mechanisms (`disruptor.py`); restore after every
   walk; unconfirmed injection → UNEXECUTABLE; an owed observable's absence
   judged by the case; relative dates (`@date-8`); the two-call pointer-sequence
   click and native-setter typing for React (`executors.py`). The first Spliit
   PASS predates the oracle and was vacuous; it is not counted.
3. **Model changes made during the campaign**: the DISRUPTOR's `i` branch was
   removed (it made every composed state divergent, TESTOR marked every state
   quiescent, and no silent SUT could fail); the UE_KILL arm now names the gate
   before the click it shares with the commit arm. Both regenerated on narval;
   the case counts did not change (16).
4. **Every expense is 40.00.** The band counts rows in rungs of one expense; with a
   25.00 weekly row the model's S2 would have read as S1 — a tester artefact.
   Titles, not amounts, tell rows apart. Spliit's arithmetic is not under test.
5. **Windows.** The quiescence window is the harness timeout (10 s). The stale
   window is Spliit's 30 s `staleTime`; every read-back in this campaign happened
   inside it.
6. **Not measured.** Variants 1–3 of app_cache_stale and app_extapi_fail (they
   fail on O3 before their fault, see above). `coverage.svl` was not run.
   `verify_restored` is absent for DB_CORRUPT and APP_EXTAPI_FAIL.

## Files

`generated/tc/tc_*.aut` (canonical) and `generated/tc/variants/` (16 cases);
`run_<case>.out` per walk; `notes/observed_behaviour.md` (source-grounded
behaviour, live measurements of both stale windows); `properties/*.yml`;
`test_purposes/tp_*.lnt`; `testor/generate_tc_all.sh`.
