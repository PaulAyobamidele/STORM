"""
run.py
Command-line interface for the STORM concretization algorithm.

Modes:
    Single flat label list (original v2 mode):
        python run.py --labels-file properties/tc_red_labels.txt --platform mock
        python run.py --labels "REGISTER" "LOGIN" "PASS" --platform mock

    Single AUT graph file (v3 graph walker mode):
        python run.py --aut Test_Cases/tc_red_2.aut --platform html

    Single BCG file (auto-converts to AUT then walks):
        python run.py --bcg Test_Cases/tc_red_2.bcg --platform html

    All TCs in a directory (runs every .aut file found):
        python run.py --aut-dir Test_Cases/ --platform html

    All BCG TCs in a directory (converts each then runs):
        python run.py --bcg-dir Test_Cases/ --platform html

Fault injection (HTML platform only):
        python run.py --aut Test_Cases/tc_red_2.aut --platform html --fault no_alert
"""

import argparse
import glob
import json
import os
import sys
import yaml
import logging

sys.path.insert(0, os.path.dirname(__file__))
from concretization.algorithm import ConcretizationAlgorithm, Verdict
from concretization.executors import MockExecutor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_yaml(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def inject_gate_keys(element_map: dict) -> dict:
    """
    Stamp each action dict with its gate name so HTMLExecutorAdapter
    can detect gate transitions and navigate to the correct URL.
    """
    for gate_name, spec in element_map.get("gates", {}).items():
        for action in spec.get("actions", []):
            action["gate"] = gate_name
    return element_map


class _YAMLSIAdapter:
    """
    Minimal adapter that makes a YAML element map look like an
    LNTSystemInterface to LNTSIExecutorAdapter.
    Used when --element-map is passed with traversal_paths entries,
    allowing screen-aware navigation without an LNT SI file.
    """
    def __init__(self, element_map: dict):
        self._gates = element_map.get("gates", {})

    def get_concrete_tree(self, gate_name: str) -> dict:
        return self._gates.get(gate_name, {})

    def get_abstract_gates(self) -> list:
        return list(self._gates.keys())

    def get_none_gates(self):
        return frozenset()

    def get_structural_gates(self):
        return frozenset()

    def validate_invariants(self, aut_path: str) -> None:
        pass


def build_executor(platform: str, args, element_map: dict,
                   type_desc: dict = None, lnt_si=None):
    if platform == "mock":
        return MockExecutor(mock_outputs=args.mock_outputs or [])

    elif platform == "html":
        from concretization.executors import HTMLExecutor, HTMLExecutorAdapter
        base_url  = args.url or "http://localhost:5000"
        html_exec = HTMLExecutor(
            base_url     = base_url,
            browser      = args.browser or "chrome",
            element_map  = element_map,
            headless     = not args.no_headless,
        )

        has_traversal = any(
            spec.get("traversal_paths")
            for spec in element_map.get("gates", {}).values()
        )
        if lnt_si is not None or has_traversal:
            from concretization.executors import LNTSIExecutorAdapter
            si_source = lnt_si if lnt_si is not None else _YAMLSIAdapter(element_map)
            adapter = LNTSIExecutorAdapter(html_exec, si_source, type_desc or {},
                                           wait_timeout=args.timeout)
        else:
            adapter = HTMLExecutorAdapter(html_exec, element_map)

        if args.fault and args.fault != "none":
            adapter.set_fault_mode(args.fault)
        adapter.reset_sut()
        return adapter

    elif platform == "android":
        from concretization.executors import (
            AndroidExecutor, HTMLExecutorAdapter)
        config        = json.loads(args.device_config or "{}")
        android_exec  = AndroidExecutor(device_config=config, element_map=element_map,
                                        wait_timeout=args.timeout)

        has_traversal = any(
            spec.get("traversal_paths")
            for spec in element_map.get("gates", {}).values()
        )
        if lnt_si is not None or has_traversal:
            from concretization.executors import LNTSIExecutorAdapter
            si_source = lnt_si if lnt_si is not None else _YAMLSIAdapter(element_map)
            adapter = LNTSIExecutorAdapter(android_exec, si_source, type_desc or {},
                                           wait_timeout=args.timeout)
        else:
            adapter = HTMLExecutorAdapter(android_exec, element_map)

        adapter.reset_sut()
        return adapter

    elif platform == "ios":
        from concretization.executors import IOSExecutor
        config = json.loads(args.device_config or "{}")
        return IOSExecutor(device_config=config)

    raise ValueError(f"Unknown platform: {platform}")


def print_verdict(verdict: Verdict, label: str = ""):
    colours = {
        Verdict.PASS:   "\033[92m",
        Verdict.FAIL:   "\033[91m",
        Verdict.INCONC: "\033[93m",
    }
    reset  = "\033[0m"
    suffix = f" ({label})" if label else ""

    # UNEXECUTABLE is deliberately NOT printed on a "Verdict:" line. Every sweep
    # script in the repo scrapes verdicts with `grep -oE 'Verdict: (PASS|FAIL|
    # INCONC)'`, so emitting it there would either be silently dropped or, worse,
    # counted. A distinct "Status:" line makes an unexecuted run impossible to
    # mistake for a result -- which is the entire point of the category.
    if verdict is Verdict.UNEXECUTABLE:
        print(f"Status: \033[95mUNEXECUTABLE\033[0m{suffix}")
        print("  This run produced NO verdict: the apparatus prevented the walk,")
        print("  so the SUT was never put to the question. Excluded from results;")
        print("  fix the cause and run again.")
        return

    colour = colours.get(verdict, "")
    print(f"Verdict: {colour}{verdict.name}{reset}{suffix}")


def _exit_for(verdict: Verdict):
    """Exit code from an outcome, honouring the run_variants.sh contract.

        0  PASS
        1  the test case did not pass (FAIL / INCONC)
        2  NO VERDICT was produced -- same code HarnessNotReady already uses,
           because an unexecuted run and a harness failure are the same claim:
           nothing was measured. Sweep drivers must not record either as a result.
    """
    if verdict is Verdict.UNEXECUTABLE:
        sys.exit(2)
    sys.exit(0 if verdict is Verdict.PASS else 1)


def print_report(algo: ConcretizationAlgorithm):
    report = algo.get_report()
    print("\nExecution Report")
    print("=" * 50)
    for step in report["execution_log"]:
        status = step["verdict"] or "ok"
        err    = f"  -- {step['error']}"         if step["error"]    else ""
        cap    = f"  captured={step['captured']}" if step["captured"] else ""
        print(f"  {step['gate']:<32} {status}{err}{cap}")
    print()
    print("Captured values (g_dict):")
    for k, v in report["g_dict_final"].items():
        print(f"  {k}: {v}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="STORM Concretization Algorithm Runner"
    )

    # ---- Input modes ----
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--aut",
        help="Single AUT graph file (produced by bcg_io)")
    input_group.add_argument("--bcg",
        help="Single BCG file (auto-converted to AUT)")
    input_group.add_argument("--aut-dir",
        help="Directory of .aut files — runs all TCs found")
    input_group.add_argument("--bcg-dir",
        help="Directory of .bcg files — converts each and runs all")
    input_group.add_argument("--labels", nargs="+",
        help="Flat label list provided directly")
    input_group.add_argument("--labels-file",
        help="File containing flat labels (one per line)")
    input_group.add_argument("--atc",
        help="BCG file (legacy --atc mode, same as --bcg)")

    # ---- Configuration ----
    parser.add_argument("--element-map",
        default="properties/html_element_map.yml")
    parser.add_argument("--type-description",
        default="properties/type_description.yml")
    parser.add_argument(
        "--system-interface",
        type=str,
        default=None,
        help="Path to LNT System Interface file (.lnt). "
             "If provided, uses formal LNT SI instead of --element-map YAML. "
             "Mutually exclusive with --element-map.",
    )
    parser.add_argument(
        "--concrete-domain",
        type=str,
        default=None,
        dest="concrete_domain",
        help="Path to concrete_domain.yml (overrides auto-discovery next to --system-interface).",
    )

    # ---- Platform ----
    parser.add_argument("--platform", default="mock",
        choices=["mock", "html", "android", "ios"])
    parser.add_argument("--url",
        help="Base URL for HTML platform (default: http://localhost:5000)")
    parser.add_argument("--browser", default="chrome")
    parser.add_argument("--no-headless", action="store_true",
        help="Show browser window (useful for debugging)")
    parser.add_argument("--device-config",
        help="JSON device config for mobile platforms")
    parser.add_argument("--mock-outputs", nargs="*")

    # ---- Fault injection ----
    parser.add_argument("--fault", default="none",
        choices=["none", "no_alert", "data_access", "no_outreach"],
        help="Fault injection mode (HTML platform only)")
    
    parser.add_argument(
    '--disruption-key',
    type=str,
    default=None,
    help='Forced disruption key (e.g., "DISRUPTION_OCCURS !SENSOR_TIMEOUT !SPO2_SENSOR")')
    
    
    parser.add_argument(
    '--disruption-mapping',
    type=str,
    default=None,
    help='Path to disruption_mapping.yml for taxonomy-driven fault injection'
    )

    # ---- Execution ----
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--log-file",
        help="Append verdicts to this file (for batch runs)")

    args = parser.parse_args()

    # ---- Logging ----
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s  %(message)s")

    # ---- Mutual exclusion: --system-interface vs --element-map ----
    if args.system_interface is not None and "--element-map" in sys.argv:
        parser.error(
            "--system-interface and --element-map are mutually exclusive. "
            "Provide only one."
        )

    # ---- Load type description ----
    type_desc = {}
    if os.path.exists(args.type_description):
        type_desc = load_yaml(args.type_description)

    # ---- Load config: LNT SI path or YAML path ----
    element_map = {}
    lnt_si_obj  = None

    if args.system_interface is not None:
        from concretization.si_lnt_parser import LNTSystemInterface
        # Faults the SUT declares are disruption gates, not UI gates, so the
        # parser must not demand an SI entry for them. Taking the names from
        # the SUT's own mapping keeps fault vocabularies out of the framework.
        declared_faults = set()
        if getattr(args, "disruption_mapping", None):
            try:
                _m = load_yaml(args.disruption_mapping) or {}
                declared_faults = set(_m.get("faults") or _m.get("disruptions") or {})
            except Exception as e:
                logging.warning(f"could not read fault names from "
                                f"{args.disruption_mapping}: {e}")
        lnt_si_obj = LNTSystemInterface(args.system_interface, args.concrete_domain,
                                        extra_skip_gates=declared_faults)
        if args.aut:
            lnt_si_obj.validate_invariants(args.aut)
        element_map = inject_gate_keys(lnt_si_obj.to_element_map())
    elif os.path.exists(args.element_map):
        element_map = inject_gate_keys(load_yaml(args.element_map))
    elif args.platform == "html":
        logging.warning(f"Element map not found: {args.element_map}")

    # ---- Build executor ----
    executor = build_executor(args.platform, args, element_map,
                              type_desc=type_desc, lnt_si=lnt_si_obj)

    # ---- Build algorithm ----
    algo = ConcretizationAlgorithm(
    element_map=element_map,
    type_description=type_desc,
    executor=executor,
    timeout_seconds=args.timeout,
    mapping_path=args.disruption_mapping,
    base_url=args.url,
    forced_disruption_key=args.disruption_key)

    # ================================================================
    # Determine run mode
    # ================================================================

    # ---- Mode A: directory of AUT files ----
    if args.aut_dir:
        aut_files = sorted(glob.glob(os.path.join(args.aut_dir, "*.aut")))
        if not aut_files:
            print(f"No .aut files found in {args.aut_dir}")
            sys.exit(1)
        _run_batch(algo, aut_files, "aut", args, executor)
        return

    # ---- Mode B: directory of BCG files ----
    if args.bcg_dir:
        bcg_files = sorted(glob.glob(os.path.join(args.bcg_dir, "*.bcg")))
        if not bcg_files:
            print(f"No .bcg files found in {args.bcg_dir}")
            sys.exit(1)
        _run_batch(algo, bcg_files, "bcg", args, executor)
        return

    # ---- Mode C: single AUT file ----
    if args.aut:
        _run_single_aut(algo, args.aut, args, executor)
        return

    # ---- Mode D: single BCG file ----
    if args.bcg or args.atc:
        bcg_path = args.bcg or args.atc
        _run_single_bcg(algo, bcg_path, args, executor)
        return

    # ---- Mode E: flat labels (original v2 mode) ----
    labels = []
    if args.labels:
        labels = args.labels
    elif args.labels_file:
        with open(args.labels_file) as f:
            labels = [line.strip() for line in f if line.strip()]

    _run_flat(algo, labels, args, executor)


