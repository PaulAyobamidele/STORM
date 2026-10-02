# SimpleBaby — the one test path

Decided 2026-09-29. One happy path runs through every journey in an order
that leaves a place for every disruption. The nominal purpose walks all of
it with no fault. Each disruption purpose walks the same path up to its
injection point, injects there, and ends at the verdict on the output the
specification owes.

A violation on the path before the injection point is a normal-path finding
and is reported once, as such. It is never counted as the disruption's
result.

## The path

| # | Step (abstract labels) | Screen after it |
|---|---|---|
| 1 | `START (md)`: sign up and first child, or guest and first child | Trackers |
| 2 | `ADD (feed_a, VALID)`: the feeding form filled | Feeding form |
| 3 | `SAVED_SHOWN`: "Feeding log saved successfully!" | alert over the tabs |
| 4 | `CONFIRM (COMMITTED, NAMED, feed_a)`: the history, read fresh, names the item | History |
| 5 | `READ (feed_a)`, then `LIST (NAMED, feed_a)`: the history opened again | History |
| 6 | `REMOVE (rec_a)`, then `CONFIRM (COMMITTED, UNNAMED, feed_a)`: the card deleted, list read in place | History |
| 7 | `SLEEP_ADD (SAME_DAY)`, then `SLEEP_SAVED`: 1:00 PM to 2:00 PM | alert over the tabs |
| 8 | `TIMER_START`, then `TIMER_READ (T0)`: the stopwatch read at once | Sleep form |

Every purpose fixes its mode. The walker always takes the input closest to
`:PASS:`, so a case that leaves the mode open would only ever be walked in
one mode. The baseline is therefore two purposes, `nominal_signed` and
`nominal_guest`. The faults hosted in both modes (UE_KILL, APP_KEY_LOST,
INFRA_DOZE) and the two input variants run signed in; their guest runs are
not in this suite.

Each purpose refuses, at EVERY step, every tester input other than that
step's own. TESTOR lets a label the purpose does not mention at a step pass
through, and the first generation (2026-10-01) showed it: cases opened the
history before any feeding existed, or repeated a journey and injected
twice.

## Injection points

| Point | Where on the path | Faults | Mode |
|---|---|---|---|
| P1 | between steps 2 and 3, before the save tap | UE_KILL, UE_OFFLINE, APP_UNAVAILABLE, DB_ABORT, INFRA_DB_DOWN | signed in (UE_KILL both) |
| | | UE_STORAGE_FULL | guest |
| P1' | step 2 with the amount empty (a variant of the input, not a fault) | INPUT_INVALID | both |
| P2 | after step 4, before step 5 | APP_KEY_LOST | both |
| P3 | inside step 5, before the list is opened | DB_CORRUPT, DB_DATA_LOST | signed in |
| | | DB_CORRUPT_LOCAL, INFRA_STORAGE_MEDIA | guest |
| P4 | inside step 6, before the delete is confirmed | APP_CACHE_STALE | signed in |
| P5 | step 7 as 10:00 PM to 6:00 AM (a variant of the input) | INPUT_OVERNIGHT | both |
| P6 | inside step 8, after the stopwatch starts | INFRA_DOZE | both |

Layer tally on the path: USER 3, APP 3, DB 4, INFRA 3, plus two input
variants.

## What this asks of phase E

- `tp_nominal` accepts only the whole path, per mode.
- Each fault purpose is the path's prefix up to its point, then the fault,
  then the owed output, then ACCEPT. Everything else is refused, including
  off-path inputs and every other fault (negative closure at the input level).
- Verdicts are the ioco verdicts only, earned by walking the generated case:
  PASS (`:PASS:` reached), FAIL (an output the case does not allow, silence
  included where no `:DELTA:` is offered), INCONCLUSIVE (`:INCONCLUSIVE:`
  reached). A walk that cannot finish is an apparatus problem: fixed and
  rerun, never reported as a verdict.
