# FoodYou — A Hybrid ioco Concretization Campaign

### Specification, Generation, and Concretization, Purpose by Purpose

Written 2026-09-01. This note supersedes every prior verdict summary for
FoodYou, including the "4 PASS / 1 FAIL / 3 INCONCLUSIVE" matrix that appears
in earlier project notes — that was a one-run-per-fault smoke test from
2026-07-27, not this campaign. It should not be quoted going forward.

---

## The verified claim, stated once, precisely

Across a **793-case sweep covering all 9 of FoodYou's test purposes**,
measured directly from `Verdict:` lines in
`generated/variant_logs/*/v*.log`:

```
285 PASS   488 FAIL   20 UNEXECUTABLE
```

`storage_media` (144 cases) and `extapi_fail` (45 cases) both completed
2026-09-02, moving the total from the original 8-purpose figure
(285/443/20/748) to the figures above. See §7.7, §7.9, and §9 for the
per-purpose table.

Of those:

- **22 of the 285 passes are unfalsifiable** — they sit at the saturating
  `OVER` band of the daily-total abstraction, where the model cannot
  distinguish a write that landed from one that silently failed.
- **256 of the write-abort FAILs (disruption_db/storage_full/ue1_kill) did
  not test the requirement they are filed under** — three write-abort
  faults arm after the write already committed, so the FAIL is a timing
  artifact of the concretization, not evidence about the app. One case
  (`disruption_db` v47) shows what these should look like, and it is the
  single most important result in the campaign.
- **`extapi_fail` measured 0 PASS / 45 FAIL / 0 UNEXECUTABLE.** 34 of those
  45 FAILs were checked directly against the run's own live device captures
  (all 34, not a sample) on 2026-09-03: FoodYou renders "external API
  unreachable" identically to "external API found nothing" — no selector
  could distinguish them, because no such element exists. Confirmed finding,
  not a tooling artifact; see `THREATS_TO_VALIDITY.md` §1.
- **20 UNEXECUTABLE** = 17 harness/apparatus failures from the original
  8-purpose sweep + 3 from `storage_media` (1 Appium connection reset,
  2 confirmed fault-did-not-manifest).
- **The sweep has run once.** No flakiness measurement exists.
- **There is no fourth outcome.** §1 below is the argument for why the
  verdict set is `{PASS, FAIL, UNEXECUTABLE}` and not a classical
  three-valued ioco `{PASS, FAIL, INCONCLUSIVE}` — checked mechanically
  against every generated test graph, not asserted. (That check itself
  covers 8 of the 9 purposes — `storage_media`'s CTG is the one not yet
  checked the same way, see §11.)

Nothing below is stated more strongly than this evidence supports. Where a
number is pending a re-run, it is marked pending, not estimated.

---

## 1. Verdict Semantics — How PASS, FAIL, and UNEXECUTABLE Were Judged

Every case in this campaign resolves to exactly one of three outcomes. This
section is the argument for why there are three, not four, and it is checked
mechanically below, not asserted.

### 1.1 Three outcomes

| Outcome | Meaning |
|---|---|
| **PASS** | the walk reached a `:PASS:` trap state |
| **FAIL** | the SUT produced an output — or a quiescence — the specification forbids |
| **UNEXECUTABLE** | the apparatus could not run the case. Not a verdict; carries no information about the SUT |

No log in this campaign contains `Verdict: INCONCLUSIVE`. Where
"INCONCLUSIVE" appears elsewhere in this project's history — including
quoted directly in §7.9's excerpt from `tp_extapi_fail.lnt` — it names a
harness-level abort or a test-purpose author's expectation, never a
model-derived verdict this campaign actually produced. Read every such
quotation as meaning UNEXECUTABLE.

### 1.2 The controllability argument

`testor` derives each `tc_<purpose>.aut` as a **controllable test case** —
one the tester can actually drive, deterministically, against a real SUT.
Controllability constrains what extraction is allowed to do with
nondeterminism at a state that offers several transitions:

- **Among inputs, extraction may choose.** The tester decides what to type or
  tap; offering two different inputs at the same state is a choice the
  tester makes, not the SUT. A test purpose (or the walker's own
  pass-steering) may resolve this nondeterminism by picking one input and
  discarding the rest — that is what "controllable" means.
- **Among outputs, extraction may not choose.** The SUT decides what it
  produces; a controllable test case is only usable if it is prepared to
  accept *any* output the SUT might legally give at that point. Extraction
  cannot prune an output-reached branch just because it is inconvenient —
  doing so would mean the derived test case silently refuses to recognize a
  legal SUT response, which is not controllability, it is a hole in the
  test case.

The rule that follows, confirmed directly with the project's supervisor: **an
`INCONCLUSIVE` state reached only through transitions the tester chooses
among may be extracted away. An `INCONCLUSIVE` state reachable through an
output the SUT is free to produce must survive extraction.** If ours had
been dropped, that would be a tool defect — not a property of a clean
specification, but evidence that `extract_all` was throwing away a real
ambiguity.

### 1.3 Checked mechanically against every generated CTG

Every `INCONCLUSIVE` state in every one of the 8 generated Complete Test
Graphs (`Test_Cases/tc_*.aut`) was inspected directly — not sampled, all
of them — by parsing the `.aut`'s `(src, "LABEL", dst)` triples, collecting
every state carrying an `:INCONCLUSIVE:` self-loop, and tallying the labels
of the transitions that lead *into* each one:

| CTG | INCONC states | incoming transitions | all inputs? |
|---|---:|---:|---|
| cache_stale | 3 | 6 | ✓ |
| db_corrupt | 9 | 12 | ✓ |
| disruption_db | 12 | 15 | ✓ |
| extapi_fail | 9 | 12 | ✓ |
| happy | 15 | 18 | ✓ |
| input_invalid | 12 | 15 | ✓ |
| storage_full | 12 | 15 | ✓ |
| ue1_kill | 12 | 15 | ✓ |
| **total** | **84** | **108** | **96 `TAP` + 12 `ENTER_TEXT`** |

**108 of 108 incoming labels are inputs. Zero are outputs.** Every
`INCONCLUSIVE` state in every generated CTG sits strictly behind a tester
choice — reached only by a `TAP` or an `ENTER_TEXT`, never by an abstract
gate the SUT itself fires. **`storage_media` is not in this table** — the
check above covers 8 of the 9 purposes; extending it to `storage_media`
before quoting this result as covering the whole model is outstanding work,
not yet done.

### 1.4 What this proves, and what it does not

**It proves extraction was sound.** By the rule in §1.2, every one of these
84 states was extraction's to prune, and `extract_all` pruned all of them.
The extracted test-case variants this campaign actually ran genuinely
contain no `INCONCLUSIVE` state — that is not a defect in CADP, in `testor`,
or in this project's own extraction step. It is the correct, checked
consequence of a controllable derivation applied to a specification that
happens to have this particular shape.