# ================================================================
# Run helpers
# ================================================================

def _run_single_aut(algo, aut_path, args, executor):
    print(f"\nSTORM Concretization — Graph Walker")
    print(f"Platform : {args.platform}")
    print(f"Fault    : {args.fault}")
    print(f"AUT      : {aut_path}")
    print("-" * 50)

    # A harness failure is NOT a verdict. If the apparatus could not put the SUT
    # into a state where the test case can begin, the run says nothing about the
    # SUT or the model, and recording it as INCONCLUSIVE would put it in the same
    # column as an unappliable stimulus -- which IS a statement about the SUT.
    # Exit 2 so a sweep driver can tell "the device is broken" from "this test
    # case did not pass", and stop rather than grind through the rest.
    try:
        from concretization.executors import HarnessNotReady
    except Exception:
        HarnessNotReady = ()
    try:
        verdict = algo.run_aut(aut_path)
    except HarnessNotReady as e:
        print()
        print(f"HARNESS FAILURE: {e}", file=sys.stderr)
        print("  This run produced NO verdict. It is excluded from results,",
              file=sys.stderr)
        print("  not recorded as INCONCLUSIVE.", file=sys.stderr)
        try:
            executor.close()
        except Exception:
            pass
        sys.exit(2)

    print()
    print_verdict(verdict, os.path.basename(aut_path))

    if args.report:
        print_report(algo)

    _log_result(args, os.path.basename(aut_path), verdict)
    executor.close()
    _exit_for(verdict)


