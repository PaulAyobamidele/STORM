#!/usr/bin/env python3
"""gen_purposes.py -- write every campaign-two test purpose from ONE definition
of the happy path, so each disruption follows the happy path exactly and
injects its fault at the points listed for it. Re-run after editing STEPS or
POINTS:  python3 systems/medtimer/notes/gen_purposes.py
"""
import os
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "test_purposes")

# The happy path, ordering 1. Each step: (key, input, output, dose, kind)
STEPS = [
    ("create",   "ADD_MEDICINE (VALID)",       "MEDICINE_SHOWN",                                   None,   "create"),
    ("take_a1",  "ACT (d_a1, TAKE)",           "CONFIRM (COMMITTED, ?any StockBand, TAKEN, d_a1)", "d_a1", "mark"),
    ("view_a1",  "VIEW (d_a1)",                "CONFIRM (COMMITTED, ?any StockBand, TAKEN, d_a1)", "d_a1", "view"),
    ("del_a1",   "DELETE (d_a1)",              "CONFIRM (COMMITTED, ?any StockBand, ABSENT, d_a1)", "d_a1", "delete"),
    ("view_a1b", "VIEW (d_a1)",                "CONFIRM (COMMITTED, ?any StockBand, ABSENT, d_a1)", "d_a1", "view"),
    ("skip_a2",  "ACT (d_a2, SKIP)",           "CONFIRM (COMMITTED, ?any StockBand, SKIPPED, d_a2)", "d_a2", "mark"),
    ("view_a2",  "VIEW (d_a2)",                "CONFIRM (COMMITTED, ?any StockBand, SKIPPED, d_a2)", "d_a2", "view"),
    ("forbid_a", "NO_SKIP (med_a)",            None,                                               None,   "forbid"),
    ("take_a3",  "ACT (d_a3, TAKE)",           "CONFIRM (COMMITTED, ?any StockBand, TAKEN, d_a3)", "d_a3", "mark"),
    ("view_a3",  "VIEW (d_a3)",                "CONFIRM (COMMITTED, ?any StockBand, TAKEN, d_a3)", "d_a3", "view"),
    ("take_b",   "ACT (d_b, TAKE)",            "CONFIRM (COMMITTED, ?any StockBand, TAKEN, d_b)",  "d_b",  "mark"),
    ("view_b",   "VIEW (d_b)",                 "CONFIRM (COMMITTED, ?any StockBand, TAKEN, d_b)",  "d_b",  "view"),
    ("edit_a3",  "EDIT (d_a3, SKIP)",          "CONFIRM (COMMITTED, ?any StockBand, SKIPPED, d_a3)", "d_a3", "edit"),
]
IDX = {s[0]: i for i, s in enumerate(STEPS)}
# The two further orderings of the happy path (indices into STEPS); each
# starts with a different input, so the purpose stays deterministic.
ORDERINGS = [
    list(range(len(STEPS))),
    [IDX[k] for k in ("take_b", "view_b", "create", "take_a1", "view_a1", "del_a1", "view_a1b",
                      "skip_a2", "view_a2", "forbid_a", "take_a3", "view_a3", "edit_a3")],
    [IDX[k] for k in ("take_a1", "view_a1", "del_a1", "view_a1b", "skip_a2", "view_a2", "create",
                      "forbid_a", "take_a3", "view_a3", "take_b", "view_b", "edit_a3")],
]
WRITES = [k for k, *_, kind in STEPS if kind in ("mark", "delete", "edit")]
MARKS = [k for k, *_, kind in STEPS if kind == "mark"]
VIEWS = [k for k, *_, kind in STEPS if kind == "view"]
STOCK_MOVING = ["take_a1", "del_a1", "take_a3", "take_b", "edit_a3"]
# fault -> (shape, points)
POINTS = {
    "APP_WRITE_FAIL":      ("write", WRITES),
    "INFRA_STORAGE_FULL":  ("write", WRITES),
    "UE_KILL":             ("kill", WRITES),
    "DB_ABORT":            ("write", MARKS),
    "APP_CACHE_STALE":     ("cache", STOCK_MOVING),
    "DB_CORRUPT":          ("read:DB_CORRUPT_DETECTED", VIEWS),
    "DB_CORRUPT_STOCK":    ("read:DB_CORRUPT_DETECTED", VIEWS),
    "INFRA_STORAGE_MEDIA": ("read:INFRA_STORAGE_ERROR", VIEWS),
    "DB_EVENT_LOSS":       ("loss", MARKS),
}
FAULTS = list(POINTS)
DOSES = ["d_a1", "d_a2", "d_a3", "d_b"]
ALL_INPUTS = (["ADD_MEDICINE (VALID)", "ADD_MEDICINE (INVALID)", "NO_SKIP (med_a)", "NO_SKIP (med_b)"]
              + [f"ACT ({d}, {a})" for d in DOSES for a in ("TAKE", "SKIP")]
              + [f"DELETE ({d})" for d in DOSES]
              + [f"EDIT ({d}, {a})" for d in DOSES for a in ("TAKE", "SKIP")]
              + [f"VIEW ({d})" for d in DOSES])
