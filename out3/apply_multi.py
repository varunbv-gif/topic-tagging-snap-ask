"""Add all_chapters / all_topics / n_topics / is_multi to the mapping, and validate
every extra name against the tree so nothing invented gets written."""
import csv, json, collections

concept = {tuple(k.split("\t")): v for k, v in json.load(open("out2/concepts.json", encoding="utf-8")).items()}
chapter_names = {c for _, c in concept}
nodes = json.load(open("out2/nodes_by_chapter.json", encoding="utf-8"))
node_names = {n["name"] for v in nodes.values() for n in v}

extra = {}
for l in open("out3/multi_result.tsv", encoding="utf-8"):
    if not l.strip(): continue
    p = (l.rstrip("\n").split("\t") + ["", "", ""])[:4]
    extra[p[0]] = {"chapters": [x for x in p[1].split("|") if x],
                   "topics":   [x for x in p[2].split("|") if x],
                   "flag": p[3]}

rows = list(csv.DictReader(open("topic_mapping.csv", encoding="utf-8")))
bad = collections.Counter()
for r in rows:
    e = extra.get(r["conversation_id"], {"chapters": [], "topics": [], "flag": ""})
    if not r["chapter_id"]:                                   # not on the tree at all
        r.update(all_chapters="", all_topics="", n_topics="0", is_multi="", multi_note="")
        continue
    chs = e["chapters"] or [r["chapter"]]
    tps = e["topics"] or ([r["topic"]] if r["topic"] and r["topic"] != "CHAPTER_ONLY" else [])
    if r["chapter"] not in chs: chs = [r["chapter"]] + chs     # primary always first
    for c in chs:
        if c not in chapter_names: bad[f"chapter:{c}"] += 1
    for t in tps:
        if t not in node_names: bad[f"topic:{t}"] += 1
    r.update(all_chapters="|".join(dict.fromkeys(chs)),
             all_topics="|".join(dict.fromkeys(tps)),
             n_topics=str(len(dict.fromkeys(tps))),
             is_multi="Y" if (len(set(chs)) > 1 or len(set(tps)) > 1) else "N",
             multi_note=e["flag"])

print("names not found in the tree:", len(bad))
for k, v in bad.most_common(): print("   ", k)

cols = list(rows[0].keys())
with open("topic_mapping.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)

tagged = [r for r in rows if r["chapter_id"]]
multi  = [r for r in tagged if r["is_multi"] == "Y"]
xchap  = [r for r in multi if "|" in r["all_chapters"]]
print(f"\ntagged conversations        {len(tagged)}")
print(f"  more than one topic       {len(multi)}   ({len(multi)/len(tagged):.1%})")
print(f"  more than one CHAPTER     {len(xchap)}   ({len(xchap)/len(tagged):.1%})")
print(f"  flagged with a note       {sum(1 for r in tagged if r['multi_note'])}")
print(f"  topics now recorded       {sum(int(r['n_topics']) for r in tagged)}  (was {len([r for r in tagged if r['topic_id']])})")
for r in sorted(multi, key=lambda r: -int(r["n_topics"]))[:5]:
    print(f"   {r['conversation_id'][:8]}  {r['n_topics']} topics  {r['all_chapters'][:72]}")
