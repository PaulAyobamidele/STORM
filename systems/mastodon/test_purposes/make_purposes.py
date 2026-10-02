#!/usr/bin/env python
"""make_purposes.py -- write every tp_*.lnt of this case study from one table.

ONE happy path H (the nominal purpose):
    S1 post A, S2 post B, S3 post C, S4 read without refresh (C),
    S5 fresh check (C), S6 delete C
Every other purpose is ONE disruption of H, which may strike at any step where
the specification states what is owed. Two loosenings give the tester choices
for TESTOR to resolve: where the disruption strikes, and the order of the two
reads (S4, S5). The test cases are what extract_all extracts from these
choices, as in FoodYou; the suite grows there, not in the number of purposes.

Determinism is kept explicitly: at every point the purpose offers exactly the
inputs expected there (H's next input, and the disruption where it may
strike); every other input the purpose uses somewhere is refused at that
point, and every input it never uses is refused everywhere (the outer
disrupt). Outputs are left free except the status that names the branch.

    python3 systems/mastodon/test_purposes/make_purposes.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FAULTS = ["UE_KILL", "UE_SESSION_EXPIRED", "APP_WRITE_FAIL", "APP_UNAVAILABLE",
          "APP_EXTAPI_FAIL", "APP_CACHE_STALE", "APP_LAZY_PROCESSING",
          "DB_ABORT", "DB_CORRUPT", "DB_EVENT_LOSS",
          "INFRA_DB_DOWN", "INFRA_SIDEKIQ_DEAD", "INFRA_STORAGE_FULL"]
ITEMS = ["post_a", "post_b", "post_c"]
RECS = ["rec_a", "rec_b", "rec_c"]
ANY4 = "?any CountBand, ?any HomeState, ?any ProfileState"
ACCEPT = "loop TP_ACCEPT end loop"
# loosening: S4 (read without refresh) and S5 (fresh check) in either order
READS_EITHER_ORDER = True
REFUSE = "loop TP_REFUSE end loop"

# the happy path: (kind, item)
H = [("post", "post_a"), ("post", "post_b"), ("post", "post_c"),
     ("peek", "post_c"), ("check", "post_c"), ("delete", "post_c")]
STEP = ["S1 post A", "S2 post B", "S3 post C", "S4 read without refresh",
        "S5 fresh check", "S6 delete C"]


def step_input(kind, item):
    return {"post": f"ADD ({item}, PUBLIC, VALID)", "peek": "PEEK (RID)",
            "check": "CHECK (RID)", "delete": "REMOVE (RID)"}[kind]


def step_output(kind, item):
    return {"post": f"CONFIRM (COMMITTED, {ANY4}, {item})",
            "peek": "SHOW (RID, ?any Value)",
            "check": f"CONFIRM (?any WriteStatus, {ANY4}, {item})",
            "delete": f"CONFIRM (COMMITTED, {ANY4}, {item})"}[kind]


def seq(*parts):
    """Join LNT statements (lists of lines) with ';' between statements."""
    out = []
    for p in parts:
        if not p:
            continue
        if out:
            out[-1] = out[-1] + ";"
        out += p
    return out


def alt(arms):
    """arms: list of line-lists -> an alt over them (or the single arm)."""
    arms = [a for a in arms if a]
    if len(arms) == 1:
        return arms[0]
    out = ["alt"]
    for i, a in enumerate(arms):
        if i:
            out.append("[]")
        out += ["    " + l for l in a]
    out.append("end alt")
    return out


def refuse(pats):
    if not pats:
        return []
    return seq(alt([[p] for p in pats]), [REFUSE])


class Purpose:
    def __init__(self, name, shape, owed, expected, hooks, nominal=False):
        # hooks: {step index: [(kind, fault)]} with kind in
        #   after_add  fault strikes between ADD and its CONFIRM (write path)
        #   kill       UE_KILL there (either consistent outcome)
        #   param      INVALID / OVERLIMIT instead of the VALID post
        #   pre        fault just before the step, which then runs nominally
        #   delete_err fault just before the delete is confirmed
        #   during     DB_CORRUPT interrupting the fresh check
        self.name, self.shape, self.owed, self.expected = name, shape, owed, expected
        self.hooks, self.nominal = hooks, nominal
        self.path = self._path_inputs()

    def _path_inputs(self):
        ins = {step_input(k, i) for k, i in H}
        for j, hs in self.hooks.items():
            for kind, f in hs:
                if kind == "param":
                    ins.add(f"ADD ({H[j][1]}, PUBLIC, {f})")
                else:
                    ins.add(f)
        return ins

    def point_expected(self, j):
        """first inputs the purpose accepts at the resting point before step j"""
        k, i = H[j]
        exp = [step_input(k, i)]
        for kind, f in self.hooks.get(j, []):
            if kind == "param":
                exp.append(f"ADD ({i}, PUBLIC, {f})")
            elif kind in ("pre", "delete_err"):
                exp.append(f)
        return exp

    def gen(self, j, done=frozenset()):
        """from the resting point before step j; `done` = the read steps
        already walked (the two reads may come in either order)"""
        # which step comes next: H in order, except that S4 (read without
        # refresh) and S5 (fresh check) may be taken in either order
        if j == len(H):
            return [ACCEPT if self.nominal else REFUSE]
        nxt = [j]
        if j in (3, 4) and READS_EITHER_ORDER:
            nxt = [r for r in (3, 4) if r not in done]
        arms = []
        expected = set()
        for jj in nxt:
            k, i = H[jj]
            hooks = self.hooks.get(jj, [])
            inp, outp = step_input(k, i), step_output(k, i)
            after = self._after(jj, done)
            mid = [(kind, f) for kind, f in hooks if kind in ("after_add", "kill", "during")]
            if mid:
                kind, f = mid[0]
                if kind == "after_add":
                    strike = [f"{f};", "WRITE_ERROR_SHOWN;", f"CONFIRM (ROLLED_BACK, {ANY4}, {i});", ACCEPT]
                elif kind == "kill":
                    strike = seq([f"{f}"], alt([[f"CONFIRM (COMMITTED, {ANY4}, {i})"],
                                                [f"CONFIRM (ROLLED_BACK, {ANY4}, {i})"]]), [ACCEPT])
                else:
                    strike = [f"{f};", "DB_CORRUPT_DETECTED;", ACCEPT]
                arms.append(seq([inp], alt([strike, seq([outp], after)])))
            else:
                arms.append(seq([inp], [outp], after))
            expected |= set(self.point_expected(jj))
            for kind, f in hooks:
                if kind == "param":
                    arms.append([f"ADD ({i}, PUBLIC, {f});", "REJECT_SHOWN;",
                                 f"CONFIRM (REJECTED, {ANY4}, {i});", ACCEPT])
                elif kind == "pre":
                    arms.append([f"{f};", f"{inp};", f"{outp};", ACCEPT])
                elif kind == "delete_err":
                    arms.append([f"{f};", f"{inp};", "WRITE_ERROR_SHOWN;",
                                 f"CONFIRM (ROLLED_BACK, {ANY4}, {i});", ACCEPT])
        arms.append(refuse(sorted(self.path - expected)))
        return alt(arms)

    def _after(self, jj, done):
        if jj in (3, 4) and READS_EITHER_ORDER:
            d = done | {jj}
            return self.gen(5 if d >= {3, 4} else min({3, 4} - d), d)
        return self.gen(jj + 1, done)

    def never_used(self):
        g = [f for f in FAULTS if f not in self.path]
        g += ["ADD (?any ItemId, FOLLOWERS, ?any Validity)", "EDIT (?any RecordId)"]
        for v in ("INVALID", "OVERLIMIT"):
            if not any(f"PUBLIC, {v})" in p for p in self.path):
                g.append(f"ADD (?any ItemId, PUBLIC, {v})")
        for r in RECS[:2]:
            g += [f"PEEK ({r})", f"CHECK ({r})", f"REMOVE ({r})"]
        return g

    def body(self):
        return seq(["disrupt"] + ["    " + l for l in self.gen(0)] + ["by"]
                   + ["    -- every fault and input this purpose never uses"]
                   + ["    " + l for l in refuse(self.never_used())] + ["end disrupt"])


HEADER_GATES = """    ADD     : AddChannel,
    CONFIRM : ConfirmChannel,
    EDIT    : RecordChannel,
    REMOVE  : RecordChannel,
    CHECK   : RecordChannel,
    PEEK    : RecordChannel,
    SHOW    : ShowChannel,
    WRITE_ERROR_SHOWN   : none,
    REJECT_SHOWN        : none,
    DB_CORRUPT_DETECTED : none,
