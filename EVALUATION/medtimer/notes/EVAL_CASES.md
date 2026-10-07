# MedTimer — evaluation cases (campaign two)

Every claim carries `path:line` relative to the repository root. Walk logs and
screen captures live under `EVALUATION/medtimer/generated/variant_logs/` (local, not
committed: 316 MB); the test cases, CTGs and sweep rows are committed.

## 1. System and scope

MedTimer 1.24.0 (Android, Kotlin, Room/SQLite; F-Droid flavour debug build of the
clone at `EVALUATION/medtimer/sut/medtimer`, commit abd1950), installed on two identical Android 14 emulators
(AVD `medtimer_test` and its twin `medtimer_test2`, same system image, same APK).
The model covers creating a medicine, forbidding skips, marking a scheduled dose
Taken or Skipped, deleting and editing a dose record, and re-reading a dose after
a relaunch, on a fixture of two medicines and four doses tonight. Out of scope:
notifications and alarms, the manual-dose journey, refills, over-limit doses,
expiry (EVALUATION/medtimer/notes/DISRUPTION_COVERAGE.md:47-50).

## 2. The normal run

Ordering 1 of `tp_nominal` (EVALUATION/medtimer/Test_Purposes/tp_nominal.lnt); each step's gates are in the specification
(EVALUATION/medtimer/model/specification_medtimer.lnt:62, EVALUATION/medtimer/model/specification_medtimer.lnt:232, EVALUATION/medtimer/model/specification_medtimer.lnt:236, EVALUATION/medtimer/model/specification_medtimer.lnt:274, EVALUATION/medtimer/model/specification_medtimer.lnt:305,
EVALUATION/medtimer/model/specification_medtimer.lnt:389). Every write and re-read ends in `CONFIRM (status, stock, state, dose)`.

- **S1** create a medicine with a valid name: `ADD_MEDICINE (VALID)` then `MEDICINE_SHOWN`; the user sees the medicine's edit screen (EVALUATION/medtimer/Test_Purposes/tp_nominal.lnt:51)
- **S2** mark Vitamin C's 11:57 PM dose Taken: `ACT (d_a1, TAKE)` then `CONFIRM`; the user sees row 'Taken', card 'Vitamin C (2 pills left)' (EVALUATION/medtimer/Test_Purposes/tp_nominal.lnt:55)
- **S3** relaunch and re-read that dose: `VIEW (d_a1)` then `CONFIRM`; the user sees row 'Taken', 2 pills left (EVALUATION/medtimer/Test_Purposes/tp_nominal.lnt:75)
- **S4** delete that dose's record: `DELETE (d_a1)` then `CONFIRM`; the user sees row gone, 3 pills left (EVALUATION/medtimer/Test_Purposes/tp_nominal.lnt:106)
- **S5** relaunch and re-read: `VIEW (d_a1)` then `CONFIRM`; the user sees no row, 3 pills left (EVALUATION/medtimer/Test_Purposes/tp_nominal.lnt:118)
- **S6** mark the 11:58 PM dose Skipped: `ACT (d_a2, SKIP)` then `CONFIRM`; the user sees row 'Skipped', 3 pills left (EVALUATION/medtimer/Test_Purposes/tp_nominal.lnt:145)
- **S7** relaunch and re-read: `VIEW (d_a2)` then `CONFIRM`; the user sees row 'Skipped', 3 pills left (EVALUATION/medtimer/Test_Purposes/tp_nominal.lnt:163)
- **S8** set Vitamin C to 'cannot be skipped': `NO_SKIP (med_a)`; the user sees the switch on (EVALUATION/medtimer/Test_Purposes/tp_nominal.lnt:184)
- **S9** mark the 11:59 PM dose Taken: `ACT (d_a3, TAKE)` then `CONFIRM`; the user sees row 'Taken', 2 pills left (EVALUATION/medtimer/Test_Purposes/tp_nominal.lnt:190)
- **S10** relaunch and re-read: `VIEW (d_a3)` then `CONFIRM`; the user sees row 'Taken', 2 pills left (EVALUATION/medtimer/Test_Purposes/tp_nominal.lnt:207)
- **S11** mark Zinc's 11:56 PM dose Taken: `ACT (d_b, TAKE)` then `CONFIRM`; the user sees row 'Taken', card 'Zinc (1 pills left)' (EVALUATION/medtimer/Test_Purposes/tp_nominal.lnt:235)
- **S12** relaunch and re-read: `VIEW (d_b)` then `CONFIRM`; the user sees row 'Taken', 1 pill left (EVALUATION/medtimer/Test_Purposes/tp_nominal.lnt:252)
- **S13** edit the 11:59 PM record to Skipped: `EDIT (d_a3, SKIP)` then `CONFIRM`; the user sees row 'Skipped', owed 3 pills left (EVALUATION/medtimer/Test_Purposes/tp_nominal.lnt:289)

## 3. Obligations

| ID | Obligation in plain words | Gate(s) that witness it | `path:line` |
|---|---|---|---|
| O1 | a dose marked Taken is recorded Taken and its medicine loses one pill | `ACT`, `CONFIRM` | EVALUATION/medtimer/model/specification_medtimer.lnt:16 |
| O2 | a dose marked Skipped is recorded Skipped and no stock moves | `ACT`, `CONFIRM` | EVALUATION/medtimer/model/specification_medtimer.lnt:17 |
| O3 | after a write the committed state is shown, also when the list was read just before | `APP_CACHE_STALE`, `CONFIRM` | EVALUATION/medtimer/model/specification_medtimer.lnt:18 |
| O4 | a failed write is reported and nothing moved | `WRITE_ERROR_SHOWN`, `CONFIRM (ROLLED_BACK…)` | EVALUATION/medtimer/model/specification_medtimer.lnt:20 |
| O5 | the stock follows the records (delete, correction, lost record) | `DELETE`, `EDIT`, `DB_EVENT_LOSS`, `CONFIRM` | EVALUATION/medtimer/model/specification_medtimer.lnt:21 |
| O6 | a corrupt record (status or stock) is flagged | `DB_CORRUPT_DETECTED` | EVALUATION/medtimer/model/specification_medtimer.lnt:24 |
| O7 | an unreadable store is reported | `INFRA_STORAGE_ERROR` | EVALUATION/medtimer/model/specification_medtimer.lnt:25 |
| O8 | a medicine that cannot be skipped is not skipped | `NO_SKIP`, `CONFIRM (REJECTED…)` | EVALUATION/medtimer/model/specification_medtimer.lnt:26 |
| O9 | an invalid (empty) name is refused | `REJECT_SHOWN` | EVALUATION/medtimer/model/specification_medtimer.lnt:27 |

## 4. Campaign identity

| Item | Value |
|---|---|
| Campaign name and date | campaign two, generated 2026-10-01/02 on narval3, walked 2026-10-02 |
| Matches the current model? (how verified) | yes: every md5 in `EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/inputs.md5` equals the current file in `model/`, `testor/`, `Test_Purposes/` (checked file by file) |
| Composed model size (states / transitions) | 2887562 / 4117530 (EVALUATION/medtimer/model_size.txt:4) |
| Purposes | 14 (EVALUATION/medtimer/gen_times.tsv) |
| Test cases | 240, one TESTOR test case per accepting branch of a purpose (EVALUATION/medtimer/testor/generate_tc_all.sh) |
| PASS / FAIL / INCONCLUSIVE / UNEXECUTABLE | 59 / 181 / 0 / 0 in the final rows; 2 earlier attempts were UNEXECUTABLE and were walked again (§7) |
| Generation time / walk time | 5069 s / 67115 s |

`EVALUATION/medtimer/RESULTS_campaign.md` describes campaign one (a superseded model, 13
cases) and is not used here; the totals above agree with `eval_tables.py --paper`
(EVALUATION/medtimer/runs/2026-10-02_campaign2/paper_table.txt).

## 5. Results by purpose

| Purpose | Layer | Cases | P | F | I | U | One-line cause |
|---|---|---|---|---|---|---|---|
| nominal | NOMINAL | 3 | 0 | 3 | 0 | 0 | the edit sheet moves no stock at S13 |
| input_invalid | INPUT | 1 | 0 | 1 | 0 | 0 | an empty name is accepted |
| cannot_skip | INPUT | 1 | 0 | 1 | 0 | 0 | a 'cannot be skipped' dose is skipped |
| delete_skipped | INPUT | 1 | 0 | 1 | 0 | 0 | deleting a Skipped dose refunds a pill |
| edit_flip | INPUT | 1 | 0 | 1 | 0 | 0 | editing Skipped → Taken consumes no pill |
| ue_kill | USER | 39 | 36 | 3 | 0 | 0 | FAILs are the edit / delete-skipped stock defects; the kill itself left no half-done write the walk observed |
| app_write_fail | APP | 39 | 0 | 39 | 0 | 0 | no error shown; the record update fails, a take or delete moves the stock anyway |
| app_cache_stale | APP | 21 | 14 | 7 | 0 | 0 | FAILs are all edit writes (edit-sheet defect); the cache itself held |
| db_abort | DB | 19 | 0 | 19 | 0 | 0 | no error shown; nothing recorded |
| db_corrupt | DB | 20 | 0 | 20 | 0 | 0 | no flag; MedTimer not on screen |
| db_corrupt_stock | DB | 20 | 0 | 20 | 0 | 0 | no flag; app stays up |
| db_event_loss | DB | 16 | 9 | 7 | 0 | 0 | a lost Taken record leaves its pill consumed (7); a lost Skipped record or the other medicine is fine (9) |
| infra_storage_full | INFRA | 39 | 0 | 39 | 0 | 0 | no error shown; nothing written (35 app up, 4 not on screen) |
| infra_storage_media | INFRA | 20 | 0 | 20 | 0 | 0 | no storage error; MedTimer not on screen |
| **total** | | **240** | **59** | **181** | **0** | **0** | |

## 6. Case cards

One card per FAIL (181), no INCONCLUSIVE was returned, and two PASSes.

### nominal

#### MedTimer-1  Editing the 11:59 PM record from Taken to Skipped gives no pill back (ordering 1)
```
Purpose / test case : tp_nominal / tc_nominal.1.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/nominal/tc_nominal.1.aut; branch 1 of the purpose, row EVALUATION/medtimer/variants_nominal.log:3)
Disruption          : none
Where it struck     : S13 (edit the 11:59 PM record to Skipped), after the edit sheet is dismissed (BACK); orderings differ only in the position of S1 and S11-S12
The obligation      : O5, a correction moves the stock with it (EVALUATION/medtimer/model/specification_medtimer.lnt:21; EVALUATION/medtimer/model/specification_medtimer.lnt:305, EVALUATION/medtimer/model/specification_medtimer.lnt:248)
What the app did    : the card still reads 2 pills: EVALUATION/medtimer/generated/variant_logs/nominal/v1.log:1883 ("CONFIRM mismatch — StockBand: AUT expects S3, observed 'vitamin c (2 pills left)' classifies as S2")
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/nominal/v1.log:1883; verdict EVALUATION/medtimer/generated/variant_logs/nominal/v1.log:1894
Counterexample      : `EDIT !D_A3 !SKIP` → `TAP !CV_BACK` → `WAIT_FOR !EL_ROW_A3` → `OBSERVE !EL_STATE_A3` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S3 !SKIPPED !D_A3`
Failure class       : NOMINAL
Silent failure?     : no (no disruption)
Root cause in app   : `EditEventViewModel.updateEvent` copies the chosen status into the row and does a plain UPDATE with no stock handling (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/EditEventViewModel.kt:124, EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/EditEventViewModel.kt:139)
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/nominal/v1.log:2112–2119): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|SKIPPED|1|3.0|2.0
Separate evidence?  : yes, this is the nominal baseline
Forecast            : "FAIL at the edit (last step): the edit sheet moves no stock" (EVALUATION/medtimer/properties/disruption_mapping.yml:148); held
Reproduced          : three orderings, three FAILs at the same step (MedTimer-1 to -3)
Doubts              : none recorded
```

#### MedTimer-2  Editing the 11:59 PM record from Taken to Skipped gives no pill back (ordering 2)
```
Purpose / test case : tp_nominal / tc_nominal.2.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/nominal/tc_nominal.2.aut; branch 2 of the purpose, row EVALUATION/medtimer/variants_nominal.log:4)
Disruption          : none
Where it struck     : S13 (edit the 11:59 PM record to Skipped), after the edit sheet is dismissed (BACK); orderings differ only in the position of S1 and S11-S12
The obligation      : O5, a correction moves the stock with it (EVALUATION/medtimer/model/specification_medtimer.lnt:21; EVALUATION/medtimer/model/specification_medtimer.lnt:305, EVALUATION/medtimer/model/specification_medtimer.lnt:248)
What the app did    : the card still reads 2 pills: EVALUATION/medtimer/generated/variant_logs/nominal/v2.log:1927 ("CONFIRM mismatch — StockBand: AUT expects S3, observed 'vitamin c (2 pills left)' classifies as S2")
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/nominal/v2.log:1927; verdict EVALUATION/medtimer/generated/variant_logs/nominal/v2.log:1938
Counterexample      : `EDIT !D_A3 !SKIP` → `TAP !CV_BACK` → `WAIT_FOR !EL_ROW_A3` → `OBSERVE !EL_STATE_A3` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S3 !SKIPPED !D_A3`
Failure class       : NOMINAL
Silent failure?     : no (no disruption)
Root cause in app   : `EditEventViewModel.updateEvent` copies the chosen status into the row and does a plain UPDATE with no stock handling (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/EditEventViewModel.kt:124, EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/EditEventViewModel.kt:139)
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/nominal/v2.log:2156–2163): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 4|3|SKIPPED|1|3.0|2.0
Separate evidence?  : yes, this is the nominal baseline
Forecast            : "FAIL at the edit (last step): the edit sheet moves no stock" (EVALUATION/medtimer/properties/disruption_mapping.yml:148); held
Reproduced          : three orderings, three FAILs at the same step (MedTimer-1 to -3)
Doubts              : none recorded
```

#### MedTimer-3  Editing the 11:59 PM record from Taken to Skipped gives no pill back (ordering 3)
```
Purpose / test case : tp_nominal / tc_nominal.3.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/nominal/tc_nominal.3.aut; branch 3 of the purpose, row EVALUATION/medtimer/variants_nominal.log:5)
Disruption          : none
Where it struck     : S13 (edit the 11:59 PM record to Skipped), after the edit sheet is dismissed (BACK); orderings differ only in the position of S1 and S11-S12
The obligation      : O5, a correction moves the stock with it (EVALUATION/medtimer/model/specification_medtimer.lnt:21; EVALUATION/medtimer/model/specification_medtimer.lnt:305, EVALUATION/medtimer/model/specification_medtimer.lnt:248)
What the app did    : the card still reads 2 pills: EVALUATION/medtimer/generated/variant_logs/nominal/v3.log:1903 ("CONFIRM mismatch — StockBand: AUT expects S3, observed 'vitamin c (2 pills left)' classifies as S2")
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/nominal/v3.log:1903; verdict EVALUATION/medtimer/generated/variant_logs/nominal/v3.log:1914
Counterexample      : `EDIT !D_A3 !SKIP` → `TAP !CV_BACK` → `WAIT_FOR !EL_ROW_A3` → `OBSERVE !EL_STATE_A3` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S3 !SKIPPED !D_A3`
Failure class       : NOMINAL
Silent failure?     : no (no disruption)
Root cause in app   : `EditEventViewModel.updateEvent` copies the chosen status into the row and does a plain UPDATE with no stock handling (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/EditEventViewModel.kt:124, EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/EditEventViewModel.kt:139)
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/nominal/v3.log:2132–2139): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|SKIPPED|1|3.0|2.0
Separate evidence?  : yes, this is the nominal baseline
Forecast            : "FAIL at the edit (last step): the edit sheet moves no stock" (EVALUATION/medtimer/properties/disruption_mapping.yml:148); held
Reproduced          : three orderings, three FAILs at the same step (MedTimer-1 to -3)
Doubts              : none recorded
```

### input_invalid

#### MedTimer-4  An empty medicine name is accepted
```
Purpose / test case : tp_input_invalid / tc_input_invalid.1.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/input_invalid/tc_input_invalid.1.aut; branch 1 of the purpose, row EVALUATION/medtimer/variants_input_invalid.log:3)
Disruption          : none (INPUT domain variant driven by the System Interface, `timing: none`)
Where it struck     : in place of S1: the tester creates a medicine with an empty name
The obligation      : O9, an invalid name is refused (EVALUATION/medtimer/model/specification_medtimer.lnt:27; EVALUATION/medtimer/model/specification_medtimer.lnt:62)
What the app did    : no name error appeared: EVALUATION/medtimer/generated/variant_logs/input_invalid/v1.log:1193 ("State 80 waits for OBSERVE !EL_NAME_ERROR — it never appeared and this state does NOT permit quiescence. The specification required an output here and none appeared: CONFORM")
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/input_invalid/v1.log:1193; verdict EVALUATION/medtimer/generated/variant_logs/input_invalid/v1.log:1204
Counterexample      : `ADD_MEDICINE !INVALID` → `OBSERVE !EL_NAME_ERROR`
Failure class       : NOMINAL
Silent failure?     : no (no disruption)
Root cause in app   : the Add-medicine OK handler trims the text and creates the medicine with no emptiness check (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/medicine/MedicinesFragment.kt:175)
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/input_invalid/v1.log:1294–1297): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes (no disruption; not on the nominal run)
Forecast            : "FAIL: the empty name is accepted" (EVALUATION/medtimer/properties/disruption_mapping.yml:160); held
Reproduced          : walked once
Doubts              : none recorded
```

### cannot_skip

#### MedTimer-5  A medicine marked 'cannot be skipped' is skipped from the overview
```
Purpose / test case : tp_cannot_skip / tc_cannot_skip.1.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/cannot_skip/tc_cannot_skip.1.aut; branch 1 of the purpose, row EVALUATION/medtimer/variants_cannot_skip.log:3)
Disruption          : none (INPUT domain variant driven by the System Interface, `timing: none`)
Where it struck     : after S8 (Vitamin C set to 'cannot be skipped'), in place of S9: the tester marks the 11:59 PM dose Skipped
The obligation      : O8, a medicine that cannot be skipped is not skipped (EVALUATION/medtimer/model/specification_medtimer.lnt:26; EVALUATION/medtimer/model/specification_medtimer.lnt:26)
What the app did    : the row became Skipped: EVALUATION/medtimer/generated/variant_logs/cannot_skip/v1.log:1934 ("CONFIRM mismatch — DoseState: AUT expects PENDING, observed 'skipped' classifies as SKIPPED")
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/cannot_skip/v1.log:1934; verdict EVALUATION/medtimer/generated/variant_logs/cannot_skip/v1.log:1945
Counterexample      : `ACT !D_A3 !SKIP` → `TAP !CV_SKIPPED` → `WAIT_FOR !EL_ROW_A3` → `OBSERVE !EL_STATE_A3` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !REJECTED !S3 !PENDING !D_A3`
Failure class       : NOMINAL
Silent failure?     : no (no disruption)
Root cause in app   : the scheduled-row popup always adds the Skipped button and never reads the medicine's flag (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ScheduledReminderActions.kt:39)
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/cannot_skip/v1.log:2121–2127): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|SKIPPED|0|3.0|3.0
Separate evidence?  : yes (no disruption; not on the nominal run)
Forecast            : "FAIL: the popup still skips" (EVALUATION/medtimer/properties/disruption_mapping.yml:161); held
Reproduced          : walked once
Doubts              : none recorded
```

### delete_skipped