GATES = """    ADD_MEDICINE : AddMedChannel,
    MEDICINE_SHOWN      : none,
    REJECT_SHOWN        : none,
    NO_SKIP : MedChannel,
    ACT     : ActChannel,
    DELETE  : DoseChannel,
    EDIT    : ActChannel,
    VIEW    : DoseChannel,
    CONFIRM : ConfirmChannel,
    WRITE_ERROR_SHOWN   : none,
    DB_CORRUPT_DETECTED : none,
    INFRA_STORAGE_ERROR : none,
    UE_KILL             : none,
    APP_WRITE_FAIL      : none,
    APP_CACHE_STALE     : none,
    DB_ABORT            : none,
    DB_CORRUPT          : none,
    DB_CORRUPT_STOCK    : none,
    DB_EVENT_LOSS       : none,
    INFRA_STORAGE_FULL  : none,
    INFRA_STORAGE_MEDIA : none,
    TP_ACCEPT           : none,
    TP_REFUSE           : none"""
ACCEPT, REFUSE = "loop TP_ACCEPT end loop", "loop TP_REFUSE end loop"

def plain(step):
    _, inp, out, _, _ = step
    return [inp + ";"] + ([out + ";"] if out else [])

def block(lines, ind):
    return "\n".join(" " * ind + l for l in lines)

def alt(arms, ind):
    p = " " * ind
    return f"{p}alt\n" + f"\n{p}[]\n".join(arms) + f"\n{p}end alt"

def other_action(inp):
    return inp.replace("TAKE)", "@").replace("SKIP)", "TAKE)").replace("@", "SKIP)")

def written_before(prefix, d):
    """Doses marked earlier on this path, other than d, in order (the cap for lever C)."""
    seen = []
    for i in prefix:
        k, _, _, dd, kind = STEPS[i]
        if kind == "mark" and dd != d and dd not in seen:
            seen.append(dd)
    return seen

def _reindent(text, extra):
    return "\n".join(" " * extra + l if l.strip() else l for l in text.split("\n"))

def extra_inputs(order, fault):
    """Inputs a fault purpose uses beyond the happy path (levers A and C)."""
    if not fault:
        return set()
    shape, pts = POINTS[fault]
    extra = set()
    for n, i in enumerate(order):
        k, inp, _, d, kind = STEPS[i]
        if k not in pts:
            continue
        if shape in ("write", "kill") and kind == "mark":
            extra.add(other_action(inp))
        if shape.startswith("read:"):
            extra |= {f"VIEW ({od})" for od in written_before(order[:n], d)}
    return extra

def state_before(prefix):
    """The day and the forbidden medicines after the happy-path steps in
    `prefix` (indices into STEPS), as the specification computes them."""
    dy = {d: "PENDING" for d in DOSES}
    ns = set()
    for i in prefix:
        _, inp, _, d, kind = STEPS[i]
        if kind in ("mark", "edit"):
            if kind == "mark" and "SKIP)" in inp and med(d) in ns:
                continue
            dy[d] = "TAKEN" if "TAKE)" in inp else "SKIPPED"
        elif kind == "delete":
            dy[d] = "ABSENT"
        elif kind == "forbid":
            ns.add(inp.split("(")[1].rstrip(")"))
    return dy, ns

def med(d):
    return "med_b" if d == "d_b" else "med_a"

