# FoodYou — Nominal-Behaviour Conformance Campaign

**Result report for the fault-free ("happy") test purpose, prior to disruption testing.**

Campaign closed 2026-08-19. All figures below are measured from the artefacts named
in §9, not reconstructed. Where a figure is inferred rather than measured, it is
labelled as such.

---

## 1. What this campaign establishes

The disruption results this project is built to produce are only meaningful if a
`FAIL` on the fault-free path means what it says. This campaign tests the
**baseline**: does the SUT conform to its specification when nothing is being
injected, and — equally — does the tester itself produce verdicts that can be
trusted?

Two questions, and the second turned out to carry the finding:

- **RQ1.** Does FoodYou conform to the nominal specification under ioco?
- **RQ2.** Are the verdicts sound — i.e. is every reported `FAIL` one the tester
  actually earned?

**Answer to RQ1: yes.** 102 generated test cases, **zero conformance
counter-examples**, across 503 `CONFIRM_TOTAL` observations and 558 independent
arithmetic checks.

**Answer to RQ2: not initially.** Every `FAIL` observed during the campaign was
traced to a defect in the *test framework*, not the SUT. Four distinct defects were
found and fixed. This is reported as a primary result rather than as
housekeeping — see §6.

---

## 2. Subject under test

| | |
|---|---|
| Application | FoodYou (`com.maksimowiczm.foodyou`) |
| Type | Local-first calorie/nutrition tracker |
| Platform | Android, Kotlin + Jetpack Compose |
| Persistence | Room (SQLite), `open_source_database.db` |
| Catalogues | Swiss Food Composition Database (bundled, offline); Open Food Facts (remote); user-defined; recent history |
| Driver | Appium / UiAutomator2 |
| UI identification | No resource-ids (Compose) — text and content-description selectors only |

FoodYou snapshots nutrition values into the diary entry at log time
(`DiaryProduct`), so a logged entry does not track later catalogue changes. This
constrains what a staleness disruption can mean and is recorded here for the
disruption campaign that follows.

---

## 3. Model and test generation

**Specification × System Interface × disruptors** are composed in LNT and test
cases extracted with CADP/TESTOR.

| Artefact | Path |
|---|---|
| Specification | `model/specification_foodyou_copy.lnt` |
| System Interface | `model/system_interface_foodyou_copy.lnt` (17 gates) |
| Types | `model/foodyou_types.lnt` |
| Test purpose | `Test_Purposes/tp_happy.lnt` |
| Interpretation | `properties/concrete_domain.yml`, `properties/type_description.yml` |

**Generated suite: 102 test cases.**

| | min | median | max |
|---|---|---|---|
| States per case | 58 | 216 | 255 |
| Transitions per case | 88 | 323 | 381 |

Total: **32,030 transitions**. Test cases are *controllable* — at most one input is
enabled per state — which is what makes the tester's behaviour determined by the
case rather than by its own choices.

### 3.1 Abstract domain

`DailyTotal` is a **saturating band**, not an exact figure: `EMPTY, LOW, MODERATE,
HIGH, OVER`. The specification counts committed entries, one rung per entry; the
concretization inverts that as `rung = round(observed_kcal / bucket_unit)`.

The model file states its own validity condition explicitly: *the band inversion is
only valid while every logged entry is the same food.* That limitation is not
papered over — it is the reason the exact-sum oracle (§4) exists.

### 3.2 Fixture

Three real Swiss Food Composition Database products, deliberately spread so that a
mixed-food total cannot be mistaken for a whole number of portions:

| Abstract | Product | kcal / 100 g |
|---|---|---|
| `food_peanut` | Peanut butter | 636 |
| `food_butter` | Cooking butter | 745 |
| `food_oil` | Corn germ oil | 900 (`defaultF`) |

Daily goal 2000 kcal; band rungs 0 / 900 / 1800 / 2700 / 3600. The energies are
**not asserted by the harness** — they are read back from the app's own `Product`
table, so a mismatch means the app disagrees with its own catalogue rather than
with a hand-maintained constant. `seed_foods.sh` verifies this before every run and
aborts if it fails.

---

## 4. Oracle design

