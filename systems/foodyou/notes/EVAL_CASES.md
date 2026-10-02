# FoodYou: evaluation cases (campaign v1, SUPERSEDED model)

> **Superseded.** These results come from campaign v1, the model at commit
> aa2f73d. That is the model behind the paper's FoodYou table. The current model
> differs from it: by md5, `foodyou_types.lnt`, `system_interface_foodyou_copy.lnt`,
> `disruption_mapping.yml` and `tp_storage_media.lnt` all differ from
> `runs/v1_spec-2026-08_model/`. §10 lists those corrections. No v2 result is
> mixed in here.

**Citation shorthand.** The v1 per-case logs exist only in git commit aa2f73d.
Read them with `git show aa2f73d:<path>`.

| Short | Full path |
|---|---|
| `A:` | `aa2f73d:systems/foodyou/` |
| `VL/<p>/vN.log` | `aa2f73d:systems/foodyou/generated/variant_logs/<p>/vN.log` |
| `VA/<p>.N` | `aa2f73d:systems/foodyou/generated/tc/variants/<p>/tc_<p>.N.aut` |
| `ROWS/<p>` | `aa2f73d:systems/foodyou/variants_<p>.log` (one row per case: VARIANT STATES TRANSITIONS TIME_S VERDICT NOTE) |
| `V1M/` | `systems/foodyou/runs/v1_spec-2026-08_model/` (working tree, byte-identical to aa2f73d inputs, `V1M/MANIFEST.md5`) |
| `MAP:` | `aa2f73d:systems/foodyou/properties/disruption_mapping.yml` |
| `CD:` | `aa2f73d:systems/foodyou/properties/concrete_domain.yml` |

**Grouping rule for §6.** Cases with the same purpose, the same failing step, the
same selector or oracle message and the same apparatus condition share one card.
Every card lists all of its case ids. A card's evidence is cited from one example
case. The grouping was computed from the `Verdict:` and execution-report lines of
every log, plus the foreground package in each failure capture's XML.

---

## 1. System and scope

FoodYou 3.4.8 is an open-source Android calorie and food diary written in
Kotlin/Compose (`systems/foodyou/sut/foodyou/gradle/libs.versions.toml:2`). It
runs on an Android emulator driven by Appium (`systems/foodyou/env.sh:24`). The
model covers one diary journey: search a food (LOCAL Swiss database or EXTERNAL
Open Food Facts), read its kcal, add an entry to Breakfast, check the daily total,
view an entry and remove it (`V1M/specification_foodyou_copy.lnt:186-258`).
Faults: external-API loss, process kill, DB write abort, full storage, corrupt
record, stale value, unreadable DB file, and an invalid amount. Out of scope:
recipes, goals, settings, sync. The daily total is abstracted to bands
EMPTY/LOW/MODERATE/HIGH/OVER that count entries, not calories
(`V1M/foodyou_types.lnt:87`).

## 2. The normal run

Nominal purpose: `V1M/tp_happy.lnt:26-29`. Canonical test case: `V1M/tc/tc_happy.aut`.

| Step | User action | Abstract gate (spec) | What the user is shown |
|---|---|---|---|
| S1 | Tap Breakfast, type "Corn germ oil", submit, pick the LOCAL source | UI steps `tc_happy.aut:2-15` | the source tabs and the result row |
| S2 | Open the food | `SEARCH_FOOD (fid, LOCAL)` spec:187 | the food sheet |
| S3 | Read the kcal | `FOOD_INFO (fid, kcal_of (fid))` spec:188, `tc_happy.aut:37` | "900 kcal" (e.g. `VL/storage_media/v1.log:845`) |
| S4 | Enter the amount, tap Save | `ADD_ENTRY (meal, fid, VALID)` spec:208, `tc_happy.aut:36` | back on the diary |
| S5 | Read the daily total | `CONFIRM_TOTAL (COMMITTED, bump(total), fid)` spec:211-212, `tc_happy.aut:54` | "N / 2000 kcal" |
| S6 | Open an entry, delete it, read the total | `REMOVE_ENTRY` spec:234, `CONFIRM_TOTAL (COMMITTED, …)` spec:257, `tc_happy.aut:89` | the total drops by one band |

"spec" means `V1M/specification_foodyou_copy.lnt`. The test case ends at `:PASS:` (`tc_happy.aut:151`).

## 3. Obligations

