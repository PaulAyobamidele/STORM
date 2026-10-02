# Spliit: evaluation facts (campaign 2, 2026-10-01)

Current campaign: the 48 cases generated 2026-10-01 17:34 (`model_size.txt:1`) and walked
2026-10-01 22:52–23:14 (`variants_nominal.log:1`, `variants_app_extapi_fail.log:1`). Their
generator inputs match the current model (§5). `RESULTS_campaign.md` describes the
superseded 16-case campaign of 2026-09-28 (`RESULTS_campaign.md:1-3`,
`runs/2026-09-28_16cases/README.md:1`) and is not used below. All paths are relative to
`systems/spliit/`.

## 1. Candidate headlines

1. **Spliit-7 (db_corrupt, 12 FAILs):** the split rows of every expense in the group were
   deleted and the probe confirmed it (`generated/variant_logs/db_corrupt/v1.log:27`);
   the opened row showed no notice where `DB_CORRUPT_DETECTED` is owed and the case
   offers no `:DELTA:` (`generated/variant_logs/db_corrupt/v1.log:29`).
2. **Spliit-4 (db_abort, 4 FAILs):** with an abort trigger confirmed on the expense
   insert (`generated/variant_logs/db_abort/v1.log:18`), no write error appeared
   (`generated/variant_logs/db_abort/v1.log:22`). The source writes the activity row
   before the insert, outside any transaction (`sut/spliit/src/lib/api.ts:52-57`).
3. **Spliit-6 (app_cache_stale, 8 FAILs):** after the Stats view was opened before a
   committed write, the total read back did not move, e.g. `$0.00` where one expense was
   committed (`generated/variant_logs/app_cache_stale/v8.log:16`).

## 2. Setup facts

- **App:** Spliit, package version `0.1.0` (`sut/spliit/package.json:3`), clone at
  commit `d3b151e` (2025-12-06) (`notes/observed_behaviour.md:4`, verified with
  `git log` in `sut/spliit`). Next.js 16, tRPC 11, Prisma 6 over PostgreSQL
  (`notes/observed_behaviour.md:27`).
- **Deployment:** `docker compose up -d` in `sut/spliit` gives `spliit-app-1` (:3000) and
  `spliit-db-1` (Postgres 17); the walk goes through the fault proxy on :3002
  (`properties/disruption_mapping.yml:9-12`).
- **Driving:** the web executor through `framework/scripts/run.py --platform html --url
  http://localhost:3002` (`run_variants.sh:67-73`). Fixture user: NOT RECORDED. Each case
  creates its own group, so no seeding is done (`run_variants.sh:26-27`).
- **Journeys the model covers:** create an expense (`ADD` / `CONFIRM`), open a row
  (`VIEW` / `DETAIL`), delete a row (`REMOVE` / `CONFIRM`); `CONFIRM` reads back the
  total and the activity log (`model/specification_spliit.lnt:5-7`).
- **Left out:** NOT RECORDED as a list. The source admits participant deletion and
  cross-group edits (`notes/observed_behaviour.md:149-153`, `:323-333`), and no
  purpose exercises them (§4).
- **Suite construction:** `testor -all` then `extract_all` per purpose
  (`testor/generate_tc_all.sh:5`, `:124`, `:142`). Cases per purpose:
  `gen_times.tsv:2-12`.

## 3. Obligations

| ID | Obligation in plain words | Witnessed by (gates) | path:line |
|---|---|---|---|
| O1 | a rejected save is reported | `REJECT_SHOWN` | `model/specification_spliit.lnt:11` |
| O2 | the log covers every row a write made, also weekly copies | `CONFIRM … LOGGED` | `model/specification_spliit.lnt:12` |
| O3 | the total shown is the committed one | `CONFIRM` band after `APP_CACHE_STALE` | `model/specification_spliit.lnt:13` |
| O4 | a failed save is reported | `WRITE_ERROR_SHOWN` | `model/specification_spliit.lnt:14` |
| O5 | the log never claims a write that failed | `CONFIRM … UNLOGGED` after a rollback | `model/specification_spliit.lnt:15` |
| O6 | a failed rate lookup is reported | `RATE_ERROR_SHOWN` | `model/specification_spliit.lnt:16` |
| O7 | a corrupt record is flagged when opened | `DB_CORRUPT_DETECTED` | `model/specification_spliit.lnt:17` |
| O8 | a delete drops the total and is logged | `CONFIRM … DELETED`, band one rung down | `model/specification_spliit.lnt:18` |

