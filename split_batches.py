import os, glob, json, re
os.makedirs("out2/chunks", exist_ok=True)
for f in glob.glob("out2/chunks/*"): os.remove(f)
MAX = 15000
man = []
for path in sorted(glob.glob("out2/batches/g*.txt")):
    g = os.path.basename(path)[:3]
    body = open(path, encoding="utf-8").read().split("="*60 + "\n")[-1].strip()
    convs = [b.strip() for b in body.split("\n\n### ")]
    convs = [c if c.startswith("###") else "### " + c for c in convs]
    cur, n, i = [], 0, 0
    def flush():
        global cur, n, i
        if not cur: return
        p = f"out2/chunks/{g}_c{i:02d}.txt"
        open(p, "w", encoding="utf-8").write("\n\n".join(cur))
        man.append({"chunk": os.path.basename(p), "group": g, "n": len(cur), "kb": n//1024})
        cur, n, i = [], 0, i + 1
    for c in convs:
        if cur and n + len(c) > MAX: flush()
        cur.append(c); n += len(c)
    flush()
json.dump(man, open("out2/chunk_manifest.json","w"), indent=0)
print(len(man), "chunks |", sum(m["n"] for m in man), "conversations |", sum(m["kb"] for m in man), "KB")
for m in man: print(" ", m["chunk"], m["n"], f'{m["kb"]}KB')
