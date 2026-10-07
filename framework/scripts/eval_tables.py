#!/usr/bin/env python3
"""
eval_tables.py — build the evaluation tables from a campaign's own artifacts.

    python framework/scripts/eval_tables.py EVALUATION/foodyou --domain "Android nutrition tracker"
    python framework/scripts/eval_tables.py EVALUATION/foodyou --latex
    python framework/scripts/eval_tables.py EVALUATION/foodyou --baseline happy

Every number comes from `EVALUATION/<sut>/variants_<purpose>.log`, the per-purpose
sweep logs, which carry one row per test case:

    VARIANT     STATES    TRANSITNS   VERDICT

so case counts, verdict distributions and test-case sizes are all derivable and
re-derivable. Nothing is typed in by hand, which is the point: a table that can
be regenerated from the logs cannot drift from them.

WHAT THIS DELIBERATELY WILL NOT DO
Generation time, execution time and model size are NOT recorded anywhere in the
artifacts. They are emitted as an explicit marker rather than estimated, because
a plausible-looking number in a results table is indistinguishable from a
measured one once it is in print. Fill them from:

    model size       bcg_info <sut>/generated/compose_<sut>.bcg     (CADP node)
    generation time  time the testor/generate_all.sh run
    execution time   wall-clock of the sweep; not per-case anywhere today

TWO VIEWS, AND WHY THE SECOND EXISTS
Table 2 reports every purpose. Table 3 reports only the disruption purposes for
which the nominal baseline PASSES. A disruption verdict is only evidence about
resilience if the same machinery conforms without the disruption -- otherwise a
FAIL under disruption may be the same failure the nominal path already has, and
attributing it to the fault overstates the finding.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import statistics
import sys

NA = "--"          # not measured; never an estimate

# Two row formats, both accepted for ever (a campaign never changes format
# midway, but the table must read old campaigns too):
#     VARIANT  STATES  TRANSITNS  VERDICT                      (original)
#     VARIANT  STATES  TRANSITIONS  TIME_S  VERDICT  NOTE      (preferred)
ROW_RE = re.compile(
    r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+(?:(\d+)\s+)?(PASS|FAIL|INCONC|UNEXECUTABLE|ERROR|MISSING)"
    r"(?:\s+.*)?$")

# NOT verdicts. These rows mean the campaign never obtained evidence, so they are
# reported in their own column and excluded from every verdict total.
#
# UNEXECUTABLE is the walker's own answer for "the apparatus prevented the walk".
# ERROR/MISSING are the sweep driver's: no outcome could even be scraped. All
# three are work queues, not results -- and none of them may be summed with
# INCONC, which is a genuine ioco outcome (a refuse state, or no accepting state
# reachable) that the walk reasoned its way to.
UNEXECUTED = ("UNEXECUTABLE", "ERROR", "MISSING")


def parse_sweep(path: str) -> dict:
    """One purpose's sweep log -> counts and size distribution."""
    verdicts: dict[str, int] = {}
    states: list[int] = []
    trans: list[int] = []
    times: list[int] = []
    variants: list[tuple[int, int, int]] = []     # (variant, states, transitions)
    with open(path, errors="replace") as f:
        for ln in f:
            m = ROW_RE.match(ln)
            if not m:
                continue
            var, st, tr, t, v = m.groups()
            verdicts[v] = verdicts.get(v, 0) + 1
            states.append(int(st))
            trans.append(int(tr))
            variants.append((int(var), int(st), int(tr)))
            if t is not None:
                times.append(int(t))
    return {
        "cases": len(states),
        "verdicts": verdicts,
        "states": states,
        "trans": trans,
        "times": times,
        "variants": variants,
    }