def _run_single_bcg(algo, bcg_path, args, executor):
    print(f"\nSTORM Concretization — Graph Walker")
    print(f"Platform : {args.platform}")
    print(f"Fault    : {args.fault}")
    print(f"BCG      : {bcg_path}")
    print("-" * 50)

    verdict = algo.run_bcg(bcg_path)
    print()
    print_verdict(verdict, os.path.basename(bcg_path))

    if args.report:
        print_report(algo)

    _log_result(args, os.path.basename(bcg_path), verdict)
    executor.close()
    _exit_for(verdict)


def _run_flat(algo, labels, args, executor):
    print(f"\nSTORM Concretization — Flat Mode")
    print(f"Platform : {args.platform}")
    print(f"Steps    : {len(labels)}")
    print("-" * 50)

    verdict = algo.run(labels)
    print()
    print_verdict(verdict)

    if args.report:
        print_report(algo)

    executor.close()
    _exit_for(verdict)


def _run_batch(algo, files, mode, args, executor):
    """
    Run all TCs in a directory and collect verdicts.
    Resets SUT state between each TC.
    """
    results = {}
    pass_count = fail_count = inconc_count = 0

    print(f"\nSTORM Concretization — Batch Mode")
    print(f"Platform : {args.platform}")
    print(f"Fault    : {args.fault}")
    print(f"TCs      : {len(files)}")
    print("=" * 50)

    for f in files:
        name = os.path.basename(f)

        # Reset SUT state between TCs
        if hasattr(executor, "reset_sut"):
            executor.reset_sut()

        if mode == "aut":
            verdict = algo.run_aut(f)
        else:
            verdict = algo.run_bcg(f)

        results[name] = verdict
        print_verdict(verdict, name)
        _log_result(args, name, verdict)

        if verdict == Verdict.PASS:
            pass_count += 1
        elif verdict == Verdict.FAIL:
            fail_count += 1
        else:
            inconc_count += 1

        if args.report:
            print_report(algo)

    # Summary
    total = len(files)
    print()
    print("=" * 50)
    print(f"SUMMARY: {total} TCs")
    print(f"  PASS        : {pass_count}")
    print(f"  FAIL        : {fail_count}")
    print(f"  INCONCLUSIVE: {inconc_count}")
    print("=" * 50)

    executor.close()
    sys.exit(0 if fail_count == 0 else 1)


