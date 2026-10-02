#!/usr/bin/env python
"""check_faults.py -- prove every Mastodon fault BITES and LETS GO, driven
through the framework's own DisruptionExecutor (the class the walker uses),
not by re-running the YAML commands by hand.

For each fault with an injection: its verify_restored probe must hold before
(clean state), activate_disruption must inject AND confirm verify_injected,
restore() must undo AND confirm verify_restored. The faults that act on the
fixture post run while one exists (created through PostStatusService); the
seed runs before and after.

    .venv/bin/python systems/mastodon/check_faults.py [FAULT ...]
Exit 1 if any fault fails any of the three checks.
"""
import logging, os, subprocess, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "framework"))
from concretization.disruptor import DisruptionExecutor  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
MAP = os.path.join(ROOT, "systems/mastodon/properties/disruption_mapping.yml")
NEEDS_POST = ["APP_CACHE_STALE", "DB_CORRUPT", "DB_EVENT_LOSS"]   # last one removes it
TEXT = "@alice ioco note C https://example.com"


def sh(cmd):
    return subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)


def seed():
    r = sh("sh systems/mastodon/seed.sh")
    print(r.stdout.strip().splitlines()[-1] if r.returncode == 0 else r.stdout + r.stderr)
    return r.returncode == 0


def make_post():
    r = sh("docker exec mastodon-web-1 bin/rails runner "
           f"'PostStatusService.new.call(Account.find_local(\"bob\"), text: \"{TEXT}\")' 2>&1")
    time.sleep(2)
    return r.returncode == 0


def check(de, name):
    entry = de.faults[name]
    before = de._verify(entry, "verify_restored")
    injected = de.activate_disruption(name)
    restored = de.restore([name])
    ok = before and injected and restored and not de.is_poisoned()
    print(f"  {'PASS' if ok else 'FAIL'}  {name:22s} clean-before={before} bites={injected} lets-go={restored}")
    if de.is_poisoned():
        de._poisoned = False          # keep checking the others; seed clears the stack
    return ok


def main(names):
    de = DisruptionExecutor(MAP, base_url="https://mastodon.localhost", project_root=ROOT)
    todo = [k for k, v in de.faults.items()
            if isinstance(v, dict) and v.get("timing", "gate") != "none"]
    if names:
        todo = [k for k in todo if k in names]
    plain = [k for k in todo if k not in NEEDS_POST]
    post = [k for k in NEEDS_POST if k in todo]
    if not seed():
        print("seed failed before the check"); return 1
    results = {}
    for k in plain:
        results[k] = check(de, k)
    if post:
        for k in post:
            if not make_post():
                print(f"  FAIL  could not create the fixture post for {k}"); results[k] = False; continue
            results[k] = check(de, k)
            seed()
    print("after the batch:", "seed ok" if seed() else "SEED FAILED")
    bad = [k for k, v in results.items() if not v]
    print(f"\n{len(results) - len(bad)}/{len(results)} faults bite and let go" + (f"; FAILED: {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