#### MedTimer-6  Deleting a Skipped dose gives back a pill that was never taken
```
Purpose / test case : tp_delete_skipped / tc_delete_skipped.1.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/delete_skipped/tc_delete_skipped.1.aut; branch 1 of the purpose, row EVALUATION/medtimer/variants_delete_skipped.log:3)
Disruption          : none (INPUT domain variant driven by the System Interface, `timing: none`)
Where it struck     : after S7, in place of S8: the tester deletes the Skipped 11:58 PM record
The obligation      : O5, a deleted Skipped gives nothing back (EVALUATION/medtimer/model/specification_medtimer.lnt:21; EVALUATION/medtimer/model/specification_medtimer.lnt:274)
What the app did    : the card went from 3 to 4 pills: EVALUATION/medtimer/generated/variant_logs/delete_skipped/v1.log:1849 ("CONFIRM mismatch — StockBand: AUT expects S3, observed 'vitamin c (4 pills left)' classifies as S4")
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/delete_skipped/v1.log:1849; verdict EVALUATION/medtimer/generated/variant_logs/delete_skipped/v1.log:1860
Counterexample      : `DELETE !D_A2` → `TAP !CV_CONFIRM_DELETE` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S3 !ABSENT !D_A2`
Failure class       : NOMINAL
Silent failure?     : no (no disruption)
Root cause in app   : delete first calls `undoStock`, which adds the dose back without checking `stockHandled` (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:129, EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:123)
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/delete_skipped/v1.log:2025–2030): Medicine 1|Vitamin C|4.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|DELETED|0|3.0|3.0
Separate evidence?  : yes (no disruption; not on the nominal run)
Forecast            : "FAIL: a unit is refunded" (EVALUATION/medtimer/properties/disruption_mapping.yml:162); held
Reproduced          : walked once
Doubts              : none recorded
```

### edit_flip

#### MedTimer-7  Editing a Skipped record to Taken consumes no pill
```
Purpose / test case : tp_edit_flip / tc_edit_flip.1.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/edit_flip/tc_edit_flip.1.aut; branch 1 of the purpose, row EVALUATION/medtimer/variants_edit_flip.log:3)
Disruption          : none (INPUT domain variant driven by the System Interface, `timing: none`)
Where it struck     : after S7, in place of S8: the tester edits the Skipped 11:58 PM record to Taken
The obligation      : O5, a correction moves the stock with it (EVALUATION/medtimer/model/specification_medtimer.lnt:21; EVALUATION/medtimer/model/specification_medtimer.lnt:305)
What the app did    : the card stayed at 3 pills: EVALUATION/medtimer/generated/variant_logs/edit_flip/v1.log:1897 ("CONFIRM mismatch — StockBand: AUT expects S2, observed 'vitamin c (3 pills left)' classifies as S3")
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/edit_flip/v1.log:1897; verdict EVALUATION/medtimer/generated/variant_logs/edit_flip/v1.log:1908
Counterexample      : `EDIT !D_A2 !TAKE` → `TAP !CV_BACK` → `WAIT_FOR !EL_ROW_A2` → `OBSERVE !EL_STATE_A2` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S2 !TAKEN !D_A2`
Failure class       : NOMINAL
Silent failure?     : no (no disruption)
Root cause in app   : `updateEvent` does a plain UPDATE with no stock handling (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/EditEventViewModel.kt:139)
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/edit_flip/v1.log:2075–2080): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|TAKEN|0|3.0|3.0
Separate evidence?  : yes (no disruption; same root cause as the nominal FAIL, opposite direction)
Forecast            : "FAIL: the status flips, the stock does not" (EVALUATION/medtimer/properties/disruption_mapping.yml:163); held
Reproduced          : walked once
Doubts              : none recorded
```

### ue_kill