## 4. Purposes

| Code name | Layer | What the test does (fault mechanism, when it strikes) | Obligation | Confirmed by probe? | path:line |
|---|---|---|---|---|---|
| nominal | NOMINAL | no fault: write, read back, open the row, delete it, read back | O2, O8 | n/a | `test_purposes/tp_nominal.lnt:3`, `:34` |
| input_invalid | INPUT | amount `0` typed into the form | O1 | n/a (`timing: none`) | `test_purposes/tp_input_invalid.lnt:3`; `properties/concrete_domain.yml:103`; `model/system_interface_spliit.lnt:311` |
| input_overlimit | INPUT | amount `20000000` typed into the form | O1 | n/a (`timing: none`) | `test_purposes/tp_input_overlimit.lnt:3`; `properties/concrete_domain.yml:104`; `model/system_interface_spliit.lnt:373` |
| weekly | INPUT | a weekly recurring expense dated eight days back | O2 | n/a (`timing: none`) | `test_purposes/tp_weekly.lnt:3`; `properties/concrete_domain.yml:109`; `model/system_interface_spliit.lnt:247` |
| ue_kill | UE | after Create is clicked, the user navigates away and comes back; realised by the SI's own steps | O5 | n/a (`timing: none`) | `test_purposes/tp_ue_kill.lnt:3`, `:38`; `properties/disruption_mapping.yml:24-26`; `model/system_interface_spliit.lnt:167` |
| app_unavailable | APP | the proxy answers 503 on `/api/trpc/*`, switched on before the Create click | O4 | yes (`/admin/fault/status`) | `test_purposes/tp_app_unavailable.lnt:3`, `:38`; `properties/disruption_mapping.yml:32-43`; `model/system_interface_spliit.lnt:135` |
| app_cache_stale | APP | the Stats view is opened before the write, so its cache is warm when the total is read; realised by the SI's own steps | O3 | n/a (`timing: none`) | `test_purposes/tp_app_cache_stale.lnt:3`, `:33`; `properties/disruption_mapping.yml:28-30`; `model/system_interface_spliit.lnt:426` |
| app_extapi_fail | APP | `api.frankfurter.app` resolves to 127.0.0.1 (hosts line placed by hand), before the currency is picked | O6 | yes (hosts line present); restore not probed | `test_purposes/tp_app_extapi_fail.lnt:3`, `:33`; `properties/disruption_mapping.yml:45-61`; `model/system_interface_spliit.lnt:489` |
| db_abort | DB | a BEFORE INSERT trigger on `Expense` raises, installed before the Create click | O4, O5 | yes (`pg_trigger` count) | `test_purposes/tp_db_abort.lnt:3`, `:38`; `properties/disruption_mapping.yml:63-77`; `model/system_interface_spliit.lnt:144` |
| db_corrupt | DB | the split rows of every expense in the walk's group are deleted by SQL, while a row is being opened | O7 | yes (rows exist and have no splits); restore not probed | `test_purposes/tp_db_corrupt.lnt:3`, `:41`; `properties/disruption_mapping.yml:79-90`; `model/system_interface_spliit.lnt:575` |
| infra_db_down | INFRA | `docker pause spliit-db-1` before the Create click, unpaused after 25 s | O4 | yes (`State.Paused`) | `test_purposes/tp_infra_db_down.lnt:3`, `:38`; `properties/disruption_mapping.yml:92-105`; `model/system_interface_spliit.lnt:153` |

## 5. Campaign identity

