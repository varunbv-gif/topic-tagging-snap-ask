"""Write one conversation in the reference sheet's layout, with the pipeline's columns added.

    python out4/make_turn_csv.py 8d31eff5

Left of the divider is the sheet as supplied: turn by turn, exact verbatim, the two prior
coverage columns. Right of it is what the pipeline does with those same turns - which
segment the turn belongs to, and what that segment was tagged.
"""
import csv, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cascade as C

SHEET = os.path.join(os.path.expanduser("~"), "Downloads", "Snap & Ask - Sheet2.csv")
HEAD = ["Turn", "Role", "Exact Verbatim", "Prior Coverage Recent", "Prior Coverage Older Delivered",
        "|", "Stage 0 field", "Segment", "Posed (the ask)", "Delivered (what the bot did)",
        "Subject", "Chapter", "Topic", "Topic ID", "Tree", "Confidence", "Ask source"]


def turns_from_sheet(path):
    """The reference sheet is the turn-level record; conv_records.json is already collapsed."""
    rows = list(csv.reader(open(path, encoding="utf-8")))
    start = next(i for i, r in enumerate(rows) if r and r[0] == "User Turn")
    return [r for r in rows[start:] if r and r[0] in ("User Turn", "Bot Turn")]


def which_segment(text, segs):
    """Attribute a turn to a segment by word overlap with its posed/delivered lines."""
    words = set(re.findall(r"[a-z0-9]{4,}", (text or "").lower()))
    if not words:
        return None
    best, score = None, 0
    for s in segs:
        hay = set(re.findall(r"[a-z0-9]{4,}", f"{s['posed']} {s['delivered']}".lower()))
        hit = len(words & hay)
        if hit > score:
            best, score = s, hit
    return best if score >= 2 else None


def main(short):
    segs = [json.loads(l) for l in open(C.P("out4/segments.jsonl"), encoding="utf-8")
            if json.loads(l)["conversation_id"].startswith(short)]
    if not segs:
        raise SystemExit(f"no segments for {short} - run cascade.py first")
    records = json.load(open(C.P("out2/conv_records.json"), encoding="utf-8"))
    cid = next(k for k in records if k.startswith(short))
    pay = C.assemble(cid, records[cid])

    turns = turns_from_sheet(SHEET) if os.path.exists(SHEET) else []
    stage0 = [("user_id", pay["user_id"]), ("conversation_id", pay["conversation_id"]),
              ("grade", pay["grade"]), ("board", pay["board"]), ("target", pay["target"]),
              ("exchanges", pay["exchanges"]), ("student (chips stripped)", pay["student"]),
              ("taught (de-duplicated)", pay["taught"]), ("wanted", pay["wanted"]),
              ("earlier", pay["earlier"])]

    out = [HEAD]
    for i, t in enumerate(turns, 1):
        role, verbatim = t[0], (t[1] if len(t) > 1 else "")
        recent = t[2] if len(t) > 2 else ""
        older = t[3] if len(t) > 3 else ""
        s = which_segment(verbatim, segs) if role == "Bot Turn" else None
        f = stage0[i - 1] if i <= len(stage0) else ("", "")
        row = [i, role, verbatim, recent, older, "|", f"{f[0]}: {f[1]}" if f[0] else ""]
        row += ([s["segment"], s["posed"], s["delivered"], s["asked_subject"], s["asked_chapter"],
                 s["asked_topic"], s["asked_topic_id"], s["tree"], s["confidence"], s["ask_source"]]
                if s else ["", "", "", "", "", "", "", "", "", ""])
        out.append(row)

    out += [[], ["SEGMENTS - what stage 1 split this conversation into"],
            ["Segment", "Posed (the ask)", "Delivered", "Ask source", "Diverged",
             "Subject", "Chapter", "Chapter ID", "Topic", "Topic ID", "Level", "Tree", "Confidence"]]
    for s in segs:
        out.append([s["segment"], s["posed"], s["delivered"], s["ask_source"],
                    "yes" if s["diverged"] else "no", s["asked_subject"], s["asked_chapter"],
                    s["asked_chapter_id"], s["asked_topic"], s["asked_topic_id"],
                    s["asked_topic_level"], s["tree"], s["confidence"]])

    row = next(r for r in csv.DictReader(open(C.P("out4/topic_mapping.csv"), encoding="utf-8"))
               if r["conversation_id"].startswith(short))
    out += [[], ["FINAL ROW - one per conversation, what stage 4 wrote"], list(row.keys()), list(row.values())]

    path = C.P("out4", f"conversation_{short}.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows(out)
    print(f"{path}\n{len(turns)} turns, {len(segs)} segment(s)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "8d31eff5")
