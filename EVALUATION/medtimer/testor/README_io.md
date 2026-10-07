# medtimer.io -- what the tester CONTROLS

TESTOR's `-io` file lists the labels that are **inputs** (tester -> SUT).
Everything not listed is an **output** (SUT -> tester), and it is on outputs
that ioco verdicts are earned: an output the specification forbids is FAIL,
and silence where an output is owed is FAIL by quiescence.

Three groups, in this order:

| group | entries | why they are inputs |
|---|---|---|
| concrete primitives | `NAVIGATE`, `TAP`, `ENTER_TEXT` | the tester performs them |
| abstract requests | `SEARCH`, `ADD`, `VIEW`, `REMOVE` | the tester initiates each journey |
| faults | every fault gate | the tester injects them (disruption_mapping.yml) |

Deliberately **absent** (so they are outputs):

- `WAIT_FOR`, `OBSERVE` -- an element appearing is something the SUT does.
  The runtime then separates the two: a `wait_for` that times out is a
  precondition the tester could not establish (UNEXECUTABLE), an `observe`
  that times out is an oracle miss (FAIL).
- `INFO`, `DETAIL`, `CONFIRM` -- the SUT's answers.
- every fault OBSERVABLE (`*_DETECTED`, `*_WARNING`, `*_ERROR`) -- what the
  SUT owes after a fault.

## Pattern rules (HOLE 20)

Patterns match the **whole** BCG label.

- A parameterised gate is emitted as `GATE !p1 !p2`, so write `"GATE .*"`
  **with the space**. That also stops `GATE` from swallowing a longer gate
  that begins with the same letters.
- A parameterless gate is emitted as exactly `GATE`, so write `"GATE"` with
  **no** wildcard. `"DB_CORRUPT.*"` would also capture the OUTPUT
  `DB_CORRUPT_DETECTED` and silently make the SUT's answer a tester action.
- Labels are upper-case even where the LNT gate is lower-case
  (`navigate` -> `NAVIGATE`).

Verify once on the first Complete Test Graph:

```sh
bcg_info -labels medtimer_nominal.ctg.bcg | sort
```

Every label ending in `; INPUT` must be one you meant to control; every
fault observable must end in `; OUTPUT`.
