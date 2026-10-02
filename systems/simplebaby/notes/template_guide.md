# The per-SUT template

A new case study starts as a copy of this directory. It gives you a
specification, a System Interface, a fixture, a composition, six test-purpose
shapes, the `.io` file, the three properties files and the generation script,
all agreeing on one alphabet, with every decision you still have to make
marked `HOLE n`. Fill the holes in order, run the checker, generate.

The domain is generic on purpose: an **item** the user selects, a **value**
read back for it, a **write** into a **context** that moves a saturating
**band**, and a persisted **record** that can be opened or removed. That is
the skeleton every case study so far reduces to; TEMPLATE_ANALYSIS.md says
where each one strains it.

## Instantiate

```sh
sh systems/template/new_system.sh <name>          # lowercase; becomes the LNT module prefix
python framework/scripts/check_alphabet.py systems/<name>
grep -rn HOLE systems/<name>                        # what is still open
```

The guide you are reading is copied to `systems/<name>/notes/template_guide.md`.

## Files

| file | what it is | must agree with |
|---|---|---|
| `model/<sut>_types.lnt` | D_abs (types, channels), D_sys (Route / Element / ConcreteValue), L : D_abs -> D_sys | concrete_domain.yml keys, type_description.yml values |
| `model/<sut>_fixture.lnt` | test selection: defaultItem / defaultContext / defaultRecord. Imported by the SI and the purposes, never by the spec | type_description bucket_unit_from, disruption_mapping restore values |
| `model/specification_<sut>.lnt` | USER, APP, DATABASE, DISRUPTOR, SPEC. Flat three-way rendezvous, no hide | its own gate list IS the alphabet |
| `model/system_interface_<sut>.lnt` | process SI: concrete steps first, gate last; `screen` variable; fault injection points and recovery steps | SPEC's alphabet + the five primitives; every el_/cv_/rt_ it uses |
| `model/compose_<sut>.lnt` | COMPOSED = SPEC \|\| SI synchronised on the whole alphabet | SPEC's alphabet |
| `test_purposes/tp_*.lnt` | one MAIN per purpose, full alphabet declared, TP_ACCEPT / TP_REFUSE | file name = target fault lower-cased |
| `test_purposes/accept.ren`, `refuse.ren` | TP_ACCEPT -> ACCEPT, TP_REFUSE -> REFUSE | fixed |
| `testor/<sut>.io` | what the tester controls (inputs); everything else is an output | faults, abstract requests, primitives |
| `testor/generate_tc_all.sh` | CTG + extract_all per purpose, on the licensed node, flat layout | file names above |
| `properties/concrete_domain.yml` | I() of every D_sys value; screen anchors | the SI's el_/cv_/rt_ usage |
| `properties/type_description.yml` | Sampler contract + oracle data (authoritative values, band unit) | the LNT enum values; the fixture default |
| `properties/disruption_mapping.yml` | how each fault is injected and undone | the fault gate names |

## Holes, in the order to fill them