| ID | Obligation in plain words | Gate(s) that witness it | `path:line` |
|---|---|---|---|
| O1 | A valid add commits, and the total rises by one band | ADD_ENTRY, CONFIRM_TOTAL COMMITTED | `V1M/specification_foodyou_copy.lnt:208-212` |
| O2 | If the process is killed during the add, the entry is not committed | UE1_KILL, CONFIRM_TOTAL ROLLED_BACK | `…:214-215` |
| O3 | If the DB write aborts, the entry is not committed | DISRUPTION_DB, CONFIRM_TOTAL ROLLED_BACK | `…:217-218` |
| O4 | If storage is full, the entry is not committed | STORAGE_FULL, CONFIRM_TOTAL ROLLED_BACK | `…:220-221` |
| O5 | An invalid amount is rejected, and the total is unchanged | ADD_ENTRY INVALID, CONFIRM_TOTAL REJECTED | `…:223-224` |
| O6 | A corrupt local record shows an error, not a wrong calorie value | DB_CORRUPT, DB_CORRUPT_DETECTED | `…:116-118` |
| O7 | If the external API fails, the app shows a warning | EXTAPI_FAIL, EXTAPI_WARNING | `…:127-132` |
| O8 | After a stale cache, a local read shows the authoritative kcal | CACHE_STALE, FOOD_INFO (kcal_of) | `…:195-197` |
| O9 | If the DB file is unreadable when the diary is viewed, an error is shown | STORAGE_MEDIA, STORAGE_ERROR_SHOWN | `…:140-144` |
| O10 | Removing an entry lowers the total | REMOVE_ENTRY, CONFIRM_TOTAL | `…:234`, `…:257` |

## 4. Campaign identity

| Item | Value |
|---|---|
| Campaign name and date | v1 variant sweep, rows headed 2026-09-11 15:15 (`ROWS/happy:1`) to 2026-09-15 09:55 (`ROWS/storage_media:1`); logs committed in aa2f73d (2026-09-16) |
| Matches the current model? (how verified) | **No, superseded.** The md5s of `V1M/` against `systems/foodyou/model/` differ for types, SI and mapping, and against `systems/foodyou/test_purposes/` for `tp_storage_media.lnt`. Regenerating `V1M/` on narval gives the v1 case count for all 9 purposes (`systems/foodyou/runs/v1_spec-2026-08_summaries/ctg_v1.tsv:5-13`) |
| Composed model size (states / transitions) | 4,085 / 21,477 (`A:compile_stats.tsv:1`) |
| Purposes | 9 (happy + 8 disruptions) |
| Test cases | 793 |
| PASS / FAIL / INCONCLUSIVE / UNEXECUTABLE | 283 / 352 / 58 / 100 (the rows record UNEXECUTABLE as `HARNESS` 99 + `ERROR` 1) |
| Generation time / walk time | Generation: NOT RECORDED (v1 captured no per-purpose times). Walk: 116,977 s, the sum of TIME_S over all `ROWS/*` |

**Reconciliation.** `systems/foodyou/RESULTS_campaign.md:19` gives
285 / 488 / 20 / 793. Its own header says it was written 2026-09-01
(`RESULTS_campaign.md:5`), so it describes an earlier sweep. The aa2f73d rows
above are the source of the paper table and are taken as correct. The paper
table's 452 FAIL equals 352 FAIL + 100 UNEXECUTABLE, so it counted
UNEXECUTABLE as FAIL (see §10).

## 5. Results by purpose

Counts from `ROWS/<p>`. "Cause" refers to the cards in §6 and the table in §7.

| Purpose | Layer | Cases | P | F | I | U | One-line cause |
|---|---|---|---|---|---|---|---|
| happy | NOMINAL | 104 | 91 | 0 | 0 | 13 | U: search-row precondition never met (§7) |
| ue1_kill | USER | 108 | 8 | 83 | 0 | 17 | F: kill landed after Save had committed (FY-4) |
| input_invalid | INPUT | 86 | 72 | 0 | 0 | 14 | Empty amount rejected, total unchanged (FY-12) |
| extapi_fail | APP | 45 | 0 | 41 | 3 | 1 | F: no warning after the API was cut (FY-5, 31); search row before injection (FY-6, 10) |
| cache_stale | APP | 48 | 40 | 0 | 0 | 8 | P: pre-injection reported failed (§10) |
| disruption_db | DB | 109 | 7 | 86 | 0 | 16 | F: abort trigger installed after Save had committed (FY-2) |
| db_corrupt | DB | 40 | 0 | 37 | 0 | 3 | F: total 0 kcal after a 900 kcal add; pre-injection reported failed (FY-1) |
| storage_full | INFRA | 109 | 8 | 86 | 0 | 15 | F: ballast after Save had committed (FY-3) |
| storage_media | INFRA | 144 | 57 | 19 | 55 | 13 | I and 8 F: Android quick-settings shade in the foreground (FY-8, FY-10); 11 F: search row (FY-7) |
| **total** | | **793** | **283** | **352** | **58** | **100** | |

