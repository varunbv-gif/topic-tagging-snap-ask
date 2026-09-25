import re, os, json, glob, collections

D = r"C:\Users\user\.claude\projects\C--Users-user-Desktop-topic-tree-tagging-simulation\ab117ee0-a88c-4c6f-9d40-394524888f7b\tool-results"
def rows(stamp):
    """Yield logical records from a spilled MCP result (bucketed text)."""
    f = glob.glob(os.path.join(D, f"*execute_sql-{stamp}.txt"))[0]
    for line in open(f, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if not line or line.startswith(("SQL Results:", "Columns:", "Rows:")):
            continue
        yield re.sub(r"^\d+\s+\|\s", "", line)

conv = collections.defaultdict(dict)

HDR = ["exchanges","images","title","grade","board","stream","target","exam_targets","student_typed"]
for r in rows("1789978795786"):
    p = r.split("\t")
    if len(p) < 10 or not re.fullmatch(r"[0-9a-f-]{36}", p[0]): continue
    conv[p[0]].update(dict(zip(HDR, p[1:10])))

KEY = {"D":"taught","S":"wanted","OD":"older_delivered","OS":"older_student",
       "ANSWER":"answer","closing-question":"closing","deep-dive-reference":"deepdive","MD":"md"}
for stamp in ("1789978807608","1789978818875","1789978827973"):
    for r in rows(stamp):
        p = r.split("\t", 2)
        if len(p) != 3 or p[1] not in KEY: continue
        conv[p[0]][KEY[p[1]]] = p[2]

for c in conv.values():
    for k in list(KEY.values()) + HDR:
        c.setdefault(k, "")
    c["exchanges"] = int(c["exchanges"] or 0)
    c["images"] = int(c["images"] or 0)

json.dump(conv, open("out2/conv_records.json","w",encoding="utf-8"), ensure_ascii=False)
print("conversations:", len(conv), "| exchanges:", sum(c["exchanges"] for c in conv.values()))
for k in ["title","grade","board","stream","target","exam_targets","student_typed",
          "taught","wanted","older_delivered","older_student","answer","closing","deepdive","md"]:
    n = sum(1 for c in conv.values() if c[k])
    kb = sum(len(c[k]) for c in conv.values())/1024
    print(f"  {k:<16} present {n:>3}/271   {kb:>7.1f} KB")
