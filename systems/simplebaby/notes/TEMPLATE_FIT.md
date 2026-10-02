# SimpleBaby — template fit

One row per template hole: fitted as-is / adjusted (how) / did not fit (why).
Filled as each phase decides it. Phase A decides none of them; it only
establishes what they will be decided against.

| Hole | File | Decision | Status |
|---|---|---|---|
| 1 ItemId | types | adjusted: `FeedId` with one value, a tester-created feeding (the app ships no catalogue); one value because the band counts cards of one item | fitted (draft) |
| 2 Scope | types | adjusted: `Mode` = SIGNED / GUEST, chosen once by a START input, not a field of the read channel | fitted (draft) |
| 3 Context | types | did not fit: a feeding lands in no bucket; type and channel field deleted | done |
| 4 RecordId | types | fitted as-is, one value `rec_a` | fitted (draft) |
| 5 Value | types | did not fit: nothing is looked up by item; replaced by `NameState` (does the history name the item, readably) | adjusted |
| 6 StateBand | types | did not fit: the app shows no count anywhere (notes/ui/13). Replaced by a has-a-card flag in DATABASE; the SI keeps at most one card, so `NameState` alone is exact | dropped (phase C) |
| 7 value_of / item_of | types | item_of kept; value_of replaced by `named_by (band)` | adjusted |
| 8 SUT-initiated journeys | types | none: no reminders or notifications (observed_behaviour §8) | did not fit (nothing to model) |
| 9-11 Route / Element / ConcreteValue | types | adjusted: the Android primitives click / type_into (by selector) replace tap / enter_text, because enter_text types into the FIRST EditText and every SimpleBaby form has several | fitted (draft) |
| 12-14 fixture | fixture | defaultItem feed_a, defaultRecord rec_a; defaultContext deleted with Context | fitted (draft) |
| 15-18 spec processes | spec | adjusted: the SEARCH / INFO read journey replaced by READ / LIST of the history; two journeys added outside the template (manual sleep, stopwatch), carried by USER and APP only because no store fault reaches them | fitted (draft) |
| 19 purposes | purposes | | open (phase E) |
| 20 .io | testor | | open |
| 21 generate script | testor | | open |
| 22-26 SI | SI | adjusted: the mode choice (START) is an arm of the main loop guarded by `started`, not a prelude, because the runner requires every non-fault gate in the parsed loop; six screens; a SAVED_SHOWN output added so the "saved" alert is an oracle (the parser attaches an observation only to a gate that follows it) | fitted (draft) |
| 27-30 concrete_domain | properties | adjusted: UiSelector and XPath selectors from the live dumps; testIDs are bare resource-ids; three XPath unions (history anchor, history state, flags) so every oracle element exists whether or not a card does; a fresh sign-up address per run through `@env:SB_EMAIL` | fitted |
| 31-33 type_description | properties | adjusted: `names` role for NameState (CONFIRM) and ShownState (LIST), one type per gate because the oracle reads a type at one gate; `band` role with unit 1 for the stopwatch minutes; no StateBand | fitted |
| 34 platform block | disruption_mapping | adjusted: Android block (package, RKStorage, seed.sh). The Android injector had no way to run the host-side Supabase faults, so the framework gained a `host` mechanism (fault_injector.py, self-test framework/tests/test_fault_injector_host.py; no other system uses the name). adbd runs as root because the release build is not debuggable | fitted |
| 35 faults | disruption_mapping | thirteen faults, each with inject / restore / verify_injected / verify_restored; the three that would break the read-back undo themselves after a delay. Host faults proved live 2026-09-29 (check_faults: APP_UNAVAILABLE, APP_CACHE_STALE, DB_ABORT, INFRA_DB_DOWN confirmed and restored); device faults wait for the release build | fitted (device part open) |
| 36 where the SUT caches | disruption_mapping | nowhere: no query cache; the delete path's client-side list is the only view that can diverge | fitted (answered) |
| 37 expectations | disruption_mapping | forecast header written 2026-09-29 before any run | fitted |
