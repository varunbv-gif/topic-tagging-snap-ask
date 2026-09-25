"""Final output: exact topic mapping, one line per conversation, from the nine input parameters."""
import csv, json, collections
nodes = json.load(open("out2/nodes_by_chapter.json", encoding="utf-8"))
tree9 = json.load(open("out3/tree_9p.json", encoding="utf-8"))
repick = dict(l.rstrip("\n").split("\t") for l in open("out3/repick.tsv", encoding="utf-8") if l.strip())
gbt = {}
for l in open("out2/gbt.tsv", encoding="utf-8"):
    cid, uid, grade, board, stream, target = l.rstrip("\n").split("\t")
    gbt[cid] = (uid, grade, board, target)

out = []
for r in csv.DictReader(open("conversation_topic_tags_v3.csv", encoding="utf-8")):
    uid, grade, board, target = gbt[r["cid"]]
    row = {"user_id": uid, "conversation_id": r["cid"], "grade": grade, "board": board,
           "target": target, "exchanges": r["exchanges"], "confidence": r["confidence"],
           "subject": r["subject"], "chapter": r["chapter"], "chapter_id": "",
           "topic": "", "topic_id": "", "topic_level": "", "tree": "", "note": r["note"]}
    if r["chapter_id"]:
        tree, ch = tree9[r["cid"]]
        row.update(tree=tree, chapter_id=ch)
        byname = {n["name"]: n for n in nodes.get(ch, [])}
        want = repick.get(r["cid"], r["node"])
        if want == "CHAPTER_ONLY" or not want:
            row["topic"] = "CHAPTER_ONLY"
        elif want in byname:
            n = byname[want]
            row.update(topic=n["name"], topic_id=n["id"], topic_level=n["lvl"])
        else:
            row["topic"] = "CHAPTER_ONLY"
    else:
        row.update(chapter=r["chapter"], topic="")     # NOT_ACADEMIC / OUT_OF_SCOPE / UNKNOWN
    out.append(row)

cols = ["user_id","conversation_id","grade","board","target","exchanges",
        "subject","chapter","chapter_id","topic","topic_id","topic_level","tree","confidence","note"]
with open("topic_mapping.csv","w",newline="",encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(out)

with open("topic_mapping.tsv","w",encoding="utf-8") as fh:
    for r in out:
        fh.write(f'{r["conversation_id"]}\t{r["subject"]}\t{r["chapter"]}\t{r["topic"] or r["subject"]}\t{r["confidence"]}\n')

tagged = [r for r in out if r["chapter_id"]]
exact = [r for r in tagged if r["topic_id"]]
print(f"conversations              {len(out)}")
print(f"  tagged to a chapter      {len(tagged)}  ({len(tagged)/len(out):.1%})")
print(f"  with an EXACT topic      {len(exact)}  ({len(exact)/len(out):.1%})")
print(f"  CHAPTER_ONLY             {len(tagged)-len(exact)}")
print(f"  level:", dict(collections.Counter(r["topic_level"] for r in exact)))
print(f"  not tagged               {len(out)-len(tagged)}",
      dict(collections.Counter(r["subject"] for r in out if not r["chapter_id"])))
print(f"  distinct topics used     {len({r['topic_id'] for r in exact})}")
print(f"  distinct users           {len({r['user_id'] for r in out})}")
