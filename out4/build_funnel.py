"""out4/funnel_data.json - every conversation of 20-09-2026, conversation_id to exact topic."""
import csv, json, os, sys, collections

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cascade as C

rows = list(csv.DictReader(open(C.P("topic_mapping.csv"), encoding="utf-8")))
records = json.load(open(C.P("out2/conv_records.json"), encoding="utf-8"))
segs = collections.defaultdict(list)
for l in open(C.P("out4/segments.jsonl"), encoding="utf-8"):
    s = json.loads(l)
    segs[s["conversation_id"][:8]].append(s)

REJECT = {"NOT_ACADEMIC": "not academic", "OUT_OF_SCOPE": "not in the tree",
          "UNKNOWN": "nothing to go on"}

# where each conversation stopped, in funnel order
def stage_of(r):
    if r["subject"] in REJECT:
        return {"NOT_ACADEMIC": "no_subject", "OUT_OF_SCOPE": "no_chapter",
                "UNKNOWN": "no_signal"}[r["subject"]]
    return "topic" if r["topic"] and r["topic"] != "CHAPTER_ONLY" else "chapter"

out = []
for r in rows:
    cid = r["conversation_id"]
    rec = records.get(cid, {})
    pay = C.assemble(cid, rec)
    stage = stage_of(r)
    out.append({
        "cid": cid[:8], "uid": r["user_id"][-6:],
        "grade": r["grade"], "board": r["board"], "target": r["target"],
        "ex": int(r["exchanges"] or 0),
        "image": bool(rec.get("images")), "typed": bool(pay["student"]),
        "ranked": C.preferred_trees(pay, n=3),
        "tree": r["tree"], "subject": r["subject"] if stage[0] != "n" else "",
        "chapter": r["chapter"] if r["chapter_id"] else "",
        "topic": r["topic"] if r["topic"] != "CHAPTER_ONLY" else "",
        "why": r["chapter"] if not r["chapter_id"] else "",
        "reject": REJECT.get(r["subject"], ""),
        "stage": stage, "conf": r["confidence"],
        "n": int(r["n_topics"] or 0),
        "all": [t for t in r["all_topics"].split("|") if t][1:],
        "chaps": [c for c in r["all_chapters"].split("|") if c][1:],
        "segs": len(segs.get(cid[:8], [])),
    })

# ---- grade-wise views -------------------------------------------------------
from trees import band_family
GRADES = ["6", "7", "8", "9", "10", "11", "12", "13"]
tag = [r for r in out if r["chapter"]]

def band_label(tree):
    b, _ = band_family(tree)
    return "-".join(str(x) for x in b) if b else "any"

SUBJECTS = [s for s, _ in collections.Counter(r["subject"] for r in tag).most_common()]
BANDS = sorted({band_label(r["tree"]) for r in tag},
               key=lambda b: (int(b.split("-")[0]) if b[0].isdigit() else 99, b))

grid = lambda cols, key: [
    {"row": g, "cells": [sum(1 for r in tag if r["grade"] == g and key(r) == c) for c in cols],
     "tot": sum(1 for r in tag if r["grade"] == g)}
    for g in GRADES]

by_grade = []
for g in GRADES:
    allg = [r for r in out if r["grade"] == g]
    mine = [r for r in allg if r["chapter"]]

    # one entry per conversation: the topic it reached, or the chapter where no node
    # fitted, or the reason it left the funnel. These sum to the grade's conversations.
    seen = collections.Counter()
    for r in allg:
        if r["topic"]:
            seen[(r["topic"], "topic", r["chapter"], r["subject"], r["tree"])] += 1
        elif r["chapter"]:
            seen[(r["chapter"], "chapter", r["chapter"], r["subject"], r["tree"])] += 1
        else:
            seen[(r["why"] or r["reject"], "reject", "", r["reject"], "")] += 1

    # nodes these conversations also covered, beyond the one they are counted under
    extra = collections.Counter()
    for r in mine:
        for t in r["all"]:
            extra[(t, r["chapter"])] += 1
        for c in r["chaps"]:
            extra[(c, "")] += 1

    by_grade.append({
        "grade": g, "convs": len(allg), "tagged": len(mine),
        "off": sum(1 for r in mine if band_label(r["tree"]) != g
                   and g not in band_label(r["tree"]).split("-")),
        "subjects": collections.Counter(r["subject"] for r in mine).most_common(4),
        "entries": [[lab, kind, ch, sub, tr, n] for (lab, kind, ch, sub, tr), n
                    in sorted(seen.items(), key=lambda kv: (-kv[1], kv[0][1] != "topic", kv[0][0]))],
        "extras": [[t, c, n] for (t, c), n in extra.most_common()],
    })
assert all(sum(e[5] for e in g["entries"]) == g["convs"] for g in by_grade),     "every conversation in a grade must appear exactly once"

n = len(out)
at = lambda *s: sum(1 for r in out if r["stage"] in s)
FUNNEL = [
    ("Conversation", n, "every Snap-and-Ask conversation on 20-09-2026"),
    ("User resolved", n, "conversation_id joins to user_id on all of them"),
    ("Profile read", n, "grade, board and target from the central student profile"),
    ("Trees ranked", n, "all 73 trees ordered for this student - ranked, never filtered"),
    ("Subject found", at("topic", "chapter", "no_chapter"), "the conversation is academic"),
    ("Chapter matched", at("topic", "chapter"), "a chapter in the tree covers it"),
    ("Exact topic", at("topic"), "a node inside that chapter fits"),
]
D = {
    "rows": out,
    "funnel": [{"label": l, "n": v, "note": t} for l, v, t in FUNNEL],
    "losses": [
        {"after": "Subject found", "n": at("no_subject"), "label": "not academic",
         "note": "chit-chat, app questions, a photo with no schoolwork in it"},
        {"after": "Chapter matched", "n": at("no_chapter"), "label": "no chapter covers it",
         "note": "real schoolwork the tree has no home for"},
        {"after": "Subject found", "n": at("no_signal"), "label": "nothing to go on",
         "note": "blurred or blank image, no text"},
        {"after": "Exact topic", "n": at("chapter"), "label": "chapter only",
         "note": "the chapter is right but no node inside it fits"},
    ],
    "heat": {
        "subjects": {"cols": SUBJECTS, "rows": grid(SUBJECTS, lambda r: r["subject"])},
        "bands": {"cols": BANDS, "rows": grid(BANDS, lambda r: band_label(r["tree"]))},
    },
    "byGrade": by_grade,
    "totals": {
        "convs": n, "users": len({r["uid"] for r in out}),
        "tagged": at("topic", "chapter"), "exact": at("topic"),
        "records": sum(r["n"] for r in out),
        "trees": len({r["tree"] for r in out if r["tree"]}),
        "chapters": len({r["chapter"] for r in out if r["chapter"]}),
        "topics": len({(r["tree"], r["topic"]) for r in out if r["topic"]}),
        "multi": sum(1 for r in out if r["n"] > 1 or r["chaps"]),
        "cascade": sum(1 for r in out if r["segs"]),
        "cascade_qs": sum(r["segs"] for r in out),
    },
}
json.dump(D, open(C.P("out4/funnel_data.json"), "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
for f in D["funnel"]:
    print(f'{f["n"]:>5}  {f["label"]}')
for l in D["losses"]:
    print(f'   -{l["n"]:<4} {l["label"]}')
print(D["totals"])
