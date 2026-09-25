import csv, json, collections
rows = list(csv.DictReader(open("conversation_topic_tags_v2.csv", encoding="utf-8")))
tagged = [r for r in rows if r["chapter_id"]]
E = lambda rs: sum(int(r["exchanges"]) for r in rs)

d = {
  "convs": len(rows), "exchanges": E(rows),
  "tagged": len(tagged), "node": sum(1 for r in tagged if r["node_id"]),
  "scope": {
    "A": sum(1 for r in tagged if r["in_A"] == "Y"),
    "B": sum(1 for r in tagged if r["in_B"] == "Y"),
    "C": len(tagged)},
  "outcome": [[k, sum(1 for r in rows if r["subject"] == k), E([r for r in rows if r["subject"] == k])]
              for k in ["NOT_ACADEMIC", "OUT_OF_SCOPE", "UNKNOWN"]],
  "conf": collections.Counter(r["confidence"] for r in tagged),
  "subjects": collections.Counter(r["subject"] for r in tagged).most_common(),
  "trees": collections.Counter(r["tree"] for r in tagged).most_common(),
  "chapters": collections.Counter(f'{r["subject"]} · {r["chapter"]}' for r in tagged).most_common(12),
  "nodes": collections.Counter(f'{r["chapter"]} › {r["node"]}' for r in tagged if r["node"]).most_common(10),
  "rescued": [],
  "grade_subject": {},
}
for (s, c), n in collections.Counter((r["subject"], r["chapter"]) for r in tagged if r["in_A"] == "N").most_common():
    trees = sorted({r["tree"] for r in tagged if (r["subject"], r["chapter"]) == (s, c)})
    d["rescued"].append([n, s, c, ", ".join(trees)])
grades = sorted({(r["grade"] or "?") for r in tagged}, key=lambda x: (x == "?", int(x) if x.isdigit() else 0))
subs = [s for s, _ in d["subjects"]]
d["grades"] = grades
d["grade_subject"] = [[s] + [sum(1 for r in tagged if r["subject"] == s and (r["grade"] or "?") == g) for g in grades] for s in subs]
# what the new input columns bought
conv = json.load(open("out2/conv_records.json", encoding="utf-8"))
d["thin"] = sum(1 for r in tagged if len(conv[r["cid"]]["taught"]) + len(conv[r["cid"]]["older_delivered"]) < 150)
d["nonote"] = sum(1 for r in tagged if not conv[r["cid"]]["taught"] and not conv[r["cid"]]["older_delivered"])
d["conf"] = dict(d["conf"])
json.dump(d, open("dashboard_data_v2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in d.items() if k not in ("rescued","grade_subject","chapters","nodes","trees")}, ensure_ascii=False)[:900])
print("rescued rows:", len(d["rescued"]), "| trees:", len(d["trees"]))
