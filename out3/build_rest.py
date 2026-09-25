import csv, json, os, glob
cur  = {r["conversation_id"]: r for r in csv.DictReader(open("topic_mapping.csv", encoding="utf-8"))}
conv = json.load(open("out2/conv_records.json", encoding="utf-8"))
done = {l.split("\t")[0] for l in open("out3/multi_result.tsv", encoding="utf-8") if l.strip()}
rest = [r for r in cur.values() if r["chapter_id"] and r["conversation_id"] not in done]
rest.sort(key=lambda r: (r["tree"], r["subject"], r["chapter"]))

def block(r):
    cid = r["conversation_id"]; c = conv[cid]
    segs, seen = [], set()
    for s in [x.strip() for x in c["taught"].split("||") if x.strip()]:
        k = s[:80]
        if k not in seen: seen.add(k); segs.append(s[:260])
    if not segs:
        segs = [("ANSWER: " + (c["answer"] or "(none)"))[:400]]
    L = [f"### {cid[:8]} [{r['exchanges']}ex]  {r['tree']} > {r['subject']} > {r['chapter']} > {r['topic']}"]
    L += [f"   - {s}" for s in segs]
    return "\n".join(L)

os.makedirs("out3/rest", exist_ok=True)
for f in glob.glob("out3/rest/*"): os.remove(f)
blocks = [block(r) for r in rest]
buf, n, i = [], 0, 0
for b in blocks:
    if buf and n + len(b) > 13000:
        open(f"out3/rest/r{i:02d}.txt","w",encoding="utf-8").write("\n\n".join(buf)); buf, n, i = [], 0, i+1
    buf.append(b); n += len(b)
if buf: open(f"out3/rest/r{i:02d}.txt","w",encoding="utf-8").write("\n\n".join(buf)); i += 1
print(f"{len(rest)} remaining -> {i} files, {sum(len(b) for b in blocks)//1024} KB")