**It proves something about the specification, not about the tooling.**
`{PASS, FAIL}` — the verdict set the extracted variants can produce, before
`UNEXECUTABLE` is added for apparatus reasons — is a property of *this*
specification: it contains no branch where a SUT output is legal yet leaves
the purpose undecided. Every output `SPEC` can produce either advances a
purpose toward `:PASS:` or is outside what the purpose permits, with nothing
in between. This is the same fact, examined from the generation side rather
than the verdict-semantics side, that makes "empty search = FAIL" (§8.2) the
consistent reading rather than a stretch: **there is no `FOOD_ABSENT` output
anywhere in `specification_foodyou_copy.lnt` for a confirmed empty search to
be inconclusive on.** If one existed, a confirmed empty result would
legitimately be a model-derived `INCONCLUSIVE` surviving extraction — a
controllable test case must accept every output the SUT can produce, even
though it may offer only one input at that state, so `FOOD_ABSENT` would sit
on the output side of §1.2's rule and survive exactly the way DB_CORRUPT's
and STORAGE_MEDIA's genuine detection failures would. Adding it was
considered and rejected (recorded in `HANDOVER.md` §1 as a "rejected
alternative"): it is mechanically correct, but it would have weakened the
specification's own claim — from "a search always returns information" to
"a search returns information, or explicitly admits it has none" — and that
softer claim was not wanted.

**The honest limit.** This check establishes that `extract_all` did not
discard anything it should have kept — every `INCONCLUSIVE` state genuinely
was reachable only through a tester-controlled choice, so pruning it was
sound in every one of the 84 cases checked. It does **not** establish that
the specification *ought* to have no output-reached `INCONCLUSIVE`
anywhere — that is a separate, prior design question (add `FOOD_ABSENT` and
accept a weaker specification, in exchange for a genuinely three-valued
ioco verdict on that branch), and it was already decided against, by the
supervisor, before this check was ever run. This check confirms the
decision was *implemented* soundly. It is not, by itself, the argument for
having made the decision in the first place — that argument is in
`HANDOVER.md` §1 and restated at §8.2 below.

---

## 2. The System Under Test

FoodYou (`com.maksimowiczm.foodyou`) is a local-first calorie tracker for
Android, written in Kotlin with Jetpack Compose. It holds nutrition and diary
data in a Room-managed SQLite database (`databases/open_source_database.db`).
Two data sources exist inside the app's search screen:

- **The Swiss Food Composition Database** — 1,190 real products imported from
  a CSV bundled inside the APK. Local, offline, deterministic.
- **Open Food Facts (OFF)** — a live, crowd-sourced product database fetched
  over the network. The only source the specification allows to fail.

Both are filtered views over the *same* `Product` table (`sourceType` column),
confirmed from the app's own source — not separate stores, which matters for
the model: a three-way USER/SWISS/EXTERNAL split was tried early and reverted
because the specification treats user-added and imported rows identically, so
the distinction bought state-space cost with no test power.

Being Jetpack Compose, the UI exposes **no resource-ids** on interactive
controls. Every concrete selector in this project is text or content-desc
based, and several selectors had to be hardened twice against a search field
that echoes the typed query back as a `TextView`-adjacent node (see §7.9).

---

## 3. The Formal Model

### 3.1 Composition

```lnt
process SPEC [...] is
    par EXTAPI_FAIL, UE1_KILL, DISRUPTION_DB, DB_CORRUPT, STORAGE_FULL,
        STORAGE_MEDIA, CACHE_STALE in
        par SEARCH_FOOD, FOOD_INFO, ADD_ENTRY, CONFIRM_TOTAL, VIEW_DIARY,
            DIARY_INFO, REMOVE_ENTRY, EXTAPI_WARNING, DB_CORRUPT_DETECTED,
            STORAGE_ERROR_SHOWN in
            USER [...] || (APP [...] || DATABASE [...])
        end par
        ||
        par NETWORK_DEGRADED in
            DISRUPTOR [EXTAPI_FAIL, NETWORK_DEGRADED, UE1_KILL, DISRUPTION_DB,
                       DB_CORRUPT, CACHE_STALE]
            ||
            INFRA_DISRUPTOR [NETWORK_DEGRADED, STORAGE_FULL, STORAGE_MEDIA]
        end par
    end par
end process
```

Five processes, composed with **no `hide` block** — a deliberate, standing
principle of this project ("I do not want to hide anything"). Every internal
protocol gate that a lesser model might tuck away is either folded into the
handshake structure directly or, where it names something the user can
actually observe on screen, promoted to a real synchronization gate that
`USER`, `APP`, and `DATABASE` all rendezvous on. `FOOD_INFO`, `CONFIRM_TOTAL`,
and `DIARY_INFO` are exactly this: `DATABASE` is the authoritative source for
each, `APP` mediates, `USER` receives. Nothing is invented at a layer that
does not own it.

`DISRUPTOR` and `INFRA_DISRUPTOR` are unconstrained choice processes — each
loop offers either an internal `i` (nothing happens) or one of its faults, so
*when* a fault fires is left entirely to the composition with the test
purpose, never hard-coded into `SPEC` itself:

```lnt
process DISRUPTOR [EXTAPI_FAIL, NETWORK_DEGRADED, UE1_KILL, DISRUPTION_DB,
                    DB_CORRUPT, CACHE_STALE : none] is
    loop
        alt i [] EXTAPI_FAIL [] UE1_KILL [] DISRUPTION_DB [] DB_CORRUPT
        []  CACHE_STALE end alt
    end loop
end process
```

### 3.2 The saturating `DailyTotal` band

Modelling calories as `Nat` makes the LTS infinite. `DailyTotal` is instead a
five-value band:

```lnt
type DailyTotal is EMPTY, LOW, MODERATE, HIGH, OVER with == end type

function bump (t : DailyTotal) : DailyTotal is
    case t in
        EMPTY -> return LOW | LOW -> return MODERATE
      | MODERATE -> return HIGH | HIGH -> return OVER | OVER -> return OVER
    end case
end function

function drop (t : DailyTotal) : DailyTotal is
    case t in
        EMPTY -> return EMPTY | LOW -> return EMPTY
      | MODERATE -> return LOW | HIGH -> return MODERATE | OVER -> return HIGH
    end case
end function
```

`OVER` saturates — `bump(OVER) = OVER` — which makes `drop` ambiguous exactly
at the top: removing one entry from "four or more" leaves "three or more,"
which could be `HIGH` or still `OVER`, and the model has no way to know which
without counting past what the band represents. `DATABASE`'s `REMOVE_ENTRY`
branch resolves this the only sound way — by **not** resolving it:

```lnt
if total == OVER then
    alt total := HIGH [] total := OVER end alt
else
    total := drop (total)
end if;
```

This is not a workaround; it is the correct application of ioco's own
semantics. A specification may permit several outputs after a given trace,
and a conformant SUT may produce any of them — only an output outside that
set is a violation. Committing to `HIGH` (the naive reading of `drop`) is a
guess, and the guess was live-tested wrong: 2026-08-13, six entries logged,
one removed, the app correctly showed 620 kcal (`OVER`), and the earlier
single-valued model insisted on `HIGH` and reported a counter-example that
did not exist. Below `OVER`, `drop` stays exact — only the saturating rung
needs the nondeterministic offer.

### 3.3 Where the fixture lives in the types

```lnt
type FoodId is food_peanut, food_butter, food_oil with == end type
```

Three real Swiss Food Composition Database products — Peanut butter
(636 kcal/100g), Cooking butter (745), Corn germ oil (900) — chosen for three
properties verified against the device, not assumed: each search query
matches exactly one product ("Almond" and "Olive oil" were rejected for
matching several); the three energies are far enough apart that a total
cannot come out right by coincidence; and `food_oil` at 900 kcal/100g is high
enough that three logged portions (2,700 kcal) cross the 2,000 kcal daily
goal with a 17 kcal margin either side of the boundary — tight enough that a
rounding slip or a double-counted entry would cross it. An earlier fixture
topped out near 620 kcal and could never reach the over-goal branch at all;
that branch was dead code in the test suite until this fixture replaced it.

The calorie values themselves are **not injected as constants**. `Calorie` is
an opaque token type (`kcal_peanut`, `kcal_butter`, `kcal_oil`); the
concretizer treats the displayed number as an *observed* value and checks it
for consistency (same food → same number) and, where a fault should have
changed it, against the app's own `Product` table — never against a number
the fixture invented. Injecting `CALORIE(636)` would mean re-implementing
FoodYou's own nutrition database inside the test harness; the calorie is the
app's data, not the model's prediction.

---

## 4. The Disruption Taxonomy

| Layer | Gate | Timing | Mechanism | Injection |
|---|---|---|---|---|
| App | EXTAPI_FAIL | gate | connectivity | `svc data disable ; svc wifi disable` |
| User/Env | UE1_KILL | gate | adb | `am force-stop {pkg} ; am start -n {pkg}/.MainActivity` |
| Database | DISRUPTION_DB | gate | sqlite | `CREATE TRIGGER ... BEFORE INSERT ... RAISE(ABORT, ...)` |
| Database | DB_CORRUPT | pre | sqlite | `UPDATE Product SET energy = NULL WHERE name IN (...)` |
| App | CACHE_STALE | pre | sqlite | `UPDATE Product SET energy = 999 WHERE name IN (...)` |
| Infra | STORAGE_FULL | gate | adb | ballast file sized from live free space, 20 MB headroom |
| Infra | STORAGE_MEDIA | gate | adb | `chmod 0000 {db} ; force-stop ; relaunch` |
| User/Env | INPUT_INVALID | none | none | driven by the SI itself (empty amount field) |

`UE1_KILL`, `DISRUPTION_DB`, and `STORAGE_FULL` used to be **the same
byte-identical SQL under three names** — `DELETE FROM Measurement`, which
erases the diary and drives the total to `EMPTY`, directly contradicting the
specification's own requirement that an aborted write leave the total
*unchanged*. That would have failed all three purposes for a reason the app
never caused. Rewritten 2026-08-23 into three genuinely independent
implementation paths — process kill, SQL trigger abort, filesystem
exhaustion — stressing the same requirement from three different layers.

---

## 5. The Generation Pipeline

Model source lives in five LNT files (`foodyou_types`, `specification_
foodyou_copy`, `system_interface_foodyou_copy`, `compose_foodyou_copy`, and
one `tp_<purpose>.lnt` per test purpose) and is compiled on a licensed CADP
node (`narval3`, `CADP=/home/paulad/cadp`) — this Mac's CADP install has
`tgv.a` but no `testor.a`, so generation cannot happen locally. Per purpose,
`generate_all.sh` runs the ioco derivation in three steps:

```
1. tp_X.lnt          -> tp_X.bcg    (TP_ACCEPT -> ACCEPT, TP_REFUSE -> REFUSE)
2. COMPOSED x tp_X.bcg  -> tc_X.bcg   (on-the-fly test-case derivation, testor -io)
3. tc_X.bcg           -> tc_X.aut    (what the Python graph walker actually reads)
```

The script guards against the failure mode that matters most here: an
**empty test case**. If a test purpose over-constrains the specification, the
product of `COMPOSED` and `tp` is empty, `testor` still exits cleanly, and
`bcg_io` still writes a well-formed `.aut` with 0 transitions — nothing
downstream notices, and the purpose silently contributes zero coverage while
looking present in a directory listing. `generate_all.sh` reads the `.aut`
header (`des (init, transitions, states)`) and refuses to call a 0-transition
result a success; this project treats an empty test case as a finding about
the model, never a purpose to quietly drop.

### The engineering story generation actually produced: sibling leakage

The three write-abort purposes (`disruption_db`, `storage_full`, `ue1_kill`)
each fire their fault as a **sibling of a successful commit** inside
`DATABASE`'s own `alt`:

```lnt
ADD_ENTRY (?meal, ?fid, ?amount_ok);
if amount_ok == VALID then
    alt
        total := bump (total); CONFIRM_TOTAL (COMMITTED, total, fid)
    []  UE1_KILL;      CONFIRM_TOTAL (ROLLED_BACK, total, fid)
    []  DISRUPTION_DB; CONFIRM_TOTAL (ROLLED_BACK, total, fid)
    []  STORAGE_FULL;  CONFIRM_TOTAL (ROLLED_BACK, total, fid)
    end alt
```

A minimal-style test purpose that only names its own target fault leaves the
*other* two abort faults — and the plain commit — reachable as
`otherwise`-style branches, and the walker (which is controllable and free to
pick among alternative inputs) would wander into a sibling instead of the
fault under test. The fix, visible directly in `tp_disruption_db.lnt`, is a
**staged, nested `disrupt`**:

```lnt
disrupt
    SEARCH_FOOD (IDF, LOCAL); FOOD_INFO (IDF, ?any Calorie);
    ADD_ENTRY (BREAKFAST, IDF, VALID);
    disrupt
        CONFIRM_TOTAL (COMMITTED, ?any DailyTotal, IDF);
        loop TP_REFUSE end loop
    by
        DISRUPTION_DB;
        CONFIRM_TOTAL (ROLLED_BACK, ?any DailyTotal, IDF);
        loop TP_ACCEPT end loop
    end disrupt
by
    alt EXTAPI_FAIL [] UE1_KILL [] DB_CORRUPT [] STORAGE_FULL [] STORAGE_MEDIA
    []  CACHE_STALE end alt;
    loop TP_REFUSE end loop
end disrupt
```

The inner `disrupt` pins the choice between "commits" and "this specific
fault"; the outer `disrupt` explicitly refuses every *other* fault (all six
of the remaining seven, this purpose's own excluded) rather than leaving them
to fall through to an implicit `otherwise`. **Every purpose in this project
follows this two-level shape** — a lesson paid for once, in the write-abort
trio, and applied everywhere else afterward. The one purpose that looks
different, `tp_input_invalid`, has no inner `disrupt` at all: `INPUT_INVALID`
is not a gate but a parameter of `ADD_ENTRY` itself (`Validity`), so its
accept path is linear by construction and all seven gate-level faults are
simply refused as a flat sibling set.

A second, orthogonal lesson from generation: **every off-target branch in a
test purpose must lead to `TP_REFUSE`, never fall through to an implicit
"otherwise."** `tp_happy` leaked twice during development — once via
`SEARCH_FOOD (EXTERNAL)` (the walker tapped "Open Food Facts," which the
fixture cannot satisfy), once via `ADD_ENTRY (INVALID)` (the walker typed an
empty amount, found Save disabled, and failed) — both because those branches
stayed PASS-reachable and the pass-steering walker chose them. Fixed by
refusing both explicitly. The generated `.aut` file still *contains* those
concrete steps (they precede the point of refusal); what changed is that
they now dead-end in `TP_REFUSE` rather than remaining a live path to
`:PASS:`. Grepping an `.aut` for a step's presence is therefore never a valid
correctness check on its own — only re-running the walk against a real
device is.

---

## 6. The Concretization Layer

The System Interface (`system_interface_foodyou_copy.lnt`) is the bridge
between abstract gates and concrete Appium/UiAutomator2 actions: each abstract
step compiles to a sequence of `tap` / `wait_for` / `observe` / `enter_text`
primitives against selectors declared in `concrete_domain.yml`, resolved by
`framework/concretization/si_lnt_parser.py` and executed by
`AndroidExecutor` (`framework/concretization/executors.py`). The Python graph
walker (`framework/concretization/algorithm.py`) reads the generated `.aut`,
picks a controllable path toward `:PASS:` when alternatives exist, and drives
the device state by state — this is the literal mechanism behind every
"the app was asked to..." sentence in this note; nothing here is a black-box
"we ran the test suite."

Fault injection happens **out of band**, never through the UI:
`AndroidFaultInjector` (`framework/concretization/fault_injector.py`) reads
`disruption_mapping.yml` and, at the moment the walker reaches a fault's gate
(`timing: gate`) or before the walk starts (`timing: pre`), issues the
`adb`/`sqlite3` command directly against the device. `restore()` undoes every
active injection in LIFO order when the run ends, in a `finally` block, so a
crashed run cannot leave the device in a state that poisons the next one.

### `manifested()` — the dynamic verdict correction

A fault gate being *reached* in the abstract trace does not guarantee the
fault actually *took effect* on the device — timing, permission quirks, and
already-open file handles can all silently defeat an injection.
`manifested(target)` reads the SUT's own state back (a schema probe for
`DISRUPTION_DB`'s trigger, a file-existence probe for `STORAGE_FULL`'s
ballast, a file-mode probe for `STORAGE_MEDIA` as of today — see §7.7) and
returns `True`, `False`, or `None` ("can't tell"). This is not a hard-coded
verdict table; it is a live, self-correcting check: if the SUT or the
injection mechanism changes, the answer changes with it, because it is
answered from the device, not asserted from the harness.

