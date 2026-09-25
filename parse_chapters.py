import re, glob, os, collections
D = r"C:\Users\user\.claude\projects\C--Users-user-Desktop-topic-tree-tagging-simulation\ab117ee0-a88c-4c6f-9d40-394524888f7b\tool-results"
files = sorted(glob.glob(os.path.join(D, "*execute_sql-17899787*.txt")), key=os.path.getmtime)
rows, seen = [], set()
for f in files:
    for line in open(f, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        # strip the "<bucket>  | " prefix that starts each bucket's first line
        line = re.sub(r"^\d+\s+\|\s+", "", line)
        p = line.split("|")
        if len(p) != 4:
            continue
        tree, subj, chap, cid = [x.strip() for x in p]
        if not re.fullmatch(r"[0-9a-f]{24}", cid) or cid in seen:
            continue
        seen.add(cid)
        rows.append((tree, subj, chap, cid))
print("chapters parsed:", len(rows), "from", len(files), "files")
with open("out2/chapters_all.tsv", "w", encoding="utf-8") as fh:
    for r in rows:
        fh.write("\t".join(r) + "\n")
t = collections.Counter(r[0] for r in rows)
print("trees:", len(t))
print("distinct chapter names:", len({r[2] for r in rows}))
print("subjects:", len({r[1] for r in rows}))
