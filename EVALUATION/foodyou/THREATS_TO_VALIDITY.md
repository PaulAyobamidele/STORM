# FoodYou Campaign — Threats to Validity

Written 2026-09-02. A focused extract, not a replacement for
`RESULTS_campaign.md` (the authoritative deep note) or `HANDOVER.md` — this
note exists so the caveats a reader most needs before trusting a number are
in one place, not scattered across an 1,100-line document.

Nothing below is new invention; each item is sourced to where it was found
in this campaign, most of them this week.

---

## 1. RESOLVED 2026-09-03 — `extapi_fail`'s 34 selector-timeout FAILs are confirmed, not a tooling artifact

**The measured result stands: `extapi_fail` is 0 PASS / 45 FAIL / 0
UNEXECUTABLE (45/45 cases)** — 11 by the same empty-EXTERNAL-search rule
already applied to 81 other cases in this campaign, 34 on a different
signature: `EXTAPI_FAIL` genuinely fires, then the walker times out waiting
for `el_extapi_warning`.

This item previously flagged those 34 as resting on an unconfirmed
selector. That doubt is now closed. Checked directly against the live
device captures already on disk — the accessibility-tree XML and the
screenshot recorded at the exact moment of each of the 34 timeouts, all 34
checked, not a sample: every one shows the same food-search screen, with
the "Open Food Facts" source chip reading "0", styled identically to every
other source chip (`Recent`, `Your food`, `Swiss Food Composition
Database`). No warning icon, no error banner, no text anywhere in the tree
or on screen containing "warning", "error", "fail", "offline",
"unavailable", or "retry", confirmed both by a full-text scan of all 34
captures and by visual inspection of two.

**Conclusion: the selector was never pointed at the wrong string — there is
no element for any selector to find.** FoodYou renders "external API
unreachable" identically to "external API legitimately returned nothing."
The specification's requirement (`EXTAPI_WARNING : none`) demands *some*
observable acknowledgment; FoodYou provides none, distinguishably, ever.
These 34 FAILs are a confirmed app-level finding — a real gap in FoodYou's
observability of API failure — not a false FAIL about the concretization.
No re-run is possible or needed: there is no different selector that would
find something that isn't there. `concrete_domain.yml`'s `el_extapi_warning`
comment records this.

## 2. 256 of 293 write-path FAILs are timing artifacts, not fixed

`UE1_KILL`, `DISRUPTION_DB`, and `STORAGE_FULL` all arm at the `ADD_ENTRY`
gate — by which point the write has already committed. The fault fires too
late to test what its purpose claims to test. v47 (`disruption_db`) is the
one case where the fault armed early enough to hit a live write, and it
shows what these should look like: a real crash, a real DAO stack trace, a
real FAIL. The fix (re-time the three faults to arm before the add) is
identified, concretization-layer only, and **not yet applied.** Every
number quoted for these three purposes should carry this caveat.

## 3. The fixture cannot produce a genuine EXTERNAL-branch PASS

Every food in `FoodId` is a Swiss Food Composition Database product; none
exists in Open Food Facts. This is why 81 cases across seven purposes
(the original 70 + `extapi_fail`'s 11) hit a structurally guaranteed empty
external search — a coverage gap in the fixture, not a discovery about the
app. Until the model or fixture includes a product Open Food Facts actually
carries, no purpose's EXTERNAL arm can ever conform, only refuse or fail.

## 4. Single repetition — no flakiness measurement exists

The entire campaign (progressively: 748, then +144, then +45 cases) has
run exactly once per case. A stratified `REPEATS=3` re-run with Wilson
intervals is identified and not done. Every number in this campaign is a
single sample, not a rate.

## 5. Classifier validity unverified

`classify_failure.py`'s root-cause category labels — the ones that
mislabeled v47 as ARTIFACT rather than the campaign's most important
result — have not been checked against an independent human rater. A
Cohen's κ study against ~50 hand-labeled cases is identified and not done.
Whoever writes the classifier should not also be its only rater.

## 6. 22 passes sit at a saturating band that cannot be falsified

`ue1_kill` (8), `disruption_db` (7), `storage_full` (7) — all at the `OVER`
band of the `DailyTotal` abstraction, where the model cannot distinguish a
write that landed from one that silently failed. Not evidence of correct
behaviour, regardless of how confidently they read as PASS.
`storage_media`'s 58 passes have not yet been audited for the same
problem.

## 7. The controllability / no-INCONCLUSIVE proof covers 8 of 9 purposes

The mechanical check establishing FoodYou's verdict set as `{PASS, FAIL,
UNEXECUTABLE}` — no output-reached `INCONCLUSIVE` anywhere — was run
against 8 generated Complete Test Graphs. `storage_media`'s CTG has not
been checked by the same method. The claim should be read as covering the
eight purposes actually checked, not the whole model, until that gap
closes.

## 8. 17 harness cases never produced a verdict

Step-budget exhaustion, an Appium session death, a weak manifestation
probe, one empty screen capture — apparatus reasons, not statements about
the SUT. Listed exactly in `HANDOVER.md` §6. Re-run identified, not done.

## 9. Evidence chain-of-custody is fixed only going forward

The 1,457 pre-2026-09-01 capture files in `tmp/failure_artifacts/` are
still unlinked to the cases that produced them — including the ones this
campaign's own headline finding (v47) depends on. The fix (scoping
captures to each case's own log directory) applies to every sweep run
since; it does not retroactively organize what came before.

## 10. `extapi_fail`'s 11 confirmed FAILs, and every reclassification like
them, rely on a pattern match, not a re-verification of every instance

The empty-search reclassification rule was established by visually
confirming 2 cases, then mechanically confirming the remaining 68 (and
later 11, and 11 again) via an identical log signature — not by re-opening
every screenshot. The mechanism is structural (the fixture genuinely has
no matching Open Food Facts product), which is why this is treated as
reliable pattern-matching rather than case-by-case guessing — but it is
still inference from a shared cause, not 90 independent confirmations.

---

## What this list is not

Not a claim that these threats invalidate the campaign's real findings.
v47, the `CACHE_STALE` counter-example, and the `DB_CORRUPT` fat-trust
defect (§9/§10 of `RESULTS_campaign.md`) each stand on their own direct
evidence, independent of every item above. This list exists so that
evidence stays distinguishable from the numbers still waiting on a fix.