#### MedTimer-8  Kill around an edit of Vitamin C 11:59 PM: the edit moves no stock (edit-sheet defect, not the UE_KILL)
```
Purpose / test case : tp_ue_kill / tc_ue_kill.1.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/ue_kill/tc_ue_kill.1.aut; branch 1 of the purpose, row EVALUATION/medtimer/variants_ue_kill.log:3)
Disruption          : UE_KILL (USER), process killed and relaunched by the System Interface's `navigate` right after the commit tap (EVALUATION/medtimer/properties/disruption_mapping.yml:33), timing none
Where it struck     : at S13 (edit the 11:59 PM record to Skipped); the process is killed and relaunched right after the commit tap (the System Interface's navigate)
The obligation      : O5 (EVALUATION/medtimer/model/specification_medtimer.lnt:21) and, for this purpose, whole-or-nothing under a kill (EVALUATION/medtimer/model/specification_medtimer.lnt:260)
What the app did    : EVALUATION/medtimer/generated/variant_logs/ue_kill/v1.log:1993 ("CONFIRM mismatch — StockBand: AUT expects S3, observed 'vitamin c (2 pills left)' classifies as S2"); MedTimer on screen (overview), no error element; no row for Vitamin C 11:59 PM (EVALUATION/medtimer/generated/variant_logs/ue_kill/v1_captures/20261002-012717_confirm_stockband_S3_got_S2.xml)
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/ue_kill/v1.log:1993; verdict EVALUATION/medtimer/generated/variant_logs/ue_kill/v1.log:2004
Counterexample      : `TAP !CV_TOGGLE_SKIPPED` → `EDIT !D_A3 !SKIP` → `UE_KILL` → `TAP !CV_BACK` → `NAVIGATE !RT_HOME` → `WAIT_FOR !EL_ROW_A3` → `OBSERVE !EL_STATE_A3` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S3 !SKIPPED !D_A3`
Failure class       : NOMINAL
Silent failure?     : no (the shown stock is the defect's, the write itself took effect)
Root cause in app   : `updateEvent` does a plain UPDATE with no stock handling (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/EditEventViewModel.kt:139)
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/ue_kill/v1.log:2226–2233): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|SKIPPED|1|3.0|2.0
Separate evidence?  : no: the stock symptom is the edit-sheet defect the nominal run fails on (MedTimer-1); the disruption does not produce it
Forecast            : PASS forecast for UE_KILL (EVALUATION/medtimer/properties/disruption_mapping.yml:150); the purpose's own fault did not cause this FAIL
Reproduced          : walked once
Doubts              : this FAIL is about stock arithmetic the nominal or domain purposes already fail; it is not evidence about the disruption
```

#### MedTimer-9  Kill around deleting the Skipped Vitamin C 11:58 PM: a pill is refunded (delete-skipped defect, not the kill)
```
Purpose / test case : tp_ue_kill / tc_ue_kill.2.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/ue_kill/tc_ue_kill.2.aut; branch 2 of the purpose, row EVALUATION/medtimer/variants_ue_kill.log:4)
Disruption          : UE_KILL (USER), process killed and relaunched by the System Interface's `navigate` right after the commit tap (EVALUATION/medtimer/properties/disruption_mapping.yml:33), timing none
Where it struck     : after S12, in place of S13: the tester chose `DELETE !D_A2`; the process is killed and relaunched right after the commit tap (the System Interface's navigate)
The obligation      : O5 (EVALUATION/medtimer/model/specification_medtimer.lnt:21) and, for this purpose, whole-or-nothing under a kill (EVALUATION/medtimer/model/specification_medtimer.lnt:260)
What the app did    : EVALUATION/medtimer/generated/variant_logs/ue_kill/v2.log:1969 ("CONFIRM mismatch — StockBand: AUT expects S2, observed 'vitamin c (3 pills left)' classifies as S3"); MedTimer on screen (overview), no error element; no row for Vitamin C 11:58 PM (EVALUATION/medtimer/generated/variant_logs/ue_kill/v2_captures/20261002-013904_confirm_stockband_S2_got_S3.xml)
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/ue_kill/v2.log:1969; verdict EVALUATION/medtimer/generated/variant_logs/ue_kill/v2.log:1980
Counterexample      : `WAIT_FOR !EL_DELETE_DIALOG` → `DELETE !D_A2` → `UE_KILL` → `TAP !CV_CONFIRM_DELETE` → `NAVIGATE !RT_HOME` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S2 !ABSENT !D_A2`
Failure class       : NOMINAL
Silent failure?     : no (the shown stock is the defect's, the write itself took effect)
Root cause in app   : `undoStock` adds the dose back without checking `stockHandled` (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:123)
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/ue_kill/v2.log:2200–2207): Medicine 1|Vitamin C|3.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : no: the symptom is the delete-skipped refund that tp_delete_skipped shows with no fault; the kill does not produce it
Forecast            : PASS forecast for UE_KILL (EVALUATION/medtimer/properties/disruption_mapping.yml:150); the purpose's own fault did not cause this FAIL
Reproduced          : walked once
Doubts              : this FAIL is about stock arithmetic the nominal or domain purposes already fail; it is not evidence about the disruption
```

#### MedTimer-10  Kill around deleting the Skipped Vitamin C 11:58 PM: a pill is refunded (delete-skipped defect, not the kill)
```
Purpose / test case : tp_ue_kill / tc_ue_kill.16.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/ue_kill/tc_ue_kill.16.aut; branch 16 of the purpose, row EVALUATION/medtimer/variants_ue_kill.log:18)
Disruption          : UE_KILL (USER), process killed and relaunched by the System Interface's `navigate` right after the commit tap (EVALUATION/medtimer/properties/disruption_mapping.yml:33), timing none
Where it struck     : after S8, in place of S9: the tester chose `DELETE !D_A2`; the process is killed and relaunched right after the commit tap (the System Interface's navigate)
The obligation      : O5 (EVALUATION/medtimer/model/specification_medtimer.lnt:21) and, for this purpose, whole-or-nothing under a kill (EVALUATION/medtimer/model/specification_medtimer.lnt:260)
What the app did    : EVALUATION/medtimer/generated/variant_logs/ue_kill/v16.log:1657 ("CONFIRM mismatch — StockBand: AUT expects S3, observed 'vitamin c (4 pills left)' classifies as S4"); MedTimer on screen (overview), no error element; no row for Vitamin C 11:58 PM (EVALUATION/medtimer/generated/variant_logs/ue_kill/v16_captures/20261002-034051_confirm_stockband_S3_got_S4.xml)
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/ue_kill/v16.log:1657; verdict EVALUATION/medtimer/generated/variant_logs/ue_kill/v16.log:1668
Counterexample      : `WAIT_FOR !EL_DELETE_DIALOG` → `DELETE !D_A2` → `UE_KILL` → `TAP !CV_CONFIRM_DELETE` → `NAVIGATE !RT_HOME` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S3 !ABSENT !D_A2`
Failure class       : NOMINAL
Silent failure?     : no (the shown stock is the defect's, the write itself took effect)
Root cause in app   : `undoStock` adds the dose back without checking `stockHandled` (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:123)
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/ue_kill/v16.log:1848–1853): Medicine 1|Vitamin C|4.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : no: the symptom is the delete-skipped refund that tp_delete_skipped shows with no fault; the kill does not produce it
Forecast            : PASS forecast for UE_KILL (EVALUATION/medtimer/properties/disruption_mapping.yml:150); the purpose's own fault did not cause this FAIL
Reproduced          : walked once
Doubts              : this FAIL is about stock arithmetic the nominal or domain purposes already fail; it is not evidence about the disruption
```

### app_write_fail

#### MedTimer-11  APP_WRITE_FAIL on 'edit Vitamin C 11:59 PM to Skipped': record unchanged, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.1.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.1.aut; branch 1 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:3)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v1.log:2023, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v1.log:2024
Where it struck     : at S13 (edit the 11:59 PM record to Skipped); the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v1.log:2179; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Taken" (text "11:59 PM ➡ 6:02 AM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v1_captures/20261002-060503_missing_el_write_error.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v1.log:2179; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v1.log:2191
Counterexample      : `TAP !CV_TOGGLE_SKIPPED` → `EDIT !D_A3 !SKIP` → `APP_WRITE_FAIL` → `TAP !CV_BACK` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record unchanged) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v1.log:2405–2412): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-12  APP_WRITE_FAIL on 'delete the record of Vitamin C 11:58 PM': record not deleted, stock moved, the pill was refunded although the record was not deleted, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.2.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.2.aut; branch 2 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:5)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v2.log:1967, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v2.log:1968
Where it struck     : after S12, in place of S13: the tester chose `DELETE !D_A2`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v2.log:2151; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Skipped" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v2_captures/20261002-062740_missing_el_write_error.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v2.log:2151; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v2.log:2163
Counterexample      : `WAIT_FOR !EL_DELETE_DIALOG` → `DELETE !D_A2` → `APP_WRITE_FAIL` → `TAP !CV_CONFIRM_DELETE` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record not deleted; the pill was refunded although the record was not deleted) and the app reported nothing and stayed on its screen
Root cause in app   : delete refunds the stock (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:129) before the record update (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:130); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v2.log:2377–2384): Medicine 1|Vitamin C|3.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-13  APP_WRITE_FAIL on 'edit Vitamin C 11:58 PM to Taken': record unchanged, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.3.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.3.aut; branch 3 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:6)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v3.log:1931, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v3.log:1932
Where it struck     : after S12, in place of S13: the tester chose `EDIT !D_A2 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v3.log:2079; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Skipped" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v3_captures/20261002-063528_missing_el_write_error.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v3.log:2079; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v3.log:2091
Counterexample      : `TAP !CV_TOGGLE_TAKEN` → `EDIT !D_A2 !TAKE` → `APP_WRITE_FAIL` → `TAP !CV_BACK` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record unchanged) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v3.log:2305–2312): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-14  APP_WRITE_FAIL on 'delete the record of Vitamin C 11:59 PM': record not deleted, stock moved, the pill was refunded although the record was not deleted, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.4.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.4.aut; branch 4 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:7)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v4.log:1895, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v4.log:1896
Where it struck     : after S12, in place of S13: the tester chose `DELETE !D_A3`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v4.log:2055; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Taken" (text "11:59 PM ➡ 6:44 AM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v4_captures/20261002-064703_missing_el_write_error.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v4.log:2055; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v4.log:2067
Counterexample      : `WAIT_FOR !EL_DELETE_DIALOG` → `DELETE !D_A3` → `APP_WRITE_FAIL` → `TAP !CV_CONFIRM_DELETE` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record not deleted; the pill was refunded although the record was not deleted) and the app reported nothing and stayed on its screen
Root cause in app   : delete refunds the stock (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:129) before the record update (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:130); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v4.log:2281–2288): Medicine 1|Vitamin C|3.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-15  APP_WRITE_FAIL on 'delete the record of Zinc 11:56 PM': record not deleted, stock moved, the pill was refunded although the record was not deleted, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.5.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.5.aut; branch 5 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:8)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v5.log:1975, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v5.log:1976
Where it struck     : after S12, in place of S13: the tester chose `DELETE !D_B`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v5.log:2251; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Taken" (text "11:56 PM ➡ 6:55 AM,   1 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v5_captures/20261002-065635_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v5.log:2251; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v5.log:2263
Counterexample      : `WAIT_FOR !EL_DELETE_DIALOG` → `DELETE !D_B` → `APP_WRITE_FAIL` → `TAP !CV_CONFIRM_DELETE` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record not deleted; the pill was refunded although the record was not deleted) and the app reported nothing and stayed on its screen
Root cause in app   : delete refunds the stock (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:129) before the record update (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:130); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v5.log:2477–2484): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 4|4|TAKEN|1|2.0|1.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-16  APP_WRITE_FAIL on 'edit Zinc 11:56 PM to Skipped': record unchanged, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.6.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.6.aut; branch 6 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:9)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v6.log:1983, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v6.log:1984
Where it struck     : after S12, in place of S13: the tester chose `EDIT !D_B !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v6.log:2163; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Taken" (text "11:56 PM ➡ 7:01 AM,   1 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v6_captures/20261002-070302_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v6.log:2163; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v6.log:2175
Counterexample      : `TAP !CV_TOGGLE_SKIPPED` → `EDIT !D_B !SKIP` → `APP_WRITE_FAIL` → `TAP !CV_BACK` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record unchanged) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v6.log:2389–2396): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 4|4|TAKEN|1|2.0|1.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-17  APP_WRITE_FAIL on 'mark Zinc 11:56 PM Taken': record status RAISED, stock moved, the pill was consumed although the record was not completed, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.7.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.7.aut; branch 7 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:10)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v7.log:1806, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v7.log:1807
Where it struck     : at S11 (mark Zinc's 11:56 PM dose Taken); the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v7.log:2034; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v7_captures/20261002-070835_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v7.log:2034; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v7.log:2046
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !TAKE` → `APP_WRITE_FAIL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED; the pill was consumed although the record was not completed) and the app reported nothing and stayed on its screen
Root cause in app   : the stock is written (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:135) before the record update (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:149); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v7.log:2238–2245): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 4|4|RAISED|0|2.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report; the half-write (stock moved, record pending) also held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-18  APP_WRITE_FAIL on 'mark Zinc 11:56 PM Skipped': record status RAISED, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.8.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.8.aut; branch 8 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:11)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v8.log:1678, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v8.log:1679
Where it struck     : after S10, in place of S11: the tester chose `ACT !D_B !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v8.log:1830; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v8_captures/20261002-071834_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v8.log:1830; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v8.log:1842
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !SKIP` → `APP_WRITE_FAIL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v8.log:2034–2041): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 4|4|RAISED|0|2.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-19  APP_WRITE_FAIL on 'delete the record of Vitamin C 11:58 PM': record not deleted, stock moved, the pill was refunded although the record was not deleted, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.9.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.9.aut; branch 9 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:12)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v9.log:1667, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v9.log:1668
Where it struck     : after S10, in place of S11: the tester chose `DELETE !D_A2`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v9.log:1835; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Skipped" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v9_captures/20261002-072913_missing_el_write_error.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v9.log:1835; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v9.log:1847
Counterexample      : `WAIT_FOR !EL_DELETE_DIALOG` → `DELETE !D_A2` → `APP_WRITE_FAIL` → `TAP !CV_CONFIRM_DELETE` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record not deleted; the pill was refunded although the record was not deleted) and the app reported nothing and stayed on its screen
Root cause in app   : delete refunds the stock (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:129) before the record update (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:130); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v9.log:2041–2047): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-20  APP_WRITE_FAIL on 'edit Vitamin C 11:58 PM to Taken': record unchanged, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.10.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.10.aut; branch 10 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:13)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v10.log:1675, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v10.log:1676
Where it struck     : after S10, in place of S11: the tester chose `EDIT !D_A2 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v10.log:1839; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Skipped" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v10_captures/20261002-074016_missing_el_write_error.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v10.log:1839; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v10.log:1851
Counterexample      : `TAP !CV_TOGGLE_TAKEN` → `EDIT !D_A2 !TAKE` → `APP_WRITE_FAIL` → `TAP !CV_BACK` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record unchanged) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v10.log:2045–2051): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-21  APP_WRITE_FAIL on 'delete the record of Vitamin C 11:59 PM': record not deleted, stock moved, the pill was refunded although the record was not deleted, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.11.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.11.aut; branch 11 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:14)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v11.log:1699, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v11.log:1700
Where it struck     : after S10, in place of S11: the tester chose `DELETE !D_A3`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v11.log:1859; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Taken" (text "11:59 PM ➡ 7:49 AM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v11_captures/20261002-075136_missing_el_write_error.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v11.log:1859; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v11.log:1871
Counterexample      : `WAIT_FOR !EL_DELETE_DIALOG` → `DELETE !D_A3` → `APP_WRITE_FAIL` → `TAP !CV_CONFIRM_DELETE` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record not deleted; the pill was refunded although the record was not deleted) and the app reported nothing and stayed on its screen
Root cause in app   : delete refunds the stock (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:129) before the record update (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:130); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v11.log:2065–2071): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-22  APP_WRITE_FAIL on 'edit Vitamin C 11:59 PM to Skipped': record unchanged, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.12.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.12.aut; branch 12 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:15)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v12.log:1667, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v12.log:1668
Where it struck     : after S10, in place of S11: the tester chose `EDIT !D_A3 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v12.log:1827; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Taken" (text "11:59 PM ➡ 8:01 AM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v12_captures/20261002-080321_missing_el_write_error.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v12.log:1827; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v12.log:1839
Counterexample      : `TAP !CV_TOGGLE_SKIPPED` → `EDIT !D_A3 !SKIP` → `APP_WRITE_FAIL` → `TAP !CV_BACK` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record unchanged) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v12.log:2033–2039): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-23  APP_WRITE_FAIL on 'mark Vitamin C 11:59 PM Taken': record status RAISED, stock moved, the pill was consumed although the record was not completed, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.13.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.13.aut; branch 13 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:17)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v13.log:1582, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v13.log:1583
Where it struck     : at S9 (mark the 11:59 PM dose Taken); the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v13.log:1842; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v13_captures/20261002-081742_missing_el_write_error.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v13.log:1842; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v13.log:1854
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !TAKE` → `APP_WRITE_FAIL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED; the pill was consumed although the record was not completed) and the app reported nothing and stayed on its screen
Root cause in app   : the stock is written (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:135) before the record update (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:149); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v13.log:2026–2032): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|RAISED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report; the half-write (stock moved, record pending) also held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-24  APP_WRITE_FAIL on 'mark Zinc 11:56 PM Taken': record status RAISED, stock moved, the pill was consumed although the record was not completed, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.14.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.14.aut; branch 14 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:18)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v14.log:1530, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v14.log:1531
Where it struck     : after S8, in place of S9: the tester chose `ACT !D_B !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v14.log:1686; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v14_captures/20261002-082737_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v14.log:1686; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v14.log:1698
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !TAKE` → `APP_WRITE_FAIL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED; the pill was consumed although the record was not completed) and the app reported nothing and stayed on its screen
Root cause in app   : the stock is written (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:135) before the record update (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:149); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v14.log:1870–1876): Medicine 1|Vitamin C|3.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|4|RAISED|0|2.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report; the half-write (stock moved, record pending) also held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-25  APP_WRITE_FAIL on 'mark Zinc 11:56 PM Skipped': record status RAISED, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.15.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.15.aut; branch 15 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:19)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v15.log:1422, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v15.log:1423
Where it struck     : after S8, in place of S9: the tester chose `ACT !D_B !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v15.log:1570; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v15_captures/20261002-083535_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v15.log:1570; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v15.log:1582
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !SKIP` → `APP_WRITE_FAIL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v15.log:1754–1760): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|4|RAISED|0|2.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-26  APP_WRITE_FAIL on 'delete the record of Vitamin C 11:58 PM': record not deleted, stock moved, the pill was refunded although the record was not deleted, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.16.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.16.aut; branch 16 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:20)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v16.log:1507, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v16.log:1508
Where it struck     : after S8, in place of S9: the tester chose `DELETE !D_A2`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v16.log:1683; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Skipped" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v16_captures/20261002-084601_missing_el_write_error.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v16.log:1683; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v16.log:1695
Counterexample      : `WAIT_FOR !EL_DELETE_DIALOG` → `DELETE !D_A2` → `APP_WRITE_FAIL` → `TAP !CV_CONFIRM_DELETE` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record not deleted; the pill was refunded although the record was not deleted) and the app reported nothing and stayed on its screen
Root cause in app   : delete refunds the stock (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:129) before the record update (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:130); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v16.log:1869–1874): Medicine 1|Vitamin C|4.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-27  APP_WRITE_FAIL on 'edit Vitamin C 11:58 PM to Taken': record unchanged, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.17.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.17.aut; branch 17 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:21)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v17.log:1507, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v17.log:1508
Where it struck     : after S8, in place of S9: the tester chose `EDIT !D_A2 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v17.log:1655; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Skipped" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v17_captures/20261002-085445_missing_el_write_error.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v17.log:1655; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v17.log:1667
Counterexample      : `TAP !CV_TOGGLE_TAKEN` → `EDIT !D_A2 !TAKE` → `APP_WRITE_FAIL` → `TAP !CV_BACK` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record unchanged) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v17.log:1841–1846): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-28  APP_WRITE_FAIL on 'mark Vitamin C 11:58 PM Skipped': record status RAISED, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.18.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.18.aut; branch 18 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:22)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v18.log:1208, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v18.log:1209
Where it struck     : at S6 (mark the 11:58 PM dose Skipped); the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v18.log:1388; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Please wait…" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v18_captures/20261002-090049_missing_el_write_error.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v18.log:1388; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v18.log:1400
Counterexample      : `TAP !CV_STATE_A2` → `ACT !D_A2 !SKIP` → `APP_WRITE_FAIL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v18.log:1541–1546): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|RAISED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-29  APP_WRITE_FAIL on 'mark Vitamin C 11:58 PM Taken': record status RAISED, stock moved, the pill was consumed although the record was not completed, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.19.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.19.aut; branch 19 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:23)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v19.log:1264, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v19.log:1265
Where it struck     : after S5, in place of S6: the tester chose `ACT !D_A2 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v19.log:1428; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Please wait…" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v19_captures/20261002-090913_missing_el_write_error.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v19.log:1428; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v19.log:1440
Counterexample      : `TAP !CV_STATE_A2` → `ACT !D_A2 !TAKE` → `APP_WRITE_FAIL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED; the pill was consumed although the record was not completed) and the app reported nothing and stayed on its screen
Root cause in app   : the stock is written (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:135) before the record update (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:149); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v19.log:1581–1586): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|RAISED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report; the half-write (stock moved, record pending) also held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-30  APP_WRITE_FAIL on 'mark Vitamin C 11:59 PM Taken': record status RAISED, stock moved, the pill was consumed although the record was not completed, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.20.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.20.aut; branch 20 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:24)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v20.log:1224, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v20.log:1225
Where it struck     : after S5, in place of S6: the tester chose `ACT !D_A3 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v20.log:1392; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v20_captures/20261002-091853_missing_el_write_error.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v20.log:1392; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v20.log:1404
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !TAKE` → `APP_WRITE_FAIL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED; the pill was consumed although the record was not completed) and the app reported nothing and stayed on its screen
Root cause in app   : the stock is written (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:135) before the record update (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:149); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v20.log:1545–1550): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|3|RAISED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report; the half-write (stock moved, record pending) also held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-31  APP_WRITE_FAIL on 'mark Vitamin C 11:59 PM Skipped': record status RAISED, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.21.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.21.aut; branch 21 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:25)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v21.log:1204, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v21.log:1205
Where it struck     : after S5, in place of S6: the tester chose `ACT !D_A3 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v21.log:1396; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v21_captures/20261002-092446_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v21.log:1396; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v21.log:1408
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !SKIP` → `APP_WRITE_FAIL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v21.log:1549–1554): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|3|RAISED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-32  APP_WRITE_FAIL on 'mark Zinc 11:56 PM Taken': record status RAISED, stock moved, the pill was consumed although the record was not completed, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.22.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.22.aut; branch 22 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:26)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v22.log:1276, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v22.log:1277
Where it struck     : after S5, in place of S6: the tester chose `ACT !D_B !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v22.log:1428; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v22_captures/20261002-093017_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v22.log:1428; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v22.log:1440
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !TAKE` → `APP_WRITE_FAIL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED; the pill was consumed although the record was not completed) and the app reported nothing and stayed on its screen
Root cause in app   : the stock is written (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:135) before the record update (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:149); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v22.log:1581–1586): Medicine 1|Vitamin C|3.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|4|RAISED|0|2.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report; the half-write (stock moved, record pending) also held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-33  APP_WRITE_FAIL on 'mark Zinc 11:56 PM Skipped': record status RAISED, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.23.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.23.aut; branch 23 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:27)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v23.log:1336, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v23.log:1337
Where it struck     : after S5, in place of S6: the tester chose `ACT !D_B !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v23.log:1572; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v23_captures/20261002-093554_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v23.log:1572; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v23.log:1584
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !SKIP` → `APP_WRITE_FAIL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v23.log:1725–1730): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|4|RAISED|0|2.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-34  APP_WRITE_FAIL on 'delete the record of Vitamin C 11:57 PM': record not deleted, stock moved, the pill was refunded although the record was not deleted, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.24.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.24.aut; branch 24 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:28)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v24.log:1080, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v24.log:1081
Where it struck     : at S4 (delete that dose's record); the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v24.log:1244; MedTimer on screen, no error element; the Vitamin C 11:57 PM row shows state "Taken" (text "11:57 PM ➡ 9:41 AM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v24_captures/20261002-094401_missing_el_write_error.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v24.log:1244; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v24.log:1256
Counterexample      : `WAIT_FOR !EL_DELETE_DIALOG` → `DELETE !D_A1` → `APP_WRITE_FAIL` → `TAP !CV_CONFIRM_DELETE` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record not deleted; the pill was refunded although the record was not deleted) and the app reported nothing and stayed on its screen
Root cause in app   : delete refunds the stock (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:129) before the record update (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:130); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v24.log:1381–1385): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-35  APP_WRITE_FAIL on 'mark Vitamin C 11:58 PM Taken': record status RAISED, stock moved, the pill was consumed although the record was not completed, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.25.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.25.aut; branch 25 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:29)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v25.log:1047, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v25.log:1048
Where it struck     : after S3, in place of S4: the tester chose `ACT !D_A2 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v25.log:1191; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Please wait…" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v25_captures/20261002-095523_missing_el_write_error.xml:64)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v25.log:1191; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v25.log:1203
Counterexample      : `TAP !CV_STATE_A2` → `ACT !D_A2 !TAKE` → `APP_WRITE_FAIL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED; the pill was consumed although the record was not completed) and the app reported nothing and stayed on its screen
Root cause in app   : the stock is written (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:135) before the record update (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:149); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v25.log:1326–1331): Medicine 1|Vitamin C|1.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|RAISED|0|2.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report; the half-write (stock moved, record pending) also held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-36  APP_WRITE_FAIL on 'mark Vitamin C 11:58 PM Skipped': record status RAISED, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.26.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.26.aut; branch 26 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:30)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v26.log:1051, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v26.log:1052
Where it struck     : after S3, in place of S4: the tester chose `ACT !D_A2 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v26.log:1191; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Please wait…" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v26_captures/20261002-100812_missing_el_write_error.xml:64)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v26.log:1191; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v26.log:1203
Counterexample      : `TAP !CV_STATE_A2` → `ACT !D_A2 !SKIP` → `APP_WRITE_FAIL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v26.log:1326–1331): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|RAISED|0|2.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-37  APP_WRITE_FAIL on 'mark Vitamin C 11:59 PM Taken': record status RAISED, stock moved, the pill was consumed although the record was not completed, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.27.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.27.aut; branch 27 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:31)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v27.log:1015, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v27.log:1016
Where it struck     : after S3, in place of S4: the tester chose `ACT !D_A3 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v27.log:1151; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v27_captures/20261002-102010_missing_el_write_error.xml:71)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v27.log:1151; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v27.log:1163
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !TAKE` → `APP_WRITE_FAIL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED; the pill was consumed although the record was not completed) and the app reported nothing and stayed on its screen
Root cause in app   : the stock is written (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:135) before the record update (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:149); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v27.log:1286–1291): Medicine 1|Vitamin C|1.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|3|RAISED|0|2.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report; the half-write (stock moved, record pending) also held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-38  APP_WRITE_FAIL on 'mark Vitamin C 11:59 PM Skipped': record status RAISED, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.28.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.28.aut; branch 28 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:32)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v28.log:1043, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v28.log:1044
Where it struck     : after S3, in place of S4: the tester chose `ACT !D_A3 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v28.log:1215; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v28_captures/20261002-102543_missing_el_write_error.xml:71)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v28.log:1215; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v28.log:1227
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !SKIP` → `APP_WRITE_FAIL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v28.log:1350–1355): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|3|RAISED|0|2.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-39  APP_WRITE_FAIL on 'mark Zinc 11:56 PM Taken': record status RAISED, stock moved, the pill was consumed although the record was not completed, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.29.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.29.aut; branch 29 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:33)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v29.log:1063, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v29.log:1064
Where it struck     : after S3, in place of S4: the tester chose `ACT !D_B !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v29.log:1219; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v29_captures/20261002-103335_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v29.log:1219; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v29.log:1231
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !TAKE` → `APP_WRITE_FAIL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED; the pill was consumed although the record was not completed) and the app reported nothing and stayed on its screen
Root cause in app   : the stock is written (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:135) before the record update (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:149); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v29.log:1354–1359): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|4|RAISED|0|2.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report; the half-write (stock moved, record pending) also held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-40  APP_WRITE_FAIL on 'mark Zinc 11:56 PM Skipped': record status RAISED, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.30.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.30.aut; branch 30 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:34)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v30.log:1087, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v30.log:1088
Where it struck     : after S3, in place of S4: the tester chose `ACT !D_B !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v30.log:1227; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v30_captures/20261002-103850_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v30.log:1227; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v30.log:1239
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !SKIP` → `APP_WRITE_FAIL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v30.log:1362–1367): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|4|RAISED|0|2.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-41  APP_WRITE_FAIL on 'edit Vitamin C 11:57 PM to Skipped': record unchanged, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.31.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.31.aut; branch 31 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:35)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v31.log:1080, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v31.log:1081
Where it struck     : after S3, in place of S4: the tester chose `EDIT !D_A1 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v31.log:1220; MedTimer on screen, no error element; the Vitamin C 11:57 PM row shows state "Taken" (text "11:57 PM ➡ 10:44 AM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v31_captures/20261002-104656_missing_el_write_error.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v31.log:1220; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v31.log:1232
Counterexample      : `TAP !CV_TOGGLE_SKIPPED` → `EDIT !D_A1 !SKIP` → `APP_WRITE_FAIL` → `TAP !CV_BACK` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record unchanged) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v31.log:1357–1361): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-42  APP_WRITE_FAIL on 'mark Vitamin C 11:57 PM Taken': record status RAISED, stock moved, the pill was consumed although the record was not completed, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.32.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.32.aut; branch 32 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:36)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v32.log:939, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v32.log:940
Where it struck     : at S2 (mark Vitamin C's 11:57 PM dose Taken); the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v32.log:1207; MedTimer on screen, no error element; the Vitamin C 11:57 PM row shows state "Please wait…" (text "11:57 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v32_captures/20261002-104920_missing_el_write_error.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v32.log:1207; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v32.log:1219
Counterexample      : `TAP !CV_STATE_A1` → `ACT !D_A1 !TAKE` → `APP_WRITE_FAIL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED; the pill was consumed although the record was not completed) and the app reported nothing and stayed on its screen
Root cause in app   : the stock is written (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:135) before the record update (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:149); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v32.log:1322–1326): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|RAISED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report; the half-write (stock moved, record pending) also held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-43  APP_WRITE_FAIL on 'mark Vitamin C 11:57 PM Skipped': record status RAISED, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.33.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.33.aut; branch 33 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:37)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v33.log:923, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v33.log:924
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_A1 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v33.log:1147; MedTimer on screen, no error element; the Vitamin C 11:57 PM row shows state "Please wait…" (text "11:57 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v33_captures/20261002-105128_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v33.log:1147; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v33.log:1159
Counterexample      : `TAP !CV_STATE_A1` → `ACT !D_A1 !SKIP` → `APP_WRITE_FAIL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v33.log:1262–1266): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|RAISED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-44  APP_WRITE_FAIL on 'mark Vitamin C 11:58 PM Taken': record status RAISED, stock moved, the pill was consumed although the record was not completed, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.34.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.34.aut; branch 34 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:38)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v34.log:903, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v34.log:904
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_A2 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v34.log:1175; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Please wait…" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v34_captures/20261002-105336_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:64)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v34.log:1175; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v34.log:1187
Counterexample      : `TAP !CV_STATE_A2` → `ACT !D_A2 !TAKE` → `APP_WRITE_FAIL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED; the pill was consumed although the record was not completed) and the app reported nothing and stayed on its screen
Root cause in app   : the stock is written (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:135) before the record update (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:149); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v34.log:1290–1294): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|2|RAISED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report; the half-write (stock moved, record pending) also held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-45  APP_WRITE_FAIL on 'mark Vitamin C 11:58 PM Skipped': record status RAISED, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.35.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.35.aut; branch 35 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:39)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v35.log:895, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v35.log:896
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_A2 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v35.log:1179; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Please wait…" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v35_captures/20261002-105546_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:64)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v35.log:1179; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v35.log:1191
Counterexample      : `TAP !CV_STATE_A2` → `ACT !D_A2 !SKIP` → `APP_WRITE_FAIL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v35.log:1294–1298): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|2|RAISED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-46  APP_WRITE_FAIL on 'mark Vitamin C 11:59 PM Taken': record status RAISED, stock moved, the pill was consumed although the record was not completed, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.36.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.36.aut; branch 36 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:40)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v36.log:891, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v36.log:892
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_A3 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v36.log:1187; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v36_captures/20261002-105801_missing_el_write_error.xml:71)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v36.log:1187; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v36.log:1199
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !TAKE` → `APP_WRITE_FAIL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED; the pill was consumed although the record was not completed) and the app reported nothing and stayed on its screen
Root cause in app   : the stock is written (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:135) before the record update (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:149); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v36.log:1302–1306): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|3|RAISED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report; the half-write (stock moved, record pending) also held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-47  APP_WRITE_FAIL on 'mark Vitamin C 11:59 PM Skipped': record status RAISED, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.37.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.37.aut; branch 37 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:41)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v37.log:923, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v37.log:924
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_A3 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v37.log:1223; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v37_captures/20261002-110015_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:71)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v37.log:1223; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v37.log:1235
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !SKIP` → `APP_WRITE_FAIL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v37.log:1338–1342): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|3|RAISED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-48  APP_WRITE_FAIL on 'mark Zinc 11:56 PM Taken': record status RAISED, stock moved, the pill was consumed although the record was not completed, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.38.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.38.aut; branch 38 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:42)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v38.log:935, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v38.log:936
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_B !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v38.log:1167; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v38_captures/20261002-110227_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v38.log:1167; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v38.log:1179
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !TAKE` → `APP_WRITE_FAIL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED; the pill was consumed although the record was not completed) and the app reported nothing and stayed on its screen
Root cause in app   : the stock is written (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:135) before the record update (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:149); the failing update is not caught (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v38.log:1282–1286): Medicine 1|Vitamin C|3.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|4|RAISED|0|2.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report; the half-write (stock moved, record pending) also held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-49  APP_WRITE_FAIL on 'mark Zinc 11:56 PM Skipped': record status RAISED, stock unchanged, no error shown
```
Purpose / test case : tp_app_write_fail / tc_app_write_fail.39.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_write_fail/tc_app_write_fail.39.aut; branch 39 of the purpose, row EVALUATION/medtimer/variants_app_write_fail.log:43)
Disruption          : APP_WRITE_FAIL (APP), SQLite trigger `BEFORE UPDATE ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:44), timing gate; injected EVALUATION/medtimer/generated/variant_logs/app_write_fail/v39.log:943, confirmed by probe EVALUATION/medtimer/generated/variant_logs/app_write_fail/v39.log:944
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_B !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:250)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v39.log:1215; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v39_captures/20261002-110438_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/app_write_fail/v39.log:1215; verdict EVALUATION/medtimer/generated/variant_logs/app_write_fail/v39.log:1227
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !SKIP` → `APP_WRITE_FAIL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record status RAISED) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/app_write_fail/v39.log:1330–1334): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|4|RAISED|0|2.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; at a take the stock has moved and the record is still pending (measured, sweep one)" (EVALUATION/medtimer/properties/disruption_mapping.yml:151-152); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

### app_cache_stale

#### MedTimer-50  List read around an edit of Vitamin C 11:57 PM: the edit moves no stock (edit-sheet defect, not the APP_CACHE_STALE)
```
Purpose / test case : tp_app_cache_stale / tc_app_cache_stale.9.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_cache_stale/tc_app_cache_stale.9.aut; branch 9 of the purpose, row EVALUATION/medtimer/variants_app_cache_stale.log:11)
Disruption          : APP_CACHE_STALE (APP), the System Interface reads the medicine list just before the write (EVALUATION/medtimer/properties/disruption_mapping.yml:128), timing none
Where it struck     : after S3: the medicine list is read, then the tester writes `EDIT !D_A1 !SKIP`
The obligation      : O5 (EVALUATION/medtimer/model/specification_medtimer.lnt:21) and, for this purpose, O3 (EVALUATION/medtimer/model/specification_medtimer.lnt:339)
What the app did    : EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v9.log:1258 ("CONFIRM mismatch — StockBand: AUT expects S3, observed 'vitamin c (2 pills left)' classifies as S2"); MedTimer on screen (overview), no error element; no row for Vitamin C 11:57 PM (EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v9_captures/20261002-082738_confirm_stockband_S3_got_S2.xml)
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v9.log:1258; verdict EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v9.log:1269
Counterexample      : `APP_CACHE_STALE` → `TAP !CV_TAB_OVERVIEW` → `WAIT_FOR !EL_OVERVIEW` → `WAIT_FOR !EL_ROW_A1` → `TAP !CV_ROW_A1` → `…` → `WAIT_FOR !EL_ROW_A1` → `OBSERVE !EL_STATE_A1` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S3 !SKIPPED !D_A1`
Failure class       : NOMINAL
Silent failure?     : no (the shown stock is the defect's, the write itself took effect)
Root cause in app   : `updateEvent` does a plain UPDATE with no stock handling (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/EditEventViewModel.kt:139)
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v9.log:1401–1405): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|SKIPPED|1|3.0|2.0
Separate evidence?  : no: the stock symptom is the edit-sheet defect the nominal run fails on (MedTimer-1); the disruption does not produce it
Forecast            : PASS forecast for APP_CACHE_STALE (EVALUATION/medtimer/properties/disruption_mapping.yml:155); the purpose's own fault did not cause this FAIL
Reproduced          : walked once
Doubts              : this FAIL is about stock arithmetic the nominal or domain purposes already fail; it is not evidence about the disruption
```

