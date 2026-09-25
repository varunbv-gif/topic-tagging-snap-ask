import json, collections, os, re
from trees import band_family

CAPS = {"student_typed":600, "wanted":500, "taught":2200, "older_delivered":900,
        "older_student":300, "answer":1600, "md":900}
def cut(s, n): return s if len(s) <= n else s[:n] + " …"
def norm_subj(s):
    return {"Math":"Mathematics", "Maths":"Mathematics"}.get(s, s or "?")

conv = json.load(open("out2/conv_records.json", encoding="utf-8"))
chap = [l.rstrip("\n").split("\t") for l in open("out2/chapters_all.tsv", encoding="utf-8")]

# concept = (subject, chapter name); each concept knows which trees carry it and with what id
concept = collections.defaultdict(dict)          # (subj,name) -> {tree: chapter_id}
for tree, subj, name, cid in chap:
    concept[(norm_subj(subj), name)][tree] = cid
json.dump({f"{s}\t{n}": t for (s, n), t in concept.items()},
          open("out2/concepts.json","w",encoding="utf-8"), ensure_ascii=False)
print("chapter rows:", len(chap), "-> concepts:", len(concept))

groups = collections.defaultdict(list)
for cid, r in conv.items():
    groups[tuple(r["trees"])].append(cid)

def block(cid, r):
    L = [f"### {cid}",   # metadata_title is a bare timestamp on every row - no signal
         f"PROFILE: grade={r['grade'] or '?'} board={r['board'] or '?'} stream={r['stream'] or '-'} "
         f"target={r['target'] or '?'} exams={r['exam_targets'] or '-'}",
         f"SHAPE: {r['exchanges']} exchanges, {r['images']} images"]
    # the coverage note is the bot's own summary of the answer; fall back to the raw
    # answer (and the worked solution) only where that note is thin or missing
    thin = len(r["taught"]) + len(r["older_delivered"])
    fields = [("ASKED(typed)","student_typed"), ("WANTED(note)","wanted"),
              ("TAUGHT(note)","taught"), ("EARLIER(delivered)","older_delivered"),
              ("EARLIER(student)","older_student")]
    if thin < 400:
        fields.append(("ANSWER(verbatim)","answer"))
    if thin < 150:
        fields.append(("WORKED(md)","md"))
    for label, key in fields:
        if r[key]:
            L.append(f"{label}: {cut(r[key], CAPS[key])}")
    return "\n".join(L)

os.makedirs("out2/batches", exist_ok=True)
for f in os.listdir("out2/batches"): os.remove(os.path.join("out2/batches", f))
sizes, index = [], {}
for i, (trees, cids) in enumerate(sorted(groups.items(), key=lambda kv: -len(kv[1]))):
    ts = set(trees)
    rows = sorted({(s, n) for (s, n), tm in concept.items() if ts & tm.keys()})
    cat = "\n".join(f"{s} | {n}" for s, n in rows)
    body = "\n\n".join(block(c, conv[c]) for c in sorted(cids))
    hdr = (f"CANDIDATE CHAPTERS for these students ({len(rows)}), format: subject | chapter\n"
           f"(trees in scope: {', '.join(trees) if len(trees) < 20 else 'all 73'})\n\n")
    open(f"out2/batches/g{i:02d}.txt","w",encoding="utf-8").write(
        hdr + cat + "\n\n" + "="*60 + f"\nCONVERSATIONS ({len(cids)})\n" + "="*60 + "\n\n" + body)
    index[f"g{i:02d}"] = {"trees": list(trees), "cids": sorted(cids)}
    sizes.append((i, len(cids), len(trees), len(rows), (len(hdr)+len(cat))//1024, len(body)//1024))

json.dump(index, open("out2/batch_index.json","w",encoding="utf-8"))
print("grp convs trees chapters cat_kb body_kb")
for s in sizes: print("  %2d  %4d  %4d  %6d  %5d  %5d" % s)
print("TOTAL cat KB:", sum(s[4] for s in sizes), "| body KB:", sum(s[5] for s in sizes))
