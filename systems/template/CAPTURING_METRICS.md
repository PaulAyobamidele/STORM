# Capturing the evaluation numbers for a new SUT

Every column of the per-purpose results table must be regenerable from files
on disk. Nothing is typed in by hand. If a number cannot be traced to a file,
it does not go in the paper.

The table, per test purpose:

    Cases | Pass | Fail | Inc. | Unexec. | Pass rate | TC size | Min variant | Max variant | Gen. | Walk

**The one results format.** Every SUT writes the same two files, and they are
enough for the whole table. File 1, `systems/<sut>/variants_<purpose>.log`: one
tab-separated row per case under the header
`VARIANT STATES TRANSITIONS TIME_S VERDICT NOTE`, written by the sweep driver
through `framework/scripts/sweep_row.sh` (`sweep_header` once, `sweep_row` per
case, `sweep_verdict` for the verdict: run.py exit code 2 or no verdict line is
`UNEXECUTABLE`), with `TIME_S` from bash's `SECONDS`. File 2,
`systems/<sut>/gen_times.tsv`: `purpose seconds cases`, written by
`testor/generate_tc_all.sh` on the CADP node together with `model_size.txt`
(`{ date; bcg_info compose_<sut>.bcg; }`), both pulled back. Then
`python framework/scripts/eval_tables.py systems/<sut> --baseline <nominal>`
prints the table with no SUT-specific code. Drivers to copy:
`systems/medtimer/run_variants.sh` (Android) and `systems/spliit/run_variants.sh`
(web); generators: either SUT's `testor/generate_tc_all.sh`.

## 1. What to record, and where

| Column | Source | How to capture it |
|---|---|---|
| Cases, Pass, Fail, Inc., Unexec. | `systems/<sut>/variants_<purpose>.log` | One row per variant. Verdict words are exactly `PASS`, `FAIL`, `INCONC`. A run that produced no verdict is `UNEXECUTABLE`: one word, never also `HARNESS` or `ERROR`. |
| TC size, Min/Max variant | first line of each `.aut` | `des (init, TRANSITIONS, STATES)`. Note the order: transitions before states. Write both into the row. |
| Walk | the sweep row | Record per-case wall time in the row (`TIME_S`). If the driver cannot, keep both `v<N>.seed.log` and `v<N>.log`; their mtimes bracket the walk. Never delete seed logs. |
| Gen | the CADP node | Time each purpose inside the generation script and write `gen_times.tsv` (purpose, seconds, cases) next to its outputs. Pull it back with the variants. Never rely on `/tmp` there: it is cleared. |
| Model size | the CADP node | `bcg_info` on the composed SPEC‖SI `.bcg`. Save the output as `model_size.txt` and pull it back. |

Preferred row schema, tab-separated (emitted by `framework/scripts/sweep_row.sh` when present):

    VARIANT  STATES  TRANSITIONS  TIME_S  VERDICT  NOTE

Use one format for the whole campaign. Never change it mid-campaign.

## 2. Provenance: a number is only as good as knowing what produced it

- At the start of every sweep, write the git revision and a dirty flag into the log header. If the tree is dirty, save `git diff -- framework/` beside the results.
- Before every generation, md5 every generator input locally and on the CADP node, and diff the two lists. A grep for one marker string is not enough. A stale `.io` once collapsed all purposes to one case each; a stale SI once made a whole purpose measure the wrong property. Both were visible only in the hashes.
- Keep exactly one copy of each generator input, beside the script that reads it. Delete stale copies elsewhere so they cannot be pushed by mistake.
- Before regenerating, move the previous campaign intact under `systems/<sut>/runs/<campaign-name>/` with a README: the revision it came from and its totals.

## 3. Check the suite before walking anything

- **Quiescence.** Count `:DELTA:` self-loops per test case. If every output state has one, the model has an internal `i` branch (typically a looping disruptor, `loop alt i [] faults`). That makes silence "permitted" everywhere, and no missing observable can ever FAIL. Fix it and regenerate.
- **Oracle waits.** Every wait for an observable the spec requires must carry no `:DELTA:`.
- **SI against spec.** The SI must not observe anything the spec does not require. An extra `observe` in a fault branch makes the verdict measure that extra thing.
- **Counts.** Every purpose must extract more than one case. One case each means lost controllability, usually the wrong `.io`.
- **Smoke test.** Walk one short purpose end to end and read its verdict causes before starting the long sweeps.

## 4. During the sweep

- Freeze `framework/`. Each case loads whatever is on disk when it starts. Do other work in a separate `git worktree`.
- One device per SUT run. With two devices attached, bare `adb` refuses to run. If lanes run in parallel, set `ANDROID_SERIAL` in each lane and give each its own `udid`, Appium port and `systemPort`.
- Resume by appending, never by restarting. A re-run must not truncate a summary log that holds finished rows.
- Scope failure captures per variant (`CONCRETIZATION_DEBUG_DIR=.../v<N>_captures`) so every screenshot traces back to its case.

## 5. Producing the table

Generate it with `framework/scripts/eval_tables.py` from the logs above:
pass rate over executed cases only (Pass + Fail + Inc.), with Unexecutable
in its own column and out of the denominator. Report the nominal purpose
first. It is the baseline: a disruption failure on functionality the
nominal run already fails is counted once, under nominal, not again under
the disruption.

## 6. Reference implementations to copy

These already work. Copy them rather than rewriting.

| Number | Copy from | Writes |
|---|---|---|
| Walk (`TIME_S` per case) | `systems/medtimer/run_variants.sh` (row header ~l.43, timing ~l.62-70) | `variants_<purpose>.log` |
| Walk + fault confirmation | `systems/mastodon/run_suite.sh` (~l.58, l.85) | `TIME_S` plus `injected=` / `restored=` in NOTE |
| Gen per purpose | `systems/spliit/testor/generate_tc_all.sh` (~l.108, 114, 176) | `gen_times.tsv` |
| Model size | `systems/medtimer/testor/generate_tc_all.sh` (~l.111) | `model_size.txt` (timestamped `bcg_info` of `compose_<sut>.bcg`) |

MedTimer is the only SUT that captures all three. As of 2026-09-30 this
template's own `testor/generate_tc_all.sh` writes neither `gen_times.tsv` nor
`model_size.txt`, and FoodYou's scripts capture none of the three -- its v2
walk times had to be recovered from seed/walk log mtimes and its generation
times from file mtimes on the CADP node. `framework/scripts/sweep_row.sh` and
`compile_stats.sh`, which generalised this, exist only in commit aa2f73d and
were never merged back.
