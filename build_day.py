"""Assemble the 2026-09-20 run: codes -> chapters, fill blanks, roll up, write CSVs + dashboard data."""
import csv, json, collections
from tag import fill_blanks, rollup, write_csv

CH = {}
for ln in open("chapters.tsv", encoding="utf-8"):
    code, cid, tree, subj, name = ln.rstrip("\n").split("\t")
    CH[code] = dict(chapter_id=cid, tree=tree, subject=subj, chapter=name)

BY_ID = {c["chapter_id"]: {k: c[k] for k in ("tree", "subject", "chapter")} for c in CH.values()}

ids = json.load(open("conv_index.json"))
convs = collections.OrderedDict((c, []) for c in ids)
for r in csv.DictReader(open("exchanges.tsv", encoding="utf-8"), delimiter="\t"):
    convs[r["conversation_id"]].append(r)

codes = {}
for ln in open("tags_raw.tsv", encoding="utf-8"):
    i, c = ln.rstrip("\n").split("\t")
    codes[int(i)] = c.split(",")

STATUS = {".": "UNKNOWN", "0": "NOT_ACADEMIC", "-1": "NOT_IN_TREE"}
results = []
for i, cid in enumerate(ids):
    rows = []
    for r, code in zip(convs[cid], codes[i]):
        st = STATUS.get(code, "TAGGED")
        ch = CH.get(code, {})
        rows.append({"conversation_id": cid, "user_id": "", "grade": r["grade"],
                     "exchange_no": r["exchange_no"],
                     "node_id": ch.get("chapter_id", ""), "chapter_id": ch.get("chapter_id", ""),
                     "tree": ch.get("tree", ""), "subject": ch.get("subject", ""),
                     "chapter": ch.get("chapter", ""),
                     "status": st, "confidence": "", "tag_source": "llm" if st == "TAGGED" else ""})
    rows = fill_blanks(rows)
    for r in rows:  # carried rows inherit the donor's id — re-attach its display names
        if r["chapter_id"] and not r["chapter"]:
            r.update(BY_ID[r["chapter_id"]])
    results.append(rows)

flat = [r for rows in results for r in rows]
write_csv("exchange_topic_tags.csv", flat)

conv_rows = []
for rows in results:
    up = rollup(rows)
    top = next((r for r in rows if r["node_id"] == up["node_id"] and r["status"] == "TAGGED"), {})
    conv_rows.append({**up, "grade": rows[0]["grade"], "exchanges": len(rows),
                      "tree": top.get("tree", ""), "subject": top.get("subject", ""),
                      "chapter": top.get("chapter", "")})
write_csv("conversation_topic_tags.csv", conv_rows)

n = len(flat)
st = collections.Counter(r["status"] for r in flat)
carried = sum(r["tag_source"] == "carried" for r in flat)
key = lambda r: (r["tree"], r["subject"], r["chapter"])
data = {
    "date": "2026-09-20", "exchanges": n, "conversations": len(results),
    "status": dict(st), "carried": carried,
    "tagged_pct": round(100 * st["TAGGED"] / n, 1),
    "chapters_hit": len({r["chapter_id"] for r in flat if r["status"] == "TAGGED"}),
    "by_subject": collections.Counter(r["subject"] for r in flat if r["status"] == "TAGGED").most_common(),
    "by_tree": collections.Counter(r["tree"] for r in flat if r["status"] == "TAGGED").most_common(),
    "by_grade": collections.Counter(c["grade"] for c in conv_rows).most_common(),
    "top_chapters": [{"tree": k[0], "subject": k[1], "chapter": k[2], "n": v}
                     for k, v in collections.Counter(key(r) for r in flat if r["status"] == "TAGGED").most_common(25)],
    "conv_status": dict(collections.Counter(c["status"] for c in conv_rows)),
    "len_buckets": collections.Counter(
        "1" if c["exchanges"] == 1 else "2-3" if c["exchanges"] <= 3 else
        "4-9" if c["exchanges"] <= 9 else "10+" for c in conv_rows).most_common(),
}
json.dump(data, open("dashboard_data.json", "w"), indent=1)
print(json.dumps({k: v for k, v in data.items() if k != "top_chapters"}, indent=1))
