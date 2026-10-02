#!/usr/bin/env python3
"""check_alphabet.py -- verify that one case study's artefacts agree on the
alphabet, before a CADP cycle is spent on them.

    python framework/scripts/check_alphabet.py systems/<sut>

A fault name must be identical in six places (specification, System
Interface, composition, every test purpose, the .io, disruption_mapping.yml);
every el_/cv_/rt_ value the SI uses must have an interpretation in
concrete_domain.yml; every screen needs an anchor; the fixture's default
record must be the record of the default item; and the .io must classify
every output as an output. None of this is checked by CADP, and each of these
mismatches has cost a generation run or a sweep once.

SUT-agnostic: everything is read from the system directory. The SUT name is
the directory's basename; file names follow the template layout
(model/specification_<sut>.lnt, model/system_interface_<sut>.lnt,
model/compose_<sut>.lnt, model/<sut>_types.lnt, model/<sut>_fixture.lnt,
test_purposes/tp_*.lnt, testor/<sut>.io, properties/*.yml).

Exit 1 on any FAIL. WARN lines are advisory.
"""
import os
import re
import sys
import glob

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

PRIMITIVES = {"navigate", "tap", "enter_text", "wait_for", "observe",
              "click", "type_into"}
VERDICT_GATES = {"TP_ACCEPT", "TP_REFUSE", "OTHERWISE"}
NOMINAL_NAMES = {"nominal", "happy"}   # plus any "nominal_<branch>": one fault-free case per journey

fails = []
warns = []


def fail(msg):
    fails.append(msg)
    print(f"  [FAIL] {msg}")


def warn(msg):
    warns.append(msg)
    print(f"  [warn] {msg}")


def ok(msg):
    print(f"  [ok]   {msg}")


def strip_comments(text):
    text = re.sub(r"\(\*.*?\*\)", " ", text, flags=re.S)
    text = re.sub(r"--[^\n]*", " ", text)
    return text


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def parse_gate_list(header):
    """'A : T, B, C : none' -> {A: T, B: none, C: none} (order kept)."""
    gates = {}
    pending = []
    for tok in header.split(","):
        tok = tok.strip()
        if not tok:
            continue
        if ":" in tok:
            name, typ = tok.split(":", 1)
            pending.append(name.strip())
            for n in pending:
                gates[n] = typ.strip()
            pending = []
        else:
            pending.append(tok)
    return gates


def process_header(text, name):
    m = re.search(r"process\s+" + name + r"\s*\[(.*?)\]\s*is\b", text, re.S | re.I)
    return parse_gate_list(m.group(1)) if m else None


def process_body(text, name):
    # `process P [gates] (params) is`: the value-parameter list is optional
    m = re.search(r"process\s+" + name + r"\s*\[.*?\]\s*(?:\(.*?\))?\s*is\b(.*?)end\s+process",
                  text, re.S | re.I)
    return m.group(1) if m else ""


def enum_types(text):
    out = {}
    for m in re.finditer(r"\btype\s+(\w+)\s+is\s+(.*?)\bend\s+type", text, re.S):
        body = re.sub(r"\bwith\s*==.*$", "", m.group(2).strip(), flags=re.S)
        vals = [v.strip() for v in body.split(",") if v.strip()]
        if vals and all(re.fullmatch(r"\w+", v) for v in vals):
            out[m.group(1)] = vals
    return out