#### MedTimer-51  List read around an edit of Vitamin C 11:58 PM: the edit moves no stock (edit-sheet defect, not the APP_CACHE_STALE)
```
Purpose / test case : tp_app_cache_stale / tc_app_cache_stale.12.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_cache_stale/tc_app_cache_stale.12.aut; branch 12 of the purpose, row EVALUATION/medtimer/variants_app_cache_stale.log:14)
Disruption          : APP_CACHE_STALE (APP), the System Interface reads the medicine list just before the write (EVALUATION/medtimer/properties/disruption_mapping.yml:128), timing none
Where it struck     : after S8: the medicine list is read, then the tester writes `EDIT !D_A2 !TAKE`
The obligation      : O5 (EVALUATION/medtimer/model/specification_medtimer.lnt:21) and, for this purpose, O3 (EVALUATION/medtimer/model/specification_medtimer.lnt:339)
What the app did    : EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v12.log:1801 ("CONFIRM mismatch — StockBand: AUT expects S2, observed 'vitamin c (3 pills left)' classifies as S3"); MedTimer on screen (overview), no error element; no row for Vitamin C 11:58 PM (EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v12_captures/20261002-083430_confirm_stockband_S2_got_S3.xml)
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v12.log:1801; verdict EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v12.log:1812
Counterexample      : `APP_CACHE_STALE` → `TAP !CV_TAB_OVERVIEW` → `WAIT_FOR !EL_OVERVIEW` → `WAIT_FOR !EL_ROW_A2` → `TAP !CV_ROW_A2` → `…` → `WAIT_FOR !EL_ROW_A2` → `OBSERVE !EL_STATE_A2` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S2 !TAKEN !D_A2`
Failure class       : NOMINAL
Silent failure?     : no (the shown stock is the defect's, the write itself took effect)
Root cause in app   : `updateEvent` does a plain UPDATE with no stock handling (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/EditEventViewModel.kt:139)
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v12.log:1993–1998): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|TAKEN|0|3.0|3.0
Separate evidence?  : no: the stock symptom is the edit-sheet defect the nominal run fails on (MedTimer-1); the disruption does not produce it
Forecast            : PASS forecast for APP_CACHE_STALE (EVALUATION/medtimer/properties/disruption_mapping.yml:155); the purpose's own fault did not cause this FAIL
Reproduced          : walked once
Doubts              : this FAIL is about stock arithmetic the nominal or domain purposes already fail; it is not evidence about the disruption
```

#### MedTimer-52  List read around an edit of Vitamin C 11:58 PM: the edit moves no stock (edit-sheet defect, not the APP_CACHE_STALE)
```
Purpose / test case : tp_app_cache_stale / tc_app_cache_stale.14.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_cache_stale/tc_app_cache_stale.14.aut; branch 14 of the purpose, row EVALUATION/medtimer/variants_app_cache_stale.log:16)
Disruption          : APP_CACHE_STALE (APP), the System Interface reads the medicine list just before the write (EVALUATION/medtimer/properties/disruption_mapping.yml:128), timing none
Where it struck     : after S10: the medicine list is read, then the tester writes `EDIT !D_A2 !TAKE`
The obligation      : O5 (EVALUATION/medtimer/model/specification_medtimer.lnt:21) and, for this purpose, O3 (EVALUATION/medtimer/model/specification_medtimer.lnt:339)
What the app did    : EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v14.log:2049 ("CONFIRM mismatch — StockBand: AUT expects S1, observed 'vitamin c (2 pills left)' classifies as S2"); MedTimer on screen (overview), no error element; no row for Vitamin C 11:58 PM (EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v14_captures/20261002-083924_confirm_stockband_S1_got_S2.xml)
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v14.log:2049; verdict EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v14.log:2060
Counterexample      : `APP_CACHE_STALE` → `TAP !CV_TAB_OVERVIEW` → `WAIT_FOR !EL_OVERVIEW` → `WAIT_FOR !EL_ROW_A2` → `TAP !CV_ROW_A2` → `…` → `WAIT_FOR !EL_ROW_A2` → `OBSERVE !EL_STATE_A2` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S1 !TAKEN !D_A2`
Failure class       : NOMINAL
Silent failure?     : no (the shown stock is the defect's, the write itself took effect)
Root cause in app   : `updateEvent` does a plain UPDATE with no stock handling (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/EditEventViewModel.kt:139)
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v14.log:2261–2267): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|TAKEN|0|3.0|3.0
Separate evidence?  : no: the stock symptom is the edit-sheet defect the nominal run fails on (MedTimer-1); the disruption does not produce it
Forecast            : PASS forecast for APP_CACHE_STALE (EVALUATION/medtimer/properties/disruption_mapping.yml:155); the purpose's own fault did not cause this FAIL
Reproduced          : walked once
Doubts              : this FAIL is about stock arithmetic the nominal or domain purposes already fail; it is not evidence about the disruption
```

#### MedTimer-53  List read around an edit of Vitamin C 11:59 PM: the edit moves no stock (edit-sheet defect, not the APP_CACHE_STALE)
```
Purpose / test case : tp_app_cache_stale / tc_app_cache_stale.16.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_cache_stale/tc_app_cache_stale.16.aut; branch 16 of the purpose, row EVALUATION/medtimer/variants_app_cache_stale.log:18)
Disruption          : APP_CACHE_STALE (APP), the System Interface reads the medicine list just before the write (EVALUATION/medtimer/properties/disruption_mapping.yml:128), timing none
Where it struck     : after S10: the medicine list is read, then the tester writes `EDIT !D_A3 !SKIP`
The obligation      : O5 (EVALUATION/medtimer/model/specification_medtimer.lnt:21) and, for this purpose, O3 (EVALUATION/medtimer/model/specification_medtimer.lnt:339)
What the app did    : EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v16.log:2057 ("CONFIRM mismatch — StockBand: AUT expects S3, observed 'vitamin c (2 pills left)' classifies as S2"); MedTimer on screen (overview), no error element; no row for Vitamin C 11:59 PM (EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v16_captures/20261002-084418_confirm_stockband_S3_got_S2.xml)
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v16.log:2057; verdict EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v16.log:2068
Counterexample      : `APP_CACHE_STALE` → `TAP !CV_TAB_OVERVIEW` → `WAIT_FOR !EL_OVERVIEW` → `WAIT_FOR !EL_ROW_A3` → `TAP !CV_ROW_A3` → `…` → `WAIT_FOR !EL_ROW_A3` → `OBSERVE !EL_STATE_A3` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S3 !SKIPPED !D_A3`
Failure class       : NOMINAL
Silent failure?     : no (the shown stock is the defect's, the write itself took effect)
Root cause in app   : `updateEvent` does a plain UPDATE with no stock handling (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/EditEventViewModel.kt:139)
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v16.log:2269–2275): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|SKIPPED|1|3.0|2.0
Separate evidence?  : no: the stock symptom is the edit-sheet defect the nominal run fails on (MedTimer-1); the disruption does not produce it
Forecast            : PASS forecast for APP_CACHE_STALE (EVALUATION/medtimer/properties/disruption_mapping.yml:155); the purpose's own fault did not cause this FAIL
Reproduced          : walked once
Doubts              : this FAIL is about stock arithmetic the nominal or domain purposes already fail; it is not evidence about the disruption
```

#### MedTimer-54  List read around an edit of Vitamin C 11:59 PM: the edit moves no stock (edit-sheet defect, not the APP_CACHE_STALE)
```
Purpose / test case : tp_app_cache_stale / tc_app_cache_stale.17.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_cache_stale/tc_app_cache_stale.17.aut; branch 17 of the purpose, row EVALUATION/medtimer/variants_app_cache_stale.log:19)
Disruption          : APP_CACHE_STALE (APP), the System Interface reads the medicine list just before the write (EVALUATION/medtimer/properties/disruption_mapping.yml:128), timing none
Where it struck     : after S12: the medicine list is read, then the tester writes `EDIT !D_A3 !SKIP`
The obligation      : O5 (EVALUATION/medtimer/model/specification_medtimer.lnt:21) and, for this purpose, O3 (EVALUATION/medtimer/model/specification_medtimer.lnt:339)
What the app did    : EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v17.log:2273 ("CONFIRM mismatch — StockBand: AUT expects S3, observed 'vitamin c (2 pills left)' classifies as S2"); MedTimer on screen (overview), no error element; no row for Vitamin C 11:59 PM (EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v17_captures/20261002-084706_confirm_stockband_S3_got_S2.xml)
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v17.log:2273; verdict EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v17.log:2284
Counterexample      : `APP_CACHE_STALE` → `TAP !CV_TAB_OVERVIEW` → `WAIT_FOR !EL_OVERVIEW` → `WAIT_FOR !EL_ROW_A3` → `TAP !CV_ROW_A3` → `…` → `WAIT_FOR !EL_ROW_A3` → `OBSERVE !EL_STATE_A3` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S3 !SKIPPED !D_A3`
Failure class       : NOMINAL
Silent failure?     : no (the shown stock is the defect's, the write itself took effect)
Root cause in app   : `updateEvent` does a plain UPDATE with no stock handling (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/EditEventViewModel.kt:139)
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v17.log:2505–2512): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|SKIPPED|1|3.0|2.0
Separate evidence?  : no: the stock symptom is the edit-sheet defect the nominal run fails on (MedTimer-1); the disruption does not produce it
Forecast            : PASS forecast for APP_CACHE_STALE (EVALUATION/medtimer/properties/disruption_mapping.yml:155); the purpose's own fault did not cause this FAIL
Reproduced          : walked once
Doubts              : this FAIL is about stock arithmetic the nominal or domain purposes already fail; it is not evidence about the disruption
```

#### MedTimer-55  List read around an edit of Vitamin C 11:58 PM: the edit moves no stock (edit-sheet defect, not the APP_CACHE_STALE)
```
Purpose / test case : tp_app_cache_stale / tc_app_cache_stale.18.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_cache_stale/tc_app_cache_stale.18.aut; branch 18 of the purpose, row EVALUATION/medtimer/variants_app_cache_stale.log:20)
Disruption          : APP_CACHE_STALE (APP), the System Interface reads the medicine list just before the write (EVALUATION/medtimer/properties/disruption_mapping.yml:128), timing none
Where it struck     : after S12: the medicine list is read, then the tester writes `EDIT !D_A2 !TAKE`
The obligation      : O5 (EVALUATION/medtimer/model/specification_medtimer.lnt:21) and, for this purpose, O3 (EVALUATION/medtimer/model/specification_medtimer.lnt:339)
What the app did    : EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v18.log:2293 ("CONFIRM mismatch — StockBand: AUT expects S1, observed 'vitamin c (2 pills left)' classifies as S2"); MedTimer on screen (overview), no error element; no row for Vitamin C 11:58 PM (EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v18_captures/20261002-084949_confirm_stockband_S1_got_S2.xml)
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v18.log:2293; verdict EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v18.log:2304
Counterexample      : `APP_CACHE_STALE` → `TAP !CV_TAB_OVERVIEW` → `WAIT_FOR !EL_OVERVIEW` → `WAIT_FOR !EL_ROW_A2` → `TAP !CV_ROW_A2` → `…` → `WAIT_FOR !EL_ROW_A2` → `OBSERVE !EL_STATE_A2` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S1 !TAKEN !D_A2`
Failure class       : NOMINAL
Silent failure?     : no (the shown stock is the defect's, the write itself took effect)
Root cause in app   : `updateEvent` does a plain UPDATE with no stock handling (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/EditEventViewModel.kt:139)
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v18.log:2525–2532): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|TAKEN|0|3.0|3.0
Separate evidence?  : no: the stock symptom is the edit-sheet defect the nominal run fails on (MedTimer-1); the disruption does not produce it
Forecast            : PASS forecast for APP_CACHE_STALE (EVALUATION/medtimer/properties/disruption_mapping.yml:155); the purpose's own fault did not cause this FAIL
Reproduced          : walked once
Doubts              : this FAIL is about stock arithmetic the nominal or domain purposes already fail; it is not evidence about the disruption
```

#### MedTimer-56  List read around an edit of Zinc 11:56 PM: the edit moves no stock (edit-sheet defect, not the APP_CACHE_STALE)
```
Purpose / test case : tp_app_cache_stale / tc_app_cache_stale.21.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_cache_stale/tc_app_cache_stale.21.aut; branch 21 of the purpose, row EVALUATION/medtimer/variants_app_cache_stale.log:23)
Disruption          : APP_CACHE_STALE (APP), the System Interface reads the medicine list just before the write (EVALUATION/medtimer/properties/disruption_mapping.yml:128), timing none
Where it struck     : after S12: the medicine list is read, then the tester writes `EDIT !D_B !SKIP`
The obligation      : O5 (EVALUATION/medtimer/model/specification_medtimer.lnt:21) and, for this purpose, O3 (EVALUATION/medtimer/model/specification_medtimer.lnt:339)
What the app did    : EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v21.log:2269 ("CONFIRM mismatch — StockBand: AUT expects S2, observed 'zinc (1 pills left)' classifies as S1"); MedTimer on screen (overview), no error element; no row for Zinc 11:56 PM (EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v21_captures/20261002-085757_confirm_stockband_S2_got_S1.xml)
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v21.log:2269; verdict EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v21.log:2280
Counterexample      : `APP_CACHE_STALE` → `TAP !CV_TAB_OVERVIEW` → `WAIT_FOR !EL_OVERVIEW` → `WAIT_FOR !EL_ROW_B` → `TAP !CV_ROW_B` → `…` → `WAIT_FOR !EL_ROW_B` → `OBSERVE !EL_STATE_B` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_B` → `CONFIRM !COMMITTED !S2 !SKIPPED !D_B`
Failure class       : NOMINAL
Silent failure?     : no (the shown stock is the defect's, the write itself took effect)
Root cause in app   : `updateEvent` does a plain UPDATE with no stock handling (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/EditEventViewModel.kt:139)
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v21.log:2501–2508): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 4|4|SKIPPED|1|2.0|1.0
Separate evidence?  : no: the stock symptom is the edit-sheet defect the nominal run fails on (MedTimer-1); the disruption does not produce it
Forecast            : PASS forecast for APP_CACHE_STALE (EVALUATION/medtimer/properties/disruption_mapping.yml:155); the purpose's own fault did not cause this FAIL
Reproduced          : walked once
Doubts              : this FAIL is about stock arithmetic the nominal or domain purposes already fail; it is not evidence about the disruption
```

### db_abort

#### MedTimer-57  DB_ABORT on 'mark Zinc 11:56 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.1.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.1.aut; branch 1 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:3)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v1.log:2038, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v1.log:2039
Where it struck     : at S11 (mark Zinc's 11:56 PM dose Taken); the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v1.log:2334; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   2 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v1_captures/20261002-134226_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v1.log:2334; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v1.log:2346
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !TAKE` → `DB_ABORT` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v1.log:2538–2544): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-58  DB_ABORT on 'mark Zinc 11:56 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.2.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.2.aut; branch 2 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:4)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v2.log:2102, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v2.log:2103
Where it struck     : after S10, in place of S11: the tester chose `ACT !D_B !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v2.log:2386; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   2 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v2_captures/20261002-134519_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v2.log:2386; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v2.log:2398
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !SKIP` → `DB_ABORT` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v2.log:2590–2596): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-59  DB_ABORT on 'mark Vitamin C 11:59 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.3.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.3.aut; branch 3 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:5)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v3.log:1886, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v3.log:1887
Where it struck     : at S9 (mark the 11:59 PM dose Taken); the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v3.log:2170; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v3_captures/20261002-134758_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v3.log:2170; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v3.log:2182
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !TAKE` → `DB_ABORT` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v3.log:2354–2359): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-60  DB_ABORT on 'mark Zinc 11:56 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.4.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.4.aut; branch 4 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:6)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v4.log:1770, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v4.log:1771
Where it struck     : after S8, in place of S9: the tester chose `ACT !D_B !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v4.log:2058; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   2 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v4_captures/20261002-135053_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v4.log:2058; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v4.log:2070
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !TAKE` → `DB_ABORT` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v4.log:2242–2247): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-61  DB_ABORT on 'mark Zinc 11:56 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.5.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.5.aut; branch 5 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:7)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v5.log:1814, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v5.log:1815
Where it struck     : after S8, in place of S9: the tester chose `ACT !D_B !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v5.log:2106; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   2 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v5_captures/20261002-135334_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v5.log:2106; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v5.log:2118
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !SKIP` → `DB_ABORT` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v5.log:2290–2295): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-62  DB_ABORT on 'mark Vitamin C 11:58 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.6.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.6.aut; branch 6 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:8)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v6.log:1524, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v6.log:1525
Where it struck     : at S6 (mark the 11:58 PM dose Skipped); the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v6.log:1816; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Please wait…" (text "11:58 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v6_captures/20261002-135556_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v6.log:1816; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v6.log:1828
Counterexample      : `TAP !CV_STATE_A2` → `ACT !D_A2 !SKIP` → `DB_ABORT` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v6.log:1969–1973): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-63  DB_ABORT on 'mark Vitamin C 11:58 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.7.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.7.aut; branch 7 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:9)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v7.log:1436, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v7.log:1437
Where it struck     : after S5, in place of S6: the tester chose `ACT !D_A2 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v7.log:1720; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Please wait…" (text "11:58 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v7_captures/20261002-135819_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v7.log:1720; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v7.log:1732
Counterexample      : `TAP !CV_STATE_A2` → `ACT !D_A2 !TAKE` → `DB_ABORT` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v7.log:1873–1877): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-64  DB_ABORT on 'mark Vitamin C 11:59 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.8.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.8.aut; branch 8 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:10)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v8.log:1408, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v8.log:1409
Where it struck     : after S5, in place of S6: the tester chose `ACT !D_A3 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v8.log:1692; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v8_captures/20261002-140052_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v8.log:1692; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v8.log:1704
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !TAKE` → `DB_ABORT` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v8.log:1845–1849): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-65  DB_ABORT on 'mark Vitamin C 11:59 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.9.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.9.aut; branch 9 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:11)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v9.log:1444, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v9.log:1445
Where it struck     : after S5, in place of S6: the tester chose `ACT !D_A3 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v9.log:1732; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v9_captures/20261002-140335_missing_el_write_error.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v9.log:1732; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v9.log:1744
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !SKIP` → `DB_ABORT` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v9.log:1885–1889): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-66  DB_ABORT on 'mark Zinc 11:56 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.10.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.10.aut; branch 10 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:12)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v10.log:1444, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v10.log:1445
Where it struck     : after S5, in place of S6: the tester chose `ACT !D_B !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v10.log:1720; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   2 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v10_captures/20261002-140616_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v10.log:1720; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v10.log:1732
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !TAKE` → `DB_ABORT` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v10.log:1873–1877): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-67  DB_ABORT on 'mark Zinc 11:56 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.11.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.11.aut; branch 11 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:13)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v11.log:1444, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v11.log:1445
Where it struck     : after S5, in place of S6: the tester chose `ACT !D_B !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v11.log:1724; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   2 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v11_captures/20261002-140853_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v11.log:1724; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v11.log:1736
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !SKIP` → `DB_ABORT` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v11.log:1877–1881): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-68  DB_ABORT on 'mark Vitamin C 11:57 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.12.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.12.aut; branch 12 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:14)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v12.log:951, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v12.log:952
Where it struck     : at S2 (mark Vitamin C's 11:57 PM dose Taken); the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v12.log:1231; MedTimer on screen, no error element; the Vitamin C 11:57 PM row shows state "Please wait…" (text "11:57 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v12_captures/20261002-141051_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v12.log:1231; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v12.log:1243
Counterexample      : `TAP !CV_STATE_A1` → `ACT !D_A1 !TAKE` → `DB_ABORT` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v12.log:1346–1349): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-69  DB_ABORT on 'mark Vitamin C 11:57 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.13.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.13.aut; branch 13 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:15)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v13.log:935, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v13.log:936
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_A1 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v13.log:1223; MedTimer on screen, no error element; the Vitamin C 11:57 PM row shows state "Please wait…" (text "11:57 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v13_captures/20261002-141248_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v13.log:1223; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v13.log:1235
Counterexample      : `TAP !CV_STATE_A1` → `ACT !D_A1 !SKIP` → `DB_ABORT` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v13.log:1338–1341): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-70  DB_ABORT on 'mark Vitamin C 11:58 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.14.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.14.aut; branch 14 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:16)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v14.log:935, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v14.log:936
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_A2 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v14.log:1219; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Please wait…" (text "11:58 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v14_captures/20261002-141444_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:64)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v14.log:1219; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v14.log:1231
Counterexample      : `TAP !CV_STATE_A2` → `ACT !D_A2 !TAKE` → `DB_ABORT` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v14.log:1334–1337): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-71  DB_ABORT on 'mark Vitamin C 11:58 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.15.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.15.aut; branch 15 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:17)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v15.log:935, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v15.log:936
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_A2 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v15.log:1219; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Please wait…" (text "11:58 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v15_captures/20261002-141641_missing_el_write_error.xml:64)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v15.log:1219; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v15.log:1231
Counterexample      : `TAP !CV_STATE_A2` → `ACT !D_A2 !SKIP` → `DB_ABORT` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v15.log:1334–1337): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-72  DB_ABORT on 'mark Vitamin C 11:59 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.16.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.16.aut; branch 16 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:18)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v16.log:935, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v16.log:936
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_A3 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v16.log:1219; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v16_captures/20261002-141837_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:71)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v16.log:1219; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v16.log:1231
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !TAKE` → `DB_ABORT` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v16.log:1334–1337): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-73  DB_ABORT on 'mark Vitamin C 11:59 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.17.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.17.aut; branch 17 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:19)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v17.log:955, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v17.log:956
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_A3 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v17.log:1243; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v17_captures/20261002-142033_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:71)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v17.log:1243; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v17.log:1255
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !SKIP` → `DB_ABORT` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v17.log:1358–1361): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-74  DB_ABORT on 'mark Zinc 11:56 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.18.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.18.aut; branch 18 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:20)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v18.log:951, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v18.log:952
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_B !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v18.log:1231; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   2 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v18_captures/20261002-142229_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v18.log:1231; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v18.log:1243
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !TAKE` → `DB_ABORT` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v18.log:1346–1349): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-75  DB_ABORT on 'mark Zinc 11:56 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_db_abort / tc_db_abort.19.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_abort/tc_db_abort.19.aut; branch 19 of the purpose, row EVALUATION/medtimer/variants_db_abort.log:21)
Disruption          : DB_ABORT (DB), SQLite trigger `BEFORE INSERT ON ReminderEvent … RAISE(ABORT)` (EVALUATION/medtimer/properties/disruption_mapping.yml:55), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_abort/v19.log:935, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_abort/v19.log:936
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_B !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:253)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/db_abort/v19.log:1223; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   2 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/db_abort/v19_captures/20261002-142425_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_abort/v19.log:1223; verdict EVALUATION/medtimer/generated/variant_logs/db_abort/v19.log:1235
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !SKIP` → `DB_ABORT` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the record INSERT (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventCreator.kt:32) raises and no handler reports it: the scope has no `CoroutineExceptionHandler` (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_abort/v19.log:1338–1341): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report; nothing committed" (EVALUATION/medtimer/properties/disruption_mapping.yml:153); held for the missing report
Reproduced          : walked once
Doubts              : none recorded
```

