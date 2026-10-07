#!/usr/bin/env python3
"""make_results_table.py -- print SimpleBaby's results rows in the paper's
LaTeX layout, every number read from a file on disk:

  TP (trans., states)        bcg_info of generated/ctg/tp_<purpose>.bcg
  cases                      count of Test_Cases/variants/<purpose>/*.aut
  variants (min - max)       first line of each .aut: des (0, TRANSITIONS, STATES)
  Gen. (s)                   gen_times.tsv, the LAST row of the purpose
  Walk (s)                   sum of TIME_S in variants_<purpose>.log
  (#PASS|#FAIL|#INCONC)      VERDICT column of variants_<purpose>.log

    .venv/bin/python EVALUATION/simplebaby/make_results_table.py [> RESULTS_table.tex]
"""
import csv, glob, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CADP = os.path.expanduser("~/cadp")
ORDER = ["nominal_signed", "nominal_guest", "ue_kill", "ue_offline", "ue_storage_full",
         "app_unavailable", "app_key_lost", "app_cache_stale", "db_abort", "db_corrupt",
         "db_corrupt_local", "db_data_lost", "infra_db_down", "infra_storage_media",
         "infra_doze", "input_invalid", "input_overnight"]
NOMINAL_LABEL = {"nominal_signed": "nomi-TP (signed in)", "nominal_guest": "nomi-TP (guest)"}


def bcg_size(path):
    arch = subprocess.run([f"{CADP}/com/arch"], capture_output=True, text=True).stdout.strip()
    env = dict(os.environ, CADP=CADP,
               PATH=f"{CADP}/com:{CADP}/bin.{arch}:" + os.environ["PATH"])
    out = subprocess.run(["bcg_info", path], capture_output=True, text=True, env=env).stdout
    states = int(re.search(r"(\d+) states", out).group(1))
    trans = int(re.search(r"(\d+) transitions", out).group(1))
    return trans, states


def aut_size(path):
    m = re.match(r"des \(\d+, (\d+), (\d+)\)", open(path).readline())
    return int(m.group(1)), int(m.group(2))


def gen_seconds():
    last = {}
    for r in csv.DictReader(open(os.path.join(HERE, "gen_times.tsv")), delimiter="\t"):
        last[r["purpose"]] = int(r["seconds"])
    return last


def tex(name):
    return name.upper().replace("_", r"\_")


def main():
    gen = gen_seconds()
    rows = []
    for p in ORDER:
        tp_t, tp_s = bcg_size(os.path.join(HERE, "generated", "ctg", f"tp_{p}.bcg"))
        auts = sorted(glob.glob(os.path.join(HERE, "generated", "tc", "variants", p, "*.aut")))
        sizes = [aut_size(a) for a in auts]
        lo, hi = min(sizes, key=lambda x: x[1]), max(sizes, key=lambda x: x[1])
        res = list(csv.DictReader(open(os.path.join(HERE, f"variants_{p}.log")), delimiter="\t"))
        walk = sum(int(r["TIME_S"] or 0) for r in res)
        v = {k: sum(1 for r in res if r["VERDICT"] == k) for k in ("PASS", "FAIL", "INCONC")}
        assert sum(v.values()) == len(res), (p, "a result row has a verdict outside PASS/FAIL/INCONC")
        assert len(res) == len(auts), (p, "rows", len(res), "cases", len(auts))
        label = NOMINAL_LABEL.get(p, f"{tex(p)}-TP")
        rows.append(f"& {label} & ({tp_t},{tp_s}) & {len(auts)} & ({lo[0]},{lo[1]} - {hi[0]},{hi[1]}) "
                    f"& {gen[p]} & {walk} & {{({v['PASS']}$|${v['FAIL']}$|${v['INCONC']})}} \\\\")
    rows[0] = r"\multirow{%d}{*}{SimpleBaby} " % len(rows) + rows[0]
    rows[1:] = ["              " + r for r in rows[1:]]
    rows[-1] += r" \toprule"
    print("\n".join(rows))
    tot = {k: 0 for k in ("PASS", "FAIL", "INCONC")}
    for p in ORDER:
        for r in csv.DictReader(open(os.path.join(HERE, f"variants_{p}.log")), delimiter="\t"):
            tot[r["VERDICT"]] += 1
    print(f"% totals: {tot['PASS']} PASS, {tot['FAIL']} FAIL, {tot['INCONC']} INCONC", file=sys.stderr)


if __name__ == "__main__":
    main()
