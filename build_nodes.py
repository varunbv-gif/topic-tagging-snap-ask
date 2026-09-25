"""Stage 2: attach the exact topic-tree node to each tagged exchange, re-fill, re-roll-up."""
import csv, json, collections
from tag import fill_blanks, rollup, write_csv

CH = {}
for ln in open("chapters.tsv", encoding="utf-8"):
    code, cid, tree, subj, name = ln.rstrip("\n").split("\t")
    CH[code] = dict(chapter_id=cid, tree=tree, subject=subj, chapter=name)
BY_CID = {v["chapter_id"]: (k, v) for k, v in CH.items()}

NODE = {r["ncode"]: r for r in csv.DictReader(open("nodes.tsv", encoding="utf-8"), delimiter="\t")}
todo = json.load(open("todo.json"))
picks = {}
for ln in open("node_tags.tsv", encoding="utf-8"):
    chcode, codes = ln.rstrip("\n").split("\t")
    for (cid, eno), code in zip(todo[chcode], codes.split(",")):
        picks[(cid, eno)] = code

rows = list(csv.DictReader(open("exchange_topic_tags.csv", encoding="utf-8")))
for r in rows:                                   # drop stage-1's chapter-as-node
    if r["tag_source"] == "carried":              # re-open: it must re-borrow a NODE, not a chapter
        r["status"], r["chapter_id"] = "UNKNOWN", ""
        r["tree"] = r["subject"] = r["chapter"] = ""
    r["node_id"] = r["node_name"] = r["node_level"] = ""
    code = picks.get((r["conversation_id"], r["exchange_no"]))
    if code and code != "C":
        n = NODE[code]
        r["node_id"], r["node_name"] = n["node_id"], n["name"]
        r["node_level"] = "TOPIC" if n["level"] == "T" else "SUB_TOPIC"
        if n["topic"]:
            r["node_name"] = f'{n["topic"]} > {n["name"]}'
    elif code == "C":
        r["node_id"], r["node_name"], r["node_level"] = r["chapter_id"], r["chapter"], "CHAPTER"
    if r["status"] == "TAGGED":
        r["tag_source"] = "llm"                  # reset; fill_blanks re-marks the carried ones

convs = collections.OrderedDict()
for r in rows:
    convs.setdefault(r["conversation_id"], []).append(r)
results = []
for rs in convs.values():
    rs = fill_blanks(rs)
    for r in rs:                                 # a carried row inherits the donor's node names too
        if r["tag_source"] == "carried" and r["node_id"]:
            donor = next(x for x in rs if x["node_id"] == r["node_id"] and x["tag_source"] == "llm")
            for k in ("node_name", "node_level", "tree", "subject", "chapter"):
                r[k] = donor[k]
    results.append(rs)

flat = [r for rs in results for r in rs]
cols = ["conversation_id", "user_id", "grade", "exchange_no", "tree", "subject", "chapter",
        "chapter_id", "node_id", "node_name", "node_level", "status", "confidence", "tag_source"]
write_csv("exchange_topic_tags.csv", [{k: r.get(k, "") for k in cols} for r in flat])

conv_rows = []
for rs in results:
    up = rollup(rs)
    top = next((r for r in rs if r["node_id"] == up["node_id"] and r["status"] == "TAGGED"), {})
    conv_rows.append({"conversation_id": up["conversation_id"], "grade": rs[0]["grade"],
                      "exchanges": len(rs), "status": up["status"],
                      "tree": top.get("tree", ""), "subject": top.get("subject", ""),
                      "chapter": top.get("chapter", ""), "node_id": up["node_id"],
                      "node_name": top.get("node_name", ""), "node_level": top.get("node_level", ""),
                      "all_node_ids": up["all_node_ids"]})
write_csv("conversation_topic_tags.csv", conv_rows)

n = len(flat)
lev = collections.Counter(r["node_level"] for r in flat if r["status"] == "TAGGED")
print(f"{n} exchanges | tagged {sum(lev.values())}")
print("  node level:", dict(lev))
print("  distinct nodes:", len({r['node_id'] for r in flat if r['status']=='TAGGED'}))
print("  conversations by level:", dict(collections.Counter(c["node_level"] for c in conv_rows)))
top = collections.Counter((r["tree"], r["subject"], r["chapter"], r["node_name"])
                          for r in flat if r["status"] == "TAGGED" and r["node_level"] != "CHAPTER")
json.dump([{"tree": k[0], "subject": k[1], "chapter": k[2], "node": k[3], "n": v}
           for k, v in top.most_common(25)], open("top_nodes.json", "w"), indent=1)
for k, v in top.most_common(15):
    print(f"  {v:3}  {k[0]:11} {k[2][:34]:34} > {k[3][:45]}")