### db_corrupt

#### MedTimer-76  An unreadable dose status during the re-read of Zinc 11:56 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.1.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.1.aut; branch 1 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:3)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v1.log:2142, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v1.log:2143
Where it struck     : at S12 (relaunch and re-read); the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v1.log:2574; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v1_captures/20261002-090152_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v1.log:2574; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v1.log:2586
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v1.log:2787–2794): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 4|4|TAKEN|1|2.0|1.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-77  An unreadable dose status during the re-read of Vitamin C 11:57 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.2.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.2.aut; branch 2 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:4)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v2.log:2509, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v2.log:2510
Where it struck     : after S11, in place of S12: the tester chose `VIEW !D_A1`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v2.log:2929; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v2_captures/20261002-090555_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v2.log:2929; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v2.log:2941
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v2.log:3142–3149): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|DELETED|0|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-78  An unreadable dose status during the re-read of Vitamin C 11:58 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.3.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.3.aut; branch 3 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:5)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v3.log:2649, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v3.log:2650
Where it struck     : after S11, in place of S12: the tester chose `VIEW !D_A2`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v3.log:3131; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v3_captures/20261002-090954_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v3.log:3131; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v3.log:3143
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v3.log:3344–3351): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-79  An unreadable dose status during the re-read of Vitamin C 11:59 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.4.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.4.aut; branch 4 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:6)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v4.log:2629, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v4.log:2630
Where it struck     : after S11, in place of S12: the tester chose `VIEW !D_A3`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v4.log:3069; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v4_captures/20261002-091402_missing_el_corrupt_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v4.log:3069; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v4.log:3081
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v4.log:3282–3289): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-80  An unreadable dose status during the re-read of Vitamin C 11:59 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.5.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.5.aut; branch 5 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:7)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v5.log:2345, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v5.log:2346
Where it struck     : at S10 (relaunch and re-read); the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v5.log:2785; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v5_captures/20261002-091750_missing_el_corrupt_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v5.log:2785; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v5.log:2797
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v5.log:2978–2984): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-81  An unreadable dose status during the re-read of Vitamin C 11:57 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.6.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.6.aut; branch 6 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:8)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v6.log:2345, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v6.log:2346
Where it struck     : after S9, in place of S10: the tester chose `VIEW !D_A1`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v6.log:2785; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v6_captures/20261002-092142_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v6.log:2785; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v6.log:2797
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v6.log:2978–2984): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|DELETED|0|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-82  An unreadable dose status during the re-read of Vitamin C 11:58 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.7.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.7.aut; branch 7 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:9)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v7.log:2321, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v7.log:2322
Where it struck     : after S9, in place of S10: the tester chose `VIEW !D_A2`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v7.log:2717; MedTimer not in the foreground at the failure: the captured screen belongs to `com.google.android.apps.nexuslauncher` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v7_captures/20261002-092556_missing_el_corrupt_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v7.log:2717; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v7.log:2729
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v7.log:2910–2916): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-83  An unreadable dose status during the re-read of Zinc 11:56 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.8.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.8.aut; branch 8 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:10)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v8.log:1846, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v8.log:1847
Where it struck     : after S9, in place of S10: the tester chose `VIEW !D_B`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v8.log:2262; MedTimer not in the foreground at the failure: the captured screen belongs to `com.google.android.apps.nexuslauncher` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v8_captures/20261002-092931_missing_el_corrupt_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v8.log:2262; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v8.log:2274
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v8.log:2455–2461): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-84  An unreadable dose status during the re-read of Vitamin C 11:58 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.9.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.9.aut; branch 9 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:11)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v9.log:1608, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v9.log:1609
Where it struck     : at S7 (relaunch and re-read); the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v9.log:2090; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v9_captures/20261002-093249_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v9.log:2090; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v9.log:2102
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v9.log:2252–2257): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-85  An unreadable dose status during the re-read of Vitamin C 11:57 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.10.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.10.aut; branch 10 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:12)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v10.log:2007, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v10.log:2008
Where it struck     : after S6, in place of S7: the tester chose `VIEW !D_A1`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v10.log:2405; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v10_captures/20261002-093634_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v10.log:2405; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v10.log:2417
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v10.log:2567–2572): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|DELETED|0|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-86  An unreadable dose status during the re-read of Vitamin C 11:59 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.11.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.11.aut; branch 11 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:13)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v11.log:2187, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v11.log:2188
Where it struck     : after S6, in place of S7: the tester chose `VIEW !D_A3`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v11.log:2635; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v11_captures/20261002-094013_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v11.log:2635; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v11.log:2647
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v11.log:2797–2802): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-87  An unreadable dose status during the re-read of Zinc 11:56 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.12.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.12.aut; branch 12 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:14)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v12.log:2219, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v12.log:2220
Where it struck     : after S6, in place of S7: the tester chose `VIEW !D_B`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v12.log:2665; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v12_captures/20261002-094344_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v12.log:2665; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v12.log:2677
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v12.log:2827–2832): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-88  An unreadable dose status during the re-read of Vitamin C 11:57 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.13.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.13.aut; branch 13 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:15)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v13.log:1915, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v13.log:1916
Where it struck     : at S5 (relaunch and re-read); the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v13.log:2397; MedTimer not in the foreground at the failure: the captured screen belongs to `com.google.android.apps.nexuslauncher` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v13_captures/20261002-094701_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v13.log:2397; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v13.log:2409
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v13.log:2541–2545): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|DELETED|0|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-89  An unreadable dose status during the re-read of Vitamin C 11:58 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.14.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.14.aut; branch 14 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:16)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v14.log:1480, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v14.log:1481
Where it struck     : after S4, in place of S5: the tester chose `VIEW !D_A2`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v14.log:2008; MedTimer not in the foreground at the failure: the captured screen belongs to `com.google.android.apps.nexuslauncher` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v14_captures/20261002-094949_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v14.log:2008; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v14.log:2020
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v14.log:2152–2156): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-90  An unreadable dose status during the re-read of Vitamin C 11:59 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.15.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.15.aut; branch 15 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:17)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v15.log:1440, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v15.log:1441
Where it struck     : after S4, in place of S5: the tester chose `VIEW !D_A3`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v15.log:1948; MedTimer not in the foreground at the failure: the captured screen belongs to `com.google.android.apps.nexuslauncher` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v15_captures/20261002-095237_missing_el_corrupt_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v15.log:1948; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v15.log:1960
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v15.log:2092–2096): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-91  An unreadable dose status during the re-read of Zinc 11:56 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.16.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.16.aut; branch 16 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:18)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v16.log:1452, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v16.log:1453
Where it struck     : after S4, in place of S5: the tester chose `VIEW !D_B`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v16.log:1900; MedTimer not in the foreground at the failure: the captured screen belongs to `com.google.android.apps.nexuslauncher` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v16_captures/20261002-095529_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v16.log:1900; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v16.log:1912
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v16.log:2044–2048): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-92  An unreadable dose status during the re-read of Vitamin C 11:57 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.17.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.17.aut; branch 17 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:19)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v17.log:1175, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v17.log:1176
Where it struck     : at S3 (relaunch and re-read that dose); the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v17.log:1613; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v17_captures/20261002-095805_missing_el_corrupt_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v17.log:1613; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v17.log:1625
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v17.log:1737–1741): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-93  An unreadable dose status during the re-read of Vitamin C 11:58 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.18.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.18.aut; branch 18 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:20)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v18.log:1646, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v18.log:1647
Where it struck     : after S2, in place of S3: the tester chose `VIEW !D_A2`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v18.log:2108; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v18_captures/20261002-100115_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v18.log:2108; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v18.log:2120
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v18.log:2232–2236): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-94  An unreadable dose status during the re-read of Vitamin C 11:59 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.19.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.19.aut; branch 19 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:21)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v19.log:1642, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v19.log:1643
Where it struck     : after S2, in place of S3: the tester chose `VIEW !D_A3`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v19.log:2042; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v19_captures/20261002-100412_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v19.log:2042; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v19.log:2054
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v19.log:2166–2170): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-95  An unreadable dose status during the re-read of Zinc 11:56 PM: no corruption reported
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.20.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt/tc_db_corrupt.20.aut; branch 20 of the purpose, row EVALUATION/medtimer/variants_db_corrupt.log:22)
Disruption          : DB_CORRUPT (DB), newest ReminderEvent.status set to 'BOGUS' (EVALUATION/medtimer/properties/disruption_mapping.yml:82), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt/v20.log:1670, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt/v20.log:1671
Where it struck     : after S2, in place of S3: the tester chose `VIEW !D_B`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v20.log:2118; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v20_captures/20261002-100714_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt/v20.log:2118; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt/v20.log:2130
Counterexample      : `DB_CORRUPT` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidates: the status column is an enum (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/ReminderEventEntity.kt:22) and no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt/v20.log:2242–2246): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies on relaunch, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:156); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

### db_corrupt_stock

#### MedTimer-96  A negative pill count during the re-read of Zinc 11:56 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.1.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.1.aut; branch 1 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:3)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v1.log:2857, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v1.log:2858
Where it struck     : at S12 (relaunch and re-read); the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v1.log:3295; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Taken" (text "11:56 PM ➡ 10:09 AM,   1 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v1_captures/20261002-101049_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v1.log:3295; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v1.log:3307
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v1.log:3508–3515): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 4|4|TAKEN|1|2.0|1.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-97  A negative pill count during the re-read of Vitamin C 11:57 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.2.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.2.aut; branch 2 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:4)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v2.log:2370, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v2.log:2371
Where it struck     : after S11, in place of S12: the tester chose `VIEW !D_A1`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v2.log:2832; MedTimer on screen (overview), no error element; no row for Vitamin C 11:57 PM (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v2_captures/20261002-101358_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v2.log:2832; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v2.log:2844
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v2.log:3045–3052): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|DELETED|0|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-98  A negative pill count during the re-read of Vitamin C 11:58 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.3.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.3.aut; branch 3 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:5)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v3.log:2358, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v3.log:2359
Where it struck     : after S11, in place of S12: the tester chose `VIEW !D_A2`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v3.log:2796; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Skipped" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v3_captures/20261002-101706_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v3.log:2796; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v3.log:2808
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v3.log:3009–3016): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-99  A negative pill count during the re-read of Vitamin C 11:59 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.4.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.4.aut; branch 4 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:6)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v4.log:2442, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v4.log:2443
Where it struck     : after S11, in place of S12: the tester chose `VIEW !D_A3`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v4.log:2880; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Taken" (text "11:59 PM ➡ 10:19 AM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v4_captures/20261002-102016_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v4.log:2880; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v4.log:2892
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v4.log:3093–3100): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-100  A negative pill count during the re-read of Vitamin C 11:59 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.5.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.5.aut; branch 5 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:7)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v5.log:1970, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v5.log:1971
Where it struck     : at S10 (relaunch and re-read); the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v5.log:2388; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Taken" (text "11:59 PM ➡ 10:22 AM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v5_captures/20261002-102320_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v5.log:2388; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v5.log:2400
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v5.log:2581–2587): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-101  A negative pill count during the re-read of Vitamin C 11:57 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.6.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.6.aut; branch 6 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:8)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v6.log:2082, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v6.log:2083
Where it struck     : after S9, in place of S10: the tester chose `VIEW !D_A1`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v6.log:2516; MedTimer on screen (overview), no error element; no row for Vitamin C 11:57 PM (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v6_captures/20261002-102617_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v6.log:2516; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v6.log:2528
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v6.log:2709–2715): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|DELETED|0|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-102  A negative pill count during the re-read of Vitamin C 11:58 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.7.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.7.aut; branch 7 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:9)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v7.log:2050, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v7.log:2051
Where it struck     : after S9, in place of S10: the tester chose `VIEW !D_A2`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v7.log:2480; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Skipped" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v7_captures/20261002-102913_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v7.log:2480; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v7.log:2492
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v7.log:2673–2679): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-103  A negative pill count during the re-read of Zinc 11:56 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.8.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.8.aut; branch 8 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:10)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v8.log:2078, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v8.log:2079
Where it struck     : after S9, in place of S10: the tester chose `VIEW !D_B`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v8.log:2536; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   -1 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v8_captures/20261002-103210_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v8.log:2536; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v8.log:2548
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v8.log:2729–2735): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-104  A negative pill count during the re-read of Vitamin C 11:58 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.9.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.9.aut; branch 9 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:11)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v9.log:1540, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v9.log:1541
Where it struck     : at S7 (relaunch and re-read); the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v9.log:1954; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Skipped" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v9_captures/20261002-103455_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v9.log:1954; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v9.log:1966
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v9.log:2116–2121): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-105  A negative pill count during the re-read of Vitamin C 11:57 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.10.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.10.aut; branch 10 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:12)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v10.log:1736, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v10.log:1737
Where it struck     : after S6, in place of S7: the tester chose `VIEW !D_A1`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v10.log:2158; MedTimer on screen (overview), no error element; no row for Vitamin C 11:57 PM (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v10_captures/20261002-103739_missing_el_corrupt_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v10.log:2158; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v10.log:2170
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v10.log:2320–2325): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|DELETED|0|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-106  A negative pill count during the re-read of Vitamin C 11:59 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.11.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.11.aut; branch 11 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:13)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v11.log:1696, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v11.log:1697
Where it struck     : after S6, in place of S7: the tester chose `VIEW !D_A3`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v11.log:2130; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM,   -1 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v11_captures/20261002-104020_missing_el_corrupt_error.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v11.log:2130; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v11.log:2142
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v11.log:2292–2297): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-107  A negative pill count during the re-read of Zinc 11:56 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.12.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.12.aut; branch 12 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:14)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v12.log:1668, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v12.log:1669
Where it struck     : after S6, in place of S7: the tester chose `VIEW !D_B`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v12.log:2134; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   -1 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v12_captures/20261002-104259_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v12.log:2134; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v12.log:2146
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v12.log:2296–2301): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-108  A negative pill count during the re-read of Vitamin C 11:57 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.13.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.13.aut; branch 13 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:15)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v13.log:1460, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v13.log:1461
Where it struck     : at S5 (relaunch and re-read); the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v13.log:1914; MedTimer on screen (overview), no error element; no row for Vitamin C 11:57 PM (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v13_captures/20261002-104525_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v13.log:1914; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v13.log:1926
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v13.log:2058–2062): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|DELETED|0|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-109  A negative pill count during the re-read of Vitamin C 11:58 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.14.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.14.aut; branch 14 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:16)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v14.log:1404, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v14.log:1405
Where it struck     : after S4, in place of S5: the tester chose `VIEW !D_A2`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v14.log:1790; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Please wait…" (text "11:58 PM,   -1 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v14_captures/20261002-104753_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v14.log:1790; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v14.log:1802
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v14.log:1934–1938): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-110  A negative pill count during the re-read of Vitamin C 11:59 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.15.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.15.aut; branch 15 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:17)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v15.log:1368, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v15.log:1369
Where it struck     : after S4, in place of S5: the tester chose `VIEW !D_A3`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v15.log:1770; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM,   -1 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v15_captures/20261002-105031_missing_el_corrupt_error.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v15.log:1770; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v15.log:1782
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v15.log:1914–1918): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-111  A negative pill count during the re-read of Zinc 11:56 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.16.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.16.aut; branch 16 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:18)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v16.log:1320, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v16.log:1321
Where it struck     : after S4, in place of S5: the tester chose `VIEW !D_B`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v16.log:1718; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   -1 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v16_captures/20261002-105310_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v16.log:1718; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v16.log:1730
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v16.log:1862–1866): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-112  A negative pill count during the re-read of Vitamin C 11:57 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.17.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.17.aut; branch 17 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:19)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v17.log:1127, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v17.log:1128
Where it struck     : at S3 (relaunch and re-read that dose); the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v17.log:1509; MedTimer on screen, no error element; the Vitamin C 11:57 PM row shows state "Taken" (text "11:57 PM ➡ 10:54 AM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v17_captures/20261002-105534_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v17.log:1509; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v17.log:1521
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v17.log:1633–1637): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-113  A negative pill count during the re-read of Vitamin C 11:58 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.18.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.18.aut; branch 18 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:20)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v18.log:1123, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v18.log:1124
Where it struck     : after S2, in place of S3: the tester chose `VIEW !D_A2`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v18.log:1509; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Please wait…" (text "11:58 PM,   -1 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v18_captures/20261002-105758_missing_el_corrupt_error.xml:64)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v18.log:1509; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v18.log:1521
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v18.log:1633–1637): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-114  A negative pill count during the re-read of Vitamin C 11:59 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.19.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.19.aut; branch 19 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:21)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v19.log:1059, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v19.log:1060
Where it struck     : after S2, in place of S3: the tester chose `VIEW !D_A3`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v19.log:1485; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM,   -1 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v19_captures/20261002-110022_observe_new_UiSelector_.textMatches_is_._corrupt_damaged_inv.xml:71)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v19.log:1485; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v19.log:1497
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v19.log:1609–1613): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