## 6. Case cards

#### FoodYou-1  The total shows 0 kcal after a 900 kcal add, under a corrupted record
```
Purpose / test case : tp_db_corrupt / tc_db_corrupt.{1-36,38}.aut (37 cases)
Disruption          : DB_CORRUPT (DB), sqlite "UPDATE Product SET energy = NULL ..." (MAP:117-120), timing pre
Where it struck     : before the walk (VL/db_corrupt/v1.log:197-198); walk was S1, S4, S5
The obligation      : O1 on the path walked, CONFIRM_TOTAL COMMITTED LOW (VA/db_corrupt.1:62); O6 (spec:116-118) was never reached
What the app did    : "the entries logged so far sum to 900 kcal, but the app shows 0" (VL/db_corrupt/v1.log:319);
                      "screen shows 0 kcal but its own macros (0g protein, 100g fat ...) imply ~900 kcal" (:356)
Verdict and why     : FAIL, oracle mismatch "total '0 / 2000 kcal' classifies as EMPTY, expected LOW" (:398); Verdict line :378
Counterexample      : TAP CV_OIL, ..., ADD_ENTRY BREAKFAST FOOD_OIL VALID, ..., OBSERVE EL_DAILY_TOTAL, CONFIRM_TOTAL COMMITTED LOW (VA/db_corrupt.1:62)
Failure class       : none: tester-side (§7). It is not counted as a counterexample
Silent failure?     : no (not counted)
Root cause in app   : NOT ESTABLISHED
Data store evidence : NOT RECORDED (no probe of Product.energy after injection)
Separate evidence?  : n/a
Forecast            : CD:130 predicted that FoodYou detects a NULL field ("Food is missing required fields"). Not tested: the walk never took the DB_CORRUPT branch
Reproduced          : 37 of 40 cases, same message
Doubts              : The log says "Disruption activation failed: mechanism 'sqlite' is not declared" and
                      "PRE-injection failed — this run's verdict is not attributable" (VL/db_corrupt/v1.log:199-200).
                      The 0 kcal reading suggests the UPDATE did land, but that is an inference. The test case
                      models no corruption on the path walked, so it expected LOW.
```

#### FoodYou-2  An entry is committed although the DB write was set to abort
```
Purpose / test case : tp_disruption_db / tc_disruption_db.N.aut (86 cases). Expected/observed band:
                      HIGH/OVER 1-5,7-9,12-18,20-21,23,26-28,34,36,40-42,48-49,56-57,59-61,71;
                      MODERATE/HIGH 24-25,29,37-38,43-45,50,53-54,62,65-66,72-73,77-78,80-82,87;
                      LOW/MODERATE 51-52,55,63-64,67-69,74-76,83,85,88,90,94,98,100;
                      EMPTY/LOW 84,86,89,91,93,95-96,101-102,105,108-109
Disruption          : DISRUPTION_DB (DB), sqlite trigger RAISE(ABORT) BEFORE INSERT ON Measurement (MAP:78), timing gate
Where it struck     : S4, after the Save tap. The execution report runs ADD_ENTRY ok (VL/disruption_db/v1.log:1264), then DISRUPTION_DB (:1265)
The obligation      : O3, CONFIRM_TOTAL ROLLED_BACK (spec:217-218)
What the app did    : total '3600 / 2000 kcal' (VL/disruption_db/v1.log:1152). The added entry is counted
Verdict and why     : FAIL, oracle mismatch "AUT expects HIGH, observed ... OVER" (:1152); Verdict :1164
Counterexample      : ADD_ENTRY BREAKFAST FOOD_OIL VALID, DISRUPTION_DB, ..., CONFIRM_TOTAL ROLLED_BACK (VA/disruption_db.1:131, :153)
Failure class       : none: tester-side (§7), timing artifact
Silent failure?     : no
Root cause in app   : NOT ESTABLISHED
Data store evidence : NOT RECORDED
Separate evidence?  : n/a
Forecast            : NOT RECORDED before the run. Afterwards, HANDOVER.md:263-267 explains the result as the gate firing after commit
Reproduced          : 86 of 109 cases, same pattern; the same case ids fail in FoodYou-3 and FoodYou-4
Doubts              : The fault never preceded the write, so the FAIL measures injection order, not the app
```

