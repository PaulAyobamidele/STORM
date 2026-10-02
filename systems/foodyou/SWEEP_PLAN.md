# FoodYou — Full Sweep Plan

**Goal:** execute every generated test case — all **793**, across all **9** test
purposes — against the live application, and produce a verdict table where every
non-PASS is attributed.

**Plan opened:** 23 August 2026
**Target sweep start:** 26 August 2026
**Estimated sweep duration:** ~13 hours at one repetition

Companion files: [`ROADMAP.md`](ROADMAP.md) (what comes after),
[`MILESTONES.md`](MILESTONES.md) (what already happened).

---

## 1. The suite

| Purpose | Test cases | Est. runtime @ 55 s |
|---|---:|---:|
| `storage_media` | 144 | 2 h 12 |
| `disruption_db` | 109 | 1 h 40 |
| `storage_full` | 109 | 1 h 40 |
| `ue1_kill` | 108 | 1 h 39 |
| `happy` | 104 | 1 h 35 |
| `input_invalid` | 86 | 1 h 19 |
| `cache_stale` | 48 | 44 min |
| `extapi_fail` | 45 | 41 min |
| `db_corrupt` | 40 | 37 min |
| **Total** | **793** | **≈ 12 h 47** |

Median 55 s per case is measured (range 22–133 s, n = 102, M3). Add ~40 min of
seeding overhead across the suite.

---

## 2. Prerequisites

**Nothing in §2.1 is optional.** Running the disruption purposes before these land
produces a results table that looks complete and means nothing.

### 2.1 Blocking — the fault injector

| # | Item | Owner | Target | Status |
|---|---|---|---|---|
| P1 | `manifested()` queries `name LIKE 'Test%'` — rows `seed_foods.sh` deletes. `CACHE_STALE` always reports *not manifested* (every run INCONCLUSIVE); `DB_CORRUPT` always reports *manifested* (even if the injection failed) | build | 24 Aug | ☐ |
| P2 | `UE1_KILL` / `DISRUPTION_DB` / `STORAGE_FULL` run byte-identical SQL. Three rows in the results table that cannot disagree | build | 24 Aug | ☐ |
| P3 | That shared injection `DELETE`s the diary, sending the total to `EMPTY`, while the specification requires an aborted write to leave the total **unchanged**. Would produce false FAILs across 3 purposes and 326 test cases | build | 24 Aug | ☐ |
| P4 | `check_faults.sh` — per fault: record state → inject → assert it changed → restore → assert it changed back. Proves each injection bites independently of the application | build | 25 Aug | ☐ |
| P5 | Run `check_faults.sh`; every fault must report BITES | run | 25 Aug | ☐ |

**Target mechanisms for P2/P3** — one requirement, three independent stressors:

| Disruption | Mechanism | Manifestation check |
|---|---|---|
| `DISRUPTION_DB` | `BEFORE INSERT` trigger on the measurement table that `RAISE(ABORT)` | trigger present in `sqlite_master` |
| `STORAGE_FULL` | ballast file filling the data partition → genuine `SQLITE_FULL` | free space below threshold |
| `UE1_KILL` | `am force-stop` during the save, then relaunch | process gone, then back |

### 2.2 Blocking — suppression removed

| # | Item | Owner | Target | Status |
|---|---|---|---|---|
| P6 | Withdraw the `external_dependencies` guard from `concrete_domain.yml`. It downgrades **every** failure downstream of the external chip to INCONCLUSIVE. It was scaffolding for defect D4, now fixed in the System Interface and present in the regenerated test cases | build | 24 Aug | ☐ |

### 2.3 Non-blocking — strengthens the sweep, can land alongside

| # | Item | Owner | Target | Status |
|---|---|---|---|---|
| P7 | Strict `DB_CORRUPT`: does the app **detect** a null energy, or render it as `0 kcal` and let the diary sum it as zero? | build | 25 Aug | ☐ |
| P8 | Macro / per-meal-subtotal checks at existing observation points (oracle route, no model change) | build | 25 Aug | ☐ |
| P9 | Timing fuzz on `UE1_KILL` — kill at 0/50/100/200/500 ms after save, N repeats; check the total always equals the sum of rows actually in the DB | build | after first sweep | ☐ |

### 2.4 Environment