#### MedTimer-115  A negative pill count during the re-read of Zinc 11:56 PM: no corruption flagged
```
Purpose / test case : tp_db_corrupt_stock / tc_db_corrupt_stock.20.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_corrupt_stock/tc_db_corrupt_stock.20.aut; branch 20 of the purpose, row EVALUATION/medtimer/variants_db_corrupt_stock.log:22)
Disruption          : DB_CORRUPT_STOCK (DB), every Medicine.amount set to -1 (EVALUATION/medtimer/properties/disruption_mapping.yml:95), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v20.log:1095, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v20.log:1096
Where it struck     : after S2, in place of S3: the tester chose `VIEW !D_B`; the fault interrupts the re-read after the relaunch
The obligation      : O6, a corrupt record is flagged (EVALUATION/medtimer/model/specification_medtimer.lnt:24; EVALUATION/medtimer/model/specification_medtimer.lnt:92)
What the app did    : no DB_CORRUPT_DETECTED element appeared: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v20.log:1521; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   -1 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v20_captures/20261002-110248_missing_el_corrupt_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v20.log:1521; verdict EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v20.log:1533
Counterexample      : `DB_CORRUPT_STOCK` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_CORRUPT_ERROR`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; corrupt data was present with no notice
Root cause in app   : NOT ESTABLISHED (no check of a negative amount was located in the source)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_corrupt_stock/v20.log:1645–1649): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : ""-1 pills left" shown, nothing flagged" (EVALUATION/medtimer/properties/disruption_mapping.yml:157); held for the missing flag; the "-1 pills left" display was not observed
Reproduced          : walked once
Doubts              : the walk stops on the overview, which shows no stock; whether "-1 pills left" was displayed is NOT RECORDED
```

### db_event_loss

#### MedTimer-116  The record of a Taken dose is lost; re-reading Vitamin C 11:57 PM still shows its pill consumed
```
Purpose / test case : tp_db_event_loss / tc_db_event_loss.1.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_event_loss/tc_db_event_loss.1.aut; branch 1 of the purpose, row EVALUATION/medtimer/variants_db_event_loss.log:3)
Disruption          : DB_EVENT_LOSS (DB), the newest ReminderEvent row deleted (EVALUATION/medtimer/properties/disruption_mapping.yml:106), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_event_loss/v1.log:957, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_event_loss/v1.log:958
Where it struck     : right after S2 (mark Vitamin C's 11:57 PM dose Taken) committed; then the tester re-reads `VIEW !D_A1`
The obligation      : O5, after a lost record the stock is what the remaining records imply (EVALUATION/medtimer/model/specification_medtimer.lnt:21; EVALUATION/medtimer/model/specification_medtimer.lnt:376)
What the app did    : EVALUATION/medtimer/generated/variant_logs/db_event_loss/v1.log:1172 ("CONFIRM mismatch — StockBand: AUT expects S3, observed 'vitamin c (2 pills left)' classifies as S2"); MedTimer on screen (overview), no error element; no row for Vitamin C 11:57 PM (EVALUATION/medtimer/generated/variant_logs/db_event_loss/v1_captures/20261002-110433_confirm_stockband_S3_got_S2.xml)
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/db_event_loss/v1.log:1172; verdict EVALUATION/medtimer/generated/variant_logs/db_event_loss/v1.log:1185
Counterexample      : `DB_EVENT_LOSS` → `NAVIGATE !RT_HOME` → `VIEW !D_A1` → `WAIT_FOR !EL_ROW_A1` → `OBSERVE !EL_STATE_A1` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S3 !PENDING !D_A1`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; the stock and the records disagree with no notice
Root cause in app   : the stock is a stored counter changed only by explicit calls (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/dao/MedicineDao.kt:19); no recomputation from the records was located (NOT ESTABLISHED beyond that)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_event_loss/v1.log:1301–1304): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the nominal run's re-reads pass
Forecast            : "the stock stays decremented, dose due again" (EVALUATION/medtimer/properties/disruption_mapping.yml:159); held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-117  The record of a Taken dose is lost; re-reading Vitamin C 11:58 PM still shows its pill consumed
```
Purpose / test case : tp_db_event_loss / tc_db_event_loss.2.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_event_loss/tc_db_event_loss.2.aut; branch 2 of the purpose, row EVALUATION/medtimer/variants_db_event_loss.log:4)
Disruption          : DB_EVENT_LOSS (DB), the newest ReminderEvent row deleted (EVALUATION/medtimer/properties/disruption_mapping.yml:106), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_event_loss/v2.log:985, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_event_loss/v2.log:986
Where it struck     : right after S2 (mark Vitamin C's 11:57 PM dose Taken) committed; then the tester re-reads `VIEW !D_A2`
The obligation      : O5, after a lost record the stock is what the remaining records imply (EVALUATION/medtimer/model/specification_medtimer.lnt:21; EVALUATION/medtimer/model/specification_medtimer.lnt:376)
What the app did    : EVALUATION/medtimer/generated/variant_logs/db_event_loss/v2.log:1156 ("CONFIRM mismatch — StockBand: AUT expects S3, observed 'vitamin c (2 pills left)' classifies as S2"); MedTimer on screen (overview), no error element; no row for Vitamin C 11:58 PM (EVALUATION/medtimer/generated/variant_logs/db_event_loss/v2_captures/20261002-110621_confirm_stockband_S3_got_S2.xml)
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/db_event_loss/v2.log:1156; verdict EVALUATION/medtimer/generated/variant_logs/db_event_loss/v2.log:1169
Counterexample      : `DB_EVENT_LOSS` → `NAVIGATE !RT_HOME` → `VIEW !D_A2` → `WAIT_FOR !EL_ROW_A2` → `OBSERVE !EL_STATE_A2` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S3 !PENDING !D_A2`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; the stock and the records disagree with no notice
Root cause in app   : the stock is a stored counter changed only by explicit calls (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/dao/MedicineDao.kt:19); no recomputation from the records was located (NOT ESTABLISHED beyond that)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_event_loss/v2.log:1285–1288): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the nominal run's re-reads pass
Forecast            : "the stock stays decremented, dose due again" (EVALUATION/medtimer/properties/disruption_mapping.yml:159); held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-118  The record of a Taken dose is lost; re-reading Vitamin C 11:59 PM still shows its pill consumed
```
Purpose / test case : tp_db_event_loss / tc_db_event_loss.3.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_event_loss/tc_db_event_loss.3.aut; branch 3 of the purpose, row EVALUATION/medtimer/variants_db_event_loss.log:5)
Disruption          : DB_EVENT_LOSS (DB), the newest ReminderEvent row deleted (EVALUATION/medtimer/properties/disruption_mapping.yml:106), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_event_loss/v3.log:965, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_event_loss/v3.log:966
Where it struck     : right after S2 (mark Vitamin C's 11:57 PM dose Taken) committed; then the tester re-reads `VIEW !D_A3`
The obligation      : O5, after a lost record the stock is what the remaining records imply (EVALUATION/medtimer/model/specification_medtimer.lnt:21; EVALUATION/medtimer/model/specification_medtimer.lnt:376)
What the app did    : EVALUATION/medtimer/generated/variant_logs/db_event_loss/v3.log:1136 ("CONFIRM mismatch — StockBand: AUT expects S3, observed 'vitamin c (2 pills left)' classifies as S2"); MedTimer on screen (overview), no error element; no row for Vitamin C 11:59 PM (EVALUATION/medtimer/generated/variant_logs/db_event_loss/v3_captures/20261002-110809_confirm_stockband_S3_got_S2.xml)
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/db_event_loss/v3.log:1136; verdict EVALUATION/medtimer/generated/variant_logs/db_event_loss/v3.log:1149
Counterexample      : `DB_EVENT_LOSS` → `NAVIGATE !RT_HOME` → `VIEW !D_A3` → `WAIT_FOR !EL_ROW_A3` → `OBSERVE !EL_STATE_A3` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S3 !PENDING !D_A3`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; the stock and the records disagree with no notice
Root cause in app   : the stock is a stored counter changed only by explicit calls (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/dao/MedicineDao.kt:19); no recomputation from the records was located (NOT ESTABLISHED beyond that)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_event_loss/v3.log:1265–1268): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the nominal run's re-reads pass
Forecast            : "the stock stays decremented, dose due again" (EVALUATION/medtimer/properties/disruption_mapping.yml:159); held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-119  The record of a Taken dose is lost; re-reading Vitamin C 11:59 PM still shows its pill consumed
```
Purpose / test case : tp_db_event_loss / tc_db_event_loss.9.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_event_loss/tc_db_event_loss.9.aut; branch 9 of the purpose, row EVALUATION/medtimer/variants_db_event_loss.log:11)
Disruption          : DB_EVENT_LOSS (DB), the newest ReminderEvent row deleted (EVALUATION/medtimer/properties/disruption_mapping.yml:106), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_event_loss/v9.log:1808, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_event_loss/v9.log:1809
Where it struck     : right after S9 (mark the 11:59 PM dose Taken) committed; then the tester re-reads `VIEW !D_A3`
The obligation      : O5, after a lost record the stock is what the remaining records imply (EVALUATION/medtimer/model/specification_medtimer.lnt:21; EVALUATION/medtimer/model/specification_medtimer.lnt:376)
What the app did    : EVALUATION/medtimer/generated/variant_logs/db_event_loss/v9.log:1959 ("CONFIRM mismatch — StockBand: AUT expects S3, observed 'vitamin c (2 pills left)' classifies as S2"); MedTimer on screen (overview), no error element; no row for Vitamin C 11:59 PM (EVALUATION/medtimer/generated/variant_logs/db_event_loss/v9_captures/20261002-112120_confirm_stockband_S3_got_S2.xml)
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/db_event_loss/v9.log:1959; verdict EVALUATION/medtimer/generated/variant_logs/db_event_loss/v9.log:1972
Counterexample      : `DB_EVENT_LOSS` → `NAVIGATE !RT_HOME` → `VIEW !D_A3` → `WAIT_FOR !EL_ROW_A3` → `OBSERVE !EL_STATE_A3` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S3 !PENDING !D_A3`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; the stock and the records disagree with no notice
Root cause in app   : the stock is a stored counter changed only by explicit calls (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/dao/MedicineDao.kt:19); no recomputation from the records was located (NOT ESTABLISHED beyond that)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_event_loss/v9.log:2157–2162): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the nominal run's re-reads pass
Forecast            : "the stock stays decremented, dose due again" (EVALUATION/medtimer/properties/disruption_mapping.yml:159); held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-120  The record of a Taken dose is lost; re-reading Vitamin C 11:57 PM still shows its pill consumed
```
Purpose / test case : tp_db_event_loss / tc_db_event_loss.10.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_event_loss/tc_db_event_loss.10.aut; branch 10 of the purpose, row EVALUATION/medtimer/variants_db_event_loss.log:12)
Disruption          : DB_EVENT_LOSS (DB), the newest ReminderEvent row deleted (EVALUATION/medtimer/properties/disruption_mapping.yml:106), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_event_loss/v10.log:1724, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_event_loss/v10.log:1725
Where it struck     : right after S9 (mark the 11:59 PM dose Taken) committed; then the tester re-reads `VIEW !D_A1`
The obligation      : O5, after a lost record the stock is what the remaining records imply (EVALUATION/medtimer/model/specification_medtimer.lnt:21; EVALUATION/medtimer/model/specification_medtimer.lnt:376)
What the app did    : EVALUATION/medtimer/generated/variant_logs/db_event_loss/v10.log:1883 ("CONFIRM mismatch — StockBand: AUT expects S3, observed 'vitamin c (2 pills left)' classifies as S2"); MedTimer on screen (overview), no error element; no row for Vitamin C 11:57 PM (EVALUATION/medtimer/generated/variant_logs/db_event_loss/v10_captures/20261002-112352_confirm_stockband_S3_got_S2.xml)
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/db_event_loss/v10.log:1883; verdict EVALUATION/medtimer/generated/variant_logs/db_event_loss/v10.log:1896
Counterexample      : `DB_EVENT_LOSS` → `NAVIGATE !RT_HOME` → `VIEW !D_A1` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S3 !ABSENT !D_A1`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; the stock and the records disagree with no notice
Root cause in app   : the stock is a stored counter changed only by explicit calls (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/dao/MedicineDao.kt:19); no recomputation from the records was located (NOT ESTABLISHED beyond that)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_event_loss/v10.log:2079–2084): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|DELETED|0|3.0|2.0
Separate evidence?  : yes: the nominal run's re-reads pass
Forecast            : "the stock stays decremented, dose due again" (EVALUATION/medtimer/properties/disruption_mapping.yml:159); held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-121  The record of a Taken dose is lost; re-reading Vitamin C 11:58 PM still shows its pill consumed
```
Purpose / test case : tp_db_event_loss / tc_db_event_loss.11.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_event_loss/tc_db_event_loss.11.aut; branch 11 of the purpose, row EVALUATION/medtimer/variants_db_event_loss.log:13)
Disruption          : DB_EVENT_LOSS (DB), the newest ReminderEvent row deleted (EVALUATION/medtimer/properties/disruption_mapping.yml:106), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_event_loss/v11.log:1732, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_event_loss/v11.log:1733
Where it struck     : right after S9 (mark the 11:59 PM dose Taken) committed; then the tester re-reads `VIEW !D_A2`
The obligation      : O5, after a lost record the stock is what the remaining records imply (EVALUATION/medtimer/model/specification_medtimer.lnt:21; EVALUATION/medtimer/model/specification_medtimer.lnt:376)
What the app did    : EVALUATION/medtimer/generated/variant_logs/db_event_loss/v11.log:1903 ("CONFIRM mismatch — StockBand: AUT expects S3, observed 'vitamin c (2 pills left)' classifies as S2"); MedTimer on screen (overview), no error element; no row for Vitamin C 11:58 PM (EVALUATION/medtimer/generated/variant_logs/db_event_loss/v11_captures/20261002-112625_confirm_stockband_S3_got_S2.xml)
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/db_event_loss/v11.log:1903; verdict EVALUATION/medtimer/generated/variant_logs/db_event_loss/v11.log:1916
Counterexample      : `DB_EVENT_LOSS` → `NAVIGATE !RT_HOME` → `VIEW !D_A2` → `WAIT_FOR !EL_ROW_A2` → `OBSERVE !EL_STATE_A2` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S3 !SKIPPED !D_A2`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; the stock and the records disagree with no notice
Root cause in app   : the stock is a stored counter changed only by explicit calls (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/dao/MedicineDao.kt:19); no recomputation from the records was located (NOT ESTABLISHED beyond that)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_event_loss/v11.log:2101–2106): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the nominal run's re-reads pass
Forecast            : "the stock stays decremented, dose due again" (EVALUATION/medtimer/properties/disruption_mapping.yml:159); held
Reproduced          : walked once
Doubts              : none recorded
```

#### MedTimer-122  The record of a Taken dose is lost; re-reading Zinc 11:56 PM still shows its pill consumed
```
Purpose / test case : tp_db_event_loss / tc_db_event_loss.13.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/db_event_loss/tc_db_event_loss.13.aut; branch 13 of the purpose, row EVALUATION/medtimer/variants_db_event_loss.log:15)
Disruption          : DB_EVENT_LOSS (DB), the newest ReminderEvent row deleted (EVALUATION/medtimer/properties/disruption_mapping.yml:106), timing gate; injected EVALUATION/medtimer/generated/variant_logs/db_event_loss/v13.log:2028, confirmed by probe EVALUATION/medtimer/generated/variant_logs/db_event_loss/v13.log:2029
Where it struck     : right after S11 (mark Zinc's 11:56 PM dose Taken) committed; then the tester re-reads `VIEW !D_B`
The obligation      : O5, after a lost record the stock is what the remaining records imply (EVALUATION/medtimer/model/specification_medtimer.lnt:21; EVALUATION/medtimer/model/specification_medtimer.lnt:376)
What the app did    : EVALUATION/medtimer/generated/variant_logs/db_event_loss/v13.log:2199 ("CONFIRM mismatch — StockBand: AUT expects S2, observed 'zinc (1 pills left)' classifies as S1"); MedTimer on screen (overview), no error element; no row for Zinc 11:56 PM (EVALUATION/medtimer/generated/variant_logs/db_event_loss/v13_captures/20261002-113131_confirm_stockband_S2_got_S1.xml)
Verdict and why     : FAIL, oracle mismatch: the observed value contradicts the CONFIRM label the test case expects: EVALUATION/medtimer/generated/variant_logs/db_event_loss/v13.log:2199; verdict EVALUATION/medtimer/generated/variant_logs/db_event_loss/v13.log:2212
Counterexample      : `DB_EVENT_LOSS` → `NAVIGATE !RT_HOME` → `VIEW !D_B` → `WAIT_FOR !EL_ROW_B` → `OBSERVE !EL_STATE_B` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_B` → `CONFIRM !COMMITTED !S2 !PENDING !D_B`
Failure class       : INTEGRITY
Silent failure?     : no: no operation of the user failed; the stock and the records disagree with no notice
Root cause in app   : the stock is a stored counter changed only by explicit calls (EVALUATION/medtimer/sut/medtimer/core/database/src/main/java/com/futsch1/medtimer/database/dao/MedicineDao.kt:19); no recomputation from the records was located (NOT ESTABLISHED beyond that)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/db_event_loss/v13.log:2417–2423): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the nominal run's re-reads pass
Forecast            : "the stock stays decremented, dose due again" (EVALUATION/medtimer/properties/disruption_mapping.yml:159); held
Reproduced          : walked once
Doubts              : none recorded
```

### infra_storage_full

#### MedTimer-123  INFRA_STORAGE_FULL on 'edit Vitamin C 11:59 PM to Skipped': record unchanged, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.1.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.1.aut; branch 1 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:3)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v1.log:2139, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v1.log:2140
Where it struck     : at S13 (edit the 11:59 PM record to Skipped); the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v1.log:2395; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Taken" (text "11:59 PM ➡ 11:07 AM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v1_captures/20261002-110826_missing_el_write_error.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v1.log:2395; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v1.log:2407
Counterexample      : `TAP !CV_TOGGLE_SKIPPED` → `EDIT !D_A3 !SKIP` → `INFRA_STORAGE_FULL` → `TAP !CV_BACK` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record unchanged) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v1.log:2621–2628): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-124  INFRA_STORAGE_FULL on 'delete the record of Vitamin C 11:58 PM': record not deleted, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.2.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.2.aut; branch 2 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:4)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v2.log:2179, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v2.log:2180
Where it struck     : after S12, in place of S13: the tester chose `DELETE !D_A2`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v2.log:2413; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Skipped" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v2_captures/20261002-111244_missing_el_write_error.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v2.log:2413; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v2.log:2425
Counterexample      : `WAIT_FOR !EL_DELETE_DIALOG` → `DELETE !D_A2` → `INFRA_STORAGE_FULL` → `TAP !CV_CONFIRM_DELETE` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record not deleted) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v2.log:2639–2646): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-125  INFRA_STORAGE_FULL on 'edit Vitamin C 11:58 PM to Taken': record unchanged, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.3.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.3.aut; branch 3 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:5)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v3.log:2187, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v3.log:2188
Where it struck     : after S12, in place of S13: the tester chose `EDIT !D_A2 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v3.log:2393; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v3_captures/20261002-111649_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v3.log:2393; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v3.log:2405
Counterexample      : `TAP !CV_TOGGLE_TAKEN` → `EDIT !D_A2 !TAKE` → `INFRA_STORAGE_FULL` → `TAP !CV_BACK` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: the app was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (the walk recorded no stack trace; the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21) is a candidate)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v3.log:2619–2626): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer; the foreground was System UI, which may be the device reacting to the full disk rather than MedTimer crashing
```

#### MedTimer-126  INFRA_STORAGE_FULL on 'delete the record of Vitamin C 11:59 PM': record not deleted, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.4.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.4.aut; branch 4 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:6)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v4.log:2574, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v4.log:2575
Where it struck     : after S12, in place of S13: the tester chose `DELETE !D_A3`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v4.log:2830; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Taken" (text "11:59 PM ➡ 11:19 AM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v4_captures/20261002-112057_missing_el_write_error.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v4.log:2830; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v4.log:2842
Counterexample      : `WAIT_FOR !EL_DELETE_DIALOG` → `DELETE !D_A3` → `INFRA_STORAGE_FULL` → `TAP !CV_CONFIRM_DELETE` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record not deleted) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v4.log:3056–3063): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-127  INFRA_STORAGE_FULL on 'delete the record of Zinc 11:56 PM': record not deleted, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.5.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.5.aut; branch 5 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:7)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v5.log:2207, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v5.log:2208
Where it struck     : after S12, in place of S13: the tester chose `DELETE !D_B`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v5.log:2441; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v5_captures/20261002-112451_missing_el_write_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v5.log:2441; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v5.log:2453
Counterexample      : `WAIT_FOR !EL_DELETE_DIALOG` → `DELETE !D_B` → `INFRA_STORAGE_FULL` → `TAP !CV_CONFIRM_DELETE` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: the app was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (the walk recorded no stack trace; the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21) is a candidate)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v5.log:2667–2674): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 4|4|TAKEN|1|2.0|1.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer; the foreground was System UI, which may be the device reacting to the full disk rather than MedTimer crashing
```

