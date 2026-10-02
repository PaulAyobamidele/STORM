"""Self-test for eval_tables: both row formats parse, times and model size are
read from files (never estimated), and the pass rate excludes UNEXECUTABLE.

    .venv/bin/python -m pytest framework/tests/test_eval_tables.py -q
"""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import eval_tables as E  # noqa: E402


def _sut(tmp, rows_old=None, rows_new=None, gen=None, size=None):
    d = os.path.join(tmp, "demo"); os.makedirs(os.path.join(d, "generated"))
    if rows_old:
        open(os.path.join(d, "variants_old.log"), "w").write("# hdr\nVARIANT STATES TRANSITNS VERDICT\n" + rows_old)
    if rows_new:
        open(os.path.join(d, "variants_new.log"), "w").write("# hdr\nVARIANT\tSTATES\tTRANSITIONS\tTIME_S\tVERDICT\tNOTE\n" + rows_new)
    if gen:
        open(os.path.join(d, "generated", "gen_times.tsv"), "w").write("PURPOSE\tSECONDS\tCASES\n" + gen)
    if size:
        open(os.path.join(d, "generated", "model_size.txt"), "w").write(size)
    return d


def test_both_formats_and_files():
    with tempfile.TemporaryDirectory() as tmp:
        d = _sut(tmp,
                 rows_old="1   10   11   PASS\n2   12   13   FAIL\n",
                 rows_new="1\t20\t21\t60\tPASS\t-\n2\t22\t23\t70\tUNEXECUTABLE\tno verdict line\n3\t24\t25\t80\tINCONC\t-\n",
                 gen="new\t40\t3\nnew\t45\t3\n",
                 size="2026\n\t2887562 states\n\t4117530 transitions\n")
        rows = {r["purpose"]: r for r in E.collect(d)}
        old, new = rows["old"], rows["new"]
        assert (old["cases"], old["pass"], old["fail"], old["walk_s"]) == (2, 1, 1, None)
        assert (new["cases"], new["pass"], new["inconc"], new["unexec"]) == (3, 1, 1, 1)
        assert new["walk_s"] == 210 and new["gen_s"] == 45          # last gen row wins
        assert E.rate(new) == "50%"                                  # 1 PASS of 2 executed
        assert E.model_size(d) == (2887562, 4117530)


def test_missing_files_stay_unmeasured():
    with tempfile.TemporaryDirectory() as tmp:
        d = _sut(tmp, rows_old="1 10 11 PASS\n")
        r = E.collect(d)[0]
        assert r["gen_s"] is None and r["walk_s"] is None and E.model_size(d) is None
        assert E.fmt_s(None) == E.NA


def test_min_max_variant_and_strict_walk():
    with tempfile.TemporaryDirectory() as tmp:
        d = _sut(tmp, rows_new="1\t30\t45\t10\tPASS\t\n2\t25\t40\t12\tFAIL\tCONFORMANCE FAILURE\n"
                               "3\t40\t60\t\tPASS\t\n")
        r = E.collect(d)[0]
        assert E.fmt_var(r["min_var"]) == ".2 (25/40)" and E.fmt_var(r["max_var"]) == ".3 (40/60)"
        assert E.tc_size(r) == "25–40"
        assert r["walk_s"] is None          # one row lacks TIME_S: no partial total


def test_file2_at_sut_root_wins():
    with tempfile.TemporaryDirectory() as tmp:
        d = _sut(tmp, rows_new="1\t20\t21\t5\tPASS\t\n", gen="new\t99\t1\n")
        open(os.path.join(d, "gen_times.tsv"), "w").write("purpose\tseconds\tcases\nnew\t7\t1\n")
        assert E.collect(d)[0]["gen_s"] == 7


def test_paper_table_reads_ctg_from_the_generation_log():
    with tempfile.TemporaryDirectory() as tmp:
        d = _sut(tmp, rows_new="1\t20\t21\t60\tPASS\t-\n2\t30\t33\t70\tFAIL\t-\n3\t25\t27\t80\tUNEXECUTABLE\tno verdict line\n",
                 gen="new\t45\t3\n")
        open(os.path.join(d, "generated", "generate_tc_all.log"), "w").write(
            "==> new\n     ctg: 63 states, 100 transitions\n==> new\n     ctg: 64 states, 101 transitions\n")
        assert E.ctg_sizes(d) == {"new": (101, 64)}             # last block wins
        out = E.paper_table(E.collect(d), "App", d)
        row = [l for l in out.splitlines() if l.startswith("App")][0].split()
        assert row[1:4] == ["new", "101,64", "3"]
        assert "21,20 - 33,30" in out                            # fewest / most STATES
        assert row[-3:] == ["210", "1|1|0", "+1"] or "1|1|0 +1 unexec." in out