def enabled_writes(prefix, act_only=False, stock_moving=False):
    """Every write the specification accepts after `prefix`, as (input, dose):
    a mark of a scheduled dose (a forbidden skip is refused, not written, so it
    is left out), a delete or a flipping edit of a recorded one. Lever B: the
    tester chooses WHICH write the fault strikes."""
    dy, ns = state_before(prefix)
    w = []
    for d in DOSES:
        if dy[d] == "PENDING":
            for a in ("TAKE", "SKIP"):
                if a == "SKIP" and (med(d) in ns or stock_moving):
                    continue
                w.append((f"ACT ({d}, {a})", d))
    if act_only:
        return w
    for d in DOSES:
        if dy[d] in ("TAKEN", "SKIPPED"):
            if not (stock_moving and dy[d] == "SKIPPED"):
                w.append((f"DELETE ({d})", d))
            flip = "SKIP" if dy[d] == "TAKEN" else "TAKE"
            w.append((f"EDIT ({d}, {flip})", d))
    return w

def walk(order, fault=None, ind=12, done=()):
    """The happy path along `order`; with a fault, the tester may inject it at
    each of its points, and the walk refuses once no point is left."""
    shape, pts = POINTS[fault] if fault else (None, [])
    remaining = [k for k in (STEPS[i][0] for i in order) if k in pts]
    out = []
    for n, i in enumerate(order):
        st = STEPS[i]
        key, inp, outp, d, kind = st
        rest_order = order[n + 1:]
        if key not in pts:
            out += plain(st)
            continue
        cont = walk(rest_order, fault, ind + 4, tuple(done) + tuple(order[:n + 1])) if any(STEPS[j][0] in pts for j in rest_order) \
            else " " * (ind + 4) + REFUSE
        p4 = ind + 4
        prefix = list(done) + list(order[:n])
        if shape in ("write", "kill"):
            def farm_for(dd):
                if shape == "write":
                    return block([f"{fault};", "WRITE_ERROR_SHOWN;",
                                  f"CONFIRM (ROLLED_BACK, ?any StockBand, ?any DoseState, {dd});", ACCEPT], p4)
                return (block([f"{fault};"], p4) + "\n" + alt(
                    [block([f"CONFIRM (COMMITTED, ?any StockBand, ?any DoseState, {dd})"], p4 + 4),
                     block([f"CONFIRM (ROLLED_BACK, ?any StockBand, ?any DoseState, {dd})"], p4 + 4)], p4)
                        + ";\n" + block([ACCEPT], p4))
            inner = alt([block([outp + ";"], p4 + 4) + "\n" + _reindent(cont, 4),
                         _reindent(farm_for(d), 4)], p4)
            top = [block([inp + ";"], p4) + "\n" + inner]
            # lever B: the fault may strike any other write the spec accepts here
            for w, dw in enabled_writes(prefix, act_only=(fault == "DB_ABORT")):
                if w != inp:
                    top.append(block([w + ";"], p4) + "\n" + farm_for(dw))
            out.append(("\n" + alt(top, ind)).lstrip("\n")[ind:])
            return "\n".join(_flat(out, ind))
        if shape == "cache":
            # lever B: after the priming, any stock-moving write the spec accepts
            arms = [block([inp + ";", outp + ";", ACCEPT], p4 + 4)]
            for w, dw in enabled_writes(prefix, stock_moving=True):
                if w != inp:
                    arms.append(block([w + ";", f"CONFIRM (COMMITTED, ?any StockBand, ?any DoseState, {dw});", ACCEPT], p4 + 4))
            farm = block([f"{fault};"], p4) + "\n" + alt(arms, p4)
            narm = block([inp + ";", outp + ";"], p4) + "\n" + cont
            out.append(("\n" + alt([farm, narm], ind)).lstrip("\n")[ind:])
            return "\n".join(_flat(out, ind))
        if shape.startswith("read:"):
            obs = shape.split(":")[1]
            farm = block([f"{fault};", obs + ";", ACCEPT], p4 + 4)
            narm = block([outp + ";"], p4 + 4) + "\n" + _reindent(cont, 4)
            top = [block([inp + ";"], p4) + "\n" + alt([narm, farm], p4)]
            # lever C: the same fault on a re-read of any OTHER dose
            for od in [x for x in DOSES if x != d]:
                top.append(block([f"VIEW ({od});", f"{fault};", obs + ";", ACCEPT], p4))
            out.append(("\n" + alt(top, ind)).lstrip("\n")[ind:])
            return "\n".join(_flat(out, ind))
        if shape == "loss":
            out += plain(st)
            # lever C: after the loss, the re-read may be of any dose
            arms = [block([f"VIEW ({d});", f"CONFIRM (COMMITTED, ?any StockBand, PENDING, {d});", ACCEPT], p4 + 4)]
            arms += [block([f"VIEW ({od});", f"CONFIRM (COMMITTED, ?any StockBand, ?any DoseState, {od});", ACCEPT], p4 + 4)
                     for od in DOSES if od != d]
            farm = block([f"{fault};"], p4) + "\n" + alt(arms, p4)
            # At the last point there is no continuation. A bare REFUSE arm
            # here would make this very state a refuse state (TESTOR marks
            # the SOURCE of a REFUSE transition) and cut the farm with it.
            last_point = cont.strip() == REFUSE
            out.append(("\n" + (farm if last_point else alt([farm, cont], ind))).lstrip("\n")[ind:] if not last_point
                       else farm.lstrip(" "))
            return "\n".join(_flat(out, ind))
    out.append(ACCEPT if not fault else REFUSE)
    return "\n".join(_flat(out, ind))