#### MedTimer-128  INFRA_STORAGE_FULL on 'edit Zinc 11:56 PM to Skipped': record unchanged, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.6.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.6.aut; branch 6 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:8)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v6.log:2426, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v6.log:2427
Where it struck     : after S12, in place of S13: the tester chose `EDIT !D_B !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v6.log:2616; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Taken" (text "11:56 PM ➡ 11:29 AM,   1 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v6_captures/20261002-113127_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v6.log:2616; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v6.log:2628
Counterexample      : `TAP !CV_TOGGLE_SKIPPED` → `EDIT !D_B !SKIP` → `INFRA_STORAGE_FULL` → `TAP !CV_BACK` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record unchanged) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v6.log:2842–2849): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 4|4|TAKEN|1|2.0|1.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-129  INFRA_STORAGE_FULL on 'mark Zinc 11:56 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.7.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.7.aut; branch 7 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:9)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v7.log:1706, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v7.log:1707
Where it struck     : at S11 (mark Zinc's 11:56 PM dose Taken); the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v7.log:1862; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   2 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v7_captures/20261002-114151_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v7.log:1862; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v7.log:1874
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !TAKE` → `INFRA_STORAGE_FULL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v7.log:2066–2072): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-130  INFRA_STORAGE_FULL on 'mark Zinc 11:56 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.8.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.8.aut; branch 8 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:10)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v8.log:1858, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v8.log:1859
Where it struck     : after S10, in place of S11: the tester chose `ACT !D_B !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v8.log:2124; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v8_captures/20261002-114608_missing_el_write_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v8.log:2124; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v8.log:2136
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !SKIP` → `INFRA_STORAGE_FULL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: the app was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (the walk recorded no stack trace; the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21) is a candidate)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v8.log:2328–2334): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer; the foreground was System UI, which may be the device reacting to the full disk rather than MedTimer crashing
```

#### MedTimer-131  INFRA_STORAGE_FULL on 'delete the record of Vitamin C 11:58 PM': record not deleted, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.9.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.9.aut; branch 9 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:11)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v9.log:2406, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v9.log:2407
Where it struck     : after S10, in place of S11: the tester chose `DELETE !D_A2`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v9.log:2622; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Skipped" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v9_captures/20261002-115018_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v9.log:2622; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v9.log:2634
Counterexample      : `WAIT_FOR !EL_DELETE_DIALOG` → `DELETE !D_A2` → `INFRA_STORAGE_FULL` → `TAP !CV_CONFIRM_DELETE` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record not deleted) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v9.log:2828–2834): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-132  INFRA_STORAGE_FULL on 'edit Vitamin C 11:58 PM to Taken': record unchanged, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.10.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.10.aut; branch 10 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:12)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v10.log:1911, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v10.log:1912
Where it struck     : after S10, in place of S11: the tester chose `EDIT !D_A2 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v10.log:2143; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Skipped" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v10_captures/20261002-115350_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v10.log:2143; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v10.log:2155
Counterexample      : `TAP !CV_TOGGLE_TAKEN` → `EDIT !D_A2 !TAKE` → `INFRA_STORAGE_FULL` → `TAP !CV_BACK` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record unchanged) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v10.log:2349–2355): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-133  INFRA_STORAGE_FULL on 'delete the record of Vitamin C 11:59 PM': record not deleted, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.11.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.11.aut; branch 11 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:13)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v11.log:1951, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v11.log:1952
Where it struck     : after S10, in place of S11: the tester chose `DELETE !D_A3`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v11.log:2141; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Taken" (text "11:59 PM ➡ 11:56 AM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v11_captures/20261002-115727_missing_el_write_error.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v11.log:2141; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v11.log:2153
Counterexample      : `WAIT_FOR !EL_DELETE_DIALOG` → `DELETE !D_A3` → `INFRA_STORAGE_FULL` → `TAP !CV_CONFIRM_DELETE` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record not deleted) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v11.log:2347–2353): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-134  INFRA_STORAGE_FULL on 'edit Vitamin C 11:59 PM to Skipped': record unchanged, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.12.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.12.aut; branch 12 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:14)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v12.log:1931, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v12.log:1932
Where it struck     : after S10, in place of S11: the tester chose `EDIT !D_A3 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v12.log:2171; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Taken" (text "11:59 PM ➡ 12:00 PM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v12_captures/20261002-120057_missing_el_write_error.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v12.log:2171; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v12.log:2183
Counterexample      : `TAP !CV_TOGGLE_SKIPPED` → `EDIT !D_A3 !SKIP` → `INFRA_STORAGE_FULL` → `TAP !CV_BACK` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record unchanged) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v12.log:2377–2383): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-135  INFRA_STORAGE_FULL on 'mark Vitamin C 11:59 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.13.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.13.aut; branch 13 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:15)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v13.log:1650, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v13.log:1651
Where it struck     : at S9 (mark the 11:59 PM dose Taken); the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v13.log:1902; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v13_captures/20261002-120415_missing_el_write_error.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v13.log:1902; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v13.log:1914
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !TAKE` → `INFRA_STORAGE_FULL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v13.log:2086–2091): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-136  INFRA_STORAGE_FULL on 'mark Zinc 11:56 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.14.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.14.aut; branch 14 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:16)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v14.log:1670, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v14.log:1671
Where it struck     : after S8, in place of S9: the tester chose `ACT !D_B !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v14.log:1904; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   2 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v14_captures/20261002-120742_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v14.log:1904; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v14.log:1916
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !TAKE` → `INFRA_STORAGE_FULL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v14.log:2088–2093): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-137  INFRA_STORAGE_FULL on 'mark Zinc 11:56 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.15.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.15.aut; branch 15 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:17)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v15.log:1702, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v15.log:1703
Where it struck     : after S8, in place of S9: the tester chose `ACT !D_B !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v15.log:1928; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   2 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v15_captures/20261002-121117_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v15.log:1928; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v15.log:1940
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !SKIP` → `INFRA_STORAGE_FULL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v15.log:2112–2117): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-138  INFRA_STORAGE_FULL on 'delete the record of Vitamin C 11:58 PM': record not deleted, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.16.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.16.aut; branch 16 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:18)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v16.log:1775, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v16.log:1776
Where it struck     : after S8, in place of S9: the tester chose `DELETE !D_A2`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v16.log:2045; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Skipped" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v16_captures/20261002-121454_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v16.log:2045; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v16.log:2057
Counterexample      : `WAIT_FOR !EL_DELETE_DIALOG` → `DELETE !D_A2` → `INFRA_STORAGE_FULL` → `TAP !CV_CONFIRM_DELETE` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record not deleted) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v16.log:2231–2236): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-139  INFRA_STORAGE_FULL on 'edit Vitamin C 11:58 PM to Taken': record unchanged, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.17.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.17.aut; branch 17 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:19)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v17.log:1747, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v17.log:1748
Where it struck     : after S8, in place of S9: the tester chose `EDIT !D_A2 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v17.log:2009; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Skipped" (text "11:58 PM / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v17_captures/20261002-121819_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v17.log:2009; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v17.log:2021
Counterexample      : `TAP !CV_TOGGLE_TAKEN` → `EDIT !D_A2 !TAKE` → `INFRA_STORAGE_FULL` → `TAP !CV_BACK` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record unchanged) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v17.log:2195–2200): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-140  INFRA_STORAGE_FULL on 'mark Vitamin C 11:58 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.18.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.18.aut; branch 18 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:20)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v18.log:1388, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v18.log:1389
Where it struck     : at S6 (mark the 11:58 PM dose Skipped); the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v18.log:1662; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Please wait…" (text "11:58 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v18_captures/20261002-122132_missing_el_write_error.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v18.log:1662; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v18.log:1674
Counterexample      : `TAP !CV_STATE_A2` → `ACT !D_A2 !SKIP` → `INFRA_STORAGE_FULL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v18.log:1815–1819): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-141  INFRA_STORAGE_FULL on 'mark Vitamin C 11:58 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.19.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.19.aut; branch 19 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:21)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v19.log:1412, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v19.log:1413
Where it struck     : after S5, in place of S6: the tester chose `ACT !D_A2 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v19.log:1694; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Please wait…" (text "11:58 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v19_captures/20261002-122444_missing_el_write_error.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v19.log:1694; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v19.log:1706
Counterexample      : `TAP !CV_STATE_A2` → `ACT !D_A2 !TAKE` → `INFRA_STORAGE_FULL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v19.log:1847–1851): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-142  INFRA_STORAGE_FULL on 'mark Vitamin C 11:59 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.20.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.20.aut; branch 20 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:22)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v20.log:1404, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v20.log:1405
Where it struck     : after S5, in place of S6: the tester chose `ACT !D_A3 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v20.log:1616; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v20_captures/20261002-122802_missing_el_write_error.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v20.log:1616; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v20.log:1628
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !TAKE` → `INFRA_STORAGE_FULL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v20.log:1769–1773): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-143  INFRA_STORAGE_FULL on 'mark Vitamin C 11:59 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.21.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.21.aut; branch 21 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:23)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v21.log:1368, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v21.log:1369
Where it struck     : after S5, in place of S6: the tester chose `ACT !D_A3 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v21.log:1600; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v21_captures/20261002-123119_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:63)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v21.log:1600; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v21.log:1612
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !SKIP` → `INFRA_STORAGE_FULL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v21.log:1753–1757): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-144  INFRA_STORAGE_FULL on 'mark Zinc 11:56 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.22.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.22.aut; branch 22 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:24)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v22.log:1388, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v22.log:1389
Where it struck     : after S5, in place of S6: the tester chose `ACT !D_B !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v22.log:1624; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   2 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v22_captures/20261002-123432_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v22.log:1624; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v22.log:1636
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !TAKE` → `INFRA_STORAGE_FULL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v22.log:1777–1781): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-145  INFRA_STORAGE_FULL on 'mark Zinc 11:56 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.23.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.23.aut; branch 23 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:25)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v23.log:1472, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v23.log:1473
Where it struck     : after S5, in place of S6: the tester chose `ACT !D_B !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v23.log:1686; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   2 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v23_captures/20261002-123747_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v23.log:1686; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v23.log:1698
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !SKIP` → `INFRA_STORAGE_FULL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v23.log:1839–1843): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-146  INFRA_STORAGE_FULL on 'delete the record of Vitamin C 11:57 PM': record not deleted, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.24.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.24.aut; branch 24 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:26)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v24.log:1172, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v24.log:1173
Where it struck     : at S4 (delete that dose's record); the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v24.log:1392; MedTimer on screen, no error element; the Vitamin C 11:57 PM row shows state "Taken" (text "11:57 PM ➡ 12:39 PM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v24_captures/20261002-124020_missing_el_write_error.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v24.log:1392; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v24.log:1404
Counterexample      : `WAIT_FOR !EL_DELETE_DIALOG` → `DELETE !D_A1` → `INFRA_STORAGE_FULL` → `TAP !CV_CONFIRM_DELETE` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record not deleted) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v24.log:1529–1533): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-147  INFRA_STORAGE_FULL on 'mark Vitamin C 11:58 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.25.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.25.aut; branch 25 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:27)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v25.log:1167, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v25.log:1168
Where it struck     : after S3, in place of S4: the tester chose `ACT !D_A2 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v25.log:1415; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Please wait…" (text "11:58 PM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v25_captures/20261002-124255_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:64)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v25.log:1415; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v25.log:1427
Counterexample      : `TAP !CV_STATE_A2` → `ACT !D_A2 !TAKE` → `INFRA_STORAGE_FULL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v25.log:1550–1554): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-148  INFRA_STORAGE_FULL on 'mark Vitamin C 11:58 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.26.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.26.aut; branch 26 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:28)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v26.log:1135, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v26.log:1136
Where it struck     : after S3, in place of S4: the tester chose `ACT !D_A2 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v26.log:1383; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Please wait…" (text "11:58 PM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v26_captures/20261002-124529_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:64)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v26.log:1383; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v26.log:1395
Counterexample      : `TAP !CV_STATE_A2` → `ACT !D_A2 !SKIP` → `INFRA_STORAGE_FULL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v26.log:1518–1522): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-149  INFRA_STORAGE_FULL on 'mark Vitamin C 11:59 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.27.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.27.aut; branch 27 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:29)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v27.log:1131, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v27.log:1132
Where it struck     : after S3, in place of S4: the tester chose `ACT !D_A3 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v27.log:1367; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v27_captures/20261002-124758_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:71)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v27.log:1367; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v27.log:1379
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !TAKE` → `INFRA_STORAGE_FULL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v27.log:1502–1506): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-150  INFRA_STORAGE_FULL on 'mark Vitamin C 11:59 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.28.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.28.aut; branch 28 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:43)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v28.log:1063, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v28.log:1064
Where it struck     : after S3, in place of S4: the tester chose `ACT !D_A3 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v28.log:1239; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v28_captures/20261002-152309_missing_el_write_error.xml:71)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v28.log:1239; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v28.log:1251
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !SKIP` → `INFRA_STORAGE_FULL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v28.log:1374–1378): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked twice: the first attempt ended without a verdict (§7), the second gave this FAIL
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-151  INFRA_STORAGE_FULL on 'mark Zinc 11:56 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.29.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.29.aut; branch 29 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:31)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v29.log:1120, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v29.log:1121
Where it struck     : after S3, in place of S4: the tester chose `ACT !D_B !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v29.log:1264; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   2 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v29_captures/20261002-130617_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v29.log:1264; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v29.log:1276
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !TAKE` → `INFRA_STORAGE_FULL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v29.log:1399–1403): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-152  INFRA_STORAGE_FULL on 'mark Zinc 11:56 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.30.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.30.aut; branch 30 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:44)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v30.log:1079, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v30.log:1080
Where it struck     : after S3, in place of S4: the tester chose `ACT !D_B !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v30.log:1247; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v30_captures/20261002-153129_missing_el_write_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v30.log:1247; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v30.log:1259
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !SKIP` → `INFRA_STORAGE_FULL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: the app was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (the walk recorded no stack trace; the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21) is a candidate)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v30.log:1382–1386): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked twice: the first attempt ended without a verdict (§7), the second gave this FAIL
Doubts              : a full data partition affects the whole device, not only MedTimer; the foreground was System UI, which may be the device reacting to the full disk rather than MedTimer crashing
```

#### MedTimer-153  INFRA_STORAGE_FULL on 'edit Vitamin C 11:57 PM to Skipped': record unchanged, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.31.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.31.aut; branch 31 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:33)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v31.log:1307, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v31.log:1308
Where it struck     : after S3, in place of S4: the tester chose `EDIT !D_A1 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v31.log:1453; MedTimer on screen, no error element; the Vitamin C 11:57 PM row shows state "Taken" (text "11:57 PM ➡ 1:22 PM,   2 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v31_captures/20261002-132527_missing_el_write_error.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v31.log:1453; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v31.log:1465
Counterexample      : `TAP !CV_TOGGLE_SKIPPED` → `EDIT !D_A1 !SKIP` → `INFRA_STORAGE_FULL` → `TAP !CV_BACK` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (record unchanged) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v31.log:1590–1594): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-154  INFRA_STORAGE_FULL on 'mark Vitamin C 11:57 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.32.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.32.aut; branch 32 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:34)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v32.log:847, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v32.log:848
Where it struck     : at S2 (mark Vitamin C's 11:57 PM dose Taken); the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v32.log:1001; MedTimer on screen, no error element; the Vitamin C 11:57 PM row shows state "Please wait…" (text "11:57 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v32_captures/20261002-133401_missing_el_write_error.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v32.log:1001; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v32.log:1013
Counterexample      : `TAP !CV_STATE_A1` → `ACT !D_A1 !TAKE` → `INFRA_STORAGE_FULL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v32.log:1116–1119): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-155  INFRA_STORAGE_FULL on 'mark Vitamin C 11:57 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.33.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.33.aut; branch 33 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:35)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v33.log:860, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v33.log:861
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_A1 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v33.log:1018; MedTimer on screen, no error element; the Vitamin C 11:57 PM row shows state "Please wait…" (text "11:57 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v33_captures/20261002-134638_missing_el_write_error.xml:56)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v33.log:1018; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v33.log:1030
Counterexample      : `TAP !CV_STATE_A1` → `ACT !D_A1 !SKIP` → `INFRA_STORAGE_FULL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v33.log:1133–1136): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-156  INFRA_STORAGE_FULL on 'mark Vitamin C 11:58 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.34.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.34.aut; branch 34 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:36)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v34.log:867, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v34.log:868
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_A2 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v34.log:1089; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Please wait…" (text "11:58 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v34_captures/20261002-135055_missing_el_write_error.xml:64)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v34.log:1089; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v34.log:1101
Counterexample      : `TAP !CV_STATE_A2` → `ACT !D_A2 !TAKE` → `INFRA_STORAGE_FULL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v34.log:1204–1207): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-157  INFRA_STORAGE_FULL on 'mark Vitamin C 11:58 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.35.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.35.aut; branch 35 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:37)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v35.log:859, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v35.log:860
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_A2 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v35.log:1117; MedTimer on screen, no error element; the Vitamin C 11:58 PM row shows state "Please wait…" (text "11:58 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v35_captures/20261002-135821_missing_el_write_error.xml:64)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v35.log:1117; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v35.log:1129
Counterexample      : `TAP !CV_STATE_A2` → `ACT !D_A2 !SKIP` → `INFRA_STORAGE_FULL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v35.log:1232–1235): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-158  INFRA_STORAGE_FULL on 'mark Vitamin C 11:59 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.36.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.36.aut; branch 36 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:38)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v36.log:967, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v36.log:968
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_A3 !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v36.log:1177; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v36_captures/20261002-140053_missing_el_write_error.xml:71)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v36.log:1177; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v36.log:1189
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !TAKE` → `INFRA_STORAGE_FULL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v36.log:1292–1295): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-159  INFRA_STORAGE_FULL on 'mark Vitamin C 11:59 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.37.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.37.aut; branch 37 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:39)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v37.log:923, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v37.log:924
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_A3 !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v37.log:1157; MedTimer on screen, no error element; the Vitamin C 11:59 PM row shows state "Please wait…" (text "11:59 PM,   3 pills / Vitamin C (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v37_captures/20261002-140330_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:71)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v37.log:1157; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v37.log:1169
Counterexample      : `TAP !CV_STATE_A3` → `ACT !D_A3 !SKIP` → `INFRA_STORAGE_FULL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v37.log:1272–1275): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-160  INFRA_STORAGE_FULL on 'mark Zinc 11:56 PM Taken': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.38.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.38.aut; branch 38 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:40)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v38.log:907, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v38.log:908
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_B !TAKE`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v38.log:1153; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   2 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v38_captures/20261002-140607_missing_el_write_error.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v38.log:1153; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v38.log:1165
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !TAKE` → `INFRA_STORAGE_FULL` → `TAP !CV_TAKEN` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v38.log:1268–1271): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

#### MedTimer-161  INFRA_STORAGE_FULL on 'mark Zinc 11:56 PM Skipped': no record, stock unchanged, no error shown
```
Purpose / test case : tp_infra_storage_full / tc_infra_storage_full.39.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_full/tc_infra_storage_full.39.aut; branch 39 of the purpose, row EVALUATION/medtimer/variants_infra_storage_full.log:41)
Disruption          : INFRA_STORAGE_FULL (INFRA), ballast file written with `dd` until the data partition is full (EVALUATION/medtimer/properties/disruption_mapping.yml:65), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v39.log:931, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v39.log:932
Where it struck     : after S1, in place of S2: the tester chose `ACT !D_B !SKIP`; the fault is armed after the popup opens and before the commit tap (the gate stands before the tap)
The obligation      : O4, a failed write is reported and nothing moved (EVALUATION/medtimer/model/specification_medtimer.lnt:20; EVALUATION/medtimer/model/specification_medtimer.lnt:81; fault sibling EVALUATION/medtimer/model/specification_medtimer.lnt:256)
What the app did    : no write error appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v39.log:1169; MedTimer on screen, no error element; the Zinc 11:56 PM row shows state "Please wait…" (text "11:56 PM,   2 pills / Zinc (1)") (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v39_captures/20261002-140840_observe_new_UiSelector_.textMatches_is_._error_failed_could_.xml:48)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v39.log:1169; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v39.log:1181
Counterexample      : `TAP !CV_STATE_B` → `ACT !D_B !SKIP` → `INFRA_STORAGE_FULL` → `TAP !CV_SKIPPED` → `OBSERVE !EL_WRITE_ERROR`
Failure class       : SILENT
Silent failure?     : yes: the write did not take effect (no record) and the app reported nothing and stayed on its screen
Root cause in app   : the failing write is not caught and nothing reports it (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_full/v39.log:1284–1287): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same write without the fault passes its checkpoint on the nominal run
Forecast            : "no report" (EVALUATION/medtimer/properties/disruption_mapping.yml:154); held for the missing report; the forecast did not say whether the app survives
Reproduced          : walked once
Doubts              : a full data partition affects the whole device, not only MedTimer
```

