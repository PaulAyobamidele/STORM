#!/usr/bin/env python3
"""ctg_cover.py -- transition coverage of a complete test graph (CTG) by a set
of test cases, and a Graphviz drawing of the CTG with one case highlighted.

    python framework/scripts/ctg_cover.py CTG.aut --io SUT.io \
        --cases DIR_OR_GLOB [--highlight CASE.aut] [--excerpt] [--lr] [--compact] [--short] [--fold] [--grid N] [--lanes N] [--stack]
        [--dot out.dot]

Inputs are Aldebaran files (`bcg_io X.bcg X.aut` on the CADP node):
  CTG.aut     the complete test graph TESTOR built for one purpose
  --cases     test cases extracted from it (extract_all's TC.*.bcg, or
              bcg_control -all's tc-N.bcg), converted to .aut
  --io        the TESTOR match file: the labels it lists are tester inputs

A case's transitions are matched to the CTG by walking both graphs together
from their initial states on equal labels, so a case's state numbering does
not matter (extract_all renumbers; bcg_control -keep does not).

Drawing: the highlighted case's states and transitions are red; at every state
of that case, the tester inputs the case did not take are blue (the other
choices a covering suite must also take); everything else is black.
--excerpt keeps only the highlighted case's states and their direct successors.

SUT-agnostic: everything comes from the files given.
"""
import argparse
import glob
import os
import re
import sys
from collections import defaultdict, deque

AUT_HEAD = re.compile(r"^des\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")
AUT_EDGE = re.compile(r'^\(\s*(\d+)\s*,\s*("(?:[^"\\]|\\.)*"|[^,]+?)\s*,\s*(\d+)\s*\)\s*$')
VERDICTS = (":PASS:", ":INCONCLUSIVE:", ":FAIL:", ":DELTA:")


def read_aut(path):
    init, edges = None, []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = AUT_HEAD.match(line)
            if m:
                init = int(m.group(1))
                continue
            m = AUT_EDGE.match(line)
            if not m:
                sys.exit(f"{path}: cannot parse line: {line}")
            lab = m.group(2)
            if lab.startswith('"') and lab.endswith('"'):
                lab = lab[1:-1]
            edges.append((int(m.group(1)), lab, int(m.group(3))))
    if init is None:
        sys.exit(f"{path}: no 'des' header")
    return init, edges


def read_io(path):
    """Patterns listed after `input` in a TESTOR match file (full match)."""
    pats = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line == "input" or line.startswith("--"):
                continue
            if line.startswith('"') and line.endswith('"'):
                line = line[1:-1]
            pats.append(re.compile(line))
    return pats


def is_input(label, pats):
    return any(p.fullmatch(label) for p in pats)


def covered_by(ctg_init, ctg_edges, tc_init, tc_edges):
    """CTG edges (src, label, dst) a test case traverses."""
    out_c, out_t = defaultdict(list), defaultdict(list)
    for e in ctg_edges:
        out_c[e[0]].append(e)
    for e in tc_edges:
        out_t[e[0]].append(e)
    seen, hit = set(), set()
    todo = deque([(tc_init, ctg_init)])
    while todo:
        t, c = todo.popleft()
        if (t, c) in seen:
            continue
        seen.add((t, c))
        for (_, lab, t2) in out_t[t]:
            for e in out_c[c]:
                if e[1] == lab:
                    hit.add(e)
                    todo.append((t2, e[2]))
    return hit


def case_files(spec):
    if os.path.isdir(spec):
        files = glob.glob(os.path.join(spec, "*.aut"))
    else:
        files = glob.glob(spec)
    return sorted(files, key=lambda p: [int(x) if x.isdigit() else x
                                        for x in re.split(r"(\d+)", p)])