def _log_result(args, name: str, verdict: Verdict):
    if not args.log_file:
        return
    os.makedirs(os.path.dirname(args.log_file), exist_ok=True)
    with open(args.log_file, "a") as f:
        f.write(f"{name}\t{verdict.name}\t{args.fault}\t{args.platform}\n")


if __name__ == "__main__":
    # Exit 2 for a harness failure, from ANY call path.
    #
    # This handler is at the top level rather than around the walk, because
    # reset_sut() is also called from build_executor() -- i.e. before the walk
    # begins. A handler placed only around run_aut() missed it, Python exited 1
    # with a traceback, and the sweep driver read that as an ordinary failed test
    # case: eight consecutive apparatus failures were recorded as ERROR rows and
    # the abort never fired.
    #
    # Exit 2 is the contract with run_variants.sh: "no verdict was produced".
    # Distinct from 1, which means "this test case did not pass".
    try:
        from concretization.executors import HarnessNotReady
    except Exception:
        HarnessNotReady = ()
    try:
        main()
    except HarnessNotReady as e:
        print(f"\nHARNESS FAILURE: {e}", file=sys.stderr)
        print("  This run produced NO verdict. It is excluded from results,",
              file=sys.stderr)
        print("  not recorded as INCONCLUSIVE.", file=sys.stderr)
        sys.exit(2)