#### FoodYou-3  An entry is committed although storage was filled
```
Purpose / test case : tp_storage_full / tc_storage_full.N.aut (86 cases). Band groups as FoodYou-2, except
                      EMPTY/LOW 84,86,89,91,93,95-97,101-102,105,108
Disruption          : STORAGE_FULL (INFRA), adb ballast file (MAP:98), timing gate
Where it struck     : S4, after Save. ADD_ENTRY ok (VL/storage_full/v24.log:1025), then STORAGE_FULL (:1026)
The obligation      : O4, CONFIRM_TOTAL ROLLED_BACK (spec:220-221)
What the app did    : total '2700 / 2000 kcal' (VL/storage_full/v24.log:928)
Verdict and why     : FAIL, oracle mismatch "AUT expects MODERATE, observed ... HIGH" (:928); Verdict :940
Counterexample      : ADD_ENTRY ... VALID, STORAGE_FULL, ..., CONFIRM_TOTAL ROLLED_BACK (VA/storage_full.24 path; first fault label VA/storage_full.24:131)
Failure class       : none: tester-side (§7), timing artifact
Silent failure?     : no
Root cause in app   : NOT ESTABLISHED
Data store evidence : NOT RECORDED
Separate evidence?  : n/a
Forecast            : NOT RECORDED
Reproduced          : 86 of 109
Doubts              : As FoodYou-2. In 4 of the cases (1, 2, 7, 12) the ballast command also failed:
                      "STORAGE_FULL injected (adb) — WARNING: command failed" (VL/storage_full/v1.log:1053)
```

#### FoodYou-4  An entry is committed although the app was killed during the add
```
Purpose / test case : tp_ue1_kill / tc_ue1_kill.N.aut (83 cases). Band groups as FoodYou-2, except
                      MODERATE/HIGH without 82; LOW/MODERATE without 51; EMPTY/LOW 84,86,89,91,93,95-97,101-102,105
Disruption          : UE1_KILL (USER), adb force-stop + relaunch (MAP:64), timing gate
Where it struck     : S4, after Save. ADD_ENTRY ok (VL/ue1_kill/v1.log:2007), then UE1_KILL (:2008)
The obligation      : O2, CONFIRM_TOTAL ROLLED_BACK (spec:214-215)
What the app did    : total '3600 / 2000 kcal' (VL/ue1_kill/v1.log:1895)
Verdict and why     : FAIL, oracle mismatch "AUT expects HIGH, observed ... OVER" (:1895); Verdict :1907
Counterexample      : ADD_ENTRY ... VALID, UE1_KILL, ..., CONFIRM_TOTAL ROLLED_BACK EMPTY (VA/ue1_kill.1:42, :68)
Failure class       : none: tester-side (§7), timing artifact
Silent failure?     : no
Root cause in app   : NOT ESTABLISHED
Data store evidence : NOT RECORDED
Separate evidence?  : n/a
Forecast            : MAP:58-61: "Whether the in-flight write committed depends on timing ... a result to investigate"
Reproduced          : 83 of 108
Doubts              : As FoodYou-2
```