def summarise(name: str, d: dict) -> dict:
    v = d["verdicts"]
    st = d["states"]
    return {
        "purpose": name,
        "cases": d["cases"],
        "pass": v.get("PASS", 0),
        "fail": v.get("FAIL", 0),
        "inconc": v.get("INCONC", 0),
        "unexec": sum(v.get(k, 0) for k in UNEXECUTED),
        "min_st": min(st) if st else 0,
        "max_st": max(st) if st else 0,
        "med_st": int(statistics.median(st)) if st else 0,
        "min_tr": min(d["trans"]) if d["trans"] else 0,
        "max_tr": max(d["trans"]) if d["trans"] else 0,
        # the case with the fewest / most states, shown as .N (STATES/TRANSITIONS)
        "min_var": min(d["variants"], key=lambda x: (x[1], x[0])) if d.get("variants") else None,
        "max_var": max(d["variants"], key=lambda x: (x[1], -x[0])) if d.get("variants") else None,
        # walk wall time, summed over the purpose's cases; None when the log
        # predates TIME_S, or when any row lacks it (a partial sum would look
        # like a measured total -- never estimated)
        "walk_s": (sum(d["times"]) if d.get("times") and len(d["times"]) == d["cases"]
                   else None),
        "gen_s": None,
    }


def _first(sut_dir: str, name: str):
    for p in (os.path.join(sut_dir, name), os.path.join(sut_dir, "generated", name)):
        if os.path.exists(p):
            return p
    return None


def gen_times(sut_dir: str) -> dict:
    """purpose -> generation seconds, from gen_times.tsv (written on the CADP
    node by the generation script and pulled back). The LAST row per purpose
    wins: the file is appended, so a regenerated purpose supersedes itself."""
    p = _first(sut_dir, "gen_times.tsv")
    out: dict[str, int] = {}
    if p:
        for ln in open(p, errors="replace"):
            f = ln.rstrip("\n").split("\t")
            if len(f) >= 2 and f[1].isdigit():
                out[f[0]] = int(f[1])
    return out


def model_size(sut_dir: str):
    """(states, transitions) of the composed model, from model_size.txt, or None."""
    p = _first(sut_dir, "model_size.txt")
    if not p:
        return None
    txt = open(p, errors="replace").read()
    st = re.search(r"(\d+)\s+states", txt)
    tr = re.search(r"(\d+)\s+transitions", txt)
    return (int(st.group(1)), int(tr.group(1))) if st and tr else None


def collect(sut_dir: str) -> list[dict]:
    rows = []
    gt = gen_times(sut_dir)
    for path in sorted(glob.glob(os.path.join(sut_dir, "variants_*.log"))):
        purpose = os.path.basename(path)[len("variants_"):-len(".log")]
        d = parse_sweep(path)
        if d["cases"]:
            r = summarise(purpose, d)
            r["gen_s"] = gt.get(purpose)
            rows.append(r)
    return rows


def rate(r) -> str:
    """Pass rate over EXECUTED cases only (Pass + Fail + Inc.)."""
    n = r["pass"] + r["fail"] + r["inconc"]
    return f"{100 * r['pass'] / n:.0f}%" if n else NA


def fmt_s(x) -> str:
    return NA if x is None else str(x)


def fmt_var(v) -> str:
    return NA if v is None else f".{v[0]} ({v[1]}/{v[2]})"


def tc_size(r) -> str:
    return f"{r['min_st']}\u2013{r['max_st']}" if r["cases"] else NA


RESULT_COLS = ("Purpose", "Cases", "Pass", "Fail", "Inc.", "Unexec.", "Pass rate",
               "TC size", "Min variant", "Max variant", "Gen.", "Walk")


def result_row(r) -> tuple:
    return (r["purpose"], r["cases"], r["pass"], r["fail"], r["inconc"], r["unexec"],
            rate(r), tc_size(r), fmt_var(r["min_var"]), fmt_var(r["max_var"]),
            fmt_s(r["gen_s"]), fmt_s(r["walk_s"]))