def main(sysdir, ov=None):
    ov = ov or {}
    sysdir = sysdir.rstrip("/")
    sut = os.path.basename(sysdir)
    model = os.path.join(sysdir, "model")
    p_spec = ov.get("spec") or os.path.join(model, f"specification_{sut}.lnt")
    p_si = ov.get("si") or os.path.join(model, f"system_interface_{sut}.lnt")
    p_comp = ov.get("compose") or os.path.join(model, f"compose_{sut}.lnt")
    p_types = ov.get("types") or os.path.join(model, f"{sut}_types.lnt")
    p_fix = ov.get("fixture") or os.path.join(model, f"{sut}_fixture.lnt")
    p_io = ov.get("io") or os.path.join(sysdir, "testor", f"{sut}.io")
    props = ov.get("properties") or os.path.join(sysdir, "properties")
    p_cd = os.path.join(props, "concrete_domain.yml")
    p_td = os.path.join(props, "type_description.yml")
    p_dm = os.path.join(props, "disruption_mapping.yml")
    tps = sorted(glob.glob(os.path.join(ov.get("tp_dir") or os.path.join(sysdir, "test_purposes"), "tp_*.lnt")))

    print(f"== {sut}: alphabet consistency")
    for p in (p_spec, p_si, p_comp, p_types, p_io, p_cd, p_td, p_dm):
        if not os.path.exists(p):
            fail(f"missing {os.path.relpath(p)}")
    if fails:
        return finish()

    spec = strip_comments(read(p_spec))
    si = strip_comments(read(p_si))
    comp = strip_comments(read(p_comp))
    types = strip_comments(read(p_types))
    fixture = strip_comments(read(p_fix)) if os.path.exists(p_fix) else ""

    # ---- 1. the alphabet, from SPEC ---------------------------------------
    spec_gates = process_header(spec, "SPEC")
    if not spec_gates:
        fail("no `process SPEC [...] is` in the specification")
        return finish()
    alphabet = set(spec_gates)
    nullary = {g for g, t in spec_gates.items() if t.lower() == "none"}
    typed = alphabet - nullary
    ok(f"SPEC alphabet: {len(typed)} typed + {len(nullary)} parameterless gates")

    # every gate offered somewhere (no dead gates)
    spec_body_all = re.sub(r"process\s+SPEC\s*\[.*?\]\s*is.*?end\s+process", " ",
                           spec, flags=re.S | re.I)
    for g in sorted(nullary):
        if not re.search(r"\b" + g + r"\b\s*(;|\n|\[\]|end)", spec_body_all):
            warn(f"{g} is in SPEC's alphabet but no process body seems to offer it (dead gate?)")

    # ---- 2. disruption mapping: faults vs observables -----------------------
    dm = yaml.safe_load(read(p_dm)) if yaml else {}
    dm_faults = set((dm or {}).get("faults") or (dm or {}).get("disruptions") or {})
    faults = nullary & dm_faults
    observables = nullary - dm_faults
    for k in sorted(dm_faults - alphabet):
        t = ((dm.get("faults") or {}).get(k) or {}).get("timing")
        if t == "none":
            ok(f"{k}: in disruption_mapping with timing none (parameter-borne), not a gate")
        else:
            fail(f"disruption_mapping fault {k} is not a gate of SPEC")
    for g in sorted(nullary):
        if g in faults:
            continue
        if re.search(r"_(DETECTED|SHOWN|WARNING|ERROR)$", g):
            continue
        warn(f"{g} is parameterless, not in disruption_mapping, and not named like an observable: fault without injection, or observable?")
    ok(f"faults: {sorted(faults)}")
    ok(f"observables: {sorted(observables)}")

    # ---- 3. SI and COMPOSED carry the same alphabet -------------------------
    si_gates = process_header(si, "SI")
    if not si_gates:
        fail("no `process SI [...] is` in the System Interface")
    else:
        si_abstract = {g for g in si_gates if g not in PRIMITIVES}
        prims = {g for g in si_gates if g in PRIMITIVES}
        if si_abstract != alphabet:
            fail(f"SI alphabet differs from SPEC: missing {sorted(alphabet - si_abstract)}, extra {sorted(si_abstract - alphabet)}")
        else:
            ok(f"SI carries SPEC's alphabet plus primitives {sorted(prims)}")
    comp_gates = process_header(comp, "COMPOSED")
    if not comp_gates:
        fail("no `process COMPOSED [...] is` in the composition")
    else:
        comp_abstract = {g for g in comp_gates if g not in PRIMITIVES}
        if comp_abstract != alphabet:
            fail(f"COMPOSED alphabet differs from SPEC: missing {sorted(alphabet - comp_abstract)}, extra {sorted(comp_abstract - alphabet)}")
        body = process_body(comp, "COMPOSED")
        m = re.search(r"\bpar\s+(.*?)\bin\b", body, re.S)
        sync = set(re.findall(r"\b[A-Z][A-Z_0-9]*\b", m.group(1))) if m else set()
        if sync != alphabet:
            fail(f"COMPOSED synchronises on {sorted(sync ^ alphabet)} differently from SPEC's alphabet")
        else:
            ok("COMPOSED synchronises SPEC and SI on the whole alphabet")

    # ---- 4. test purposes ---------------------------------------------------
    if not tps:
        fail("no test_purposes/tp_*.lnt")
    for tp in tps:
        name = os.path.basename(tp)[3:-4]
        text = strip_comments(read(tp))
        hdr = process_header(text, "MAIN")
        if not hdr:
            fail(f"{name}: no `process MAIN [...] is`")
            continue
        declared = set(hdr) - VERDICT_GATES
        if declared != alphabet:
            fail(f"{name}: gate list differs from SPEC: missing {sorted(alphabet - declared)}, extra {sorted(declared - alphabet)}")
        if not ({"TP_ACCEPT", "TP_REFUSE"} <= set(hdr)):
            fail(f"{name}: must declare TP_ACCEPT and TP_REFUSE (renamed by accept.ren / refuse.ren)")
        # A purpose may factor its accept path into helper processes that MAIN
        # calls (a history, a target), so the behaviour is the bodies of EVERY
        # process in the module. Bodies only: the headers declare every gate,
        # and reading them would make the closure check below vacuous.
        body = "\n".join(process_body(text, p) or ""
                         for p in re.findall(r"\bprocess\s+(\w+)\s*\[", text))
        missing = [f for f in sorted(faults) if not re.search(r"\b" + f + r"\b", body)]
        if missing:
            fail(f"{name}: incomplete negative closure, faults never mentioned: {missing}")
        target = name.upper()
        if name in NOMINAL_NAMES or name.startswith("nominal_"):
            ok(f"{name}: nominal (untargeted by design)")
        elif target in dm_faults:
            if target in faults and not re.search(r"\b" + target + r"\b\s*;", body):
                warn(f"{name}: target {target} never fired in the accept path?")
            ok(f"{name}: targets {target}")
        else:
            fail(f"{name}: file name does not match a disruption_mapping fault (tc_{name}.aut would run UNTARGETED)")
        if re.search(r"\bloop\s+TP_ACCEPT\s+end\s+loop", body) is None:
            fail(f"{name}: no `loop TP_ACCEPT end loop` -- no verdict is reachable")

    # ---- 5. the .io -----------------------------------------------------------
    io_lines = [l.strip() for l in read(p_io).splitlines() if l.strip()]
    if not io_lines or io_lines[0].lower() != "input":
        fail(".io must start with the line `input`")
    pats = [l.strip('"') for l in io_lines[1:]]
    def is_input(label):
        return any(re.fullmatch(p, label) for p in pats)
    for g in sorted(faults):
        if not is_input(g):
            fail(f".io: fault {g} is not an input (exact pattern \"{g}\" expected)")
    for g in sorted(observables):
        if is_input(g):
            fail(f".io: observable {g} matches an input pattern -- the SUT's answer would become a tester action")
    for g in sorted(typed):
        lbl = f"{g} !X"
        # a typed gate that starts a journey is an input; one that answers is not.
        # Heuristic: the SI realises inputs with tap/enter_text before them and
        # outputs with observe before them.
        seg = re.search(r"((?:[^\n]*\n){1,4})\s*" + g + r"\s*\(", si)
        before = seg.group(1) if seg else ""
        looks_output = "observe" in before
        if looks_output and is_input(lbl):
            fail(f".io: {g} is realised by an observe in the SI but listed as an input")
        if not looks_output and not is_input(lbl):
            warn(f".io: {g} is not an input; if the tester initiates it, add \"{g} .*\"")
    # only the primitives this SI declares (tap/enter_text on Android, click/type_into on the web)
    si_prims = {g.upper() for g in (si_gates or {}) if g in PRIMITIVES}
    for prim in sorted(si_prims & {"NAVIGATE", "TAP", "ENTER_TEXT", "CLICK", "TYPE_INTO"}):
        if not is_input(f"{prim} !X"):
            warn(f".io: concrete primitive {prim} is not an input")
    for prim in ("WAIT_FOR", "OBSERVE"):
        if is_input(f"{prim} !X"):
            warn(f".io: {prim} is an input; the project convention treats it as an output (the SUT shows the element)")

    # ---- 6. concrete domain vs the SI's D_sys usage --------------------------
    cd = yaml.safe_load(read(p_cd)) if yaml else {}
    cd = cd or {}
    si_body = process_body(si, "SI")
    # rt_ routes, sel_ click/type targets (web), el_ wait/observe, cv_ typed or tapped values
    used = {p: set(re.findall(r"\b" + p + r"\w+\b", si_body)) for p in ("rt_", "sel_", "el_", "cv_")}
    # values reached through an L_* translation function the SI calls count as used
    for m in re.finditer(r"function\s+(L_\w+)\s*\(.*?\)\s*:\s*\w+\s+is(.*?)end\s+function", types, re.S):
        if re.search(r"\b" + m.group(1) + r"\b", si_body):
            for v in re.findall(r"return\s+(\w+)", m.group(2)):
                for p in ("rt_", "sel_", "el_", "cv_"):
                    if v.startswith(p):
                        used[p].add(v)
    for prefix, key in (("rt_", "routes"), ("sel_", "selectors"), ("el_", "elements"), ("cv_", "concrete_values")):
        have = set((cd.get(key) or {}).keys())
        for v in sorted(used[prefix] - have):
            fail(f"concrete_domain.yml {key}: no interpretation for {v} (used by the SI)")
        for v in sorted(have - used[prefix]):
            if v.startswith(prefix):
                warn(f"concrete_domain.yml {key}: {v} is not used by the SI")
        for v in have:
            if v != v.lower() and v.startswith(prefix):
                fail(f"concrete_domain.yml {key}: {v} must be lower-case")
    tenums = enum_types(types)
    # every D_sys value the SI uses must be declared by SOME enum type of the
    # types file (the type's name is the SUT's choice: ConcreteValue, Selector,
    # InputValue ...)
    declared = set().union(*tenums.values()) if tenums else set()
    for prefix in ("rt_", "sel_", "el_", "cv_"):
        for v in sorted(used[prefix] - declared):
            fail(f"types: SI uses {v} but no enum type in the types file declares it")
    # init values of the SI's var block must be concrete_values keys (parser)
    m = re.search(r"\bvar\b(.*?)\bin\b(.*?)\bloop\b", si_body, re.S)
    if m:
        inits = re.findall(r"(\w+)\s*:=\s*([A-Za-z_]\w*)", m.group(2))
        cvals = set((cd.get("concrete_values") or {}).keys())
        # only variables the SI passes through `tap (L_* (var))` reach the parser's
        # map by init value (Android path); click / type_into use the L table
        lvars = set(re.findall(r"\btap\s*\(\s*L_\w+\s*\(\s*(\w+)\s*\)", si_body))
        for var, val in inits:
            if var not in lvars or val in ("true", "false") or val.startswith("SCR_"):
                continue
            if val not in cvals:
                warn(f"SI init `{var} := {val}`: {val} is not a concrete_values key (the parser's map for tap (L_f ({var})) will hold the bare token)")
    # screens
    screens = set(re.findall(r"\bSCR_[A-Z_0-9]+\b", si))
    anchors = cd.get("screen_anchors") or {}
    if "SCR_HOME" not in screens:
        fail("the SI must have a screen named SCR_HOME (the executor's initial screen is hard-coded)")
    for s in sorted(screens - set(anchors)):
        # the initial screen may legitimately precede any app page (a web reset
        # clears cookies without navigating), and the framework skips the check
        # for an unanchored screen
        if s == "SCR_HOME":
            warn("screen_anchors: SCR_HOME has no anchor; the initial-screen check will be skipped")
        else:
            fail(f"screen_anchors: no anchor for {s}")
    for s, el in anchors.items():
        if el not in (cd.get("elements") or {}):
            fail(f"screen_anchors: {s} -> {el} is not in elements")
    for r, url in (cd.get("routes") or {}).items():
        if "SESSION" in str(url).upper() and "{{SESSION_ID}}" not in str(url):
            fail(f"routes: {r} mentions SESSION without {{{{SESSION_ID}}}} (validate_invariants aborts)")

    # ---- 7. type description vs the types file --------------------------------
    td = yaml.safe_load(read(p_td)) if yaml else {}
    td = td or {}
    for tname, spec_ in td.items():
        if not isinstance(spec_, dict):
            continue
        if "base" not in spec_:
            fail(f"type_description {tname}: no base")
        if spec_.get("base") == "Enum":
            vals = spec_.get("values") or []
            lnt = tenums.get(tname)
            if lnt is None:
                warn(f"type_description {tname}: Enum with no LNT type of that name")
            elif list(vals) != lnt:
                fail(f"type_description {tname}: values {vals} differ from the LNT type {lnt}")
        buf = spec_.get("bucket_unit_from")
        if buf:
            tgt = td.get(buf.get("type")) or {}
            if buf.get("value") not in (tgt.get("abstract_values") or {}):
                fail(f"type_description {tname}: bucket_unit_from {buf} does not resolve")

    # ---- 8. fixture consistency ---------------------------------------------
    if fixture:
        # the default item is whichever nullary `default*` function returns a
        # value item_of maps TO; the default record returns a value item_of maps FROM
        item_of = dict(re.findall(r"(\w+)\s*->\s*return\s+(\w+)",
                                  (re.search(r"function\s+item_of.*?end\s+function", types, re.S) or re.match("", "")).group(0)))
        defaults = re.findall(r"function\s+(default\w+)\s*:\s*\w+\s+is\s+return\s+(\w+)", fixture)
        di = next((m for m in re.finditer(r"function\s+default\w+\s*:\s*\w+\s+is\s+return\s+(\w+)", fixture)
                   if m.group(1) in set(item_of.values())), None)
        dr = next((m for m in re.finditer(r"function\s+default\w+\s*:\s*\w+\s+is\s+return\s+(\w+)", fixture)
                   if m.group(1) in item_of), None)
        if di and dr:
            if item_of.get(dr.group(1)) != di.group(1):
                fail(f"fixture: item_of ({dr.group(1)}) = {item_of.get(dr.group(1))}, but defaultItem = {di.group(1)}")
            else:
                ok(f"fixture: defaultRecord {dr.group(1)} is the record of defaultItem {di.group(1)}")
            buf = (td.get("StateBand") or {}).get("bucket_unit_from") or {}
            if buf and buf.get("value") != di.group(1):
                fail(f"type_description StateBand.bucket_unit_from.value = {buf.get('value')} but defaultItem = {di.group(1)}")
            for tname, spec_ in td.items():
                if isinstance(spec_, dict) and spec_.get("origin") == "system_generated" \
                        and "abstract_values" in spec_ and spec_.get("base") == "Integer":
                    if di.group(1) not in spec_["abstract_values"]:
                        fail(f"type_description {tname}: no abstract_values entry for defaultItem {di.group(1)} -- the oracle would silently skip")
        else:
            warn("fixture: defaultItem / defaultRecord not found")

    # ---- 9. remaining holes ---------------------------------------------------
    n = 0
    for root, _, files in os.walk(sysdir):
        if "/sut" in root or "/generated" in root or "/legacy" in root:
            continue
        for f in files:
            if f.endswith((".lnt", ".yml", ".sh", ".io")):
                try:
                    n += read(os.path.join(root, f)).count("HOLE")
                except OSError:
                    warn(f"unreadable (dangling link?): {os.path.join(root, f)}")
    if n:
        warn(f"{n} HOLE markers remain")
    return finish()


def finish():
    print()
    print(f"{len(fails)} FAIL, {len(warns)} warn")
    return 1 if fails else 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sysdir", help="systems/<sut>")
    for k in ("spec", "si", "compose", "types", "fixture", "io", "tp_dir", "properties"):
        ap.add_argument("--" + k.replace("_", "-"), dest=k, default=None,
                        help=f"override the default location of the {k} artefact")
    a = ap.parse_args()
    sys.exit(main(a.sysdir, {k: getattr(a, k) for k in ("spec", "si", "compose", "types", "fixture", "io", "tp_dir", "properties")}))