#### FoodYou-5  No warning when the external food API is cut; the search screen carries on
```
Purpose / test case : tp_extapi_fail / tc_extapi_fail.{5-6,8-12,14-17,19-23,25-27,29-34,36-39,41-42}.aut (31 cases)
Disruption          : EXTAPI_FAIL (APP), "svc data disable ; svc wifi disable" (MAP:21-24), timing gate
Where it struck     : S1/S2, the search with the external source (Open Food Facts) engaged (VL/extapi_fail/v5.log:1136),
                      fault injected (:1141)
The obligation      : O7, EXTAPI_WARNING (spec:127-132)
What the app did    : wait_for descriptionContains("warning") timed out (VL/extapi_fail/v5.log:1346-1347). The capture
                      (A:generated/variant_logs/extapi_fail/v5_captures/20260915-090010_oracle__structural_step__new_UiSelector_.descriptionContains.xml)
                      is the FoodYou search screen with tabs "Open Food Facts" / "Swiss Food Composition Database", a "Corn germ oil" /
                      "900 kcal" row, and no warning element
Verdict and why     : FAIL (:1361). The walker rule was "required observable absent inside an external source the fixture
                      cannot populate" (:1358), not the δ rule
Counterexample      : SEARCH_FOOD ..., EXTAPI_FAIL, WAIT_FOR EL_EXTAPI_WARNING, OBSERVE EL_EXTAPI_WARNING, EXTAPI_WARNING (VA/extapi_fail.5:24, :29, :36, :41)
Failure class       : SILENT
Silent failure?     : yes. The external lookup did not take effect, and the app showed nothing and continued with local results
Root cause in app   : NOT ESTABLISHED in source. THREATS_TO_VALIDITY.md:34-35: "FoodYou renders 'external API unreachable'
                      identically to 'external API legitimately returned nothing.'"
Data store evidence : n/a (no store involved)
Separate evidence?  : yes. The nominal run has 0 FAIL (ROWS/happy), and nominal never cuts the network
Forecast            : CD:118 (present since commit e685981, 2026-09-04, before this sweep): el_extapi_warning "UNUSED ... (no such
                      element exists)". The forecast held
Reproduced          : 31 of 45 cases. An earlier sweep found the same pattern in 34 captures (THREATS_TO_VALIDITY.md:28-31)
Doubts              : (1) δ is offered at the waiting state (VA/extapi_fail.5:28 "(18, :DELTA:, 18)"). By the verdict rule in
                      this document's brief, silence there is INCONCLUSIVE. Cases 2-4 got exactly that (FoodYou-9). The FAIL
                      comes from a walker rule that the current framework no longer has.
                      (2) Whether the app sent an external request before the cut: NOT RECORDED.
                      (3) The SI's selector "warning" is a guess, but no warning-like text exists in the capture (THREATS_TO_VALIDITY.md:28-31)
```

#### FoodYou-6  extapi_fail: the search-result row never appeared, before any fault
```
Purpose / test case : tp_extapi_fail / tc_extapi_fail.{7,13,18,24,28,35,40,43-45}.aut (10 cases)
Disruption          : none injected. No "injected" line in VL/extapi_fail/v7.log
Where it struck     : S1, the SI precondition wait_for(el_search_results) before SEARCH_FOOD (V1M/system_interface_foodyou_copy.lnt:134)
The obligation      : none. This is a structural precondition, not a spec output
What the app did    : row selector textMatches("Peanut butter|Cooking butter|Corn germ oil") timed out (VL/extapi_fail/v7.log:1169-1170).
                      The capture still contains "Corn germ oil" text (v7_captures/20260915-090302_precondition__structural_step_.xml)
Verdict and why     : FAIL (:1183), by the same external-source rule (:1181)
Counterexample      : n/a
Failure class       : none: tester-side (§7)
Silent failure?     : no
Root cause in app   : n/a
Data store evidence : NOT RECORDED
Separate evidence?  : n/a
Forecast            : NOT RECORDED
Reproduced          : 10 of 45
Doubts              : Why the selector did not match while the text was present: NOT ESTABLISHED
```

#### FoodYou-7  storage_media: the search-result row never appeared, before any fault
```
Purpose / test case : tp_storage_media / tc_storage_media.{4,28,43,63,76,96,132,138,140,142-143}.aut (11 cases)
Disruption          : none injected. No "injected" line before the failure in VL/storage_media/v4.log
Where it struck     : S1, the same SI precondition as FoodYou-6
The obligation      : none (structural precondition)
What the app did    : precondition not met (VL/storage_media/v4.log:1238)
Verdict and why     : FAIL (:1251), external-source rule (:1249)
Counterexample      : n/a
Failure class       : none: tester-side (§7)
Silent failure?     : no
Root cause in app   : n/a
Data store evidence : NOT RECORDED
Separate evidence?  : n/a
Forecast            : NOT RECORDED
Reproduced          : 11 of 144
Doubts              : none beyond FoodYou-6
```