def results_table(rows) -> str:
    """The per-purpose results table, from File 1 (variants_<purpose>.log) and
    File 2 (gen_times.tsv) only. Pass rate = Pass / (Pass + Fail + Inc.);
    Unexec. is its own column and outside the rate. Gen. and Walk in seconds."""
    body = [RESULT_COLS] + [tuple(str(c) for c in result_row(r)) for r in rows]
    tot = {k: sum(r[k] for r in rows) for k in ("cases", "pass", "fail", "inconc", "unexec")}
    ex = tot["pass"] + tot["fail"] + tot["inconc"]
    gens = [r["gen_s"] for r in rows]; walks = [r["walk_s"] for r in rows]
    body.append(("TOTAL", str(tot["cases"]), str(tot["pass"]), str(tot["fail"]),
                 str(tot["inconc"]), str(tot["unexec"]),
                 f"{100 * tot['pass'] / ex:.0f}%" if ex else NA, "", "", "",
                 fmt_s(sum(gens)) if None not in gens else NA,
                 fmt_s(sum(walks)) if None not in walks else NA))
    w = [max(len(row[i]) for row in body) for i in range(len(RESULT_COLS))]
    return "\n".join("  ".join(c.ljust(w[i]) if i == 0 else c.rjust(w[i])
                               for i, c in enumerate(row)) for row in body)


def ctg_sizes(sut_dir: str) -> dict:
    """purpose -> (transitions, states) of its complete test graph, read from
    the generation log the CADP node writes (`==> <purpose>` then
    `ctg: N states, M transitions`) and pulls back as generate_tc_all.log.
    The LAST block per purpose wins (a partial re-run supersedes itself)."""
    p = _first(sut_dir, "generate_tc_all.log")
    out: dict[str, tuple] = {}
    if not p:
        return out
    cur = None
    for ln in open(p, errors="replace"):
        m = re.match(r"==> (\S+)", ln)
        if m:
            cur = m.group(1)
            continue
        m = re.search(r"ctg: (\d+) states, (\d+) transitions", ln)
        if m and cur:
            out[cur] = (int(m.group(2)), int(m.group(1)))
    return out


PAPER_COLS = ("application", "test purpose", "complete test graph", "test suite",
              "range test cases", "gen-time", "exec-time", "verdicts")
PAPER_UNITS = ("", "", "(trans.,states)", "(number)", "(trans.,states - trans.,states)",
               "(sec.)", "(sec.)", "(#PASS|#FAIL|#INCONC)")


def paper_table(rows, sut, sut_dir) -> str:
    """One row per purpose in the paper's layout, every cell from a file:
    complete test graph from generate_tc_all.log, test suite and range from
    File 1 (the variants with fewest and most STATES), gen-time from File 2,
    exec-time = sum of TIME_S, verdicts from File 1. Walks with no verdict
    are not a verdict and are not counted here; they show as `+N unexec.`."""
    ctg = ctg_sizes(sut_dir)
    body = [PAPER_COLS, PAPER_UNITS]
    for r in rows:
        c = ctg.get(r["purpose"])
        lo, hi = r.get("min_var"), r.get("max_var")
        if lo and hi:
            rng = f"{lo[2]},{lo[1]}" + ("" if lo[1:] == hi[1:] else f" - {hi[2]},{hi[1]}")
        else:
            rng = NA
        v = f"{r['pass']}|{r['fail']}|{r['inconc']}" + (f" +{r['unexec']} unexec." if r["unexec"] else "")
        body.append((sut, r["purpose"], f"{c[0]},{c[1]}" if c else NA, str(r["cases"]), rng,
                     fmt_s(r["gen_s"]), fmt_s(r["walk_s"]), v))
    gens = [r["gen_s"] for r in rows]; walks = [r["walk_s"] for r in rows]
    tp = sum(r["pass"] for r in rows); tf = sum(r["fail"] for r in rows)
    ti = sum(r["inconc"] for r in rows); tu = sum(r["unexec"] for r in rows)
    body.append((sut, "TOTAL", "", str(sum(r["cases"] for r in rows)), "",
                 fmt_s(sum(gens)) if None not in gens else NA,
                 fmt_s(sum(walks)) if None not in walks else NA,
                 f"{tp}|{tf}|{ti}" + (f" +{tu} unexec." if tu else "")))
    w = [max(len(row[i]) for row in body) for i in range(len(PAPER_COLS))]
    return "\n".join("  ".join(cell.ljust(w[i]) for i, cell in enumerate(row)) for row in body)


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------



_SUT_DIRS: dict[str, str] = {}


def sut_dir_of(sut: str) -> str:
    return _SUT_DIRS.get(sut, os.path.join("EVALUATION", sut))