| Item | Value |
|---|---|
| Name and date | Spliit campaign 2, generated 2026-10-01 17:34 (`model_size.txt:1`), walked 2026-10-01 22:52–23:14 (`variants_ue_kill.log:1`, `variants_app_extapi_fail.log:1`) |
| Matches the current model | yes. 19 of the 20 hashes in `gen_inputs.md5:1-20` equal the current files. The exception, `testor/generate_tc_all.sh` (`gen_inputs.md5:9`), was edited after generation to also write `ctg_sizes.tsv` (`testor/generate_tc_all.sh:129-130`); it changes no case. Checked by recomputing md5 on 2026-10-02 |
| Composed model size | 15983 states / 19714 transitions (`model_size.txt:4-5`) |
| Purposes | 11 (`gen_times.tsv:2-12`) |
| Test cases | 48 (`gen_times.tsv:2-12`; one row each in `variants_*.log`) |
| PASS / FAIL / INCONCLUSIVE / UNEXECUTABLE | 14 / 34 / 0 / 0 (§6) |
| Generation time | 589 s, the sum of `gen_times.tsv:2-12` |
| Walk time | 711 s, the sum of the `TIME_S` column of the 11 `variants_*.log` |
| How measured | generation: `date +%s` around each purpose on the CADP node (`testor/generate_tc_all.sh:116`); walk: bash `SECONDS` around each run.py call (`run_variants.sh:66`, `:75`) |
| Parallel devices | none recorded; the driver walks cases one after another (`run_variants.sh:57-89`) |
| Code revision | `64b9e19` (dirty) for 10 purposes, `dc1bf6e` (dirty) for app_extapi_fail (line 1 of each `variants_*.log`); the dirty `framework/` diff is saved as `generated/variant_logs/<purpose>/framework.*.diff` |

## 6. Results by purpose

| Purpose | Layer | Cases | P | F | I | U | One-line cause |
|---|---|---|---|---|---|---|---|
| nominal | NOMINAL | 1 | 1 | 0 | 0 | 0 | write, open, delete all read back as owed |
| input_invalid | INPUT | 1 | 1 | 0 | 0 | 0 | "the amount must not be zero." shown |
| input_overlimit | INPUT | 1 | 0 | 1 | 0 | 0 | no reject message for 20,000,000 |
| weekly | INPUT | 1 | 0 | 1 | 0 | 0 | weekly copy has no activity entry |
| ue_kill | UE | 4 | 4 | 0 | 0 | 0 | consistent read-back after leaving |
| app_unavailable | APP | 4 | 0 | 4 | 0 | 0 | no write error after a 503 |
| app_cache_stale | APP | 8 | 0 | 8 | 0 | 0 | total read back did not move |
| app_extapi_fail | APP | 8 | 8 | 0 | 0 | 0 | rate-lookup message shown |
| db_abort | DB | 4 | 0 | 4 | 0 | 0 | no write error after an aborted insert |
| db_corrupt | DB | 12 | 0 | 12 | 0 | 0 | corrupt row opened without notice |
| infra_db_down | INFRA | 4 | 0 | 4 | 0 | 0 | no write error with the database paused |
| **Total** | | **48** | **14** | **34** | **0** | **0** | |

Rows: `variants_<purpose>.log:3-14`.

| Purpose | CTG states / transitions (`ctg_sizes.tsv`) | Test-case size, states/transitions, min – max (`variants_*.log`) |
|---|---|---|
| nominal | 2140 / 3724 (`:2`) | 1068/1775 (`variants_nominal.log:3`) |
| ue_kill | 614 / 1069 (`:3`) | 82/85 – 124/127 (`variants_ue_kill.log:5`, `:6`) |
| app_unavailable | 622 / 1061 (`:4`) | 58/58 – 122/122 (`variants_app_unavailable.log:5`, `:4`) |
| app_cache_stale | 1365 / 2404 (`:5`) | 27/27 – 93/93 (`variants_app_cache_stale.log:10`, `:3`) |
| app_extapi_fail | 1427 / 2497 (`:6`) | 33/33 – 99/99 (`variants_app_extapi_fail.log:10`, `:3`) |
| db_abort | 622 / 1061 (`:7`) | 58/58 – 122/122 (`variants_db_abort.log:5`, `:4`) |
| db_corrupt | 1680 / 2910 (`:8`) | 38/38 – 114/114 (`variants_db_corrupt.log:14`, `:9`) |
| infra_db_down | 622 / 1061 (`:9`) | 58/58 – 122/122 (`variants_infra_db_down.log:5`, `:4`) |
| input_invalid | 1106 / 1925 (`:10`) | 776/1254 (`variants_input_invalid.log:3`) |
| input_overlimit | 1106 / 1925 (`:11`) | 776/1254 (`variants_input_overlimit.log:3`) |
| weekly | 1231 / 2168 (`:12`) | 803/1343 (`variants_weekly.log:3`) |