| n | file | decide |
|---|---|---|
| 1 | types | `ItemId`: two or three REAL entries of the SUT's own data, each resolving to one UI row, values spread apart, boundary reachable |
| 2 | types | `Scope`: keep only if the specification says something different per scope; else delete the type and the channel field |
| 3 | types | `Context`: the bucket a write lands in; delete if none |
| 4 | types | `RecordId`: one per item (at most one record per item is the abstraction) |
| 5 | types | `Value`: opaque tokens, one per item; the numbers live in type_description.yml |
| 6 | types | `StateBand`: the saturating band; `bump` / `drop` |
| 7 | types | `value_of` / `item_of`: the authoritative bindings DATABASE answers with |
| 8 | types | SUT-initiated journeys (a reminder, a notification): an output gate that opens a journey |
| 9 | types | `Route`: the entry points `navigate` can reach |
| 10 | types | `Element`: everything wait_for / observe inspects; say which are oracles |
| 11 | types | `ConcreteValue`: everything tap / enter_text targets |
| 12 | fixture | `defaultItem`: the one item every purpose searches and writes |
| 13 | fixture | `defaultContext` |
| 14 | fixture | `defaultRecord`, with `item_of (defaultRecord) == defaultItem` |
| 15 | spec | USER: one branch per journey; the observables the user is owed |
| 16 | spec | APP: where app-layer faults strike and what they owe |
| 17 | spec | DATABASE: interrupts and write-path siblings; the band read back is the UNMOVED one on rollback |
| 18 | spec | DISRUPTOR: every fault always offerable; gated cascades only with an injection of their own |
| 19 | purposes | one file per fault, named `tp_<fault lower-cased>.lnt` |
| 20 | .io | pattern rules: `"GATE .*"` for parameterised gates, `"GATE"` exact for parameterless |
| 21 | generate script | the purpose list |
| 22 | SI | `Screen`: one value per screen the SI must know it is on, `SCR_HOME` first |
| 23 | SI | the search interaction, step by step |
| 24 | SI | where the value is rendered (on the row, or only after opening) |
| 25 | SI | does the SUT return home by itself after a commit |
| 26 | SI | how the SUT refuses an invalid input (error element, or withheld control) |
| 27 | concrete_domain | routes |
| 28 | concrete_domain | elements, each confirmed on the running SUT, against both the present and the absent tree |
| 29 | concrete_domain | concrete values, plus the abstract enum values the SI assigns |
| 30 | concrete_domain | screen anchors: present on that screen, absent on the others |
| 31 | type_description | tester-generated enums |
| 32 | type_description | the authoritative values, verified against the SUT's store |
| 33 | type_description | the band and its unit (must equal defaultItem) |
| 34 | disruption_mapping | the platform block |
| 35 | disruption_mapping | one entry per fault, one mechanism per fault |
| 36 | disruption_mapping | where the SUT caches (or the stale purpose is uninterpretable) |
| 37 | disruption_mapping | the honest expectation per fault, written before the run |

## The fault checklist

One fault name, identical, in six places. The checker verifies all six.

| place | what |
|---|---|
| specification | offered by DISRUPTOR; placed in APP or DATABASE in one of the four shapes; in SPEC's gate list and sync sets |
| System Interface | in SI's gate list; at its injection point, followed by the recovery steps and the observable it owes |
| composition | in COMPOSED's gate list and sync set |
| every purpose | declared; fired in its own purpose's accept path; refused in every other purpose |
| `.io` | an exact `"FAULT"` input line |
| disruption_mapping.yml | a `faults:` key with timing, mechanism, inject, restore |

Fault shapes, and which purpose template mirrors each:

| shape | specification | purpose file |
|---|---|---|
| INTERRUPT | `disrupt <journey> by FAULT; OBSERVABLE end disrupt` | `tp_db_corrupt.lnt` |
| WRITE-PATH | `ADD; alt commit [] FAULT; CONFIRM (ROLLED_BACK, band, id) end alt` | `tp_db_abort.lnt` (nested disrupt) |
| PRE-ARMED | `FAULT; <journey continues nominally>` | `tp_app_cache_stale.lnt` |
| PARAMETER | a channel field the specification routes on | `tp_input_invalid.lnt` |
| any, with a precondition | phase 1 establishes it, phase 2 targets | `tp_infra_storage_media.lnt` |
| none | | `tp_nominal.lnt` |

## Conventions the tooling depends on

- Fault names are `<LAYER>_<WHAT>` with layer in UE, APP, DB, INFRA; the
  observable owed after a fault is `<STEM>_DETECTED | _WARNING | _ERROR`.
- The generated test case is `tc_<fault lower-cased>.aut`; the walker
  derives the injection target from that name. Variants live in
  `variants/<fault>/tc_<fault>.<i>.aut`; variant 1 is copied to the canonical
  name; the per-variant runner installs each under the canonical name for
  its run.
- Purposes export `process MAIN`; the composition exports `process COMPOSED`;
  the SI exports `process SI`.
- In the SI: line comments only; `screen` is the state variable, values
  `SCR_*`, initial `SCR_HOME`; guards are exactly `if screen == SCR_X then`;
  concrete steps precede the gate they realise; `tap (cv_x)` not
  `tap (L_nullary)`; `enter_text` runs from the typed label, the parser
  emits no action for it.
- YAML keys under routes / elements / concrete_values are lower-case and
  equal to the LNT enum value.
- `.io` patterns full-match the label; parameterless gates get no wildcard.
- Verdicts are PASS, FAIL and UNEXECUTABLE. There is no INCONCLUSIVE in a
  result; silence where the specification owes an output is FAIL.

