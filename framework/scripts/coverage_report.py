#!/usr/bin/env python3
"""
coverage_report.py — how much of a test suite this deployment can actually run.

A sweep that reports "45 inconclusive" says nothing useful. The question a reader
needs answered is: of N generated test cases, how many could this environment
execute at all, and what is missing for the rest?

That is decidable from the test-case graphs alone. A test case is unrealizable
here when every route to a verdict passes through an abstract value the concrete
domain declares this deployment cannot produce (`unrealizable:` in
concrete_domain.yml). No device, no emulator time — so it can be run before a
sweep to know what the sweep can possibly show, and quoted in a report as a
coverage figure rather than discovered afterwards as a pile of INCONCLUSIVEs.

Usage:
    PYTHONPATH=framework python framework/scripts/coverage_report.py \
        --system-interface EVALUATION/<sut>/model/<si>.lnt \
        --concrete-domain  EVALUATION/<sut>/properties/concrete_domain.yml \
        EVALUATION/<sut>/Test_Cases/variants/*.aut
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from concretization.algorithm import ConcretizationAlgorithm  # noqa: E402
from concretization.si_lnt_parser import LNTSystemInterface    # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("aut", nargs="+", help="test-case .aut files")
    ap.add_argument("--system-interface", required=True)
    ap.add_argument("--concrete-domain", required=True)
    ap.add_argument("--quiet", action="store_true",
                    help="totals only, no per-test-case lines")
    args = ap.parse_args()

    si = LNTSystemInterface(args.system_interface, args.concrete_domain)
    algo = ConcretizationAlgorithm(element_map=si.to_element_map(),
                                   type_description={}, executor=None)

    declared = algo.unrealizable_values()
    if not declared:
        print("no `unrealizable:` block in the concrete domain — "
              "every test case is assumed executable here")
    else:
        print(f"this deployment cannot produce: {', '.join(sorted(declared))}")
    print()

    def reachable_states(graph):
        """States reachable from the initial one, following every transition."""
        adj = {}
        for t in graph.transitions:
            adj.setdefault(t.source, []).append(t.target)
        seen, stack = {graph.initial}, [graph.initial]
        while stack:
            for nxt in adj.get(stack.pop(), []):
                if nxt not in seen:
                    seen.add(nxt); stack.append(nxt)
        return seen

    # Three outcomes, not two. "Some route avoids the blocked value" is NOT the
    # same as "this run will avoid it": these test cases are controllable, so the
    # branch actually taken is decided by the SUT's outputs, and a blocked
    # transition on the path taken is forced -- there is no alternative to pick.
    blocked, at_risk, clear, reasons = [], [], [], {}
    for path in sorted(args.aut):
        graph = algo.reader.read_aut_file(path)
        name  = os.path.basename(path)
        bad   = [t for t in graph.transitions if algo.blocking_value(t.label)]
        needed = ", ".join(sorted({algo.blocking_value(t.label) for t in bad}))
        ok, _why = algo.realizable_here(graph)
        if not ok:
            blocked.append(name); reasons[name] = needed
            if not args.quiet:
                print(f"  BLOCKED   {name:28} every route to a verdict needs {needed}")
        elif bad and (reachable_states(graph) & {t.source for t in bad}):
            at_risk.append(name); reasons[name] = needed
            if not args.quiet:
                print(f"  AT-RISK   {name:28} can be forced onto {needed}")
        else:
            clear.append(name)
            if not args.quiet:
                print(f"  clear     {name}")

    total = len(blocked) + len(at_risk) + len(clear)
    if not total:
        print("no test cases")
        return 0
    pct = lambda n: f"{100 * n / total:.0f}%"
    print()
    print("=" * 68)
    print(f"  clear    (no unrealizable value reachable) : {len(clear):3}/{total}  {pct(len(clear))}")
    print(f"  at-risk  (can be FORCED onto one)          : {len(at_risk):3}/{total}  {pct(len(at_risk))}")
    print(f"  blocked  (every route needs one)           : {len(blocked):3}/{total}  {pct(len(blocked))}")
    if reasons:
        by_value: dict[str, int] = {}
        for v in reasons.values():
            by_value[v] = by_value.get(v, 0) + 1
        print()
        for v, n in sorted(by_value.items(), key=lambda kv: -kv[1]):
            print(f"    {n:3} affected by: {v}")
    print()
    print("Only `clear` can be quoted as tested. `blocked` never was. `at-risk`")
    print("depends on which branch the SUT's own outputs lead to, so the run tells")
    print("you -- and an INCONCLUSIVE there is a coverage gap, not a result.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