def text_tables(rows, sut, domain, baseline):
    out = []
    total = sum(r["cases"] for r in rows)
    all_st = [r for r in rows]

    out.append(f"TABLE 1 — Characterisation")
    out.append(f"{'System':<14}{'Domain':<28}{'Model':<14}{'Cases':>7}{'TC size min/max':>18}")
    mn = min(r["min_st"] for r in all_st)
    mx = max(r["max_st"] for r in all_st)
    ms = model_size(sut_dir_of(sut))
    out.append(f"{sut:<14}{domain:<28}{(f'{ms[0]}/{ms[1]}' if ms else NA + ' (bcg_info)'):<14}{total:>7}{f'{mn}/{mx}':>18}")
    out.append("")

    hdr = (f"{'PURPOSE':<16}{'CASES':>6}{'PASS':>6}{'FAIL':>6}{'INCONC':>7}"
           f"{'UNEXEC':>7}{'RATE':>6}{'ST min':>7}{'ST max':>7}{'ST med':>7}{'GEN s':>7}{'WALK s':>7}")

    out.append("TABLE 2 — Effectiveness, every purpose (incl. nominal baseline)")
    out.append(hdr)
    for r in rows:
        out.append(f"{r['purpose']:<16}{r['cases']:>6}{r['pass']:>6}{r['fail']:>6}"
                   f"{r['inconc']:>7}{r['unexec']:>7}{rate(r):>6}{r['min_st']:>7}{r['max_st']:>7}"
                   f"{r['med_st']:>7}{fmt_s(r['gen_s']):>7}{fmt_s(r['walk_s']):>7}")
    tot = {k: sum(r[k] for r in rows) for k in ("cases", "pass", "fail", "inconc", "unexec")}
    out.append(f"{'TOTAL':<16}{tot['cases']:>6}{tot['pass']:>6}{tot['fail']:>6}"
               f"{tot['inconc']:>7}{tot['unexec']:>7}")
    out.append("")

    base = next((r for r in rows if r["purpose"] == baseline), None)
    out.append(f"TABLE 3 — Disruption purposes, baseline '{baseline}' qualified")
    if base is None:
        out.append(f"  baseline purpose '{baseline}' not found — cannot qualify.")
    else:
        ok = base["fail"] == 0 and base["unexec"] == 0
        out.append(f"  baseline: {base['cases']} cases, {base['pass']} PASS, "
                   f"{base['fail']} FAIL, {base['inconc']} INCONC "
                   f"-> {'QUALIFIED' if ok else 'NOT QUALIFIED'}")
        if not ok:
            out.append("  NOTE: the nominal path does not cleanly pass, so a FAIL under")
            out.append("        disruption cannot be attributed to the disruption alone.")
        out.append(hdr)
        for r in rows:
            if r["purpose"] == baseline:
                continue
            out.append(f"{r['purpose']:<16}{r['cases']:>6}{r['pass']:>6}{r['fail']:>6}"
                       f"{r['inconc']:>7}{r['unexec']:>7}{rate(r):>6}{r['min_st']:>7}{r['max_st']:>7}"
                       f"{r['med_st']:>7}{fmt_s(r['gen_s']):>7}{fmt_s(r['walk_s']):>7}")
    out.append("")
    out.append(f"'{NA}' = not measured (no gen_times.tsv / model_size.txt / TIME_S in the")
    out.append("artifacts). Left empty rather than estimated. RATE = PASS over executed")
    out.append("cases (PASS + FAIL + INCONC); UNEXEC is outside it.")
    return "\n".join(out)


def walk_tex(r) -> str:
    return str(r["walk_s"]) if r["walk_s"] is not None else r"\textit{n/a}"