### infra_storage_media

#### MedTimer-162  Database files made unreadable during the re-read of Zinc 11:56 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.1.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.1.aut; branch 1 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:3)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v1.log:2314, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v1.log:2315
Where it struck     : at S12 (relaunch and re-read); the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v1.log:2726; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v1_captures/20261002-114255_missing_el_storage_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v1.log:2726; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v1.log:2738
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v1.log:2939–2946): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 4|4|TAKEN|1|2.0|1.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-163  Database files made unreadable during the re-read of Vitamin C 11:57 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.2.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.2.aut; branch 2 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:4)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v2.log:2629, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v2.log:2630
Where it struck     : after S11, in place of S12: the tester chose `VIEW !D_A1`; the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v2.log:3017; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v2_captures/20261002-114712_missing_el_storage_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v2.log:3017; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v2.log:3029
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v2.log:3230–3237): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|DELETED|0|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-164  Database files made unreadable during the re-read of Vitamin C 11:58 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.3.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.3.aut; branch 3 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:5)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v3.log:2569, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v3.log:2570
Where it struck     : after S11, in place of S12: the tester chose `VIEW !D_A2`; the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v3.log:2987; MedTimer not in the foreground at the failure: the captured screen belongs to `com.google.android.apps.nexuslauncher` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v3_captures/20261002-115134_observe_new_UiSelector_.textMatches_is_._storage_database_da.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v3.log:2987; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v3.log:2999
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v3.log:3200–3207): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-165  Database files made unreadable during the re-read of Vitamin C 11:59 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.4.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.4.aut; branch 4 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:6)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v4.log:2070, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v4.log:2071
Where it struck     : after S11, in place of S12: the tester chose `VIEW !D_A3`; the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v4.log:2462; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v4_captures/20261002-115553_observe_new_UiSelector_.textMatches_is_._storage_database_da.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v4.log:2462; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v4.log:2474
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v4.log:2675–2682): Medicine 1|Vitamin C|2.0; 2|Zinc|1.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-166  Database files made unreadable during the re-read of Vitamin C 11:59 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.5.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.5.aut; branch 5 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:7)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v5.log:2297, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v5.log:2298
Where it struck     : at S10 (relaunch and re-read); the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v5.log:2725; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v5_captures/20261002-120008_missing_el_storage_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v5.log:2725; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v5.log:2737
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v5.log:2918–2924): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 3|3|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-167  Database files made unreadable during the re-read of Vitamin C 11:57 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.6.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.6.aut; branch 6 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:8)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v6.log:2301, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v6.log:2302
Where it struck     : after S9, in place of S10: the tester chose `VIEW !D_A1`; the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v6.log:2733; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v6_captures/20261002-120430_observe_new_UiSelector_.textMatches_is_._storage_database_da.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v6.log:2733; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v6.log:2745
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v6.log:2926–2932): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|DELETED|0|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-168  Database files made unreadable during the re-read of Vitamin C 11:58 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.7.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.7.aut; branch 7 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:9)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v7.log:2349, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v7.log:2350
Where it struck     : after S9, in place of S10: the tester chose `VIEW !D_A2`; the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v7.log:2803; MedTimer not in the foreground at the failure: the captured screen belongs to `com.google.android.apps.nexuslauncher` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v7_captures/20261002-120850_missing_el_storage_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v7.log:2803; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v7.log:2815
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v7.log:2996–3002): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-169  Database files made unreadable during the re-read of Zinc 11:56 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.8.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.8.aut; branch 8 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:10)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v8.log:1942, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v8.log:1943
Where it struck     : after S9, in place of S10: the tester chose `VIEW !D_B`; the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v8.log:2350; MedTimer not in the foreground at the failure: the captured screen belongs to `com.google.android.apps.nexuslauncher` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v8_captures/20261002-121254_missing_el_storage_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v8.log:2350; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v8.log:2362
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v8.log:2543–2549): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-170  Database files made unreadable during the re-read of Vitamin C 11:58 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.9.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.9.aut; branch 9 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:11)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v9.log:1620, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v9.log:1621
Where it struck     : at S7 (relaunch and re-read); the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v9.log:2016; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v9_captures/20261002-121638_missing_el_storage_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v9.log:2016; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v9.log:2028
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v9.log:2178–2183): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 2|2|SKIPPED|0|3.0|3.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-171  Database files made unreadable during the re-read of Vitamin C 11:57 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.10.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.10.aut; branch 10 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:12)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v10.log:1987, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v10.log:1988
Where it struck     : after S6, in place of S7: the tester chose `VIEW !D_A1`; the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v10.log:2405; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v10_captures/20261002-122029_missing_el_storage_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v10.log:2405; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v10.log:2417
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v10.log:2567–2572): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|DELETED|0|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-172  Database files made unreadable during the re-read of Vitamin C 11:59 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.11.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.11.aut; branch 11 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:13)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v11.log:2007, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v11.log:2008
Where it struck     : after S6, in place of S7: the tester chose `VIEW !D_A3`; the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v11.log:2403; MedTimer not in the foreground at the failure: the captured screen belongs to `com.google.android.apps.nexuslauncher` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v11_captures/20261002-122440_missing_el_storage_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v11.log:2403; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v11.log:2415
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v11.log:2565–2570): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-173  Database files made unreadable during the re-read of Zinc 11:56 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.12.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.12.aut; branch 12 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:14)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v12.log:1516, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v12.log:1517
Where it struck     : after S6, in place of S7: the tester chose `VIEW !D_B`; the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v12.log:1984; MedTimer not in the foreground at the failure: the captured screen belongs to `com.google.android.apps.nexuslauncher` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v12_captures/20261002-122828_observe_new_UiSelector_.textMatches_is_._storage_database_da.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v12.log:1984; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v12.log:1996
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v12.log:2146–2151): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-174  Database files made unreadable during the re-read of Vitamin C 11:57 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.13.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.13.aut; branch 13 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:15)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v13.log:1352, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v13.log:1353
Where it struck     : at S5 (relaunch and re-read); the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v13.log:1792; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v13_captures/20261002-123155_observe_new_UiSelector_.textMatches_is_._storage_database_da.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v13.log:1792; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v13.log:1804
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v13.log:1936–1940): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|DELETED|0|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-175  Database files made unreadable during the re-read of Vitamin C 11:58 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.14.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.14.aut; branch 14 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:16)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v14.log:1775, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v14.log:1776
Where it struck     : after S4, in place of S5: the tester chose `VIEW !D_A2`; the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v14.log:2207; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v14_captures/20261002-123552_observe_new_UiSelector_.textMatches_is_._storage_database_da.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v14.log:2207; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v14.log:2219
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v14.log:2351–2355): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-176  Database files made unreadable during the re-read of Vitamin C 11:59 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.15.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.15.aut; branch 15 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:17)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v15.log:1751, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v15.log:1752
Where it struck     : after S4, in place of S5: the tester chose `VIEW !D_A3`; the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v15.log:2203; MedTimer not in the foreground at the failure: the captured screen belongs to `com.google.android.apps.nexuslauncher` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v15_captures/20261002-123942_missing_el_storage_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v15.log:2203; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v15.log:2215
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v15.log:2347–2351): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-177  Database files made unreadable during the re-read of Zinc 11:56 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.16.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.16.aut; branch 16 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:18)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v16.log:1292, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v16.log:1293
Where it struck     : after S4, in place of S5: the tester chose `VIEW !D_B`; the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v16.log:1694; MedTimer not in the foreground at the failure: the captured screen belongs to `com.google.android.apps.nexuslauncher` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v16_captures/20261002-124317_missing_el_storage_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v16.log:1694; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v16.log:1706
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v16.log:1838–1842): Medicine 1|Vitamin C|3.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-178  Database files made unreadable during the re-read of Vitamin C 11:57 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.17.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.17.aut; branch 17 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:19)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v17.log:1059, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v17.log:1060
Where it struck     : at S3 (relaunch and re-read that dose); the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v17.log:1529; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v17_captures/20261002-124618_missing_el_storage_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v17.log:1529; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v17.log:1541
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v17.log:1653–1657): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|TAKEN|1|3.0|2.0
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-179  Database files made unreadable during the re-read of Vitamin C 11:58 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.18.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.18.aut; branch 18 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:20)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v18.log:1498, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v18.log:1499
Where it struck     : after S2, in place of S3: the tester chose `VIEW !D_A2`; the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v18.log:1906; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v18_captures/20261002-124951_missing_el_storage_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v18.log:1906; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v18.log:1918
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v18.log:2030–2034): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-180  Database files made unreadable during the re-read of Vitamin C 11:59 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.19.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.19.aut; branch 19 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:21)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v19.log:1590, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v19.log:1591
Where it struck     : after S2, in place of S3: the tester chose `VIEW !D_A3`; the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v19.log:2034; MedTimer not in the foreground at the failure: the captured screen belongs to `com.android.systemui` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v19_captures/20261002-125323_missing_el_storage_error.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v19.log:2034; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v19.log:2046
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v19.log:2158–2162): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

#### MedTimer-181  Database files made unreadable during the re-read of Zinc 11:56 PM: no storage error reported
```
Purpose / test case : tp_infra_storage_media / tc_infra_storage_media.20.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/infra_storage_media/tc_infra_storage_media.20.aut; branch 20 of the purpose, row EVALUATION/medtimer/variants_infra_storage_media.log:22)
Disruption          : INFRA_STORAGE_MEDIA (INFRA), `chmod 0000` on the database files, then force-stop and relaunch (EVALUATION/medtimer/properties/disruption_mapping.yml:116), timing gate; injected EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v20.log:1626, confirmed by probe EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v20.log:1627
Where it struck     : after S2, in place of S3: the tester chose `VIEW !D_B`; the fault interrupts the re-read after the relaunch
The obligation      : O7, an unreadable store is reported (EVALUATION/medtimer/model/specification_medtimer.lnt:25; EVALUATION/medtimer/model/specification_medtimer.lnt:93)
What the app did    : no INFRA_STORAGE_ERROR element appeared: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v20.log:2108; MedTimer not in the foreground at the failure: the captured screen belongs to `com.google.android.apps.nexuslauncher` (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v20_captures/20261002-125640_observe_new_UiSelector_.textMatches_is_._storage_database_da.xml)
Verdict and why     : FAIL, an output the specification owes did not appear and the test case offers no `:DELTA:` at that state: EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v20.log:2108; verdict EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v20.log:2120
Counterexample      : `INFRA_STORAGE_MEDIA` → `NAVIGATE !RT_HOME` → `OBSERVE !EL_STORAGE_ERROR`
Failure class       : MISSING-REPORT
Silent failure?     : no: MedTimer was not on screen at the failure, so it did not carry on
Root cause in app   : NOT ESTABLISHED (no stack trace recorded); candidate: no exception handler is installed (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21)
Data store evidence : after the walk and the restore (EVALUATION/medtimer/generated/variant_logs/infra_storage_media/v20.log:2232–2236): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): no row
Separate evidence?  : yes: the same re-read without the fault passes its checkpoint on the nominal run
Forecast            : "the app dies at the first query" (EVALUATION/medtimer/properties/disruption_mapping.yml:158); held
Reproduced          : walked once
Doubts              : the dialog on screen is not recorded as text, only its package
```

### informative PASSes

#### MedTimer-182  A kill right after tapping Taken on the Zinc dose leaves nothing half-done
```
Purpose / test case : tp_ue_kill / tc_ue_kill.7.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/ue_kill/tc_ue_kill.7.aut; branch 7 of the purpose, row EVALUATION/medtimer/variants_ue_kill.log:9)
Disruption          : UE_KILL (USER), process killed and relaunched by the System Interface's `navigate` right after the commit tap (EVALUATION/medtimer/properties/disruption_mapping.yml:33), timing none
Where it struck     : at S11 (mark Zinc's 11:56 PM dose Taken); the process is killed and relaunched right after the commit tap (the System Interface's navigate)
The obligation      : whole-or-nothing under a kill (EVALUATION/medtimer/model/specification_medtimer.lnt:260); O1 (EVALUATION/medtimer/model/specification_medtimer.lnt:16)
What the app did    : after the relaunch the row reads "please wait…" and the card 2 pills: EVALUATION/medtimer/generated/variant_logs/ue_kill/v7.log:1909
Verdict and why     : PASS, the walk reached `:PASS:` and every checkpoint matched: EVALUATION/medtimer/generated/variant_logs/ue_kill/v7.log:1912
Counterexample      : `TAP !CV_TAKEN` → `NAVIGATE !RT_HOME` → `WAIT_FOR !EL_ROW_B` → `OBSERVE !EL_STATE_B` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_B` → `CONFIRM !COMMITTED !S1 !TAKEN !D_B`
Failure class       : — (PASS)
Silent failure?     : no
Root cause in app   : —
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/ue_kill/v7.log:2112–2119): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 4|4|RAISED|0|2.0|2.0
Separate evidence?  : —
Forecast            : "PASS: the writes finish before the relaunch kills" (EVALUATION/medtimer/properties/disruption_mapping.yml:150); the PASS held, by rollback rather than by completion
Reproduced          : walked once
Doubts              : the CONFIRM after the kill admits COMMITTED or ROLLED_BACK; the app took the rollback
```

#### MedTimer-183  The medicine list read just before a write still shows the committed stock afterwards
```
Purpose / test case : tp_app_cache_stale / tc_app_cache_stale.1.aut  (EVALUATION/medtimer/runs/2026-10-02_campaign2/narval/variants/app_cache_stale/tc_app_cache_stale.1.aut; branch 1 of the purpose, row EVALUATION/medtimer/variants_app_cache_stale.log:3)
Disruption          : APP_CACHE_STALE (APP), the System Interface reads the medicine list just before the write (EVALUATION/medtimer/properties/disruption_mapping.yml:128), timing none
Where it struck     : after S1: the medicine list is read, then the tester writes `ACT !D_A1 !TAKE`
The obligation      : O3 (EVALUATION/medtimer/model/specification_medtimer.lnt:18; EVALUATION/medtimer/model/specification_medtimer.lnt:339)
What the app did    : EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v1.log:969 ("CONFIRM oracle OK: StockBand, DoseState agree with 'CONFIRM !COMMITTED !S2 !TAKEN !D_A1' on [('el_state_a1', 'taken'), ('el_card_a', 'vitamin c (2 pills left)')]")
Verdict and why     : PASS, the walk reached `:PASS:` and every checkpoint matched: EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v1.log:973
Counterexample      : `ACT !D_A1 !TAKE` → `TAP !CV_TAKEN` → `WAIT_FOR !EL_ROW_A1` → `OBSERVE !EL_STATE_A1` → `TAP !CV_TAB_MEDICINES` → `WAIT_FOR !EL_MEDICINES` → `OBSERVE !EL_CARD_A` → `CONFIRM !COMMITTED !S2 !TAKEN !D_A1`
Failure class       : — (PASS)
Silent failure?     : no
Root cause in app   : —
Data store evidence : after the walk (EVALUATION/medtimer/generated/variant_logs/app_cache_stale/v1.log:1084–1088): Medicine 1|Vitamin C|2.0; 2|Zinc|2.0; ReminderEvent for this dose (id|reminder|status|stockHandled|before|after): 1|1|TAKEN|1|3.0|2.0
Separate evidence?  : —
Forecast            : "PASS: the list is a Room flow, no cache" (EVALUATION/medtimer/properties/disruption_mapping.yml:155); held
Reproduced          : walked once
Doubts              : none recorded
```

## 7. Tester-side and UNEXECUTABLE runs

| Case | What went wrong in the apparatus | Evidence | Fixed? |
|---|---|---|---|
| infra_storage_full v28, first attempt | the disk fill left 8 KB free; the probe expects 0, so the fault was not confirmed and no verdict was given | EVALUATION/medtimer/variants_infra_storage_full.log:30 | walked again: FAIL |
| infra_storage_full v30, first attempt | the dose row never appeared on the overview, so the walk could not reach its step | EVALUATION/medtimer/variants_infra_storage_full.log:32 | walked again: FAIL |
| nominal, first walk before this campaign's purposes | purposes without the strict closure let `VIEW (d_b)` self-loop; the walk re-read d_b 42 times and never ended | EVALUATION/medtimer/generated/variant_logs/nominal.loop_2026-10-02/v1.log:5338 | yes: purposes regenerated with the strict closure (commit fb2b557); the walk was discarded |
| ue_kill v4, v5, v24 (PASS) | after a kill during DELETE of a Taken dose the database holds the record still TAKEN with the pill refunded, but the System Interface reads only the stock after a delete, so the walk could not see the record | EVALUATION/medtimer/generated/variant_logs/ue_kill/v4.log:2200; EVALUATION/medtimer/generated/variant_logs/ue_kill/v5.log:2228; EVALUATION/medtimer/generated/variant_logs/ue_kill/v24.log:1320 | no; the verdicts stand as returned (see §10) |
| walks interrupted by a session restart (06:13) | the tester's processes were stopped; the walk in progress left no row and was walked again | EVALUATION/medtimer/generated/sweep_campaign2.log:50 | yes |

## 8. Aggregates

Counterexamples by failure class (181 FAIL verdicts):

| Class | Count | Of which separate from the nominal baseline |
|---|---|---|
| SILENT | 93 | 93 |
| MISSING-REPORT | 44 | 44 |
| WRONG-REPORT | 0 | 0 |
| STALE | 0 | 0 |
| INTEGRITY | 27 | 27 |
| NOMINAL | 17 | 7 |

The 10 NOMINAL FAILs inside ue_kill and app_cache_stale repeat the edit-sheet and
delete-skipped defects and are counted once, under nominal and the domain purposes.

Counterexamples by disruption layer:

| Layer | Count |
|---|---|
| NOMINAL | 3 |
| INPUT | 4 |
| USER | 3 |
| APP | 46 |
| DB | 66 |
| INFRA | 59 |

**Silent failures: 93** (app_write_fail 39, db_abort 19,
infra_storage_full 35). In 13 of them a Taken mark consumed the pill
without completing the record, and in 7 a delete refunded the pill without deleting the record.

## 9. Top three for the paper

1. **MedTimer-17**: when the dose record cannot be written, MedTimer still takes the pill off the stock, shows no error and stays on the overview, so the user sees a dose that was never recorded and a stock that has already moved. It is beyond doubt because the injection was confirmed by probe, the database after the walk holds the stock decremented with the record still RAISED, the source writes the stock (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:135) before the record (EVALUATION/medtimer/sut/medtimer/feature/reminders/src/main/java/com/futsch1/medtimer/feature/reminders/NotificationProcessor.kt:149), and the forecast predicted it (EVALUATION/medtimer/properties/disruption_mapping.yml:151); 13 cases show the same half-write.
2. **MedTimer-14**: deleting a Taken dose under a failing write refunds the pill but keeps the record, with no error, so the stock and the history disagree. It is beyond doubt because the database holds the record still TAKEN with the refunded stock, and the source refunds (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:129) before it updates the record (EVALUATION/medtimer/sut/medtimer/feature/ui/src/main/java/com/futsch1/medtimer/feature/ui/overview/actions/ReminderEventActions.kt:130).
3. **MedTimer-57**: when the dose record cannot be inserted, MedTimer reports nothing and carries on; all 19 db_abort cases show it. It is beyond doubt because the probe confirmed the trigger, the database has no record for the dose, and nothing in the write path catches the exception (EVALUATION/medtimer/sut/medtimer/core/common/src/main/java/com/futsch1/medtimer/core/common/di/CoroutineScopesModule.kt:21).

## 10. Do not claim

- Any result of campaign one: it was generated from a superseded model.
- That `extract_all` produced 240 test cases: on each full CTG it produces one; the suite of 240 is one TESTOR test case per accepting branch.
- That the kill (UE_KILL) never leaves a half-done write: in ue_kill v4, v5, v24 the database shows a refund with the record still TAKEN, which the System Interface did not observe; those walks are PASS as returned, and they are not evidence either way.
- That MedTimer crashes under DB_CORRUPT or INFRA_STORAGE_MEDIA: the captures show only that MedTimer was not in the foreground; no stack trace or crash text was recorded.
- That "-1 pills left" is displayed under DB_CORRUPT_STOCK: the walk never read the stock after the corruption.
- That the 4 infra_storage_full cases with System UI in the foreground are MedTimer failures rather than device effects of a full disk.
- Notifications, alarms, the manual-dose journey, refills, over-limit doses and expiry: not modelled.
- Exec-time as single-device timing: two emulators ran in parallel on one host.