#### FoodYou-8  storage_media FAIL: the Android quick-settings shade covered the app
```
Purpose / test case : tp_storage_media / tc_storage_media.{16,32,65,67,82,104,124,128}.aut (8 cases)
Disruption          : STORAGE_MEDIA (INFRA), chmod 0000 on the DB + force-stop + relaunch (MAP:148), timing gate;
                      injected (VL/storage_media/v16.log:1068)
Where it struck     : S6, viewing a diary entry
The obligation      : O9, STORAGE_ERROR_SHOWN (spec:140-144)
What the app did    : NOT RECORDED. The capture at the failure (v16_captures/20260915-102444_..._Someth.xml) has
                      package="com.android.systemui" only (Quick Settings: "Airplane mode", "Bluetooth", "Flashlight"). FoodYou is not on screen
Verdict and why     : FAIL (VL/storage_media/v16.log:1268), external-source rule (:1265); wait "Something went wrong" timed out (:1253)
Counterexample      : n/a
Failure class       : none: tester-side (§7), screen anchor lost
Silent failure?     : no
Root cause in app   : n/a
Data store evidence : NOT RECORDED
Separate evidence?  : n/a
Forecast            : MAP:146-147 predicted "Oops! Something went wrong"; untested here
Reproduced          : 8 of 144, all with the shade in the foreground
Doubts              : What opened the shade: NOT ESTABLISHED
```

#### FoodYou-9  extapi_fail INCONCLUSIVE: no warning, silence permitted
```
Purpose / test case : tp_extapi_fail / tc_extapi_fail.{2,3,4}.aut (3 cases)
Disruption          : EXTAPI_FAIL (APP), as FoodYou-5; injected (VL/extapi_fail/v2.log:1300)
Where it struck     : S1/S2
The obligation      : O7 (spec:127-132)
What the app did    : wait for "warning" timed out (VL/extapi_fail/v2.log:1509). The capture is the FoodYou search screen, no warning
Verdict and why     : INCONCLUSIVE, "state 22 permits quiescence (delta offered)" (:1520-1521); Verdict :1524
Counterexample      : EXTAPI_FAIL, WAIT_FOR EL_EXTAPI_WARNING, (22, :DELTA:, 22) (VA/extapi_fail.2:24, :29, :35)
Failure class       : n/a (not a counterexample)
Silent failure?     : no (not counted)
Root cause in app   : as FoodYou-5
Data store evidence : n/a
Separate evidence?  : n/a
Forecast            : as FoodYou-5
Reproduced          : 3 of 45
Doubts              : The app showed the same screen as in FoodYou-5. The verdicts differ only because the walker's
                      external-source rule did not fire here: no "external data source engaged" line appears in v2-v4
```

#### FoodYou-10  storage_media INCONCLUSIVE: quick-settings shade in the foreground
```
Purpose / test case : tp_storage_media / tc_storage_media.N.aut (55 cases): 2,6,8,10,12,14,18,20,22,24,26,30,34,36,38,40,
                      42,45,47,49,51,53,55,57,59,61,69,71,73,75,78,80,84,86,88,90,92,94,98,100,102,106,108,110,112,114,116,
                      118,120,122,126,130,134,136,139
Disruption          : STORAGE_MEDIA (INFRA), as FoodYou-8; injected (VL/storage_media/v2.log:1443)
Where it struck     : S6
The obligation      : O9 (spec:140-144)
What the app did    : NOT RECORDED. All 55 failure captures show only package="com.android.systemui"
                      (e.g. v2_captures/20260915-095842_..._Someth.xml)
Verdict and why     : INCONCLUSIVE, "state 61 permits quiescence (delta offered)" (VL/storage_media/v2.log:1631-1633);
                      Verdict :1636; report line :1771
Counterexample      : STORAGE_MEDIA, WAIT_FOR EL_STORAGE_ERROR, (61, :DELTA:, 61) (VA/storage_media.2:84, :89, :93)
Failure class       : n/a
Silent failure?     : no
Root cause in app   : n/a
Data store evidence : NOT RECORDED
Separate evidence?  : n/a
Forecast            : MAP:146-147 ("Oops! Something went wrong")
Reproduced          : 55 of 144
Doubts              : The brief defines INCONCLUSIVE as "the app behaved correctly". That is not established here,
                      because the app was not on screen. The case is an apparatus problem (§7). The verdict is reported as returned
```

