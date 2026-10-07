import re, collections, glob, sys

purpose = sys.argv[1] if len(sys.argv) > 1 else "app1_write_fail"
fault = purpose.upper()

files = sorted(glob.glob(f"variants/{purpose}/tc_{purpose}.*.aut"))
good = []
for fn in files:
    edges = collections.defaultdict(list)
    for ln in open(fn):
        m = re.match(r'\((\d+),\s*(.+),\s*(\d+)\)\s*$', ln.strip())
        if m:
            edges[int(m.group(1))].append((m.group(2).strip().strip('"'), int(m.group(3))))
    targets = [t for s in edges for l, t in edges[s] if l.split()[0] == "PROCESS_ATTEMPT"]
    for t in targets:
        labels = [l.split()[0] for l, _ in edges[t] if l != ":DELTA:"]
        if fault in labels:
            good.append((fn, labels))
            break

print(f"{len(good)} / {len(files)} variants offer {fault} directly after PROCESS_ATTEMPT")
for fn, labels in good[:5]:
    print(f"  {fn}: {labels}")
