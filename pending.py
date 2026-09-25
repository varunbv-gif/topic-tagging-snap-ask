import sys, io, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
done = {l.split("\t")[0] for l in open("out2/nodes_pick.tsv", encoding="utf-8") if l.strip()}
for f in sys.argv[1:]:
    blocks, cur = [], []
    for line in open(f, encoding="utf-8"):
        l = line.rstrip()
        if l.startswith("## "):
            if cur and any(x.strip().startswith("- ") for x in cur): blocks.append(cur)
            cur = [l]
        elif l.startswith(("NODES:", "  [", "CONVERSATIONS:")):
            cur.append(l)
        elif l.strip().startswith("- ") and l.strip().split()[1] not in done:
            cur.append(l)
    if cur and any(x.strip().startswith("- ") for x in cur): blocks.append(cur)
    for b in blocks: print("\n".join(b) + "\n")