#### FoodYou-11  PASS: unreadable DB file, and the app shows an error
```
Purpose / test case : tp_storage_media / tc_storage_media.1.aut (55 PASS cases take this path, 2 take a VIEW_DIARY variant)
Disruption          : STORAGE_MEDIA (INFRA), chmod 0000 + force-stop + relaunch (MAP:148), timing gate; injected (VL/storage_media/v1.log:1133)
Where it struck     : S6, the diary entry view
The obligation      : O9, STORAGE_ERROR_SHOWN (spec:140-144)
What the app did    : "Observed ... textContains("Something went wrong") -> 'Oops! Something went wrong'" (VL/storage_media/v1.log:1150)
Verdict and why     : PASS, checkpoint STORAGE_ERROR_SHOWN advanced (:1151), :PASS: reached; Verdict :1155
Counterexample      : STORAGE_MEDIA, ..., STORAGE_ERROR_SHOWN, :PASS: (VA/storage_media.1:84, :99, :102)
Failure class       : n/a
Silent failure?     : no
Root cause in app   : n/a
Data store evidence : NOT RECORDED (the file mode during the fault was not logged in this run)
Separate evidence?  : n/a
Forecast            : MAP:147: "FoodYou shows 'Oops! Something went wrong'". The forecast held
Reproduced          : 57 of 144
Doubts              : tp_storage_media changed in v2 (the md5 differs), so this PASS belongs to the v1 purpose only
```

#### FoodYou-12  PASS: an empty amount is not saved, and the total is unchanged
```
Purpose / test case : tp_input_invalid / tc_input_invalid.1.aut (72 PASS)
Disruption          : INPUT_INVALID (INPUT), the SI types an empty amount (CD:221 cv_qty_invalid ""), timing none (MAP:151-153)
Where it struck     : S4
The obligation      : O5, CONFIRM_TOTAL REJECTED (spec:223-224)
What the app did    : "Entered text '' and submitted" (VL/input_invalid/v1.log:1093); "total exact: 2700 kcal == sum of entries logged" (:1138)
Verdict and why     : PASS, oracle "'2700 / 2000 kcal' -> HIGH" (:1167); :PASS: (:1169); Verdict :1171
Counterexample      : ENTER_TEXT CV_QTY_INVALID, ADD_ENTRY BREAKFAST FOOD_OIL INVALID, CONFIRM_TOTAL REJECTED LOW, :PASS: (VA/input_invalid.1:265, :275, :353, :363)
Failure class       : n/a
Silent failure?     : no
Root cause in app   : n/a
Data store evidence : NOT RECORDED
Separate evidence?  : n/a
Forecast            : NOT RECORDED
Reproduced          : 72 of 86 (no FAIL; 14 UNEXECUTABLE)
Doubts              : The input is the empty string only, not a negative or non-numeric amount
```

## 7. Tester-side and UNEXECUTABLE runs

| Case | What went wrong in the apparatus | Evidence | Fixed? |
|---|---|---|---|
| disruption_db 86 F, storage_full 86 F, ue1_kill 83 F (FoodYou-2/3/4) | A `gate`-timed fault fired after ADD_ENTRY's Save had committed | execution order `VL/disruption_db/v1.log:1264-1265`, `VL/storage_full/v24.log:1025-1026`, `VL/ue1_kill/v1.log:2007-2008`; HANDOVER.md:263-267 | In v2 (`runs/v1_spec-2026-08_model/README.md` lists it as corrected) |
| storage_full 1, 2, 7, 12 (subset of the above) | Ballast command failed | `VL/storage_full/v1.log:1053` | NOT RECORDED |
| db_corrupt 37 F (FoodYou-1) | Pre-injection activation reported failed (`sqlite` not under `mechanisms:`) | `VL/db_corrupt/v1.log:199-200` | NOT RECORDED |
| cache_stale 40 P | Same activation failure. The oracle compared against the injected 999 kcal as "authoritative" | `VL/cache_stale/v1.log:99-100`, `:894`; MAP:126 sets energy = 999 | NOT RECORDED |
| extapi_fail 10 F, storage_media 11 F (FoodYou-6/7) | SI precondition wait for the search row, before any fault | `VL/extapi_fail/v7.log:1169-1170`, `VL/storage_media/v4.log:1238` | In v2 (README) |
| storage_media 8 F + 55 I (FoodYou-8/10) | Android quick-settings shade in the foreground, so the app was not on screen | capture XMLs, package `com.android.systemui` (all 63 checked) | NOT RECORDED |
| 72 U, search row (happy 13: 11,31,42,56,67,79,90,96,99-100,102-104; cache_stale 5; db_corrupt 3; disruption_db 13; extapi_fail 1; input_invalid 12; storage_full 13; ue1_kill 12) | Precondition for the search row not met | e.g. `VL/happy/v11.log:1152` | In v2 (README) |
| 9 U, step budget (cache_stale 6,7,17; disruption_db 22; input_invalid 11,23; storage_full 22,35; ue1_kill 35) | Exceeded MAX_STEPS | e.g. `VL/cache_stale/v6.log:14465` | NOT RECORDED |
| 16 U, mid-walk step not applicable (storage_media 13: 15,21,48,56,62,66,81,89,91,113,115,117,123; disruption_db 47; ue1_kill 22, 82) | A typed step failed, giving `Status: UNEXECUTABLE`: the "Go back\|Close sheet" click in 14 cases, the total wait in ue1_kill 22, and the "Add" tap in ue1_kill 82 | `VL/storage_media/v15.log:1863`, `VL/disruption_db/v47.log:1435,1543` | NOT RECORDED |
| disruption_db 35 | Fault did not manifest | `VL/disruption_db/v35.log:14454` | n/a |
| ue1_kill 51 (row ERROR), ue1_kill 70 | Log ends with no verdict or status line | `VL/ue1_kill/v51.log` (131 lines), `ROWS/ue1_kill` rows 51, 70 | NOT RECORDED |