Four independent checks, deliberately layered so that the weakest is never the only
one running. This layering is what makes the "zero counter-examples" claim
meaningful rather than vacuous.

| Oracle | Compares | Sensitivity |
|---|---|---|
| **Band** | observed total → abstract bucket vs the AUT's expected bucket | coarse; tolerates ±½ portion |
| **Exact-sum** | displayed total vs the running sum of what the tester actually logged | exact, to the calorie; mixed-food safe |
| **Arithmetic** | is the total a whole number of portions | fallback when energies are undeclared |
| **Delta** | did the total move by the amount the last action implies | fallback; single-food only |
| **FOOD_INFO** | displayed per-food energy vs the app's own catalogue value | exact |

**The exact-sum oracle is the load-bearing one.** The band oracle alone tolerates
±450 kcal at a 900 kcal portion — a total of 1200 passes as "one portion". The
exact-sum check removes that slack and works on mixed diaries where the band
inversion does not.

**Findings vs verdicts.** An exact-sum mismatch is reported as a *finding*, not a
verdict: the specification states bands, so an exact discrepancy violates nothing
it asserts. Findings never terminate a walk, which means they can ride inside a
`PASS` — so they are surfaced separately in the sweep output (§9), and a `PASS` is
not treated as self-certifying.

**The ledger fails closed.** The exact-sum oracle keeps a running sum; `ADD_ENTRY`
and `REMOVE_ENTRY` stage a movement for the next `CONFIRM_TOTAL` to apply. If a
staged movement is ever overwritten unapplied, the ledger declares itself `UNKNOWN`
and **abstains for the remainder of the run** rather than reporting against a sum
it knows is stale. An oracle that abstains costs one missed check; an oracle that
is quietly wrong costs the credibility of every verdict in the campaign, because
nothing downstream can distinguish the two.

---

## 5. Results

### 5.1 Verdicts

| Verdict | Count | Status |
|---|---|---|
| PASS | 89 / 102 | measured |
| INCONCLUSIVE | 13 / 102 | **3 measured, 10 inferred** (§8.3) |
| FAIL (conformance counter-example) | **0** | measured |

**No test case produced a conformance counter-example.** Every non-PASS verdict is
a case in which the tester could not apply its stimulus, and therefore obtained no
observation to judge.

### 5.2 Oracle activity

Across the 102-case sweep:

| | count |
|---|---|
| `CONFIRM_TOTAL` band checks | 558 |
| Exact-sum ledger applications | 558 |
| `FOOD_INFO` authoritative-value checks | 165 |
| Arithmetic / delta / exact-sum **findings** | **0** |
| Ledger abstentions | **0** |

Every `CONFIRM_TOTAL` that was observed reached both the band and the exact-sum
oracle; none disagreed with the device, and the ledger never lost track.

### 5.3 Gate coverage

| Gate | test cases reaching it | total firings |
|---|---|---|
| `SEARCH_FOOD` | 102 | 178 |
| `FOOD_INFO` | 98 | 165 |
| `ADD_ENTRY` | 97 | 471 |
| `CONFIRM_TOTAL` | 97 | 503 |
| `REMOVE_ENTRY` | 72 | 87 |
| `VIEW_DIARY` | 6 | 6 |
| `DIARY_INFO` | 6 | 6 |

Note that `VIEW_DIARY`, `DIARY_INFO` and `REMOVE_ENTRY` do **not** appear in the
body of `tp_happy.lnt`. A TESTOR test purpose is a *selector over the composed
specification*, not a script: gates absent from the purpose are still woven into
the generated cases. `REMOVE_ENTRY` in particular is exercised in every generated
case and fires 87 times — including the add-then-remove-then-add sequences that
returned the total exactly to its prior value (`3600 → 2700 → 3600`, verified to
the calorie).

### 5.4 Cost

Median 55 s per test case (range 22–133 s); ≈ 1 h 45 m for the full suite at one
repetition, on a single emulator.

---

## 6. Primary finding: four defects, all in the tester

No defect was found in the SUT. Four were found in the concretization framework,
each of which had been producing or concealing incorrect verdicts. They are
reported here because *this is the result*: an ioco concretization layer is itself
a program that can be wrong, and being wrong in the direction of a false `FAIL` is
indistinguishable from a discovery unless it is actively hunted.

