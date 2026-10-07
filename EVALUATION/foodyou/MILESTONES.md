# FoodYou — Milestone Log

What was actually run, and what it actually showed. Newest entries at the bottom.

Companion file: [`ROADMAP.md`](ROADMAP.md) — what comes next and what it costs.

---

## How to add an entry

Every entry carries the same fields, so entries stay comparable across months. The
three that matter most:

- **Measured vs inferred.** If a figure was not observed, say so at the point of use.
  "13 INCONCLUSIVE" is a different claim from "3 measured, 10 inferred", and a
  reviewer who finds that gap themselves stops trusting everything else.
- **Model revision.** A result describes the model that produced it. This repository
  has held generated artefacts predating the current specification by weeks.
- **Repetitions.** One run per test case is a real weakness. Record the count rather
  than omitting it.

```markdown
## M<n> — <title>
**Date:** | **Model revision:** | **Framework state:**
**Command:** | **Repetitions:** | **Artefacts:**

### Result
<table>

### What it establishes
### What it does NOT establish
### Follow-ups opened
```

---

## M1 — Framework corrections

**Date:** 17–19 August 2026
**Framework state:** uncommitted working tree; all figures below are post-fix
**Artefacts:** `framework/concretization/algorithm.py`, `executors.py`,
`framework/scripts/classify_failure.py`

Four defects were found in the concretization layer. All had been producing or
concealing incorrect verdicts. No defect was found in the application.

| id | Defect | Reach |
|---|---|---|
| **D1** | A checkpoint shortcut selected among multiple permitted abstract **outputs** by shortest-distance-to-PASS, then failed the run when the SUT produced the other equally-allowed one | 100 of 102 test cases |
| **D2** | Branch selection compared an abstract token to a rendered value literally (`"over" == "2700 / 2000 kcal"`), never matched, and silently fell back to the first alternative — with no oracle run at all | all multi-output states |
| **D3** | The oracle had one call site, behind a single-alternative shortcut. Gates reached at multi-output states skipped both the oracle and its running ledger; a staged `−900 kcal` was overwritten unapplied and reported as a mismatch against a total the app had computed correctly | every removal from a saturated total |
| **D4** | One of 14 source-selection sites omitted `wait_for (el_search_results)` and fell through to `el_calories` — a selector that also appears in an `observe` block, hence an *oracle* selector, so its timeout was reported as a conformance failure | all 13 failures in the M3 sweep |

### What it establishes
An ioco concretization layer is itself a program that can be wrong, and being wrong
in the direction of a false FAIL is indistinguishable from a discovery unless
actively hunted.

**The D3 coupling is not a coincidence.** The only multi-output state in the
specification is `drop(OVER)`, reachable only via `REMOVE_ENTRY`. So the one skipped
oracle call site and the one *subtracting* ledger operation are the same event —
structural, not a corner case.

### Measures adopted
1. The observation selects the branch; choosing among outputs is not the tester's right
2. The oracle runs on every accepted transition, not only via a structural shortcut
3. Cross-step bookkeeping **fails closed** — invalidated the moment it loses an update, and abstains rather than reporting
4. Findings that cannot terminate a walk are counted per run, so a PASS is not self-certifying
5. Evidence (screenshot + UI tree) captured when an **oracle** rejects an observation, not only when a wait times out

### Follow-ups opened
- Converge the oracle's two call sites onto one before disruption branches add more multi-output states
- Audit Moodle (VULNERABLE 9/9) and Spliit against D1–D4

---

## M2 — Test purpose audit and rewrite

**Date:** 20 August 2026
**Artefacts:** `Test_Purposes/tp_*.lnt`, `generated/retired_Test_Purposes/`

### Result

| Finding | Detail |
|---|---|
| Byte-identical duplicate | `tp_storage_degraded.lnt` and `tp_ue2_storagefull.lnt` — same MD5, and neither targeted any fault |
| Mislabelled | `tp_network_degraded.lnt` accepted on `UE1_KILL` → `UE2_STORAGEFULL`; `NETWORK_DEGRADED` never reached `TP_ACCEPT` |
| Superseded model | All three referenced `STORAGE_DEGRADED` / `UE2_STORAGEFULL`, which appear **0 times** in the current specification |
| Dead gate | `NETWORK_DEGRADED` is declared in both disruptors' parameter lists and the `par` sync set, but **never offered by either body** |

Eight purposes rewritten to a uniform shape: 19-gate alphabet matching `process SPEC`,
a `TARGET:` comment stating the falsifiable claim, complete negative closure, and the
observable owed named explicitly. Three files retired (moved, not deleted).

### What it establishes
Six of the eight were already structurally correct — the nested-`disrupt` idiom in
`tp_storage_full`, `tp_ue1_kill` and `tp_disruption_db` expresses the requirement
precisely and was initially misgraded by a grep that could not see it.

The specification already pairs each write-path fault with the observable it owes,
and `total` in every rollback arm is the **unbumped** value — i.e. the model already
states *an aborted write must not move the daily total*.

### What it does NOT establish
Whether the purposes select the traces intended — that needed generation (M4).

---

## M3 — Nominal conformance campaign

**Date:** 18 August 2026
**Model revision:** pre-D4-fix (102-variant suite) — **superseded by M4**
**Command:** `bash EVALUATION/foodyou/run_variants.sh happy`
**Repetitions:** 1 per test case
**Artefacts:** `variants_happy.log`, `generated/variant_logs/happy/`,
`RESULTS_happy.md`, `RESULTS_happy.tex`

### Result

| Verdict | Count | Status |
|---|---|---|
| PASS | 89 / 102 | measured |
| INCONCLUSIVE | 13 / 102 | **3 measured, 10 inferred** |
| FAIL (counter-example) | **0** | measured |