UNEXECUTABLE total: 72 + 9 + 16 + 1 + 2 = 100.

## 8. Aggregates

Counterexamples are the FAILs left after removing the tester-side FAILs in §7:
352 − (255 + 37 + 21 + 8) = **31**.

- **By failure class:** SILENT 31. MISSING-REPORT 0, WRONG-REPORT 0, STALE 0, INTEGRITY 0, NOMINAL 0.
- **By disruption layer:** APP 31 (EXTAPI_FAIL). USER 0, DB 0, INFRA 0, INPUT 0, NOMINAL 0.
- **Silent failures: 31** (FoodYou-5, all EXTAPI_FAIL). All 31 carry the δ doubt stated in FoodYou-5.

## 9. Top three for the paper

1. **FoodYou-5 (31 cases).** Remembered as: after the phone loses its network, the
   external food search returns nothing and FoodYou shows no warning, so the user
   cannot tell an outage from "no match". Why it holds: the capture shows the app's
   own screen with no warning element. The same was confirmed on 34 captures of an
   earlier sweep (THREATS_TO_VALIDITY.md:28-35), and it was forecast before the
   run (CD:118). Caveat: δ was offered, so under the paper's rule this is
   INCONCLUSIVE unless the purpose is regenerated without the τ branch.
2. **FoodYou-11 (57 PASS).** Remembered as: with the database file made unreadable,
   FoodYou shows "Oops! Something went wrong" instead of a blank diary. Why it holds:
   the log shows the text that was observed (`VL/storage_media/v1.log:1150`), the
   forecast held (MAP:147), and 57 cases repeat it.
3. **FoodYou-12 (72 PASS).** Remembered as: an empty amount is never saved, and the
   total stays exact. Why it holds: no fault apparatus was involved, and the total
   was checked against the sum of the logged entries (`VL/input_invalid/v1.log:1138`).

No disruption FAIL in this campaign meets all five preferences.

## 10. Do not claim

- That any result here holds for the current model. All of it comes from the superseded v1 model.
- Any write-path finding (UE1_KILL, DISRUPTION_DB, STORAGE_FULL). All 255 FAILs had the fault after commit (§7), and the 23 PASSes in those purposes share that timing.
- 452 FAIL (the paper table). That figure counts 100 UNEXECUTABLE runs as FAIL. The walker returned 352 FAIL.
- Anything about DB_CORRUPT or CACHE_STALE. Pre-injection reported failure in both (`VL/db_corrupt/v1.log:200`, `VL/cache_stale/v1.log:100`). The cache_stale PASSes compared against the injected value.
- O6 (corrupt record detected). The walk never took the DB_CORRUPT branch.
- Any storage_media FAIL or INCONCLUSIVE as app behaviour. In all 63 the app was off screen.
- Generation times (743 s to 5,655 s, or any figure). They are NOT RECORDED for v1.
- Results from `systems/foodyou/RESULTS_campaign.md` (285/488/20). That is an earlier sweep.
- The v1 model properties corrected in v2 (`runs/v1_spec-2026-08_model/README.md`):
  (1) DISRUPTOR / INFRA_DISRUPTOR carry an internal `i` branch (`V1M/foodyou_types.lnt:349`, `:368`), so δ is offered at every output state;
  (2) the SI waits on the search row before SEARCH_FOOD (`V1M/system_interface_foodyou_copy.lnt:134`);
  (3) write faults are timed `gate`, after commit.
- The FAIL verdicts in FoodYou-5/6/7/8 are produced by a walker rule ("external source ... cannot populate") that is not part of ioco. Do not present them as δ-based FAILs.