---

## 7. Purpose by Purpose — Specification, Generation, Concretization

For each purpose: what the specification requires, what generation needed to
get right, how the fault reaches the device, and the measured result as of
this writing.

### 7.1 `happy` — the baseline

**Specification.** No `disrupt` — `USER`'s plain `alt` branch for
`ADD_ENTRY`/`CONFIRM_TOTAL` walked with every fault process free to interject
`i` (nothing) at will. `tp_happy.lnt` accepts the nominal
search→info→add→confirm sequence and refuses if *any* of the eight faults
fires during it.

**Generation.** The two leak fixes described in §5 (EXTERNAL search,
INVALID amount) both surfaced here first, because `happy` is the purpose most
likely to wander off-path when nothing constrains it toward a specific
outcome.

**Concretization.** `SEARCH_FOOD` compiles to: tap the search bar
(`el_search_input`, a content-desc "Search" view — confirmed live that no
`EditText` exists until the bar itself is tapped), type the product name,
press `KEYCODE_ENTER`, wait for a result row. `ADD_ENTRY` taps the meal's
"Add" content-desc button, fills the (already-defaulted 100 g) quantity,
taps Save. `CONFIRM_TOTAL` observes `el_daily_total`
(`textMatches("\d+ / \d+ kcal")`) on Home.