## 7. Case cards

Counterexamples below are the shortest label path in the case's `.aut` from the initial
state to the failing state named in the walk log, abstract labels only (UI steps
omitted). The walk logs do not record which branch a step took.

#### Spliit-1  An over-limit amount is refused without a message
    Purpose / test case : tp_input_overlimit / tc_input_overlimit.1.aut
    Disruption          : none; INPUT_OVERLIMIT is a typed value, amount 20000000
                          (properties/concrete_domain.yml:104; disruption_mapping.yml:111-113)
    Where it struck     : the Create click after the amount is typed
                          (model/system_interface_spliit.lnt:373)
    Obligation          : O1 (model/specification_spliit.lnt:11)
    What the app did    : the reject element never appeared
                          (generated/variant_logs/input_overlimit/v1.log:17); app on screen: NOT RECORDED
    Verdict and why     : FAIL, missing output without δ: "State 45 waits for WAIT_FOR
                          !EL_REJECT_MESSAGE … does NOT permit quiescence"
                          (generated/variant_logs/input_overlimit/v1.log:17, :19)
    Counterexample      : ADD !JOHN !EXP_C !OVERLIMIT !ONCE > (WAIT_FOR !EL_REJECT_MESSAGE)
    Class               : NOMINAL
    Silent failure?     : no disruption; no message of any kind recorded
    Root cause in app   : the server bound is in minor units, amount <= 10_000_000_00
                          (sut/spliit/src/lib/schemas.ts:72), checked on major units in the
                          browser (notes/observed_behaviour.md:248-251, marked survey); the form
                          awaits the mutation with no catch and no toast
                          (sut/spliit/src/app/groups/[groupId]/expenses/create-expense-form.tsx:33-41)
    Data store evidence : NOT RECORDED (only the fault state is logged, v1.log tail)
    Repeat of           : none
    Separate from nominal? : yes (nominal PASS, variants_nominal.log:3)
    By design?          : none found
    Forecast            : "FAIL expected: silent server rejection" (properties/disruption_mapping.yml:127); held
    Reproduced          : walked once
    Doubts              : the case is one branching case (776 states, variants_input_overlimit.log:3);
                          one route through it was walked

#### Spliit-2  The weekly expense's materialised copy has no activity entry
    Purpose / test case : tp_weekly / tc_weekly.1.aut
    Disruption          : none; WEEKLY recurrence dated "@date-8" (properties/concrete_domain.yml:109)
    Where it struck     : the activity read after the weekly write
    Obligation          : O2 (model/specification_spliit.lnt:12)
    What the app did    : total "$80.00" (generated/variant_logs/weekly/v1.log:45); activity
                          "expense “bus pass b” created by someone." once (v1.log:48)
    Verdict and why     : FAIL, missing output without δ: "State 123 waits for OBSERVE
                          !EL_ACTIVITY_COPY … does NOT permit quiescence" (v1.log:16, :18)
    Counterexample      : ADD !JACK !EXP_B !VALID !WEEKLY > (OBSERVE !EL_ACTIVITY_COPY)
    Class               : NOMINAL
    Silent failure?     : no disruption; the total counts two rows, the log names one
    Root cause in app   : createRecurringExpenses (sut/spliit/src/lib/api.ts:440) contains no
                          logActivity call; the only call sites are api.ts:53, :118, :174, :295
    Data store evidence : NOT RECORDED (the total "$80.00" is the screen reading)
    Repeat of           : none
    Separate from nominal? : yes
    By design?          : none found
    Forecast            : "FAIL expected: the copy has no log entry" (properties/disruption_mapping.yml:128); held
    Reproduced          : walked once
    Doubts              : one route through a branching case (803 states, variants_weekly.log:3)