def dot_label(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def short_label(s):
    """Gate name plus its first parameter, without the !, the symbolic
    prefixes (SEL_/EL_/RT_/CV_) and the remaining parameters:
    "WAIT_FOR !EL_WRITE_ERROR" -> "WAIT_FOR WRITE_ERROR",
    "CONFIRM !ROLLED_BACK !N1 ..." -> "CONFIRM ROLLED_BACK..."."""
    parts = s.split()
    if len(parts) < 2 or s in VERDICTS:
        return s
    first = re.sub(r"^(SEL|EL|RT|CV)_", "", parts[1].lstrip("!"))
    return f"{parts[0]} {first}" + ("..." if len(parts) > 2 else "")


CONCRETE = {"NAVIGATE", "CLICK", "TAP", "TYPE_INTO", "ENTER_TEXT", "WAIT_FOR", "OBSERVE"}


def gate_of(label):
    return label.split()[0].rstrip(";") if label.split() else label


def fold_runs(edges, colour, init):
    """Collapse each run of concrete UI steps through pass-through states
    (one edge in, one edge out, same colour) into a single edge. Abstract
    gates, fault gates, verdicts and branch points are never folded.
    Returns [(src, [labels], dst, colour)] and the folded-away states."""
    loops = [e for e in edges if e[0] == e[2]]
    plain = [e for e in edges if e[0] != e[2]]
    out, inn = defaultdict(list), defaultdict(list)
    for e in plain:
        out[e[0]].append(e)
        inn[e[2]].append(e)

    def interior(st):
        if st == init or len(inn[st]) != 1 or len(out[st]) != 1:
            return False
        a, b = inn[st][0], out[st][0]
        return (gate_of(a[1]) in CONCRETE and gate_of(b[1]) in CONCRETE
                and colour[a] == colour[b])

    gone = {st for st in set(out) | set(inn) if interior(st)}
    result = []
    for e in plain:
        if e[0] in gone:
            continue                      # reached from the run's start
        run, cur = [e], e
        while gate_of(cur[1]) in CONCRETE and cur[2] in gone:
            cur = out[cur[2]][0]
            run.append(cur)
        result.append((e[0], [r[1] for r in run], cur[2], colour[e]))
    for e in loops:
        if e[0] not in gone:
            result.append((e[0], [e[1]], e[2], colour[e]))
    return result, gone


def grid_positions(drawn, init, cols, dx=118, dy=58):
    """Pin the red path on a boustrophedon grid of `cols` states per row
    (points); every other drawn state goes just below the state it leaves."""
    nxt = {a: b for (a, labs, b, col) in drawn if col == "red" and a != b}
    path, st = [init], init
    while st in nxt and nxt[st] not in path:
        st = nxt[st]
        path.append(st)
    pos = {}
    for i, st in enumerate(path):
        r, c = divmod(i, cols)
        if r % 2:
            c = cols - 1 - c
        pos[st] = (c * dx, -r * 2 * dy)
    below = defaultdict(int)
    for (a, labs, b, col) in drawn:
        if b not in pos and a in pos:
            below[a] += 1
            x, y = pos[a]
            pos[b] = (x + (below[a] - 1) * dx / 2, y - dy)
    return pos


def lane_positions(drawn, init, cols, dx=76, dy=60):
    """Whole-graph layout that fits a page. The longest chain from the
    initial state (the spine) snakes across rows of `cols` states. Every
    other chain gets its own band of rows directly under the spine row it
    branches from, using the inner columns only, so the spine's row-to-row
    connectors (in the outer columns) never cross it. Nothing is dropped."""
    out = defaultdict(list)
    for (a, labs, b, col) in drawn:
        if a != b and b not in out[a]:
            out[a].append(b)
    memo = {}

    def longest(st, seen=()):
        if st in memo:
            return memo[st]
        best = 0
        for b in out[st]:
            if b not in seen:
                best = max(best, 1 + longest(b, seen + (st,)))
        memo[st] = best
        return best

    taken = set()

    def chain_from(st):
        ch, side = [st], []
        taken.add(st)
        while True:
            nxt = sorted((b for b in out[ch[-1]] if b not in taken),
                         key=lambda b: -longest(b))
            if not nxt:
                return ch, side
            for b in nxt[1:]:
                side.append((ch[-1], b))
            ch.append(nxt[0])
            taken.add(nxt[0])

    pos, row = {}, [0]

    def place(ch, lo, hi):
        width = hi - lo
        bands = defaultdict(list)
        for i in range(0, len(ch), width):
            seg = ch[i:i + width]
            r = row[0]
            for j, st in enumerate(seg):
                c = j if (i // width) % 2 == 0 else width - 1 - j
                pos[st] = ((lo + c) * dx, -r * dy)
            row[0] += 1
            # side chains branching off this segment go right under it
            for (src, b) in pending.get(id(ch), []):
                if src in seg and b not in taken:
                    sub, subside = chain_from(b)
                    pending[id(sub)] = subside
                    place(sub, 1, cols - 1)

    spine, side = chain_from(init)
    pending = {id(spine): side}
    place(spine, 0, cols)
    return pos


def stacked(label):
    """A label with one token per line: nothing removed, only wrapped."""
    if label == ":DELTA:":
        return "\u03b4"
    return "\n".join(label.split())


def run_label(labels, short):
    if short == "stack":
        return "\n".join(stacked(x) for x in labels)
    labs = [("\u03b4" if x == ":DELTA:" else short_label(x)) if short else x for x in labels]
    if len(labs) <= 3:
        return "\n".join(labs)
    return f"{labs[0]}\n(+{len(labs) - 2} steps)\n{labs[-1]}"


def write_dot(path, ctg_init, ctg_edges, red, pats, excerpt, rankdir="TB",
              compact=False, short=False, fold=False, rows=1):
    red_states = {e[0] for e in red} | {e[2] for e in red} | {ctg_init}
    blue = {e for e in ctg_edges
            if e[0] in red_states and e not in red and is_input(e[1], pats)}
    if excerpt:
        keep = red_states | {e[2] for e in ctg_edges if e[0] in red_states}
        edges = [e for e in ctg_edges if e[0] in keep and e[2] in keep]
    else:
        edges = list(ctg_edges)
    colour = {e: ("red" if e in red else "blue" if e in blue else "black") for e in edges}
    if fold:
        drawn, gone = fold_runs(edges, colour, ctg_init)
    else:
        drawn, gone = [(e[0], [e[1]], e[2], colour[e]) for e in edges], set()
    states = ({d[0] for d in drawn} | {d[2] for d in drawn} | {ctg_init}) - gone
    with open(path, "w") as f:
        f.write(f"digraph CTG {{\n  rankdir={rankdir};\n")
        pos = (lane_positions(drawn, ctg_init, -rows) if rows < -1
               else grid_positions(drawn, ctg_init, rows) if rows > 1 else {})
        if pos:
            f.write("  graph [splines=true, outputorder=edgesfirst];\n")
        if compact:
            f.write("  graph [nodesep=0.12, ranksep=0.22, margin=0, pad=0.02];\n"
                    "  node [shape=circle, width=0.28, height=0.28, fixedsize=true, "
                    "fontsize=7, penwidth=0.8];\n"
                    "  edge [fontsize=6, arrowsize=0.5, penwidth=0.8];\n")
        else:
            f.write("  node [shape=circle, fontsize=10];\n  edge [fontsize=8];\n")
        for st in sorted(states):
            col = "red" if st in red_states else "black"
            at = f', pos="{pos[st][0]:.0f},{pos[st][1]:.0f}!"' if st in pos else ""
            f.write(f'  {st} [color={col}, fontcolor={col}{at}];\n')
        efs = 5.5 if compact else 8
        for i, (a, labs, b, col) in enumerate(drawn):
            text = run_label(labs, short)
            if not (pos and a != b and a in pos and b in pos):
                f.write(f'  {a} -> {b} [label="{dot_label(text)}", '
                        f'color={col}, fontcolor={col}];\n')
                continue
            # pinned layout: the label is its own text node, placed off the
            # line, so it can never sit on a state
            lines = text.split("\n")
            w = max(len(x) for x in lines) * efs * 0.55
            h = len(lines) * efs * 1.15
            (x1, y1), (x2, y2) = pos[a], pos[b]
            adjacent = abs(x2 - x1) + abs(y2 - y1) <= 1.5 * max(abs(x2 - x1), abs(y2 - y1), 1) \
                and max(abs(x2 - x1), abs(y2 - y1)) < 130
            xs = [p[0] for p in pos.values()]
            left_edge = abs(x1 - min(xs)) < 1
            if adjacent:
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            else:                                     # long edge: label at its source
                d = max(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5, 1)
                mx, my = x1 + 40 * (x2 - x1) / d, y1 + 40 * (y2 - y1) / d
            if not adjacent and len(lines) > 2:       # tall label on a long edge:
                lx, ly = x1 - w / 2 - 16, y1          # in the free space left of its source
            elif abs(y2 - y1) < 1:                    # horizontal: above the line
                lx, ly = mx, my + h / 2 + 3
            elif abs(x2 - x1) < 1:                    # vertical: on the outer side
                lx, ly = (mx - w / 2 - 4 if left_edge else mx + w / 2 + 4), my
            else:                                     # diagonal: below the line
                side = -1 if x2 < x1 else 1
                lx, ly = mx + side * (w / 2 + 6), my - h / 2 - 2
            f.write(f'  L{i} [shape=plaintext, label="{dot_label(text)}", fontsize={efs}, '
                    f'fontcolor={col}, fixedsize=false, width=0, height=0, margin=0, '
                    f'pos="{lx:.0f},{ly:.0f}!"];\n')
            f.write(f'  {a} -> {b} [color={col}];\n')
        f.write("}\n")
    return len(blue), len(drawn), len(states), len(gone)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ctg")
    ap.add_argument("--io", required=True)
    ap.add_argument("--cases", required=True, help="directory of .aut, or a glob")
    ap.add_argument("--highlight", help="the case drawn in red (default: the first)")
    ap.add_argument("--excerpt", action="store_true")
    ap.add_argument("--dot", help="write the drawing here")
    ap.add_argument("--lr", action="store_true", help="lay the drawing out left to right")
    ap.add_argument("--compact", action="store_true", help="small nodes, small fonts, tight spacing")
    ap.add_argument("--short", action="store_true", help="labels: gate name and first parameter only")
    ap.add_argument("--fold", action="store_true", help="collapse runs of concrete UI steps into one edge")
    ap.add_argument("--grid", type=int, default=1, metavar="N",
                    help="pin the highlighted path on rows of N states (render with neato -n2)")
    ap.add_argument("--lanes", type=int, default=0, metavar="N",
                    help="whole graph, page-shaped: spine on rows of N states, each branch in its own band (neato -n2)")
    ap.add_argument("--stack", action="store_true",
                    help="full labels, one token per line (nothing dropped)")
    a = ap.parse_args()

    ctg_init, ctg_edges = read_aut(a.ctg)
    pats = read_io(a.io)
    files = case_files(a.cases)
    if not files:
        sys.exit(f"no test cases found at {a.cases}")

    union, per_case = set(), {}
    for p in files:
        ti, te = read_aut(p)
        per_case[p] = covered_by(ctg_init, ctg_edges, ti, te)
        union |= per_case[p]

    total = len(set(ctg_edges))
    print(f"CTG {a.ctg}: {len({e[0] for e in ctg_edges} | {e[2] for e in ctg_edges})} states, "
          f"{total} transitions")
    for p in files:
        print(f"  {os.path.basename(p):40s} covers {len(per_case[p]):4d}")
    print(f"suite of {len(files)} case(s) covers {len(union)} / {total} CTG transitions "
          f"({100.0 * len(union) / total:.1f}%)")
    missed = sorted(set(ctg_edges) - union)
    if missed:
        print("not covered:")
        for e in missed:
            kind = "input " if is_input(e[1], pats) else "verdict" if e[1] in VERDICTS else "output"
            print(f"  ({e[0]}, \"{e[1]}\", {e[2]})  [{kind}]")

    if a.dot:
        hl = a.highlight or files[0]
        if hl not in per_case:
            ti, te = read_aut(hl)
            per_case[hl] = covered_by(ctg_init, ctg_edges, ti, te)
        nb, ne, ns, ng = write_dot(a.dot, ctg_init, ctg_edges, per_case[hl], pats, a.excerpt,
                               "LR" if a.lr else "TB", a.compact, "stack" if a.stack else a.short, a.fold,
                               -a.lanes if a.lanes else a.grid)
        print(f"drawing {a.dot}: {ns} states, {ne} transitions; "
              f"red = {os.path.basename(hl)} ({len(per_case[hl])}), blue = {nb} untaken inputs"
              + (f"; {ng} pass-through states folded away" if ng else ""))


if __name__ == "__main__":
    main()