**Measured: 90 PASS, 13 FAIL, 1 UNEXECUTABLE (104 cases).** The 13 FAIL are
part of the 70-case EXTERNAL-branch reclassification (§8.2) — a walk that
selected `SEARCH_FOOD (EXTERNAL)` for a Swiss-only product and received a
confirmed, stable zero-result state where the specification demanded
`FOOD_INFO`.

### 7.2 `input_invalid` — validation, not a gate

**Specification.** Carried entirely by `ADD_ENTRY`'s `Validity` parameter:

```lnt
ADD_ENTRY (?meal, ?fid, ?amount_ok);
if amount_ok == VALID then ... else CONFIRM_TOTAL (REJECTED, total, fid)
end if
```

`total` on the rejected branch is the value from *before* the attempt — the
specification requires the total to be untouched by a refused write, not
merely "still a valid band value."

**Generation.** No inner `disrupt` is needed (§5) — the accept path is linear
and all seven gate-level faults are refused as one flat sibling set.

**Concretization.** The originally-hypothesized observable — an inline
"Invalid amount" error marker — was disproved live 2026-08-11: FoodYou
renders no such text for `""`, `"0"`, or `"abc"`. It refuses by **withdrawing
the Save control** instead (content-desc "Save" absent, keyboard still up).
`cv_qty_invalid = ""` (an explicit clear, not a no-op — `_enter_text` used to
`send_keys` without clearing first, silently testing a *valid* 100 g default
instead of an invalid one, fixed 2026-08-10). The oracle checks the stronger
property directly: the daily total is unchanged, via the exact-sum ledger
(§8.1), not a UI string match.

**Measured: 73 PASS, 11 FAIL, 2 UNEXECUTABLE (86 cases).**

### 7.3 `cache_stale` — "the sharpest of the eight"

**Specification.** Placed *before* the read, not as an interrupt of it — the
one purpose whose accept path is genuinely linear in the base model, not
staged around a sibling:

```lnt
CACHE_STALE; SEARCH_FOOD (?fid, LOCAL); FOOD_INFO (fid, ?kcal)
```

**Generation.** Straightforward — the fault fires unconditionally before the
search, so no sibling-leakage staging was needed.

**Concretization.** `pre`-timed: `UPDATE Product SET energy = 999 WHERE name
IN (...)` runs once before the walk, so the drift is already in place at
first read. The observable is not a dedicated UI marker — it is the
`FOOD_INFO` oracle itself, which compares the app's displayed kcal against
the **authoritative value read from the app's own `Product` table**, not
against the drifted number the fixture wrote. This is deliberately the
strictest oracle in the suite: every other purpose asks whether the app
*reports a failure*; this one asks whether the number it reports is *true*.

**Measured: 42 PASS, 3 FAIL, 3 UNEXECUTABLE (48 cases).** Every FAIL here is
a genuine, reproducible counter-example — FoodYou never revalidates a
drifted stored energy against anything; it serves the cache as-is.

### 7.4 `db_corrupt` — detection, not repair

**Specification.** An interrupt of the local lookup:

```lnt
disrupt SEARCH_FOOD (?fid, LOCAL); FOOD_INFO (fid, ?kcal)
by      DB_CORRUPT; DB_CORRUPT_DETECTED end disrupt
```

**Generation.** The test purpose mirrors the model's own freedom about
*which side* of `SEARCH_FOOD` the interrupt lands on, rather than pinning a
position the specification leaves open — visible directly in the two-branch
`alt` inside `tp_db_corrupt.lnt`'s inner `disrupt`.

**Concretization.** `pre`-timed `UPDATE Product SET energy = NULL WHERE name
IN (...)`. `el_corrupt_error` (`textContains("missing required fields")`) was
originally expected to time out — the working hypothesis was that FoodYou
trusts its Room DB unconditionally. **Confirmed live 2026-07-27: it does
not.** The app detects the NULL field and shows "Food is missing required
fields" in the results list, without ever rendering a fabricated calorie.

**Measured: 0 PASS, 40 FAIL, 0 UNEXECUTABLE (40 cases).** Every one of these
40 FAILs needs to be read against §10 below — the detection itself is
resilient, and the FAIL count here is *not* "the app fails to detect
corruption." It is measuring something narrower and stranger: see §10.

### 7.5 `disruption_db` — home of v47

**Specification.** Staged exactly as shown in §5 — the write-abort trio's
canonical shape.

**Generation.** The sibling-leakage fix (§5) was discovered and fixed here
first, then applied to `storage_full` and `ue1_kill`.

**Concretization.** `DISRUPTION_DB` is a real SQL trigger:
`CREATE TRIGGER IF NOT EXISTS fault_abort_write BEFORE INSERT ON Measurement
BEGIN SELECT RAISE(ABORT, 'injected transaction abort'); END`, dropped on
restore. `manifested()` probes `sqlite_master` for the trigger's presence —
directly probeable, so this is the one write-abort fault whose manifestation
can be confirmed with certainty rather than inferred.

**Measured: 7 PASS, 100 FAIL, 2 UNEXECUTABLE (109 cases).** See §4 of
`HANDOVER.md` and §8.1 below: **v47 is the only one of these FAILs that
tested what the purpose actually claims to test**, and it is the most
important single result in the whole campaign.

### 7.6 `storage_full` — least certain of the three

**Specification.** Same staged shape as `disruption_db`. The purpose file
carries its own warning, worth quoting directly because it turned out to be
prescient:

> "NOTE for the concretization layer: this fault, DISRUPTION_DB and UE1_KILL
> have historically been injected with byte-identical SQL, and none of them
> actually failed a write. Verify the injector distinguishes them before
> quoting any verdict from this purpose — a fault that does not manifest
> makes the run INCONCLUSIVE, not PASS."

**Generation.** No purpose-specific hurdle beyond the shared staging fix.

