#!/usr/bin/env python
"""check_faults.py -- prove, on the device, that every Android fault in a
system's disruption_mapping.yml bites and lets go, BEFORE a sweep trusts it.

    PYTHONPATH=framework .venv/bin/python framework/scripts/check_faults.py systems/<sut> \
        [--device emulator-5554] [--only FAULT,FAULT] [--dry-run]

For each fault whose mechanism is not `none`: inject, run verify_injected,
restore, run verify_restored, through the same AndroidFaultInjector the
walker uses (so the check exercises the injector, not a hand copy of the
commands). A fault with no probe is reported as ASSUMED, which is a gap to
close, not a pass. Exit 1 if any inject or restore is unconfirmed.

Run it on a device that holds whatever state the probes need (for a fault
that targets "the newest record", after such a record exists), and expect
faults that restart the app to leave it on its launch screen.

SUT-agnostic: everything is read from the mapping; the package and database
path come from its `android:` block.
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import yaml  # noqa: E402
from concretization.fault_injector import AndroidFaultInjector  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sysdir", help="systems/<sut>")
    ap.add_argument("--device", default=os.environ.get("DEVICE", "emulator-5554"))
    ap.add_argument("--only", default="", help="comma-separated fault names")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--adb", default=os.environ.get("ADB", "adb"))
    a = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    mp = os.path.join(a.sysdir.rstrip("/"), "properties", "disruption_mapping.yml")
    mapping = yaml.safe_load(open(mp)) or {}
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    inj = AndroidFaultInjector(mapping, device=a.device, package=None,
                               project_root=root, adb=a.adb, dry_run=a.dry_run)
    if not inj.package:
        print("ERROR: the mapping's android: block must name the package", file=sys.stderr)
        return 2

    only = {x.strip().upper() for x in a.only.split(",") if x.strip()}
    rows, bad = [], 0
    for gate, spec in (mapping.get("faults") or {}).items():
        if not isinstance(spec, dict) or (spec.get("mechanism") or "none") == "none":
            continue
        if only and gate.upper() not in only:
            continue
        print(f"\n== {gate} ({spec.get('mechanism')}, timing {spec.get('timing', 'gate')})")
        inj.target = gate
        inj.unconfirmed.clear()
        inj._do_inject(gate)
        vi = inj.last_verification.get(gate)
        inj.restore()
        vr = "FAILED" if inj.restore_failures else ("assumed" if not spec.get("verify_restored") else "ok")
        inj_s = {True: "confirmed", False: "NOT CONFIRMED", None: "assumed"}[vi]
        rows.append((gate, inj_s, vr))
        if vi is False or inj.restore_failures:
            bad += 1

    print("\n{:<24} {:<16} {:<10}".format("fault", "inject", "restore"))
    for g, i, r in rows:
        print("{:<24} {:<16} {:<10}".format(g, i, r))
    print(f"\n{bad} fault(s) unconfirmed; {sum(1 for _, i, r in rows if i == 'assumed' or r == 'assumed')} assumed (no probe)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
