import csv, json, collections
nodes = json.load(open("out2/nodes_by_chapter.json", encoding="utf-8"))
picks = {}
for l in open("out2/nodes_pick.tsv", encoding="utf-8"):
    if not l.strip(): continue
    cid, ch, idx = l.rstrip("\n").split("\t")
    picks[cid] = (ch, int(idx))

rows = list(csv.DictReader(open("out2/conversation_tags_v2.csv", encoding="utf-8")))
for r in rows:
    r["node"] = r["node_id"] = r["node_level"] = ""
    if r["cid"] in picks:
        ch, i = picks[r["cid"]]
        assert ch == r["chapter_id"], r["cid"]
        if i >= 0:
            n = nodes[ch][i]
            r["node"], r["node_id"], r["node_level"] = n["name"], n["id"], n["lvl"]

cols = ["cid","subject","chapter","chapter_id","node","node_id","node_level","confidence",
        "tree","in_A","in_B","in_C","grade","board","target","exchanges","note"]
with open("conversation_topic_tags_v2.csv","w",newline="",encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

tagged = [r for r in rows if r["chapter_id"]]
withnode = [r for r in tagged if r["node_id"]]
print(f"conversations           271")
print(f"  tagged to a chapter   {len(tagged)}  ({len(tagged)/271:.1%})")
print(f"  ...and to an exact node {len(withnode)}  ({len(withnode)/271:.1%})")
print(f"  chapter only, no node fits {len(tagged)-len(withnode)}")
print("  node level:", dict(collections.Counter(r["node_level"] for r in withnode)))
print()
print("=== duplicate node names inside a single chapter (tree data quality) ===")
dups = 0; chaps = 0
for ch, ns in nodes.items():
    c = collections.Counter(n["name"] for n in ns)
    d = sum(v-1 for v in c.values() if v > 1)
    if d: dups += d; chaps += 1
print(f"  {dups} duplicate node rows across {chaps} of the {len(nodes)} chapters actually used")
worst = sorted(((sum(v-1 for v in collections.Counter(n['name'] for n in ns).values() if v>1), ns[0]['chapter']) for ch, ns in nodes.items()), reverse=True)[:6]
for d, name in worst:
    if d: print(f"    {d:>2} duplicate nodes in '{name}'")