def latex_tables(rows, sut, domain, baseline):
    def esc(s):
        return str(s).replace("_", r"\_")

    total = sum(r["cases"] for r in rows)
    mn = min(r["min_st"] for r in rows)
    mx = max(r["max_st"] for r in rows)
    L = []

    L.append(r"% ---- Table 1: characterisation ----")
    L.append(r"\begin{table}[t]\centering")
    L.append(r"\caption{Systems under test and generated suites.}")
    L.append(r"\label{tab:eval-characterisation}")
    L.append(r"\begin{tabular}{llrrr}\toprule")
    L.append(r"System & Domain & Model (st./tr.) & Cases & TC size (min--max) \\\midrule")
    ms = model_size(sut_dir_of(sut))
    ms_txt = f"{ms[0]}/{ms[1]}" if ms else r"\textit{n/a}"
    L.append(rf"{esc(sut)} & {esc(domain)} & {ms_txt} & {total} & {mn}--{mx} \\")
    L.append(r"\bottomrule\end{tabular}")
    L.append(r"\end{table}")
    L.append("")

    def body(rs):
        for r in rs:
            L.append(rf"{esc(r['purpose'])} & {r['cases']} & {r['pass']} & {r['fail']} & "
                     rf"{r['inconc']} & {r['unexec']} & {r['min_st']}--{r['max_st']} & "
                     rf"{r['med_st']} & {walk_tex(r)} \\")

    head = (r"Purpose & Cases & Pass & Fail & Inc. & Unex. & "
            r"TC size & Med. & Time \\\midrule")

    L.append(r"% ---- Table 2: every purpose ----")
    L.append(r"\begin{table}[t]\centering")
    L.append(r"\caption{Conformance verdicts per test purpose, including the "
             r"nominal baseline.}")
    L.append(r"\label{tab:eval-all}")
    L.append(r"\begin{tabular}{lrrrrrrrr}\toprule")
    L.append(head)
    body(rows)
    tot = {k: sum(r[k] for r in rows) for k in ("cases", "pass", "fail", "inconc", "unexec")}
    L.append(r"\midrule")
    L.append(rf"\textbf{{Total}} & {tot['cases']} & {tot['pass']} & {tot['fail']} & "
             rf"{tot['inconc']} & {tot['unexec']} & & & \\")
    L.append(r"\bottomrule\end{tabular}")
    L.append(r"\end{table}")
    L.append("")

    L.append(r"% ---- Table 3: baseline-qualified disruptions ----")
    L.append(r"\begin{table}[t]\centering")
    L.append(r"\caption{Disruption purposes for which the nominal path conforms.}")
    L.append(r"\label{tab:eval-disruption}")
    L.append(r"\begin{tabular}{lrrrrrrrr}\toprule")
    L.append(head)
    body([r for r in rows if r["purpose"] != baseline])
    L.append(r"\bottomrule\end{tabular}")
    L.append(r"\end{table}")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sut_dir", help="e.g. EVALUATION/foodyou")
    ap.add_argument("--domain", default="", help="short domain description for Table 1")
    ap.add_argument("--baseline", default="happy",
                    help="nominal purpose used to qualify Table 3 (default: happy)")
    ap.add_argument("--latex", action="store_true", help="emit LaTeX instead of text")
    ap.add_argument("--app", default="", help="application name for --paper (default: the directory name)")
    ap.add_argument("--paper", action="store_true",
                    help="the paper's per-purpose layout: CTG, suite, range, gen/exec time, verdicts")
    args = ap.parse_args()

    rows = collect(args.sut_dir)
    if not rows:
        print(f"no variants_*.log with parsable rows under {args.sut_dir}", file=sys.stderr)
        return 1

    sut = os.path.basename(args.sut_dir.rstrip("/"))
    _SUT_DIRS[sut] = args.sut_dir
    # the nominal purpose first: it is the baseline the others are read against
    rows.sort(key=lambda r: (r["purpose"] != args.baseline, r["purpose"]))
    if args.paper:
        print(paper_table(rows, args.app or sut, args.sut_dir))
        return 0
    if args.latex:
        print(latex_tables(rows, sut, args.domain or "(set --domain)", args.baseline))
        return 0
    ms = model_size(args.sut_dir)
    print(f"RESULTS -- {sut}   composed model: "
          f"{f'{ms[0]} states / {ms[1]} transitions' if ms else NA + ' (no model_size.txt)'}")
    print(results_table(rows))
    print(f"\nPass rate = Pass / (Pass + Fail + Inc.); Unexec. is outside it. TC size = "
          f"min–max STATES; Min/Max variant = .N (STATES/TRANSITIONS). Gen. and Walk in "
          f"seconds, from gen_times.tsv and TIME_S; '{NA}' = not measured, never estimated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
