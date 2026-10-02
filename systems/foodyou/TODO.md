# FoodYou — TODO

Near-term actionable work. Broader plan in [`ROADMAP.md`](ROADMAP.md); what has
already been measured in [`MILESTONES.md`](MILESTONES.md); sweep prerequisites and
the results table in [`SWEEP_PLAN.md`](SWEEP_PLAN.md).

Opened 23 August 2026.

---

## 1. The finding that prompted this file

Under `DB_CORRUPT` — the energy of the foods under test set to `NULL` — 100 g of
Corn germ oil was logged. The application:

- **detected** the corruption and labelled the entry *"Food is missing required
  fields"*
- **refused to invent an energy**, showing `—` rather than `0`
- **still counted that record's 100 g of fat** into the daily total

So the day header read:

```
0 / 2000 kcal          2000 calories left
Proteins        0 / 100 g
Fats          100 / 67 g          <- over goal, from the flagged record
Carbohydrates   0 / 250 g
```

The application trusted one field of a record it had itself declared
untrustworthy. A user who logs 100 g of oil is told they have 2000 calories left.

Evidence: `tmp/failure_artifacts/20260823-125918_total_mismatch_CONFIRM_TOTAL.xml`
and the matching `.png`.

**The test suite did not find this.** The run failed for an unrelated reason (the
energy total stayed at 0 where the model expected it to rise), and that failure is
attributable to the model, not the app — the specification never describes logging
a food whose record is corrupt. The macro inconsistency was found by reading the
screenshot.

---

## 2. Implemented now — concretization only

`_check_macro_consistency` in `framework/concretization/algorithm.py`, called at
every `CONFIRM_TOTAL`.

It does **not** compare the header against the entries; those already agree (100 g
of fat in both places). It asks whether the two figures the application shows are
consistent **with each other**:

```
implied kcal = 4·protein + 9·fat + 4·carbohydrate
```

A day holding 100 g of fat cannot also hold 0 kcal. Against the captured screen:
implied 900 kcal, displayed 0, tolerance 225 — **flagged**. Against a normal day
(300 g fat, 2700 kcal) — consistent.

No external reference is needed, so the check works on any screen without an
authoritative table.

Three selectors added to `concrete_domain.yml`: `el_daily_protein`,
`el_daily_fat`, `el_daily_carbs`.

**Reported as a FINDING, never as a verdict.** The specification does not mention
macros, so a discrepancy violates nothing it asserts. Findings appear in the
`ARITH` column of the sweep table and in `classify_failure.py` output; they never
terminate a walk.

Tolerance is deliberately wide — `max(100 kcal, 25%)`. Atwater factors are
approximate, fibre and alcohol are treated differently by them, and every figure on
screen is rounded. Only a contradiction rounding cannot explain is worth reporting.

### Still to do here

- [ ] Validate on device against the `DB_CORRUPT` case that produced the finding.
      The selectors match by `instance(0/1/2)`, which is the weakest part — confirm
      the order really is Proteins, Fats, Carbohydrates on the live screen.
- [ ] Surface `MACRO INCONSISTENCY` in `classify_failure.py` alongside
      `TOTAL MISMATCH` so it appears in the `ARITH` column.

---

## 3. Expanding the specification

### Why

The check above can only ever produce a **finding**. ioco is defined relative to a
specification: if the model does not mention macros, the application cannot
contradict it there. So the strongest available claim is *"our tool noticed an
inconsistency"* — not *"the system violated its specification"*.

That distinction is the whole difference between a tool that observes and a tool
that decides. Only the second is an ioco result, and only the second belongs in a
counter-example column.

### What expanding it solves

**1. It turns this finding into a counter-example.** With protein, fat and
carbohydrate carried on `FoodInfoChannel` and the daily total, the specification
states what the application must show. An entry contributing fat while its energy
is unknown then contradicts something the model asserts, and the verdict is FAIL
rather than a note.

**2. It closes a structural blind spot.** The campaign has made 503 `CONFIRM_TOTAL`
observations, all of a single number. Every other figure on that screen is
unfalsifiable by construction. Four numbers per observation instead of one is a
fourfold increase in what can be contradicted, at no cost in test-case count.

**3. It fixes the `db_corrupt` verdict.** The current FAIL — `expected LOW, got
EMPTY` — indicts the model. The specification says a VALID add bumps the total and
never covers adding a corrupt record, so the application declining an unknown
energy is defensible. Modelling the corrupt-add branch makes that verdict mean
something either way.