#### Spliit-3  A request refused with 503 gives no write error
    Purpose / test case : tp_app_unavailable / tc_app_unavailable.1-4.aut
    Disruption          : APP_UNAVAILABLE (APP), proxy 503 on /api/trpc/*, timing gate
                          (properties/disruption_mapping.yml:32-43); "injected and confirmed":
                          v1.log:18, v2.log:18, v3.log:15, v4.log:15; restored and confirmed:
                          v1.log:23, v2.log:23, v3.log:20, v4.log:20
                          (generated/variant_logs/app_unavailable/)
    Where it struck     : before the Create click (model/system_interface_spliit.lnt:135-136);
                          on a second write in v1, v2 (state 36), on the first in v3, v4 (state 14)
    Obligation          : O4 (model/specification_spliit.lnt:14)
    What the app did    : the write-error element never appeared (v1.log:19-20); app on screen: NOT RECORDED
    Verdict and why     : FAIL, missing output without δ: v1.log:22, v2.log:22, v3.log:19, v4.log:19
    Counterexample      : v1: ADD !JOHN !EXP_B > CONFIRM !COMMITTED !S1 !LOGGED !EXP_B >
                          ADD !JOHN !EXP_A > APP_UNAVAILABLE > (WAIT_FOR !EL_WRITE_ERROR);
                          v3: ADD !JOHN !EXP_B > APP_UNAVAILABLE > (WAIT_FOR !EL_WRITE_ERROR)
    Class               : MISSING-REPORT
    Silent failure?     : yes, no report of the failure observed; explicit success: NOT RECORDED
    Root cause in app   : the form awaits the mutation with no catch and no toast
                          (sut/spliit/src/app/groups/[groupId]/expenses/create-expense-form.tsx:33-41);
                          no error.tsx under src/app (notes/observed_behaviour.md:286-295)
    Data store evidence : NOT RECORDED; fault state after the walk only (v1.log:71-74)
    Repeat of           : none
    Separate from nominal? : yes
    By design?          : none found
    Forecast            : "FAIL expected: no report on a failed save" (properties/disruption_mapping.yml:120); held
    Reproduced          : 4 cases, each walked once, same outcome
    Doubts              : the failed write is EXP_A or EXP_B in all four, not the purpose's
                          target expense (IDF := defaultExpense, test_purposes/tp_app_unavailable.lnt:33)

#### Spliit-4  An aborted insert gives no write error
    Purpose / test case : tp_db_abort / tc_db_abort.1-4.aut
    Disruption          : DB_ABORT (DB), BEFORE INSERT trigger on "Expense", timing gate
                          (properties/disruption_mapping.yml:63-77); "injected and confirmed":
                          v1.log:18, v2.log:18, v3.log:15, v4.log:15; restored and confirmed:
                          v1.log:23, v2.log:23, v3.log:20, v4.log:20 (generated/variant_logs/db_abort/)
    Where it struck     : before the Create click (model/system_interface_spliit.lnt:144-145);
                          second write in v1, v2 (state 36), first write in v3, v4 (state 14)
    Obligation          : O4 (model/specification_spliit.lnt:14); O5 not reached
    What the app did    : the write-error element never appeared; app on screen: NOT RECORDED
    Verdict and why     : FAIL, missing output without δ: v1.log:22, v2.log:22, v3.log:19, v4.log:19
    Counterexample      : v1: ADD !JOHN !EXP_B > CONFIRM !COMMITTED !S1 !LOGGED !EXP_B >
                          ADD !JOHN !EXP_A > DB_ABORT > (WAIT_FOR !EL_WRITE_ERROR);
                          v3: ADD !JOHN !EXP_B > DB_ABORT > (WAIT_FOR !EL_WRITE_ERROR)
    Class               : MISSING-REPORT
    Silent failure?     : yes, no report observed; explicit success: NOT RECORDED
    Root cause in app   : create-expense-form.tsx:33-41 as Spliit-3; the activity row is written
                          before the insert, outside any transaction (sut/spliit/src/lib/api.ts:52-57;
                          notes/observed_behaviour.md:142-145)
    Data store evidence : NOT RECORDED (no per-case query of Expense / Activity)
    Repeat of           : none
    Separate from nominal? : yes
    By design?          : none found
    Forecast            : "FAIL expected: no report, and the log names the write" (properties/disruption_mapping.yml:123); the no-report half held, the log half was not observed
    Reproduced          : 4 cases, each walked once
    Doubts              : the failed write is EXP_A or EXP_B, not the target; O5 (the activity
                          row) is not checked in this campaign

#### Spliit-5  A paused database gives no write error
    Purpose / test case : tp_infra_db_down / tc_infra_db_down.1-4.aut
    Disruption          : INFRA_DB_DOWN (INFRA), docker pause, unpause after 25 s, timing gate
                          (properties/disruption_mapping.yml:92-105); "injected and confirmed":
                          v1.log:18, v2.log:18, v3.log:15, v4.log:15; restored and confirmed:
                          v1.log:23, v2.log:23, v3.log:20, v4.log:20 (generated/variant_logs/infra_db_down/)
    Where it struck     : before the Create click (model/system_interface_spliit.lnt:153-154);
                          second write in v1, v2 (state 36), first in v3, v4 (state 14)
    Obligation          : O4 (model/specification_spliit.lnt:14)
    What the app did    : the write-error element never appeared; app on screen: NOT RECORDED
    Verdict and why     : FAIL, missing output without δ: v1.log:22, v2.log:22, v3.log:19, v4.log:19
    Counterexample      : v1: ADD !JOHN !EXP_B > CONFIRM !COMMITTED !S1 !LOGGED !EXP_B >
                          ADD !JOHN !EXP_A > INFRA_DB_DOWN > (WAIT_FOR !EL_WRITE_ERROR)
    Class               : MISSING-REPORT + TIMING
    Silent failure?     : yes, no report observed within the window; explicit success: NOT RECORDED
    Root cause in app   : create-expense-form.tsx:33-41 as Spliit-3
    Data store evidence : NOT RECORDED
    Repeat of           : none
    Separate from nominal? : yes
    By design?          : none found
    Forecast            : "FAIL expected: no report on a failed save" (properties/disruption_mapping.yml:125); held
    Reproduced          : 4 cases, each walked once
    Doubts              : the pause lasts 25 s (disruption_mapping.yml:102) and the wait is the
                          walker's timeout (TIMEOUT 10, run_variants.sh:73); a report arriving after the
                          window, or the write landing after the unpause, is not observed

#### Spliit-6  The total read back after a write does not move when Stats was opened first
    Purpose / test case : tp_app_cache_stale / tc_app_cache_stale.1-8.aut
    Disruption          : APP_CACHE_STALE (APP), the SI opens Stats before the write, timing none
                          (properties/disruption_mapping.yml:28-30; model/system_interface_spliit.lnt:426);
                          "realised by the System Interface's own steps": v1.log:22, v2.log:19 … v8.log:13
                          (generated/variant_logs/app_cache_stale/)
    Where it struck     : the Stats read after the target write
    Obligation          : O3 (model/specification_spliit.lnt:13)
    What the app did    : v1 "$120.00" for S_MORE (v1.log:25); v2–v4 "$80.00" for S3 (v2.log:22,
                          v3.log:22, v4.log:22); v5–v7 "$40.00" for S2 (v5.log:19, v6.log:19,
                          v7.log:19); v8 "$0.00" for S1 (v8.log:16). In v3, v6, v7 the activity
                          read also lacked the write, LogState classified UNLOGGED (v3.log:23,
                          v6.log:20, v7.log:20)
    Verdict and why     : FAIL, oracle mismatch on SpendBand (v1.log:25, :27 … v8.log:16, :18)
    Counterexample      : v8: APP_CACHE_STALE > ADD !JOHN !EXP_C !VALID !ONCE >
                          CONFIRM !COMMITTED !S1 (observed S0)
    Class               : STALE
    Silent failure?     : yes, a value contradicting the committed state is shown with no
                          indication; explicit success: no message recorded
    Root cause in app   : query staleTime 30 s (sut/spliit/src/trpc/query-client.ts:8); the
                          create form invalidates only groups.expenses
                          (sut/spliit/src/app/groups/[groupId]/expenses/create-expense-form.tsx:39);
                          live measurement in notes/observed_behaviour.md:305-321
    Data store evidence : NOT RECORDED
    Repeat of           : none
    Separate from nominal? : yes (the SI's other branches reload before reading,
                          model/system_interface_spliit.lnt:174, :251)
    By design?          : none found
    Forecast            : "FAIL expected: Stats served from a 30 s cache" (properties/disruption_mapping.yml:121); held
    Reproduced          : 8 cases, each walked once
    Doubts              : v1, v2, v4, v5 write the target title "Dinner C" a second time (the
                          SI's branch assigns defaultExpense without a title check,
                          model/system_interface_spliit.lnt:436); v3, v6, v7, v8 do not

#### Spliit-7  A row whose split rows were deleted opens without notice
    Purpose / test case : tp_db_corrupt / tc_db_corrupt.1-12.aut
    Disruption          : DB_CORRUPT (DB), SQL deletes ExpensePaidFor of every expense in the
                          newest group, timing gate (properties/disruption_mapping.yml:79-90);
                          "injected and confirmed": v1.log:27, v2.log:27, v3.log:24, v4.log:24,
                          v5.log:24, v6.log:24, v7.log:21, v8.log:21, v9.log:21, v10.log:18,
                          v11.log:18, v12.log:18 (generated/variant_logs/db_corrupt/)
    Where it struck     : after VIEW of a row, before its notice is read (model/system_interface_spliit.lnt:575)
    Obligation          : O7 (model/specification_spliit.lnt:17)
    What the app did    : the corrupt-notice element never appeared; app on screen: NOT RECORDED
    Verdict and why     : FAIL, missing output without δ: v1.log:29, v2.log:29, v3.log:26,
                          v4.log:26, v5.log:26, v6.log:26, v7.log:23, v8.log:23, v9.log:23,
                          v10.log:20, v11.log:20, v12.log:20
    Counterexample      : v12: ADD !JOHN !EXP_C > CONFIRM !COMMITTED !S1 !LOGGED !EXP_C >
                          VIEW !ROW_C > DB_CORRUPT > (OBSERVE !EL_CORRUPT_NOTICE);
                          v1: … REMOVE !ROW_C > CONFIRM !COMMITTED !S2 !DELETED !EXP_C >
                          VIEW !ROW_B > DB_CORRUPT > (OBSERVE !EL_CORRUPT_NOTICE)
    Class               : INTEGRITY
    Silent failure?     : yes, the record opens with no notice; explicit success: NOT RECORDED
    Root cause in app   : NOT ESTABLISHED
    Data store evidence : probe at injection: rows exist and have no splits
                          (properties/disruption_mapping.yml:90); afterwards NOT RECORDED
    Repeat of           : none
    Separate from nominal? : yes
    By design?          : none found
    Forecast            : "FAIL expected: no warning on a split-less row" (properties/disruption_mapping.yml:124); held
    Reproduced          : 12 cases, each walked once
    Doubts              : the fault corrupts every expense of the group, not a single row;
                          verify_restored is not declared (v1.log:30)

#### Spliit-8  The reference walk: write, open, delete (PASS)
    Purpose / test case : tp_nominal / tc_nominal.1.aut
    Disruption          : none
    What the app did    : "$40.00" and "expense “dinner c” created by someone." (generated/variant_logs/nominal/v1.log:14);
                          edit page title "dinner c" (v1.log:17); after delete "$0.00" and
                          "expense “dinner c” deleted by someone." (v1.log:20)
    Verdict and why     : PASS (v1.log:24); every checkpoint matched (v1.log:14, :17, :20)
    Obligation          : O2, O8
    Doubts              : one route through a branching case of 1068 states (variants_nominal.log:3)

#### Spliit-9  A failed rate lookup is reported (PASS)
    Purpose / test case : tp_app_extapi_fail / tc_app_extapi_fail.1.aut (all 8 cases PASS)
    Disruption          : APP_EXTAPI_FAIL (APP), hosts line for api.frankfurter.app,
                          "injected and confirmed" (generated/variant_logs/app_extapi_fail/v1.log:23)
    What the app did    : "oops, we could not get the most recent rates. enter a custom rate below."
                          (v1.log:114); the write then committed, "$160.00" (v1.log:26)
    Verdict and why     : PASS (v1.log:32)
    Obligation          : O6
    Doubts              : verify_restored not declared (v1.log:29); v1, v2, v3, v5 write
                          "Dinner C" twice (model/system_interface_spliit.lnt:495)

## 8. Tester-side and UNEXECUTABLE runs

The current campaign has no tester-side FAIL and no UNEXECUTABLE row (§6). Runs voided
before it, archived and not counted:

| Case(s) | What went wrong in the apparatus | Evidence | Fixed? |
|---|---|---|---|
| sweep of 2026-09-30, 16 rows | weekly writes left open in fault purposes' histories; the walker read a click at a VIEW-or-CLICK state | `runs/2026-10-01_aborted_weekly_in_history/README.md:7-14` | yes |
| sweep of 2026-10-01 22:44, 2 rows | DELETED check matched a title and "deleted by" in different entries | `runs/2026-10-01_aborted_and_phrase/README.md:3-6` | yes |
| db_corrupt, 3 rows | the fault targeted one title, which some cases had deleted | `runs/2026-10-01_db_corrupt_wrong_row/README.md:3-8` | yes |
| app_extapi_fail, 5 rows | the rate-error selector matched the Next.js `<script>` payload | `runs/2026-10-01_extapi_script_match/README.md:3-7` | yes |

## 9. Counts

- FAIL total 34 = RQ1 FAILs 2 (Spliit-1, Spliit-2) + repeats 0 + tester-side 0 +
  disruption FAILs 32 (Spliit-3 to Spliit-7).
- Disruption FAILs by class: MISSING-REPORT 12 (Spliit-3: 4, Spliit-4: 4, Spliit-5: 4,
  of which Spliit-5's 4 also TIMING); STALE 8 (Spliit-6); INTEGRITY 12 (Spliit-7).
  12 + 8 + 12 = 32.
- Purposes split across two classes: none.
- Silent-failure cases (the app proceeds without observing the disruption): 32
  (Spliit-3 to Spliit-7). Cases showing success explicitly: NOT RECORDED, because no screen
  captures were kept and the walk records only the absence of the owed element.

## 10. Do not claim

- That the failed writes in Spliit-3, -4, -5 left the store unchanged, or that Spliit-4
  left a dangling activity row: no per-case store query exists.
- That the app stayed on its screen, or showed success: no captures.
- That the purposes' target write was the one struck: in Spliit-3, -4, -5 the failed
  write is EXP_A or EXP_B.
- Any result for the routes of the four single-case purposes (nominal, input_invalid,
  input_overlimit, weekly) other than the one walked.
- That Spliit-5's report never comes: the window is the walker's timeout, the pause 25 s.
- Single-row corruption: the fault corrupts the whole group.
- Restore of DB_CORRUPT and APP_EXTAPI_FAIL: not probed.
- Results of the superseded 16-case campaign (`RESULTS_campaign.md`) as part of this one.
- That any behaviour is intended: no design intent was found for any FAIL.
