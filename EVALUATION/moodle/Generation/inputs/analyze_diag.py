import re, collections

edges = collections.defaultdict(list)
for ln in open("diag_grading.aut"):
    m = re.match(r'\((\d+),\s*(.+),\s*(\d+)\)\s*$', ln.strip())
    if m:
        edges[int(m.group(1))].append((m.group(2).strip().strip('"'), int(m.group(3))))

og = [(s, t) for s in edges for l, t in edges[s] if l.startswith("OPEN_GRADING")]
print(f"OPEN_GRADING edges found: {len(og)}")

for s, t in og[:5]:
    labels = sorted(set(l for l, _ in edges[t]))
    print(f"\n-- target state {t} (reached via OPEN_GRADING from {s}) --")
    for l in labels:
        print("   ", l)

gs = [(s, l, t) for s in edges for l, t in edges[s] if l.startswith("GRADING_SHOWS")]
print(f"\nGRADING_SHOWS edges anywhere in this diagnostic: {len(gs)}")
for s, l, t in gs[:10]:
    preds = [(ss, ll) for ss in edges for ll, tt in edges[ss] if tt == s][:3]
    print(f"   state {s} -> {l} -> {t}   (reached from: {preds})")

print("\n--- following state 527 down WAIT_FOR sel_grading_submission_text ---")
start = 527
seen = {start}
frontier = [start]
depth = 0
reached_grading_shows = False
while frontier and depth < 40:
    nxt = []
    for s in frontier:
        for l, t in edges[s]:
            if l in ("INFRA_CRON_DEAD", "UE1_LOSE_CONN", "UE2_SESSION_EXPIRE", "i") or t in seen:
                continue
            seen.add(t)
            nxt.append(t)
            if l.startswith("GRADING_SHOWS"):
                reached_grading_shows = True
                print(f"  REACHED at depth {depth+1}: state {s} -> {l} -> {t}")
    frontier = nxt
    depth += 1
print(f"GRADING_SHOWS reachable from 527 (excluding disruptor/i noise): {reached_grading_shows}")
print(f"states explored: {len(seen)}")

print("\n--- what does 527's WAIT_FOR sel_grading_submission_text edge itself lead to? ---")
for l, t in edges[527]:
    if l.startswith("WAIT_FOR !SEL_GRADING_SUBMISSION_TEXT"):
        print(f"  527 -> {t}, and {t}'s own outgoing labels:")
        for l2, t2 in sorted(set(edges[t])):
            print("     ", l2, "->", t2)
