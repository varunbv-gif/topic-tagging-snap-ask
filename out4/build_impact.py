"""Assemble out4/impact_data.json - the old run against the cascade run, on the same 20."""
import csv, json, os, sys, collections

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cascade as C

old = {r["conversation_id"][:8]: r for r in csv.DictReader(open(C.P("topic_mapping.csv"), encoding="utf-8"))}
new = list(csv.DictReader(open(C.P("out4/topic_mapping.csv"), encoding="utf-8")))
segs = [json.loads(l) for l in open(C.P("out4/segments.jsonl"), encoding="utf-8")]
records = json.load(open(C.P("out2/conv_records.json"), encoding="utf-8"))
by_conv = collections.defaultdict(list)
for s in segs:
    by_conv[s["conversation_id"][:8]].append(s)

OFF = {"NOT_ACADEMIC", "OUT_OF_SCOPE", "UNKNOWN"}
path = lambda r: (f'{r["chapter"]} › {r["topic"]}' if r["chapter_id"]
                  else f'{r["subject"].replace("_", " ").lower()}')

rows = []
for r in new:
    c = r["conversation_id"][:8]
    o = old[c]
    mine = by_conv[c]
    rows.append({
        "cid": c, "grade": r["grade"], "board": r["board"], "target": r["target"],
        "exchanges": int(r["exchanges"] or 0), "segments": len(mine),
        "old": {"path": path(o), "tree": o["tree"], "n": int(o["n_topics"] or 0),
                "off": bool(not o["chapter_id"])},
        "new": {"path": path(r), "tree": r["tree"], "n": int(r["n_topics"] or 0),
                "off": bool(not r["chapter_id"])},
        "changed": path(o) != path(r), "tree_moved": bool(o["tree"] and r["tree"] and o["tree"] != r["tree"]),
        "chapters": [x for x in r["all_chapters"].split("|") if x],
        "detail": [{"i": s["segment"], "posed": s["posed"], "delivered": s["delivered"],
                    "chapter": s["asked_chapter"], "topic": s["asked_topic"],
                    "tree": s["tree"], "src": s["ask_source"], "conf": s["confidence"],
                    "diverged": s["diverged"], "divergence": s.get("divergence"),
                    "taught_chapter": s.get("taught_chapter"), "taught_topic": s.get("taught_topic"),
                    "missing": bool(s.get("nodes_missing"))} for s in mine],
    })
rows.sort(key=lambda r: -r["segments"])

ot = [old[r["conversation_id"][:8]] for r in new if old[r["conversation_id"][:8]]["chapter_id"]]
nt = [r for r in new if r["chapter_id"]]
uniq = lambda rs, k: len({x for r in rs for x in r[k].split("|") if x})

D = {
    "rows": rows,
    "totals": {
        "convs": len(new), "segments": len(segs),
        "old_tagged": len(ot), "new_tagged": len(nt),
        "old_topics": uniq(ot, "all_topics"), "new_topics": uniq(nt, "all_topics"),
        "old_chapters": uniq(ot, "all_chapters"), "new_chapters": uniq(nt, "all_chapters"),
        "changed": sum(1 for r in rows if r["changed"]),
        "tree_moved": sum(1 for r in rows if r["tree_moved"]),
        "from_student": sum(1 for s in segs if s["ask_source"] == "student_text"),
        "diverged": sum(1 for s in segs if s["diverged"]),
        "missing_nodes": sum(1 for s in segs if s.get("nodes_missing")),
        "invalid": sum(1 for s in segs if s.get("invalid")),
    },
    "calls": {"segment": len(new), "chapter": len(segs) + 1, "topic": len(segs) - 3 - 2 + 1},
}
json.dump(D, open(C.P("out4/impact_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
t = D["totals"]
print(f'{t["convs"]} conversations -> {t["segments"]} questions; '
      f'{t["old_topics"]} -> {t["new_topics"]} distinct topics; {t["changed"]} tags changed')
