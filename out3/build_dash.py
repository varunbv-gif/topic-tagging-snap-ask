"""Rebuild out3/dash_data.json from topic_mapping.csv.

Two counting modes: `primary` (one conversation, one tag - what the prompt returns)
and `all` (every chapter and topic the conversation actually covered).
"""
import csv, json, collections

concept = {tuple(k.split("\t")): v for k, v in json.load(open("out2/concepts.json", encoding="utf-8")).items()}
chap_subject = {c: s for s, c in concept}                       # chapter name -> subject
chap_ids = {c: v for (s, c), v in concept.items()}              # chapter name -> {tree: id}
nodes = json.load(open("out2/nodes_by_chapter.json", encoding="utf-8"))
LVL = {"TOPIC": "T", "SUB_TOPIC": "S"}

rows = list(csv.DictReader(open("topic_mapping.csv", encoding="utf-8")))
tagged = [r for r in rows if r["chapter_id"]]
OFF = {"NOT_ACADEMIC", "OUT_OF_SCOPE", "UNKNOWN"}


def nodes_of(chapter, tree):
    """Every node of `chapter` as it appears in `tree` (empty if never expanded)."""
    cid = chap_ids.get(chapter, {}).get(tree)
    return nodes.get(cid, []) if cid else []


def hits(r, mode):
    """(subject, chapter, topic, level) pairs this conversation contributes."""
    tree = r["tree"]
    if mode == "primary" or r["is_multi"] != "Y":
        lvl = LVL.get(r["topic_level"], "")
        return [(chap_subject.get(r["chapter"], r["subject"]), r["chapter"], r["topic"] or "CHAPTER_ONLY", lvl)]

    chapters = [c for c in r["all_chapters"].split("|") if c]
    index = {c: {n["name"]: LVL.get(n["lvl"], "") for n in nodes_of(c, tree)} for c in chapters}
    out, placed = [], set()
    for t in (x for x in r["all_topics"].split("|") if x):
        # a node name can repeat across chapters - the conversation's own chapters decide
        home = next((c for c in chapters if t in index[c]), r["chapter"])
        placed.add(home)
        out.append((chap_subject.get(home, r["subject"]), home, t, index.get(home, {}).get(t, "")))
    for c in chapters:                                          # a chapter with no node of its own
        if c not in placed:
            out.append((chap_subject.get(c, r["subject"]), c, "CHAPTER_ONLY", ""))
    return out


def treemap(mode):
    per = collections.defaultdict(collections.Counter)
    convs = collections.defaultdict(set)
    for r in tagged:
        for h in hits(r, mode):
            per[r["tree"]][h] += 1
            convs[r["tree"]].add(r["conversation_id"])
    out = []
    for tree, c in per.items():
        rs = sorted(([s, ch, tp, lv, n] for (s, ch, tp, lv), n in c.items()), key=lambda x: (-x[4], x[1], x[2]))
        out.append({"tree": tree, "convs": len(convs[tree]),
                    "nTopics": sum(1 for x in rs if x[2] != "CHAPTER_ONLY"),
                    "nChapters": len({x[1] for x in rs}), "rows": rs})
    return sorted(out, key=lambda t: -t["convs"])


def top20():
    """Ranked by every conversation that touched the node, with the primary-tag count beside it."""
    c = {m: collections.Counter() for m in ("primary", "all")}
    for r in tagged:
        for m in c:
            for s, ch, tp, lv in hits(r, m):
                if tp != "CHAPTER_ONLY":
                    c[m][(r["tree"], tp, ch)] += 1
    return [[t, tp, ch, c["primary"][k], n] for k, n in c["all"].most_common(20) for (t, tp, ch) in [k]]


def bars(key, n=None, of=rows):
    c = collections.Counter(r[key] for r in of if r[key])
    return [[k, v] for k, v in c.most_common(n)]


exact = sum(1 for r in tagged if r["topic"] and r["topic"] != "CHAPTER_ONLY")
chonly = len(tagged) - exact
multi = [r for r in tagged if r["is_multi"] == "Y"]
cross = [r for r in multi if len(r["all_chapters"].split("|")) > 1]
distinct = {(r["tree"], tp) for r in tagged for s, ch, tp, lv in hits(r, "primary") if tp != "CHAPTER_ONLY"}
distinct_all = {(r["tree"], tp) for r in tagged for s, ch, tp, lv in hits(r, "all") if tp != "CHAPTER_ONLY"}

unplaced = collections.Counter((r["subject"], r["chapter"]) for r in rows if r["subject"] in OFF)

D = {
    "facts": [[len(rows), "Conversations"], [len(tagged), "Placed on the tree"],
              [exact, "At an exact topic"], [len(multi), "Cover more than one topic"],
              [len(distinct_all), "Distinct topics"]],
    "outcome": [["At an exact topic", exact, "--s1"],
                ["Chapter only, no node fits", chonly, "--s4"]] +
               [[{"NOT_ACADEMIC": "Not academic", "OUT_OF_SCOPE": "Not in the tree",
                  "UNKNOWN": "Nothing to go on"}[k], v, tok]
                for (k, tok) in [("NOT_ACADEMIC", "--s3"), ("OUT_OF_SCOPE", "--s2"), ("UNKNOWN", "--s5")]
                for v in [sum(1 for r in rows if r["subject"] == k)]],
    "subjects": bars("subject", of=tagged),
    "trees": bars("tree", 9, of=tagged),
    "targets": bars("target"),
    "boards": bars("board"),
    "topics": top20(),
    "TREEMAP": {"primary": treemap("primary"), "all": treemap("all")},
    "UNPLACED": sorted(([k, w, n] for (k, w), n in unplaced.items()), key=lambda x: (-x[2], x[0], x[1])),
    "rows": [[r["conversation_id"][:8], r["user_id"][-6:], r["subject"], r["chapter"], r["topic"],
              LVL.get(r["topic_level"], ""), r["tree"], r["confidence"], r["grade"], r["board"],
              r["target"], int(r["exchanges"] or 0), int(r["n_topics"] or 0),
              r["all_chapters"], r["all_topics"], r["is_multi"]] for r in rows],
    "N": {"total": len(rows), "tagged": len(tagged), "exact": exact, "chonly": chonly,
          "multi": len(multi), "cross": len(cross),
          "topicsPrimary": len(distinct), "topicsAll": len(distinct_all),
          "recorded": sum(int(r["n_topics"] or 0) for r in tagged)},
}
json.dump(D, open("out3/dash_data.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

n = D["N"]
print(f"{n['tagged']} tagged - {n['exact']} exact, {n['chonly']} chapter-only, "
      f"{n['multi']} multi ({n['cross']} cross-chapter)")
print(f"distinct topics: {n['topicsPrimary']} primary -> {n['topicsAll']} counting all, "
      f"{n['recorded']} topic records")
assert sum(x[1] for x in D["outcome"]) == len(rows), "outcome stack must add to every conversation"
assert len(D["TREEMAP"]["all"]) >= len(D["TREEMAP"]["primary"])