def _flat(items, ind):
    res = []
    for it in items:
        lines = it.split("\n")
        res.append(" " * ind + lines[0] if not lines[0].startswith(" ") else lines[0])
        res += lines[1:]
    return res

def used_inputs(order, extra=()):
    return {STEPS[i][1] for i in order} | set(extra)

def refuse(used, faults_out):
    arms = [f for f in FAULTS if f not in faults_out] + [x for x in ALL_INPUTS if x not in used]
    return "            alt\n                " + "\n            []  ".join(arms) + "\n            end alt;\n            " + REFUSE

# ---- strict closure --------------------------------------------------------
# TESTOR completes a purpose with a self-loop on every label a state does not
# mention. For an abstract input that is used LATER on the path, that loop lets
# the input fire anywhere: the CTG grows to the whole composition (4.8 M states
# for ue_kill) and a walk can circle on it for ever (the nominal walk re-read
# d_b 42 times). So every purpose state now names, as REFUSE, each abstract
# input it does not expect. The guard is deterministic: an alt's guard leaves
# out the first inputs of all its arms. Concrete SI labels and outputs keep
# their self-loops, which the walk needs.
ABSTRACT_INPUTS = FAULTS + ALL_INPUTS

def _parse(lines, k=0):
    """Body text -> list of items: ("act", label) | ("alt", [seq, ...]) | ("end", line)."""
    seq = []
    while k < len(lines):
        t = lines[k].strip()
        if not t:
            k += 1; continue
        if t == "alt":
            arms, k = [], k + 1
            while True:
                arm, k = _parse(lines, k)
                arms.append(arm)
                t2 = lines[k].strip()
                k += 1
                if t2.startswith("end alt"):
                    break
            seq.append(("alt", arms))
            continue
        if t == "[]" or t.startswith("end alt"):
            return seq, k
        if t.startswith("loop TP_"):
            seq.append(("end", t)); k += 1; continue
        seq.append(("act", t.rstrip(";"))); k += 1
    return seq, k

def _first(seq):
    kind, v = seq[0]
    if kind == "act":
        return {v}
    if kind == "alt":
        return set().union(*(_first(a) for a in v))
    return set()

def _guard(expected, ind):
    arms = [x for x in ABSTRACT_INPUTS if x not in expected]
    p = " " * ind
    return (f"{p}    alt\n{p}        " + f"\n{p}    []  ".join(arms) + f"\n{p}    end alt;\n{p}    {REFUSE}")

def _emit(seq, ind, head_free=False):
    """Emit `seq` with a guard at each state. With head_free, the first item
    is an arm's head: the enclosing alt's guard already covers its inputs, so
    it gets none of its own (a second guard would make the purpose
    nondeterministic)."""
    out = []
    for n, (kind, v) in enumerate(seq):
        p = " " * ind
        semi = ";" if n + 1 < len(seq) else ""
        free = head_free and n == 0
        if kind == "end":
            out.append(p + v)
        elif kind == "act":
            if free:
                out.append(p + v + semi)
            else:
                out.append(f"{p}alt\n{p}    {v}\n{p}[]\n{_guard({v}, ind)}\n{p}end alt{semi}")
        else:
            arms = [_emit(a, ind + 4, head_free=True) for a in v]
            if not free:
                arms.append(_guard(set().union(*(_first(a) for a in v)), ind))
            out.append(f"{p}alt\n" + f"\n{p}[]\n".join(arms) + f"\n{p}end alt{semi}")
    return "\n".join(out)