**Concretization.** A ballast file sized from *live* free space
(`dd if=/dev/zero ... count=$((FREE-20480))`), leaving 20 MB headroom so the
rest of Android keeps running. `manifested()` probes for the ballast file's
existence directly, not for a failing write — an earlier version tried a
throwaway `CREATE TABLE`/`DROP TABLE` and treated its success as "fault did
not bite," which was wrong: 20 MB is ample room for a tiny table, so the
probe reported the disk not full while it in fact was (`storage_full` v14,
2026-08-23, fixed today by the same ballast-existence check as this
project's rewrite).

**Measured: 7 PASS, 95 FAIL, 7 UNEXECUTABLE (109 cases).** Subject to the
same timing caveat as `disruption_db` — see §8.1.

### 7.7 `storage_media` — resolved 2026-09-02

**Specification.** An interrupt of the diary read, with a prefix that logs
one entry first (a read needs something to read):

```lnt
disrupt VIEW_DIARY (IDE); DIARY_INFO (IDE, IDF)
by      STORAGE_MEDIA; STORAGE_ERROR_SHOWN end disrupt
```

**Generation.** `IDE` is pinned to `entry_2` because `food_of(entry_2) =
food_oil = defaultF`, keeping one food threaded through the whole trace so
the oracle can correlate what it observes against a single authoritative
value.

**Concretization — three real bugs, found and fixed across this project's
history and this session specifically:**

1. **Open-fd no-op (fixed 2026-08-23).** `chmod 0000` alone does nothing to
   an already-open file — permissions are checked at `open()`, and FoodYou
   holds the database open for its whole process lifetime. The injection now
   force-stops and relaunches the app after the chmod, forcing a fresh
   `open()` against the now-unreadable file. Confirmed live: FoodYou shows a
   full-screen error boundary, "Oops! Something went wrong" plus the
   `SQLiteCantOpenDatabaseException` stack trace — not garbage data, not a
   silent stall, not an OS crash dialog.
2. **Self-defeating detector (fixed 2026-09-01, confirmed live 2026-09-02).**
   `manifested()`'s old probe queried `SELECT ROWID FROM Measurement LIMIT 1`
   through the *same* channel the chmod blocks — under mode `0000` the read
   errors and the probe returns "can't confirm," meaning the fault disabled
   its own detector. Replaced with a `stat -c %a`-based probe: `stat` reads
   inode metadata via a directory lookup, not a file `open()`, so it survives
   the chmod and can confirm the injection directly. Confirmed working
   against the live device in the completed sweep: 2 of the 144 cases were
   reported `manifested()`-`False` ("STORAGE_MEDIA did not manifest
   (precondition absent / injection no-op)") — the probe correctly detecting
   a real non-bite rather than defaulting to "can't tell."
3. **Restore-permission drift, and a claimed second bug that turned out not
   to exist.** `disruption_mapping.yml` restores to `0660` (matching Android's
   own creation mode), correcting an earlier bug where restore dropped to
   `0600` and lost the group bit across successive runs — confirmed fixed by
   inspection of the current file. A second claimed bug, that the exact-total
   oracle also reads the DB live under this fault, was **checked against the
   current code today and found to be false**: `_authoritative_now` only
   performs a live read when the target fault is `CACHE_STALE`; for every
   other fault, including `STORAGE_MEDIA`, it returns `None` immediately and
   the oracle falls back to the static declared fixture value. This was
   apparently already fixed by an earlier, undocumented change, and the
   stale diagnosis had not been re-checked before today.
4. **All 144 cases initially failed to reach the device**, for a reason
   unrelated to any of the above: `env.sh` pointed the Appium client at port
   4725; the live Appium server was on 4723 (fixed 2026-09-01, confirmed by
   `lsof`).
5. **The re-run was then blocked a second time** by a false-negative
   environment check — see §8.4. Fixed 2026-09-01; `check_env.sh` now
   reports `READY` against the live device.

**Measured (2026-09-02, live device, 144/144 cases completed): 58 PASS, 83
FAIL, 3 UNEXECUTABLE.** All five bugs above are fixed in code and confirmed
working against the real sweep, not just reasoned about:

- **1 UNEXECUTABLE** is a genuine apparatus failure unrelated to any of the
  five bugs — v47's log ends in a raw `ConnectionResetError` from the Appium
  session mid-run, the same class of harness flakiness already logged for
  `storage_full` (§6, harness re-run list).
- **2 UNEXECUTABLE** are `manifested()` correctly reporting the fault did
  not take (bug 2's fix working as intended, not a new problem).
- **72 raw FAIL**, plus **11 of the raw 13 INCONC-labeled runs**, which hit
  the identical EXTERNAL-branch empty-search signature established in §8.2
  (`Tapped ... "Open Food Facts"` immediately followed by a confirmed empty
  result) — reclassified to FAIL under the same rule and same evidence
  pattern as the original 70-case reclassification, for a total of **83
  FAIL**. Individual capture-by-capture visual re-confirmation was not
  repeated for all 11 — the log signature is identical to the mechanically
  verified pattern from §8.2, and that pattern's mechanism (a Swiss-only
  fixture searched against Open Food Facts) is structural, not
  case-specific.
- **58 PASS.** Not yet separately audited for how many sit at an
  unfalsifiable band the way §9's write-path passes are — flag this if it
  matters before this number is quoted as clean evidence of resilience.

### 7.8 `ue1_kill` — process layer

**Specification.** Same staged write-abort shape.

**Generation.** Shared the staging fix with `disruption_db`/`storage_full`.

**Concretization.** `am force-stop {pkg} ; am start -n {pkg}/.MainActivity`.
FoodYou reopens on Home — exactly where the next modelled step expects to be
— so the walk continues without a separate recovery branch.
`manifested()` returns `None` unconditionally for this fault: the kill is
transient by nature (the process is gone and immediately relaunched, so by
the time anything could probe, the evidence of the in-flight write's fate is
gone too). The check that matters is the invariant at the verdict: does the
displayed total equal the sum of rows actually in the database, not a
separate manifestation probe.

**Measured: 8 PASS, 98 FAIL, 2 UNEXECUTABLE (108 cases).** Subject to the
same §8.1 timing caveat.

### 7.9 `extapi_fail` — measured 2026-09-02

**Specification.** An interrupt of the external lookup:

```lnt
disrupt SEARCH_FOOD (?fid, EXTERNAL); FOOD_INFO (fid, ?kcal)
by      EXTAPI_FAIL; EXTAPI_WARNING end disrupt
```

**Generation.** The test purpose's own header comment states the coverage
problem directly, and is worth quoting in full because it is the earliest
documented instance of a finding this campaign re-derived independently,
months later, at 70-case scale (§8.2):

> "NOTE on coverage: with the present fixture this purpose cannot reach a
> verdict. Every branch searches `defaultF = Corn germ oil`, a Swiss Food
> Composition Database product that returns 0 results from Open Food Facts —
> confirmed by the app's own source count and by the catalogue API. Until the
> external branch is pointed at a product the catalogue carries, runs of
> this purpose are INCONCLUSIVE by construction, not PASS."

Read against §1: this is a test-purpose author's *expectation*, written in
July, before the controllability check in §1.3 existed. It predicts exactly
what §8.2 later confirms mechanically at scale — a structurally-guaranteed-
empty EXTERNAL search — but reaches for "INCONCLUSIVE" as the label, which
this campaign's settled semantics (§1.1) does not have. Read it as
predicting UNEXECUTABLE-by-construction; §8.2 explains why the supervisor's
ruling instead makes the confirmed cases FAIL.

**Concretization.** `svc data disable ; svc wifi disable`, restored on the
normal path only — which is itself a hazard: an interrupted run leaves the
emulator permanently offline for every later purpose until someone notices.
`el_extapi_warning` (`descriptionContains("warning")`) was never confirmed
against a real triggered warning banner before this run — and the run's own
result, confirmed 2026-09-03 against all 34 of its own live captures, shows
there is no such banner to confirm against (below).

**Measured (2026-09-02, live device, 45/45 cases completed): 0 PASS, 45
FAIL, 0 UNEXECUTABLE.** Two different signatures inside that FAIL count,
not one:

- **11 FAIL** — the coverage gap the purpose's own author predicted in July
  (quoted above), confirmed mechanically: the walker never even reaches the
  `EXTAPI_FAIL` gate; it dies earlier on the same structurally-guaranteed-
  empty EXTERNAL search as the other 81 reclassified cases in this
  campaign (§8.2). Reclassified to FAIL by the same established rule, not
  a new judgment call.
- **34 FAIL** — a different shape: `EXTAPI_FAIL` genuinely fires, then the
  walker times out waiting for `el_extapi_warning`. **RESOLVED 2026-09-03:**
  checked the live capture (accessibility-tree XML and screenshot) recorded
  at the exact timeout moment for all 34 cases, not a sample. Every one
  shows the same food-search screen, the "Open Food Facts" source chip
  reading "0" styled identically to every other source chip, and no
  warning/error text or icon anywhere in the tree or on screen. The selector
  was never pointed at the wrong string — there is no element for any
  selector to find. FoodYou renders "external API unreachable" identically
  to "external API legitimately found nothing." **These 34 are a confirmed
  app-level finding**, not a tooling artifact; no re-run is possible or
  needed. Full discussion: `THREATS_TO_VALIDITY.md` §1.

The model-level coverage gap the purpose's own author named is confirmed,
not just predicted: with the current fixture, this purpose's accept path
(a genuine external PASS) is structurally unreachable, only its refuse
paths are — which is exactly why every one of the 45 measured cases came
back FAIL and none came back PASS.

---

## 8. Cross-Cutting Findings

### 8.1 The write-path numbers are weak, and one case shows why

`UE1_KILL`, `DISRUPTION_DB`, and `STORAGE_FULL` all use `timing: gate`: the
fault fires when the `ADD_ENTRY` gate is reached, by which point the concrete
UI steps have already completed and **the write has already committed**. The
total rises, the specification expected `ROLLED_BACK`, and the verdict is
recorded FAIL — but nothing was actually disrupted. **256 of the 293 combined
FAILs across these three purposes are in this position.**

One case is the exception, and it is the most important single result in the
campaign. `disruption_db` v47:

```
1116  checkpoint ADD_ENTRY — advance      <- an entry commits
1117  DISRUPTION_DB injected               <- trigger armed
      ... a LATER insert hits the armed trigger ...
1378  Element not found: "Go back|Close sheet"
```

The tester could not find "Go back" because FoodYou had replaced its entire
UI with its own error boundary:

```
Oops! Something went wrong
android.database.sqlite.SQLiteConstraintException: injected transaction abort
    (code 1811 SQLITE_CONSTRAINT_TRIGGER)
  at MeasurementDao_Impl.insertMeasurement
  at RoomFoodDiaryEntryRepository.insert
  at CreateFoodDiaryEntryUseCase.createDiaryEntry
```

Verified mechanically: `grep -l SQLITE_CONSTRAINT_TRIGGER` matches exactly
**one** file across all 748 cases. v47's own `Verdict:` line already reads
`FAIL` — it is counted correctly in the 360 total. What is still wrong is
narrative, not arithmetic: a separate root-cause annotation layer
(`classify_failure.py`) labels it ARTIFACT because "element not found" looks
like a tester defect from the outside, when it is a direct consequence of
the app crashing. The specification requires `CONFIRM_TOTAL (ROLLED_BACK,
...)`; the app produced no output at all — it crashed to a stack trace.
Quiescence where an output was required, exactly as the specification
defines a violation, and the *only* one of 257 write-abort cases where the
fault actually reached the write it claims to test.

**Fix, not yet applied:** re-time the three write-abort faults in
`disruption_mapping.yml` so each arms *before* the add rather than at the
gate. Concretization-layer only; no CADP regeneration needed. Expected
effect: the character of the result changes substantially, from a timing
artifact to a genuine resilience measurement with the app's own DAO
appearing in the trace, the way v47 already shows.

### 8.2 The empty-search reclassification, and a documented tension resolved today

Section §1 of `HANDOVER.md` records a decision, settled with the project's
supervisor: `SEARCH_FOOD (?fid, SRC); FOOD_INFO (fid, ?kcal)` is a sequential
composition with **no alternative branch** — the specification asserts
unconditionally that a search is followed by food information, so a
confirmed "no results" state is quiescence where an output was required, and
that is a FAIL, regardless of which source was searched. §1 of this note
gives the same conclusion its generation-side foundation: there is no
`FOOD_ABSENT` output in the specification, so there is nothing for a
confirmed empty search to be inconclusive on — the extraction check in §1.3
confirms no such output-reached ambiguity exists anywhere in the eight
checked CTGs.

This directly reverses an earlier working hypothesis — mine, checked and
corrected in this same session before being written down — that an
EXTERNAL-branch search for a Swiss-only product was an unfalsifiable
"coverage gap" and should stay UNEXECUTABLE. The correction, stated by the
project's supervisor directly: **ioco verdicts are with respect to the
specification and the observed trace, not with respect to whether the
tester feels the fixture was fair to the SUT.** The specification does not
carve out an exception for a search that was destined to fail structurally;
if the app's own screen shows a stable, confirmed "no results" state, that
is an output the specification forbids, full stop.

Interestingly, `tp_extapi_fail.lnt`'s own header comment (§7.9) argues the
*opposite* conclusion for its own purpose — "runs of this purpose are
INCONCLUSIVE by construction, not PASS" — written by an earlier stage of
this same project, for the identical underlying phenomenon (a Swiss-only
product searched against Open Food Facts). Both readings are internally
coherent; they differ on whether a structurally-guaranteed-empty search is a
fact about the specification's silence or a fact about the fixture's
limitation. This note adopts the supervisor's ruling — spec-relative, not
fixture-sympathetic — as the standing decision, and records the earlier
position here rather than deleting it, because the tension is real and a
future model change (pointing the external branch at a product Open Food
Facts actually carries) would resolve it more thoroughly than either verdict
does today.

**Mechanically verified, not estimated:** of 87 logs across seven purposes
carrying no real verdict (raw `INCONC` or no verdict line at all), exactly
**70** hit an identical signature — `Tapped ... "Open Food Facts"`
immediately followed by an `el_search_results` timeout. The screenshot at
each shows the app's own "No food found" message, but that text is **not
present in the UiAutomator accessibility tree** — Compose does not expose it
— so a naive check for the text itself gives a false "unconfirmed." The
reliable, mechanically-queryable signal is the per-source result-count
badge: every one of the 70 XML captures has a bare `"0"` node horizontally
adjacent to the "Open Food Facts" chip, checked by bounds-adjacency rather
than text search. All 70 confirmed and moved to FAIL. The remaining 17 of
the 87 match `HANDOVER.md`'s harness re-run list exactly (step-budget and
apparatus failures, unrelated to search).

**A standing gap this exposed, not yet closed:** the count-badge check
exists only as a one-off post-hoc audit of saved captures. It should become
a real selector in `concrete_domain.yml` (structural match on chip text plus
adjacent numeral) so a future sweep confirms this mechanically at run time
instead of requiring another capture-by-capture audit.

### 8.3 Evidence chain-of-custody

`_capture_failure` (`executors.py`) wrote every failure screenshot/XML dump
to a single flat directory, `tmp/failure_artifacts/`, named only by
timestamp — no purpose, no variant number, nothing linking a capture back to
the case that produced it. 1,457 files accumulated there over the campaign
with no index. This is very likely why v47's crash sat unnoticed for as long
as it did: the evidence existed, but nothing pointed to it.

Fixed today at the three scripts that drive a sweep
(`run_variants.sh`, `run_matrix.sh`, `investigate_variants.sh`): each now
sets `CONCRETIZATION_DEBUG_DIR` scoped to that specific case's own log
directory before invoking `run.py`. Forward-looking only — the existing
1,457 files are untouched, and the v47 capture this note cites is still at
its original path.

### 8.4 The environment check was testing the wrong protocol

Both `check_env.sh` and `boot_emulator.sh` diagnose device connectivity with
`ping` (ICMP). The Mac this campaign runs from is on `eduroam`, a campus
network that blocks ICMP as policy while leaving real TCP/HTTPS traffic
completely untouched — confirmed directly: `ping 1.1.1.1` failed with 100%
packet loss from the Mac itself, while `curl` to Open Food Facts over HTTPS
returned `200` in the same session, and a raw TCP connection
(`nc -w 5 <host> 443`) succeeded from both the Mac and the emulator, to both
a hostname and a raw IP. **The device was never offline; the check was
asking the wrong question.** A VPN hypothesis was raised, checked directly
(`ifconfig`, `scutil --nc list`, `networksetup`, process inspection), and
ruled out — six active `utun` interfaces belonged to stock Apple system
daemons (`rapportd`, `identityservicesd`), not a VPN client.

Fixed today in both scripts: the two ICMP checks now use `nc -w 5 <host>
443` instead of `ping`, asking whether the port the app actually uses is
reachable rather than whether this particular network happens to permit
ICMP. Re-verified against the live device after the fix — all seven
`check_env.sh` checks pass, `READY`. This was gating re-runs of every
purpose, not only `storage_media`: every purpose's variant set includes
EXTERNAL-branch cases (§8.2), so a false "offline" verdict from this check
would have silently blocked honest re-measurement of any of them on a
network like this one.

---

## 9. The Verdict Matrix

| purpose | PASS | FAIL | UNEXECUTABLE | cases | status |
|---|---:|---:|---:|---:|---|
| happy | 90 | 13 | 1 | 104 | measured |
| input_invalid | 73 | 11 | 2 | 86 | measured |
| cache_stale | 42 | 3 | 3 | 48 | measured |
| db_corrupt | 0 | 40 | 0 | 40 | measured — see §10 |
| ue1_kill | 8 | 98 | 2 | 108 | measured — §8.1 caveat |
| disruption_db | 7 | 100 | 2 | 109 | measured — §8.1 caveat, v47 |
| storage_full | 7 | 95 | 7 | 109 | measured — §8.1 caveat |
| storage_media | 58 | 83 | 3 | 144 | measured — §7.7, resolved 2026-09-02 |
| extapi_fail | 0 | 45 | 0 | 45 | measured — §7.9; 34 of 45 FAIL confirmed 2026-09-03, see below |
| **total** | **285** | **488** | **20** | **793** | |

```
793  =  488 FAIL  +  285 PASS  +  20 UNEXECUTABLE
                                  (17 harness from the 8-purpose sweep
                                   + 3 from storage_media)
```

**`extapi_fail`'s 45 FAIL is not one uniform number.** 11 are the
established empty-search reclassification (same rule, same confidence as
the rest of this table). 34 rest on an unconfirmed selector
(`el_extapi_warning`) and are the least trustworthy entries anywhere in
this matrix — real, measured, and reported, but see
`THREATS_TO_VALIDITY.md` §1 before treating them as a confirmed finding
about the app.

Three qualifications that must travel with this table wherever it is quoted:

- **22 of the 285 passes are unfalsifiable** (`ue1_kill` 8, `disruption_db`
  7, `storage_full` 7 — all at the saturating `OVER` band, where the
  abstraction cannot distinguish a write that landed from one that failed).
  Not evidence of correct behaviour. `storage_media`'s 58 passes have not
  been separately audited for the same problem — see §7.7's caveat.
- **256 of the 293 write-path FAILs did not test the requirement** (§8.1).
  v47 is the one case that did.
- **`storage_media`'s 83 FAIL includes 11 reclassified on the same basis as
  the original 70** (§7.7, §8.2) — the same EXTERNAL-branch coverage-gap
  mechanism, not 11 independently discovered defects.

---

## 10. The One Confirmed Application Defect

Under `DB_CORRUPT`, FoodYou flags *"Food is missing required fields,"*
correctly refuses to display the record's energy — and **still counts its
100 g of fat into the daily total**. The header reads "0 / 2000 kcal — 2000
calories left" beside "Fats 100 / 67 g." It trusts one field of a record it
has itself just declared untrustworthy.

No ioco verdict can express this defect. `DailyTotal` models energy only, so
the abstraction has no vocabulary for fat; the specification's own oracle is
silent on it. It was caught by an oracle operating *below* the abstraction —
`_check_macro_consistency` cross-checks the displayed macros against the
displayed energy using fixed Atwater factors, on values the model never
mentions at all. This is the methodological point this project's paper
should make plainly: **a concretization layer needs oracles of its own, not
only the abstract specification's** — the 40 `db_corrupt` FAILs in the
matrix above are the specification's detection requirement working exactly
as intended (§7.4), and this fat-trust defect is a *separate*, narrower
finding underneath them, caught by different machinery entirely. Evidence:
`figures/db_corrupt_evidence.png`.

---

## 11. Threats to Validity — stated, not buried

- **Single repetition.** The entire 748-case sweep ran once. No flakiness
  measurement exists. A stratified `REPEATS=3` re-run with Wilson intervals
  is planned, not done.
- **Classifier validity unverified.** `classify_failure.py`'s root-cause
  category labels (the ones that mislabeled v47 as ARTIFACT) have not been
  checked against an independent human rater. A Cohen's κ study against
  ~50 hand-labeled cases is planned, not done — and whoever writes the
  classifier should not also be its only rater.
- **17 harness cases never produced a verdict** for apparatus reasons
  (step-budget exhaustion, Appium session death, a weak manifestation
  probe, one empty screen capture) — listed exactly in `HANDOVER.md` §6,
  re-run pending.
- **`extapi_fail` (§7.9) now has real, measured evidence — 45/45 cases,
  and the 34-case selector doubt is resolved (2026-09-03)**: checked
  against all 34 of the run's own live captures, not a sample — FoodYou
  genuinely has no observable for external-API failure. Confirmed finding,
  not a caveat; see `THREATS_TO_VALIDITY.md` §1. `storage_media` (§7.7) has
  no comparable doubt either — 144/144.
- **The `INCONCLUSIVE`-extraction check (§1.3) covers 8 of 9 purposes.**
  `storage_media` has not yet been checked by the same method; the "zero
  output-reached INCONC" claim in §1.4 should be read as covering the eight
  purposes actually checked, not the whole model, until that gap closes.
- **The fixture cannot currently produce a genuine EXTERNAL-branch PASS.**
  Every food in `FoodId` is a Swiss-only product; until the model or the
  fixture is changed to include a product Open Food Facts actually carries,
  `extapi_fail`'s accept path and the EXTERNAL arm of every other purpose
  can only ever refuse or fail, never conform.

---

## 12. Engineering Hurdles, Told As They Happened

**The sibling-leakage story.** The write-abort trio's `alt` puts a
successful commit and three distinct faults as literal siblings inside
`DATABASE`. A test purpose that named only its own target fault left the
walker — which is controllable, and free to pick among alternative inputs —
wandering into a sibling instead. The fix was not a smarter walker; it was
staging the test purpose itself into two nested `disrupt` blocks, the inner
one pinning "commit vs. this fault," the outer one explicitly refusing every
other fault by name rather than trusting an implicit `otherwise`. Paid for
once on `disruption_db`, applied identically to `storage_full` and
`ue1_kill` afterward.

**The `PRAGMA` ghost.** `_scalar()`'s read-only probe used to prefix every
query with `PRAGMA busy_timeout=5000;` to wait out the app's write lock
instead of failing on it. Android's on-device `sqlite3` shell echoes a
`PRAGMA`'s own value back as a result row — so `busy_timeout`'s echo, the
literal string `"5000"`, was masquerading as the query's actual answer.
Dropped the prefix from the read-only path entirely; reads on the WAL-mode
database do not block the way writes do, so it was never needed there.

**The open-fd trap.** `chmod` changes a file's permission bits; it does not
revoke a file descriptor the OS already handed out. FoodYou opens its
database once and holds it open for its whole process lifetime, so `chmod
0000` against an already-running app is a complete no-op — confirmed by
`STORAGE_MEDIA` initially appearing to have no effect on the SUT at all.
Forcing a fresh `open()` (force-stop, relaunch) is what makes the fault
reach the app; the same shape as `UE1_KILL`'s kill-and-relaunch, arrived at
independently.

**The `eduroam` false negative.** Told in full in §8.4. The short version,
for credibility: two environment scripts spent months correctly reporting
"NOT READY" against a campus network that blocks ICMP — for a device that,
checked directly with a real TCP connection, was never actually offline.

**The rejected shortcut.** During the write-abort investigation, a
`same_effect_as_target` classification was proposed — quietly treating a
FAIL caused by the wrong sibling fault as equivalent to a FAIL from the
intended one, on the reasoning that "the effect looks the same." Rejected.
Engineering a favourable-looking verdict by blurring which fault actually
fired is precisely the failure mode this whole framework exists to prevent;
the correct fix was staging the test purpose so the right fault fires in
the first place, not relabeling the wrong one after the fact.

---

## 13. Conclusion

FoodYou is a local-first application whose one architectural strength this
campaign can state with real confidence: **write-path resilience, where
tested honestly, holds.** v47 — the one case in 748 where a write-abort
fault actually reached a live write — shows the app failing loudly and
correctly, to its own error boundary, rather than reporting a false
`COMMITTED`. The other 256 write-path FAILs in this matrix are not evidence
against that claim; they are evidence that the *test*, not the app, arrived
too late to the write it meant to interrupt.

Two genuine, reproducible weaknesses stand on their own evidence, independent
of the timing question: `CACHE_STALE` (the app never revalidates a drifted
stored energy against its own catalogue) and the DB_CORRUPT fat-trust defect
(§10), caught by an oracle the abstract specification has no vocabulary to
express. Both are real findings a formal model alone would not have
surfaced — the second one specifically because it lives *below* the
abstraction, not because the abstraction was wrong.

The verdict scheme itself — `{PASS, FAIL, UNEXECUTABLE}`, no fourth option —
is not a convention adopted for convenience. §1 shows it is a checked
consequence of this specification's own shape: every `INCONCLUSIVE` state in
every generated test graph sits behind a tester-controlled input, never
behind a SUT output, so a controllable extraction was always entitled to
remove it. That is what makes "empty search = FAIL" defensible rather than
harsh, and it is why this note treats the ioco theory underneath the numbers
as load-bearing, not decorative.

What this campaign has *not* yet done, stated as plainly as the results
above: repeated any case to check for flakiness, independently validated
its own failure classifier, extended the §1.3 controllability check to
`storage_media`, or re-timed the three write-abort faults to test what
their purposes claim to test. (The `el_extapi_warning` selector question is
closed as of 2026-09-03 — confirmed against all 34 of its own live
captures that no such observable exists in the app.)

Both `storage_media` and `extapi_fail` are off the "never measured" list —
all 9 purposes have now run, 793/793 cases. What's left is a mix: some of
it needs no device at all (flakiness repeats, classifier validation, the
controllability check), and the `el_extapi_warning` question needs one more
live capture to settle, not a fresh campaign. None of it is done yet. The
strict discipline this project has held throughout — write an honest
specification, observe what the app does, and never engineer a favourable
verdict, in either direction — applies as much to this note's own
limitations as to FoodYou's.

---

## Appendix A — `DATABASE`, in full

See §3.1 for the composition; the process itself, unabridged, is in
`model/specification_foodyou_copy.lnt` lines 156–261. Reproduced here is the
write-path `alt` central to §7.5–7.8 and §8.1:

```lnt
ADD_ENTRY (?meal, ?fid, ?amount_ok);
if amount_ok == VALID then
    alt
        total := bump (total);
        CONFIRM_TOTAL (COMMITTED, total, fid)
    []
        UE1_KILL;
        CONFIRM_TOTAL (ROLLED_BACK, total, fid)
    []
        DISRUPTION_DB;
        CONFIRM_TOTAL (ROLLED_BACK, total, fid)
    []
        STORAGE_FULL;
        CONFIRM_TOTAL (ROLLED_BACK, total, fid)
    end alt
else
    CONFIRM_TOTAL (REJECTED, total, fid)
end if
```

## Appendix B — the fixture's authoritative values

From `foodyou_types.lnt` and cross-checked live against the app's own
`Product` table (`disruption_mapping.yml`'s `DB_CORRUPT`/`CACHE_STALE`
restore commands write these same three numbers back):

| `FoodId` | Product | kcal / 100 g |
|---|---|---:|
| `food_peanut` | Peanut butter | 636 |
| `food_butter` | Cooking butter | 745 |
| `food_oil` (= `defaultF`) | Corn germ oil | 900 |

## Appendix C — `fault_injector.py`, architecture

- `pre_inject(labels)` — fires every `timing: pre` fault whose gate appears
  in the composed `.aut`, before the walk starts.
- `inject_gate(gate)` — fires a `timing: gate` fault the instant its label
  is reached, and only if it is *this* test case's declared target (multi-
  fault `.aut`s carry every fault as a refused sibling branch; injecting an
  untargeted one would poison the run).