**4. It stresses arithmetic the current abstraction cannot reach.** `DailyTotal` is
a saturating band whose inversion is only valid while every logged entry is the
same food — the model file says so itself. Macros are per-food quantities with no
banding, so they exercise the exact arithmetic directly.

### What it costs

`foodyou_types.lnt` (channel parameters), `specification_foodyou_copy.lnt` (the
corrupt-add branch and the macro outputs), `system_interface_foodyou_copy.lnt` (the
observations), and a full CADP regeneration. It must be batched with the other
model changes — see `ROADMAP.md` §5 — not paid for on its own.

Bound the domain. The last extraction reached 323 variants before being cancelled;
three extra parameters multiply that if left unconstrained.

- [ ] Decide whether macros become full channel parameters or a single derived
      "nutrition consistent / inconsistent" abstract value. The second is far
      cheaper in state space and may be sufficient — the defect above is visible as
      a boolean.
- [ ] Model the corrupt-add branch: what should the total do when a food with an
      incomplete record is logged?

---

## 4. Other open items

### Blocking a meaningful disruption sweep

- [ ] **`cache_stale` injection is inverted.** It sets `energy = 999` *in the
      database*, and the database is the application's source of truth — so the app
      correctly displays 999 and the oracle, which expects the declared 900, calls
      it a counter-example. It rewards stale behaviour and punishes correct
      behaviour. To test staleness the value must change *underneath* a cache the
      app is already holding, not be rewritten as the new truth. **48 test cases
      uninterpretable until fixed.**
- [ ] **`storage_media` selector is wrong.** `el_storage_error` looks for
      `"Unable to load"`; the application actually shows *"Oops! Something went
      wrong"* with a stack trace and a bug-report button. Confirmed 2026-08-23.
- [ ] **`storage_media` injection cannot reach a running app.** Permissions are
      checked at open and the app holds the database open, so a mid-run `chmod`
      does nothing. The injection must force a re-open, as `UE1_KILL` does.
- [ ] **Late injection on the three write-path faults.** `UE1_KILL`,
      `DISRUPTION_DB` and `STORAGE_FULL` fire *after* `ADD_ENTRY`'s concrete steps
      complete — by which point the write has committed and there is nothing to
      abort. All three produce the identical `3600 OVER, expected HIGH`. **Not
      being fixed** (decision, 23 Aug): the FAIL is real against this
      specification, and what matters is that it is attributable. It has a
      detectable signature — the exact-sum oracle agrees with the device while the
      band oracle expects a rollback.
- [ ] Add a `LATE-INJECTION` class to `classify_failure.py` for that signature, so
      those 326 cases self-label instead of needing manual inspection.

### Ready, not yet done

- [ ] Withdraw the `external_dependencies` guard from `concrete_domain.yml`. It
      downgrades every failure downstream of the external chip to INCONCLUSIVE. It
      was scaffolding for defect D4, now fixed in the System Interface and present
      in the regenerated test cases.
- [ ] Re-measure `happy` on the new 104-variant set. `RESULTS_happy.md` describes
      the superseded 102-variant suite.
- [ ] Re-run the 10 inferred INCONCLUSIVE cases so the figure is fully measured.
- [ ] Stratified `REPEATS=3` subset for a flakiness rate — currently the weakest
      point in the evidence.
- [ ] Fix the `SWEEP SUMMARY` aggregation: it reads `variants_*.log` while SMOKE
      mode writes `investigate_*.log`, so a smoke run's table shows only `happy`.

### Environment

- [ ] Emulator has no route out; the host has six `utun` interfaces and an
      institutional default route. `LOCAL_ONLY=1` works around it for the seven
      local purposes. Not blocking, but `extapi_fail` cannot run until resolved.
- [ ] `sourceType=1 -> 1288 products`: Open Food Facts products are already cached
      on the device. The external-branch fixture can therefore be made
      deterministic and offline — better than querying the live API, which was the
      original plan and carried a reproducibility risk.

---

## 5. Rules this file operates under

- No claim about the system without the command that establishes it.
- Never adjust a model to make a verdict come out a particular way. A specification
  edit that makes a FAIL impossible by definition is the failure mode to guard
  against.
- A FAIL is not a counter-example until its cause is attributed to the application
  rather than the tester.
- Findings are not verdicts, and must not be reported as if they were.