## The pipeline

Generation runs on the licensed CADP node, in a FLAT directory that holds
every input file. Files in subdirectories are never read.

```sh
# push (mac -> node): every module, every purpose, the .io, both .ren, the script
rsync -av \
  systems/<sut>/model/<sut>_types.lnt systems/<sut>/model/<sut>_fixture.lnt \
  systems/<sut>/model/specification_<sut>.lnt systems/<sut>/model/system_interface_<sut>.lnt \
  systems/<sut>/model/compose_<sut>.lnt \
  systems/<sut>/test_purposes/tp_*.lnt systems/<sut>/test_purposes/accept.ren systems/<sut>/test_purposes/refuse.ren \
  systems/<sut>/testor/<sut>.io systems/<sut>/testor/generate_tc_all.sh \
  <user>@<node>:/scratch/<user>/testor_<sut>/
# verify the push landed (a mirror that is never read looks identical from here)
ssh <user>@<node> "grep -c 'process SPEC' /scratch/<user>/testor_<sut>/specification_<sut>.lnt"

# on the node
export CADP=/path/to/cadp ; export PATH=$CADP/com:$CADP/bin.x64:$PATH
cd /scratch/<user>/testor_<sut>
sh generate_tc_all.sh                      # or: sh generate_tc_all.sh db_corrupt
bcg_info -labels <sut>_nominal.ctg.bcg | sort   # confirm the .io classification once

# pull (node -> mac)
rsync -av '<user>@<node>:/scratch/<user>/testor_<sut>/tc_*.aut' systems/<sut>/generated/tc/
rsync -av '<user>@<node>:/scratch/<user>/testor_<sut>/variants' systems/<sut>/generated/tc/

# run one case (Android shown; --platform html --url ... for web)
PYTHONPATH=framework python framework/scripts/run.py \
  --aut systems/<sut>/generated/tc/tc_nominal.aut \
  --platform android \
  --system-interface systems/<sut>/model/system_interface_<sut>.lnt \
  --concrete-domain systems/<sut>/properties/concrete_domain.yml \
  --type-description systems/<sut>/properties/type_description.yml \
  --disruption-mapping systems/<sut>/properties/disruption_mapping.yml \
  --device-config "$DEV" --report
```

## What the template does not contain, and every case study needs

The execution layer is platform-specific and is written per system, to the
following contracts (FoodYou's `systems/foodyou/*.sh` are the reference
implementations):

| script | contract |
|---|---|
| `env.sh` | sourced, not run; exports the tool paths and the device config; reports what is actually up (device, driver port) so a stale value fails loudly |
| `check_env.sh` | refuses to run a sweep unless the device is reachable, the driver answers at the configured port, the fixture's authoritative values are intact, the store's file mode is the created one, and the external source is reachable over the port the SUT uses (not ICMP) |
| `check_faults.sh` | for every fault: record state, inject, assert it changed as claimed, restore, assert it changed back |
| `seed.sh` | deterministic reset of the SUT's state without wiping onboarding; never invents data the SUT ships |
| `run_variants.sh <purpose>` | installs each variant under the canonical name, runs it with captures scoped to its own log directory, restores the canonical file on exit |

## Framework generalisation still owed

The template is generic; the framework is not yet, in one respect that
matters. The strict oracles that turned the FoodYou sweep from "walks
completed" into counter-examples are keyed on FoodYou's literal names inside
`framework/concretization/algorithm.py`, `quantity_resolver.py` and
`fault_injector.py`: types `DailyTotal`, `Calorie`, `FoodId`; gates
`FOOD_INFO`, `ADD_ENTRY`, `REMOVE_ENTRY`, `CONFIRM_TOTAL`; bucket names
`EMPTY..OVER`; fault `CACHE_STALE`; the manifestation probes per fault name;
the seed script and database defaults. For a system instantiated from this
template the ioco walk, the trap-state verdicts and the observe / wait_for
oracle work unchanged; the band inversion, the authoritative-value check and
the manifestation probes do not fire. TEMPLATE_ANALYSIS.md §4 lists the
sites and the config hook (`role:` in type_description.yml, `verify_*` in the
Android schema) that would close the gap.