| # | Item | Owner | Target | Status |
|---|---|---|---|---|
| P10 | Artefacts collected from the node (`tc_*.aut`, `variants/`) | run | 23 Aug | ☐ |
| P11 | `check_env.sh` green — device, network, catalogue, fixture energies | run | 26 Aug | ☐ |
| P12 | Emulator undisturbed for the sweep window; laptop on power, sleep disabled | run | 26 Aug | ☐ |

---

## 3. Sweep sequence

Run in this order. The reasoning is in the third column.

| Order | Purpose | Why here |
|---|---|---|
| 1 | `happy` | The control. Re-measures the 104-variant set that supersedes M3, and tests whether the guard withdrawal (P6) holds up. **If this is not clean, stop** — nothing after it is attributable |
| 2 | `input_invalid` | No injection involved; isolates the app's own validation |
| 3 | `db_corrupt` | Smallest disruption set, and the one most likely to find something real |
| 4 | `extapi_fail` | Small; exercises the external branch that P6 just un-blindfolded |
| 5 | `cache_stale` | The authoritative-value check — the sharpest oracle in the suite |
| 6 | `ue1_kill` | First of the write-path three |
| 7 | `disruption_db` | Second — now a genuinely different mechanism from 6 |
| 8 | `storage_full` | Third |
| 9 | `storage_media` | Largest; run last so an overrun costs the least |

---

## 4. Commands

```bash
cd /Users/ayobamidele/text-conc && source systems/foodyou/env.sh

# every test case of every purpose, in the order above, resumable
bash systems/foodyou/run_all_purposes.sh

# one purpose only
bash systems/foodyou/run_all_purposes.sh cache_stale db_corrupt

# smoke first: one variant per purpose, ~10 minutes
SMOKE=1 bash systems/foodyou/run_all_purposes.sh
```

Resumable: a purpose whose log already exists is skipped. Re-run one with
`FORCE=1 bash systems/foodyou/run_all_purposes.sh <purpose>`.

---

## 5. Results

Fill in as each purpose completes. **ARITH** is the count of findings that never
reach the verdict — a PASS column alone is not a clean result.

| Purpose | Date | PASS | INCONC | FAIL | ARITH | Counter-examples confirmed |
|---|---|---:|---:|---:|---:|---|
| `happy` | | | | | | |
| `input_invalid` | | | | | | |
| `db_corrupt` | | | | | | |
| `extapi_fail` | | | | | | |
| `cache_stale` | | | | | | |
| `ue1_kill` | | | | | | |
| `disruption_db` | | | | | | |
| `storage_full` | | | | | | |
| `storage_media` | | | | | | |
| **Total** | | | | | | |

### Rules for filling this in

- A **FAIL is not a counter-example** until its log has been classified and the cause
  attributed to the application rather than the tester. Record it in the FAIL column,
  and only in the last column once established.
- **ARITH > 0 in a row that is otherwise all PASS is a finding**, not noise.
- Record the repetition count. This table is one run per test case unless stated.
- Any purpose where `check_faults.sh` did not report BITES has **no valid row** —
  leave it blank and say why, rather than entering INCONCLUSIVE.

---

## 6. After the sweep

| Item | Target |
|---|---|
| Classify every non-PASS; attribute each to app or tester | +1 day |
| Stratified `REPEATS=3` subset for a flakiness rate | +1 day |
| Full set at 3 repetitions for any purpose showing a FAIL | as needed |
| Refresh `RESULTS_happy.md` / `.tex` with the 104-variant figures | +2 days |
| Open the next CADP cycle: quantity, mixed foods, external fixture | see `ROADMAP.md` §5 |

---

## 7. Known limits of this sweep

State these in any report before a reader finds them.

- **One repetition per test case.** No flakiness rate until §6 runs.
- **Quantity never varied** — every entry is the 100 g default → exactly 900 kcal, so
  every rounding policy agrees and none is observable.
- **One food only** — `fid := defaultF` in every branch, so the band oracle's
  single-food validity condition is never stressed, and a `REMOVE_ENTRY` that deletes
  the wrong row cannot be detected.
- **External branch** — reachable only after P6, and even then it queries Open Food
  Facts for a product the catalogue does not carry (0 results, confirmed twice). A
  fixture choice, not an environmental limit.
- **One device, one Android image, one emulator.**