**D1 — The tester chose among the SUT's outputs.** A checkpoint shortcut selected
among multiple abstract *outputs* by shortest-distance-to-PASS, then failed the run
when the SUT produced the other equally-permitted one. The specification allows
either — `alt total := HIGH [] total := OVER` — and which occurs is the SUT's
decision, never the tester's. Affected 100 of 102 test cases.

**D2 — Branch selection ignored the observation.** The fallback matcher compared
the abstract token to the rendered value literally (`"over" == "2700 / 2000 kcal"`),
which never matches, so the first alternative won by default. The tester was still
choosing, now silently and with no oracle run at all. Fixed so that the
**observation** selects the branch, via the same interpretation function the oracle
uses.

**D3 — The oracle had one call site, behind a shortcut.** `_validate_checkpoint`
was reachable only from the single-alternative path. Every gate reached at a state
offering several allowed outputs skipped the oracle *and* the exact-sum ledger
update entirely. Because the only multi-output state in the specification is
`drop(OVER)` — reachable only via `REMOVE_ENTRY` — the single skipped consumer and
the single *subtracting* ledger operation were the same event. A removal's −900
kcal was staged, never applied, then silently overwritten by the next `ADD_ENTRY`,
leaving the ledger 900 kcal above the device for the rest of the run and reporting
a confident `TOTAL MISMATCH` against a total the app had computed correctly.

**D4 — An asymmetric System Interface turned an honest empty result into a FAIL.**
Of 14 source-selection sites, exactly one — the external-catalogue branch — omitted
`wait_for (el_search_results)`. It proceeded directly to `wait_for (el_calories)`,
a selector that also appears in an `observe` block and is therefore an *oracle*
selector, so its timeout was reported as a conformance failure. The app had
behaved correctly: it displayed an honest source count of 0 and "No food found".
This single omission accounted for **all 13 failures** in the sweep.

### 6.1 Trajectory

An earlier campaign on a 93-case suite reported **54 FAILs**. After D1–D4 the
102-case suite reports **zero**. These are different suites generated from
different model revisions, so this is a trajectory, **not a controlled comparison**,
and should not be quoted as a measured improvement factor.

---

## 7. Methodological measures adopted

Four changes were made to keep the verdicts auditable. Each is a candidate
contribution in its own right.

1. **The observation selects the branch.** Where a specification permits several
   outputs, the tester reads the value and follows the branch the observation
   satisfies. If none is satisfied, that — and only that — is the counter-example,
   and it is reported naming every value the specification allowed.
2. **The oracle runs on every accepted transition**, not only on those reached by a
   structural shortcut.
3. **Fail-closed bookkeeping.** State the oracle maintains across steps is
   invalidated the moment it can be shown to have lost an update, and the check
   abstains rather than reporting.
4. **Findings are surfaced independently of verdicts.** Checks that cannot
   terminate a walk are counted and reported per run, so a suite of PASSes is only
   a clean result if the findings column is clean too.

Additionally: evidence (screenshot + UI tree) is now captured when an *oracle*
rejects an observation, not only when a wait times out. The case that most needs a
picture is the one where the tester found the value and the oracle disagreed —
which is precisely a candidate counter-example.

---

## 8. Threats to validity

### 8.1 Construct validity

- The `DailyTotal` band abstraction inverts correctly only while every logged entry
  is the same food. Mitigated by the exact-sum oracle, which is mixed-food safe and
  ran 558 times without disagreement; but the band remains the abstraction the
  specification is written in.
- `WriteStatus` is internal and never directly observed; `CONFIRM_TOTAL` is the
  only window onto it.

### 8.2 Internal validity

- **The framework was defective during part of the campaign.** All figures in §5
  are post-fix. Runs predating D1–D4 are not comparable and are not quoted.
- **The external-dependency guard masks defects by construction.** Any failure
  downstream of selecting the external catalogue is downgraded to INCONCLUSIVE. A
  genuine SUT defect on that path would therefore be hidden. This is an explicit,
  configured trade-off, and it is the reason the external branch is reported as a
  coverage gap rather than as a pass.