- `manifested(target)` — reads the SUT's own state back to answer "did this
  actually take effect," per-fault (schema probe, file-existence probe,
  file-mode probe as of today for `STORAGE_MEDIA`, or `None` where no
  reliable device-side signal exists, e.g. `UE1_KILL`).
- `restore()` — undoes every active injection in LIFO order, in the run's
  `finally` block.

## Appendix D — the generation command, exactly as run

```bash
export CADP=/home/paulad/cadp
export PATH=$CADP/com:$CADP/bin.x64:$PATH
cd /scratch/paulad/testor_foodyou
sh generate_all.sh          # all nine purposes
sh generate_all.sh happy    # one purpose only
```

Per purpose (`generate_all.sh`'s inner loop):

```bash
lnt.open -main MAIN -silent "tp_${name}.lnt" generator \
    -rename accept.ren -rename refuse.ren "tp_${name}.bcg"

lnt.open -main COMPOSED compose_foodyou_copy.lnt "$TESTOR" \
    -io foodyou.io "tp_${name}.bcg" "tc_${name}.bcg"

bcg_io "tc_${name}.bcg" "tc_${name}.aut"
```

The third line's output, `tc_<purpose>.aut`, is the only artifact the Python
graph walker ever reads. Everything upstream of it is CADP; everything
downstream of it is this project's own code.

## Appendix E — reproducing the §1.3 controllability check

```python
# Parse each Test_Cases/tc_<purpose>.aut, collect states carrying an
# :INCONCLUSIVE: self-loop, and tally the labels of transitions entering them.
import re

def check_ctg(path):
    triples = []
    for line in open(path):
        m = re.match(r'\s*\((\d+),\s*"([^"]+)",\s*(\d+)\)', line)
        if m:
            triples.append((int(m.group(1)), m.group(2), int(m.group(3))))
    inconc_states = {dst for src, lbl, dst in triples
                      if ':INCONCLUSIVE:' in lbl}
    incoming = [lbl for src, lbl, dst in triples if dst in inconc_states]
    inputs = [l for l in incoming if 'TAP' in l or 'ENTER_TEXT' in l]
    return len(inconc_states), len(incoming), len(inputs) == len(incoming)
```

Run once per `tc_<purpose>.aut`; the table in §1.3 is this function's output,
unedited, across all eight purposes checked.
