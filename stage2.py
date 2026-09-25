import json, csv, collections, os, glob
conv = json.load(open("out2/conv_records.json", encoding="utf-8"))
nodes = json.load(open("out2/nodes_by_chapter.json", encoding="utf-8"))
rows = [r for r in csv.DictReader(open("out2/conversation_tags_v2.csv", encoding="utf-8")) if r["chapter_id"]]

def evidence(cid, n=420):
    r = conv[cid]
    s = r["taught"] or r["older_delivered"] or r["answer"] or r["student_typed"] or "(nothing)"
    return s[:n] + (" …" if len(s) > n else "")

by_ch = collections.defaultdict(list)
for r in rows: by_ch[r["chapter_id"]].append(r)

os.makedirs("out2/s2", exist_ok=True)
for f in glob.glob("out2/s2/*"): os.remove(f)
blocks = []
for cid_ch, rs in sorted(by_ch.items(), key=lambda kv: -len(kv[1])):
    ns = nodes[cid_ch]
    cat = "\n".join(f"  [{i}] {n['lvl'][0]} {n['name']}" for i, n in enumerate(ns))
    body = "\n".join(f"  - {r['cid']}  ({r['exchanges']} ex)  {evidence(r['cid'])}" for r in rs)
    blocks.append(f"## {rs[0]['tree']} > {rs[0]['subject']} > {rs[0]['chapter']}   [{cid_ch}]\nNODES:\n{cat}\nCONVERSATIONS:\n{body}")

MAX, cur, n, i = 13000, [], 0, 0
for b in blocks:
    if cur and n + len(b) > MAX:
        open(f"out2/s2/s{i:02d}.txt","w",encoding="utf-8").write("\n\n".join(cur)); cur, n, i = [], 0, i+1
    cur.append(b); n += len(b)
if cur: open(f"out2/s2/s{i:02d}.txt","w",encoding="utf-8").write("\n\n".join(cur)); i += 1
print(f"{len(blocks)} chapter blocks -> {i} files, {sum(len(b) for b in blocks)//1024} KB total")