- **A single repetition.** The full sweep ran at `REPEATS=1`. Stability was checked
  on a subset (identical verdicts on repeat), but a suite-wide flakiness rate has
  not been measured.

### 8.3 Reliability of the INCONCLUSIVE figure

Of the 13 INCONCLUSIVE cases, **3 were re-run and confirmed** (variants 12, 30, 91)
after the external-dependency guard was reinstated. The remaining 10 share an
identical cause, gate and selector, but **have not been individually re-run**. The
figure "13 INCONCLUSIVE" is therefore 3 measured and 10 inferred, and should be
completed before publication.

### 8.4 External validity

One application, one test purpose, one device, one Android image. No claim is made
about generality across apps or platforms from this campaign alone.

---

## 9. What is *not* claimed — coverage gaps

Stated explicitly, because each is a question a reviewer will ask.

**The external-catalogue branch was never exercised.** All 13 INCONCLUSIVE cases
search Open Food Facts for `defaultF` = Corn germ oil. That product returns **0
results**, confirmed twice independently: by the application's own displayed source
count, and by a direct query to the Open Food Facts API. This is *not* a limitation
of the catalogue — the same API returns **215 results** for "Cooking butter". The
gap arises because every System Interface branch fixes `fid := defaultF`, so the
external source is only ever queried for the one product it does not carry. **This
is a fixture choice, not an environmental constraint,** and should be described as
such.

**Quantity is never varied.** Every `ADD_ENTRY` uses the application default of
100 g, giving exactly 900 kcal. All arithmetic checks therefore ran on round
numbers. Rounding and off-by-one behaviour in the quantity path is untested.

**Only one food is ever logged.** No mixed-food diary was constructed, so the
band oracle's stated validity condition was never actually stressed on device.

**Unit conversion (g ↔ ml) never ran.** No unit control is declared in the
interpretation layer.

**`VIEW_DIARY` / `DIARY_INFO` are thinly covered** — 6 firings each, against 503
for `CONFIRM_TOTAL`.

---

## 10. Reproduction

```bash
source EVALUATION/foodyou/env.sh          # asserts device, network, catalogue, fixture energies

# full suite
bash EVALUATION/foodyou/run_variants.sh happy

# classify any non-PASS, including findings hidden inside a PASS
python framework/scripts/classify_failure.py \
  EVALUATION/foodyou/generated/variant_logs/happy/v<N>.log

# re-run selected cases with full diagnostics and repetition
REPEATS=3 bash EVALUATION/foodyou/investigate_variants.sh happy <N>...
```

`env.sh` refuses to proceed on a device that cannot reach the network or whose
fixture foods do not hold their authoritative energies, so a poisoned environment
fails loudly rather than producing a sweep of quiet false results.

**Artefacts:** `EVALUATION/foodyou/variants_happy.log` (suite verdicts),
`generated/variant_logs/happy/` (per-case stdout+stderr),
`generated/investigate/happy/` (repeat runs), `tmp/failure_artifacts/`
(screenshots and UI trees at the moment of rejection).

---

## 11. Before the disruption campaign

Ordered by what most affects the credibility of the disruption results.

1. **Re-run the remaining 10 INCONCLUSIVE cases** so §5.1 is fully measured.
2. **Measure suite-wide flakiness** — at minimum a stratified `REPEATS=3` subset.
3. **Regenerate the test cases.** The System Interface fix for D4 is composed into
   the `.aut` files at generation time and is currently inert; the runtime guard is
   standing in for it. After regeneration, reconsider whether the guard — which
   masks defects by construction — can be withdrawn.
4. **Point the external branch at a product the catalogue carries**, and make the
   authoritative energy *per source*. This converts 13 INCONCLUSIVEs into 13 real
   verdicts and closes the most visible gap in §9.
5. **Vary quantity** (a small bounded set, e.g. 100 / 137 / 250 g). This requires
   quantity to become a gate parameter, the declared energy to become a function of
   quantity, and the exact-sum ledger to scale accordingly. It is the largest
   untested surface and the one the strongest oracle is built for.
6. **Converge the oracle's two call sites onto one.** Disruption branches will add
   further multi-output states, which is exactly the shape that produced D3.

Items 4 and 5 share a CADP cycle and should be done together.