""" + "".join(f"    {f:<19} : none,\n" for f in FAULTS) + """    TP_ACCEPT           : none,
    TP_REFUSE           : none"""

POSTS = [0, 1, 2]
P = []
P.append(Purpose("nominal", "the happy path H", "S1-S3 CONFIRM (COMMITTED, count 1..3, IN_HOME, ON_PROFILE); "
                 "S4 SHOW (V_ORIG); S5 CONFIRM; S6 CONFIRM (count 2, C gone)", "PASS", {}, nominal=True))
for v, exp in [("INVALID", "PASS (\"Post can't be blank.\", live)"), ("OVERLIMIT", "PASS (button disabled, live)")]:
    P.append(Purpose(f"input_{v.lower()}", f"H, the post at S1, S2 or S3 is {v}",
                     "REJECT_SHOWN then CONFIRM (REJECTED, count unchanged)", exp,
                     {j: [("param", v)] for j in POSTS}))
P.append(Purpose("ue_kill", "H, the user leaves right after Post at S1, S2 or S3",
                 "CONFIRM in one of the two consistent forms (O9)", "PASS",
                 {j: [("kill", "UE_KILL")] for j in POSTS}))
P.append(Purpose("app_write_fail", "H, antispam drops the post at S1, S2 or S3",
                 "WRITE_ERROR_SHOWN then CONFIRM (ROLLED_BACK) (O2)",
                 "FAIL on O2: \"Post published.\" for a dropped post (live)",
                 {j: [("after_add", "APP_WRITE_FAIL")] for j in POSTS}))
for f, exp in [("UE_SESSION_EXPIRED", "PASS (401, live, post and delete)"),
               ("APP_UNAVAILABLE", "FAIL on O2 by quiescence (live, post and delete)"),
               ("DB_ABORT", "PASS (500, live, post and delete)"),
               ("INFRA_DB_DOWN", "FAIL on O2 by quiescence (live, post and delete)"),
               ("INFRA_STORAGE_FULL", "PASS (500, live, post and delete)")]:
    hooks = {j: [("after_add", f)] for j in POSTS}
    hooks[5] = [("delete_err", f)]
    P.append(Purpose(f.lower(), f"H, {f} at the Post click of S1, S2 or S3, or as the delete of S6 is confirmed",
                     "WRITE_ERROR_SHOWN then CONFIRM (ROLLED_BACK, nothing moved) (O2)", exp, hooks))
P.append(Purpose("app_extapi_fail", "H, the link-preview fetch cut off just before S1, S2 or S3",
                 "the post lands as on H (O3)", "PASS on O3: the link crawl is async and rescued",
                 {j: [("pre", "APP_EXTAPI_FAIL")] for j in POSTS}))
h = {j: [("pre", "INFRA_SIDEKIQ_DEAD")] for j in POSTS}
h[5] = [("pre", "INFRA_SIDEKIQ_DEAD")]
P.append(Purpose("infra_sidekiq_dead", "H, Sidekiq paused just before S1, S2, S3 or S6",
                 "the post reaches home / the delete takes effect everywhere (O3, O6)",
                 "FAIL: home written and count decremented only by Sidekiq (live)", h))
P.append(Purpose("app_cache_stale", "H, the newest post's text changes just before S4",
                 "S4 SHOW (RID, V_EDITED) read without refresh (O7)",
                 "FAIL on O7: the client store is never revalidated", {3: [("pre", "APP_CACHE_STALE")]}))
P.append(Purpose("db_event_loss", "H, the newest row is deleted by SQL just before S5",
                 "S5 CONFIRM (ABSENT, count down, NOT_IN_HOME, OFF_PROFILE) (O4)",
                 "FAIL on O4: the counter cache still counts the row", {4: [("pre", "DB_EVENT_LOSS")]}))
P.append(Purpose("db_corrupt", "H, post C's text is blanked during S5",
                 "DB_CORRUPT_DETECTED (O8)", "FAIL on O8: a blank post renders as an empty one",
                 {4: [("during", "DB_CORRUPT")]}))
P.append(Purpose("app_lazy_processing", "H, Sidekiq quiet just before S6",
                 "S6 CONFIRM (COMMITTED, count down, NOT_IN_HOME, OFF_PROFILE) (O6)",
                 "FAIL on O4/O6: the count is decremented only by the worker", {5: [("pre", "APP_LAZY_PROCESSING")]}))


def write(p, fname):
    where = getattr(p, "strike", "none")
    doc = (f"(* SHAPE    {p.shape}.\n"
           f"   H        {', '.join(STEP)}.\n"
           f"   STRIKES  {where} (any of these; extract_all resolves which).\n"
           f"   ACCEPT   the disruption strikes and the owed outputs follow"
           + (" (nominal: H completes)" if p.nominal else "") + ".\n"
           f"   REFUSE   H completes without the disruption; any input not expected at\n"
           f"            its point; any fault or input this purpose never uses.\n"
           f"   Owed     {p.owed}.\n"
           f"   Expected {p.expected} (observed_behaviour.md §12-13).\n"
           f"   Generated by make_purposes.py: edit the table there, not this file. *)")
    txt = (f"module {fname} (mastodon_types, mastodon_fixture) is\n\n{doc}\n\n"
           f"process MAIN [\n{HEADER_GATES}\n] is\n"
           f"    var RID : RecordId in\n"
           f"        RID := defaultRecord;\n"
           + "\n".join("        " + l for l in p.body()) +
           "\n    end var\nend process\n\nend module\n")
    with open(os.path.join(HERE, f"{fname}.lnt"), "w") as fh:
        fh.write(txt)


for old in os.listdir(HERE):
    if old.startswith("tp_") and old.endswith(".lnt"):
        os.remove(os.path.join(HERE, old))
for p in P:
    p.strike = "; ".join(f"{STEP[j]}: {', '.join(f'{k} {f}' for k, f in hs)}"
                         for j, hs in sorted(p.hooks.items())) or "none"
    write(p, f"tp_{p.name}")
    print(f"  tp_{p.name:24s} {p.strike}")
print(f"{len(P)} purposes; the number of test cases is what extract_all resolves")