def strict(body):
    seq, _ = _parse(body.split("\n"))
    return _emit(seq, 8)

def module(name, doc, body, used, faults_out):
    return f"""module tp_{name} (medtimer_types, medtimer_fixture) is

(* {doc} *)

process MAIN [
{GATES}
] is
{strict(body)}
end process

end module
"""

def domain(prefix_keys, lines):
    order = [IDX[k] for k in prefix_keys]
    body = "\n".join(_flat(sum((plain(STEPS[i]) for i in order), []) + lines + [ACCEPT], 8))
    return body, used_inputs(order, [l.rstrip(";") for l in lines if l.split()[0] in ("ADD_MEDICINE", "ACT", "DELETE", "EDIT", "VIEW", "NO_SKIP")])

files = {}
# the happy path: three orderings, one per first input
arms = [walk(o, None, 12) for o in ORDERINGS]
body = alt(arms, 8)
files["nominal"] = module("nominal", """SHAPE    the happy path: no fault, three orderings of the same steps.
   PATH     create a medicine; take d_a1, re-read; delete d_a1, re-read; skip
            d_a2, re-read; forbid skipping A; take d_a3, re-read; take d_b,
            re-read; edit d_a3 to Skipped. Orderings 2 and 3 move B's dose and
            the create earlier; every disruption follows ordering 1.
   Expected FAIL at the edit, the last step (the edit sheet moves no stock);
            every earlier checkpoint PASS.""", body, used_inputs(range(len(STEPS))), [])
docs = {
    "APP_WRITE_FAIL": "the record update fails (trigger), at each of the six writes",
    "INFRA_STORAGE_FULL": "the data partition is full, at each of the six writes",
    "UE_KILL": "the process is killed right after the tap, at each of the six writes",
    "DB_ABORT": "the record insert fails (trigger), at each of the four marks",
    "APP_CACHE_STALE": "the medicine list is read just before each stock-moving write",
    "DB_CORRUPT": "the newest record's status is made unreadable, at each re-read",
    "DB_CORRUPT_STOCK": "the stock is made negative, at each re-read",
    "INFRA_STORAGE_MEDIA": "the store is made unreadable, at each re-read",
    "DB_EVENT_LOSS": "the record just marked is deleted, after each of the four marks",
}
for f in FAULTS:
    b = walk(ORDERINGS[0], f, 8)
    files[f.lower()] = module(f.lower(), f"""SHAPE    the happy path (ordering 1) with {f} at each of its points.
   TARGET   {docs[f]}.
   ACCEPT   the fault fires at a point and the app answers as owed there.
   REFUSE   the walk passes every point without the fault; any other fault;
            any input off the path. One test case per point (extract_all).""",
        b, used_inputs(ORDERINGS[0]) | {x for x in ALL_INPUTS if x + ";" in b}, [f])
for name, doc, keys, lines in (
    ("input_invalid", "the empty medicine name at the create step (O9); expected FAIL", [],
     ["ADD_MEDICINE (INVALID);", "REJECT_SHOWN;"]),
    ("cannot_skip", "skip d_a3 after forbidding skips (O8); expected FAIL",
     ["create", "take_a1", "view_a1", "del_a1", "view_a1b", "skip_a2", "view_a2", "forbid_a"],
     ["ACT (d_a3, SKIP);", "CONFIRM (REJECTED, ?any StockBand, PENDING, d_a3);"]),
    ("delete_skipped", "delete the skipped d_a2 (O5: no refund); expected FAIL",
     ["create", "take_a1", "view_a1", "del_a1", "view_a1b", "skip_a2", "view_a2"],
     ["DELETE (d_a2);", "CONFIRM (COMMITTED, ?any StockBand, ABSENT, d_a2);"]),
    ("edit_flip", "edit the skipped d_a2 to Taken (O5: the stock follows); expected FAIL",
     ["create", "take_a1", "view_a1", "del_a1", "view_a1b", "skip_a2", "view_a2"],
     ["EDIT (d_a2, TAKE);", "CONFIRM (COMMITTED, ?any StockBand, TAKEN, d_a2);"]),
):
    b, used = domain(keys, lines)
    files[name] = module(name, f"""SHAPE    domain disruption on the happy path (ordering 1).
   TARGET   {doc}.""", b, used, [])
for n, t in files.items():
    open(os.path.join(D, f"tp_{n}.lnt"), "w").write(t)
print(" ".join(sorted(files)))
