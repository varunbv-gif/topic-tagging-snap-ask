"""Review pack for the conversations that may cover more than one topic."""
import csv, json, collections, os, glob, re

cur  = {r["conversation_id"]: r for r in csv.DictReader(open("topic_mapping.csv", encoding="utf-8"))}
conv = json.load(open("out2/conv_records.json", encoding="utf-8"))
nodes = json.load(open("out2/nodes_by_chapter.json", encoding="utf-8"))
ex = [r for r in csv.DictReader(open("exchange_topic_tags.csv", encoding="utf-8")) if r.get("chapter_id")]
v1 = collections.defaultdict(list)
for r in ex: v1[r["conversation_id"]].append(r)

cand = []
for r in cur.values():
    if not r["chapter_id"]: continue
    cid = r["conversation_id"]; rs = v1.get(cid, [])
    multi = len({x["chapter_id"] for x in rs}) > 1 or len({x["node_id"] for x in rs}) > 1
    if multi or (not rs and int(r["exchanges"]) >= 3) or re.search(
       r"spans two|also covered|multi-chapter|whole-syllabus|then became|second half|mixed ", r["note"], re.I):
        cand.append(r)
cand.sort(key=lambda r: (r["tree"], r["subject"], r["chapter"]))

os.makedirs("out3/multi", exist_ok=True)
for f in glob.glob("out3/multi/*"): os.remove(f)

def block(r):
    cid = r["conversation_id"]
    segs = [s.strip() for s in conv[cid]["taught"].split("||") if s.strip()]
    if not segs: segs = [conv[cid]["answer"][:600] or "(no note)"]
    ns = nodes.get(r["chapter_id"], [])
    L = [f"### {cid}   [{r['exchanges']} exchanges]",
         f"PRIMARY: {r['tree']} > {r['subject']} > {r['chapter']} > {r['topic']}",
         f"NODES IN THAT CHAPTER: " + " | ".join(f"[{i}] {n['name']}" for i, n in enumerate(ns)),
         "SEGMENTS:"]
    seen = set()
    for i, s in enumerate(segs, 1):
        k = s[:90]
        if k in seen: continue          # the rolling window repeats a note verbatim
        seen.add(k)
        L.append(f"  {i:>2}. {s[:300]}")
    return "\n".join(L)

blocks = [block(r) for r in cand]
cur_f, n, i = [], 0, 0
for b in blocks:
    if cur_f and n + len(b) > 13000:
        open(f"out3/multi/m{i:02d}.txt","w",encoding="utf-8").write("\n\n".join(cur_f)); cur_f, n, i = [], 0, i+1
    cur_f.append(b); n += len(b)
if cur_f: open(f"out3/multi/m{i:02d}.txt","w",encoding="utf-8").write("\n\n".join(cur_f)); i += 1
print(f"{len(cand)} candidates -> {i} files, {sum(len(b) for b in blocks)//1024} KB")
json.dump([r["conversation_id"] for r in cand], open("out3/multi_candidates.json","w"))