| Oracle activity | |
|---|---|
| `CONFIRM_TOTAL` band checks | 558 |
| Exact-sum ledger applications | 558 |
| `FOOD_INFO` authoritative-value checks | 165 |
| Arithmetic findings | **0** |
| Ledger abstentions | **0** |
| QUIESCENCE classifications | **0** |

Suite: 32,030 transitions; states per case 58 / 216 / 255 (min / median / max).
Cost: median 55 s per case (22–133 s), ≈1 h 45 m for the suite.

Gate coverage — `CONFIRM_TOTAL` 503 firings, `ADD_ENTRY` 471, `SEARCH_FOOD` 178,
`FOOD_INFO` 165, `REMOVE_ENTRY` 87, `VIEW_DIARY` 6, `DIARY_INFO` 6.

### What it establishes
Zero conformance counter-examples on the nominal path. All 13 non-PASS verdicts had
a single cause (D4) and were attributed. No QUIESCENCE means the 10 s observation
budget was adequate — every non-PASS was a precondition failure, not a timeout where
an output was owed.

### What it does NOT establish
- **10 of the 13 INCONCLUSIVE were never individually re-run.**
- **No flakiness rate.** One repetition per case; stability confirmed on a subset only.
- The external branch was never exercised: all 13 query Open Food Facts for Corn germ
  oil, which returns **0 results** — confirmed by the app's own source count and by
  the catalogue API. The same API returns **215 results** for "Cooking butter", so
  this is a fixture choice, not an environmental limit.
- Quantity was never varied (every entry 100 g → exactly 900 kcal), only one food was
  ever logged, and the g↔ml path never ran.

### Note on comparison
An earlier 93-case suite reported 54 FAILs. Different suite, different model
revision — a **trajectory, not a controlled comparison**, and it must not be quoted
as a measured improvement factor.

---

## M4 — Test suite regeneration, nine purposes

**Date:** 21–23 August 2026
**Model revision:** current (includes the D4 System Interface fix)
**Command:** `sh generate_tc_all.sh` on narval3, in tmux
**Artefacts:** `Test_Cases/tc_<purpose>.aut`, `Test_Cases/variants/<purpose>/`

### Result — 793 test cases

| Purpose | Test cases | | Purpose | Test cases |
|---|---:|---|---|---:|
| `storage_media` | 144 | | `input_invalid` | 86 |
| `happy` | 104 | | `cache_stale` | 48 |
| `disruption_db` | 109 | | `extapi_fail` | 45 |
| `storage_full` | 109 | | `db_corrupt` | 40 |
| `ue1_kill` | 108 | | | |

Output reorganised to one directory per purpose, `variants/<purpose>/`, so purposes
cannot mix and a partial re-extraction is visible. The sweep scripts prefer the new
layout and fall back to the old flat one.

### Incidents

**CADP licence is node-locked to the login node.** Every Slurm submission died with
`*007 protection violation ... on machine nc31413`. Extraction runs on `narval3`
inside `tmux`, not under `sbatch`.

**A CTG guard wrongly rejected three purposes.** It tested for the *presence* of an
`:INCONCLUSIVE:` label while reporting "INCONCLUSIVE-only". Every purpose of the form
`FAULT; RESPONSE; TP_ACCEPT` necessarily admits a branch where the fault fires and
the response never comes, and that branch is inconclusive by construction. All three
rejected purposes had a reachable `:PASS:`. Corrected to test PASS reachability;
`extapi_fail`, `db_corrupt` and `storage_media` then extracted normally.

The guard was selecting on **modelling style**, not satisfiability — and the three it
discarded were exactly those asking *"does the application tell the user something
went wrong?"*

### What it does NOT establish
No test case in this suite has been executed. `happy` regenerated to **104** variants,
so the M3 figures describe a superseded 102-variant set and must be re-measured.

---

## M5 — Fault injector audit

**Date:** 23 August 2026
**Artefacts:** `framework/concretization/fault_injector.py`,
`properties/disruption_mapping.yml`

Established **before** any disruption sweep, and it blocks M6.

| Defect | Evidence | Consequence |
|---|---|---|
| `manifested()` queries deleted fixtures | reads `WHERE name LIKE 'Test%'`; `seed_foods.sh` deletes those rows | `CACHE_STALE` always reports *not manifested* → every run INCONCLUSIVE even when the injection worked. `DB_CORRUPT` always reports *manifested* even if it failed |
| Three faults, one injection | `UE1_KILL`, `DISRUPTION_DB`, `STORAGE_FULL` run byte-identical `DELETE FROM Measurement; …` | three results-table rows that cannot disagree |
| The injection contradicts the specification | those `DELETE`s send the total to `EMPTY`; the specification requires an aborted write to leave the total **unchanged** | false FAILs across 3 disruptions, 300+ test cases |

### What it establishes
No disruption verdict recorded in this repository is currently evidence about the
application. This includes the `CACHE_STALE` FAIL quoted in the July `REPORT.md`.

### Follow-ups opened
Three distinct mechanisms (trigger-abort / ballast / force-stop), a `check_faults.sh`
self-test proving each injection bites independently of the application, and
withdrawal of the `external_dependencies` guard. See `ROADMAP.md` §4.

---

## Open at time of writing

| Item | Owner | Blocks |
|---|---|---|
| Re-run the 10 inferred INCONCLUSIVE | run | M2 completion |
| Flakiness subset at 3 repetitions | run | M2 completion |
| Fault injector: 3 defects | build | M5 → all disruption results |
| `check_faults.sh` | build + run | M5 |
| Withdraw `external_dependencies` guard | build | external-branch findings |
| Re-measure `happy` on the new 104 | run | supersedes M3 figures |
| `tp_nominal.lnt` — keep as second control or retire | decide | — |
