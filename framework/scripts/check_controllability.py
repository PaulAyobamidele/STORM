#!/usr/bin/env python3
"""Check whether generated .aut test cases are actually CONTROLLABLE.

A test case is controllable (TGV / TESTOR sense) when, in every state:
  * at most ONE input (tester-controlled) action is enabled, and
  * inputs are never offered alongside outputs.

Output branching is legitimate and expected -- the tester must accept every
output the SUT may produce, so those branches are observed, not chosen. Input
branching is not: it is a decision the generator was supposed to resolve, and
if it survives into the test case then the RUNTIME WALKER picks it, which makes
the verdict depend on the walker's tie-break rule rather than on the test case.

`extract_all -check` verifies that each extracted test case is a valid prefix
with PASS reachable. It does NOT tell you that the gates you meant to be inputs
were classified as inputs -- if the .io file's patterns do not match the label
case actually emitted by CADP, every such gate is silently treated as an output
and no conflict is ever resolved. This script is the independent check.

    python framework/scripts/check_controllability.py <file.io> <tc.aut>...

Exit status is 1 if any test case is not controllable, so it can gate a
regeneration step.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict

# Labels that are not actions: quiescence and the verdict sentinels.
SPECIAL = re.compile(r'^:(DELTA|PASS|FAIL|INCONC|INCONCLUSIVE|ACCEPT|REFUSE):$')

AUT_LINE = re.compile(r'\(\s*(\d+)\s*,\s*"(.*)"\s*,\s*(\d+)\s*\)\s*$')


def read_io(path: str) -> list[re.Pattern]:
    """Patterns naming the INPUT gates. Everything unmatched is an output."""
    pats, seen_header = [], False
    with open(path) as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            if not seen_header:
                # The header word is 'input' (TESTOR reads the rest as inputs).
                if line.lower() == "input":
                    seen_header = True
                    continue
                raise SystemExit(f"{path}: expected 'input' header, got {line!r}")
            pats.append(re.compile(line.strip('"')))
    if not seen_header:
        raise SystemExit(f"{path}: no 'input' header found")
    return pats


def read_aut(path: str):
    trans = []
    with open(path) as fh:
        for raw in fh:
            m = AUT_LINE.match(raw.strip())
            if m:
                trans.append((int(m.group(1)), m.group(2), int(m.group(3))))
    return trans


def is_input(label: str, pats: list[re.Pattern]) -> bool:
    return any(p.fullmatch(label) for p in pats)


def check(path: str, pats: list[re.Pattern]):
    out = defaultdict(set)
    for s, label, _t in read_aut(path):
        if not SPECIAL.match(label):
            out[s].add(label)

    multi_input, mixed = [], []
    for state, labels in out.items():
        ins = {l for l in labels if is_input(l, pats)}
        outs = labels - ins
        if len(ins) > 1:
            multi_input.append((state, sorted(ins)))
        if ins and outs:
            mixed.append((state, sorted(ins), sorted(outs)))
    return len(out), multi_input, mixed


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        raise SystemExit(__doc__)
    pats = read_io(argv[1])
    bad = 0

    print(f"{'test case':<44}{'states':>8}{'>1 input':>10}{'in+out':>8}  verdict")
    print("-" * 82)
    for path in argv[2:]:
        nstates, multi, mixed = check(path, pats)
        ok = not multi and not mixed
        bad += 0 if ok else 1
        name = path.rsplit("/", 1)[-1]
        print(f"{name:<44}{nstates:>8}{len(multi):>10}{len(mixed):>8}  "
              f"{'CONTROLLABLE' if ok else 'NOT CONTROLLABLE'}")

    if bad:
        # Show one concrete offender: an abstract count is easy to wave away,
        # a state with three enabled inputs is not.
        _n, multi, mixed = check(argv[2], pats)
        if multi:
            state, ins = multi[0]
            print(f"\nfirst input conflict in {argv[2].rsplit('/', 1)[-1]}, state {state} "
                  f"-- the tester must pick one of:")
            for label in ins:
                print(f"    {label}")
        if mixed:
            state, ins, outs = mixed[0]
            print(f"\nfirst input/output mix, state {state}:")
            print(f"    inputs : {', '.join(ins)}")
            print(f"    outputs: {', '.join(outs)}")
        print(f"\n{bad} of {len(argv) - 2} test case(s) NOT controllable.")
        print("The walker will be resolving those choices at run time.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
