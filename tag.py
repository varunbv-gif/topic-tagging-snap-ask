"""Tag ShowNAsk exchanges to X_CBSE topic-tree nodes.

    python tag.py exchanges.csv catalogue.csv -o tags.csv
    python tag.py exchanges.csv catalogue.csv -o tags.csv --eval gold.csv
    python tag.py --selftest

Two LLM calls per conversation-ish: one picks a chapter for every exchange at once
(whole chapter list in a cached system block), one picks the exact node per chapter.
Everything else is plain code.
"""
import argparse, collections, csv, json, os, sys
from concurrent.futures import ThreadPoolExecutor

MODEL = os.environ.get("TAG_MODEL", "claude-sonnet-5")

RULES = """You tag school-tutoring exchanges against the Vedantu CBSE topic tree.

Each exchange is a note the tutor bot wrote about itself: `student` is what the student
asked, `delivered` is what the bot taught. Tag what was ACTUALLY TAUGHT (the delivered
side); the student side is only context for what they wanted.

Rules:
- The node must cover everything in the note, not just part of it.
- Exchanges in one conversation usually continue the same chapter. Stay in the chapter
  already chosen for a neighbouring exchange unless the note clearly moved on.
- When several grades' trees cover the same content, pick the lowest grade that covers it,
  unless the student's grade is given and its tree covers it.
- A note with an empty or meaningless `delivered` (student sent only a photo, or typed
  gibberish): carry over the neighbouring exchange's chapter if the topic plainly continues,
  else answer UNKNOWN.
- Answer NOT_IN_TREE for real academics the tree has no chapter for, NOT_ACADEMIC for
  chit-chat, app questions, or anything non-academic."""


# ---------------------------------------------------------------- catalogue

def load_catalogue(path):
    """-> (nodes, chapter_lines, nodes_under_chapter)"""
    nodes = {r["node_id"]: r for r in csv.DictReader(open(path, encoding="utf-8"))}

    def climb(nid):
        """Ancestors, nearest first, stopping at a cycle or a missing parent."""
        seen = []
        while nid in nodes and nid not in seen:
            seen.append(nid)
            nid = nodes[nid]["parent_id"]
        return seen

    def chapter_of(nid):
        return next((a for a in climb(nid) if nodes[a]["level_type"] == "CHAPTER"), None)

    chapters, under = {}, collections.defaultdict(list)
    for nid, n in nodes.items():
        if n["level_type"] == "CHAPTER":
            path = " > ".join(nodes[a]["node_name"] for a in reversed(climb(nid)))
            chapters[nid] = f'{nid} | {n["tree"]} > {path}'
        elif n["level_type"] in ("TOPIC", "SUB_TOPIC"):
            ch = chapter_of(nid)
            if ch:  # path relative to the chapter — the chapter line already states the rest
                below = climb(nid)[:climb(nid).index(ch)]
                under[ch].append(f'{nid} | ' + " > ".join(nodes[a]["node_name"] for a in reversed(below)))
    return nodes, chapters, under


# ---------------------------------------------------------------- llm

def ask(client, system_block, user_text):
    msg = client.messages.create(
        model=MODEL, max_tokens=4000,
        system=system_block,
        messages=[{"role": "user", "content": user_text}],
    )
    text = msg.content[0].text.strip()
    text = text[text.find("["):text.rfind("]") + 1]  # strip any prose around the JSON
    return json.loads(text)


def tag_conversation(client, rows, chapters, under):
    grade = rows[0].get("grade") or "unknown"
    notes = "\n".join(
        f'{r["exchange_no"]}. student: {r["student_note"] or "(none)"}\n'
        f'   delivered: {r["delivered_note"] or "(none)"}' for r in rows)

    chapter_sys = [
        {"type": "text", "text": RULES},
        {"type": "text", "text": "CHAPTERS (chapter_id | tree > subject > chapter):\n"
                                 + "\n".join(chapters.values()),
         "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": 'Reply with JSON only: [{"exchange_no":1,"chapter_id":"<id>|'
                                 'NOT_IN_TREE|NOT_ACADEMIC|UNKNOWN","confidence":"high|medium|low"}]'},
    ]
    picks = ask(client, chapter_sys,
                f"Student grade: {grade}\n\nExchanges:\n{notes}\n\nOne row per exchange.")
    by_no = {str(p["exchange_no"]): p for p in picks}

    # stage 2: exact node, one call per chapter this conversation landed in
    wanted = collections.defaultdict(list)
    for r in rows:
        p = by_no.get(r["exchange_no"], {})
        if p.get("chapter_id") in chapters:
            wanted[p["chapter_id"]].append(r)

    nodes_picked = {}
    for ch, ch_rows in wanted.items():
        listing = "\n".join([chapters[ch]] + under[ch])
        node_sys = [
            {"type": "text", "text": RULES},
            {"type": "text", "text": f"NODES in this chapter (node_id | path):\n{listing}"},
            {"type": "text", "text": 'Reply with JSON only: [{"exchange_no":1,"node_id":"<id from '
                                     'the list above>"}]. Use the chapter id itself if no topic fits.'},
        ]
        sel = "\n".join(f'{r["exchange_no"]}. delivered: {r["delivered_note"] or "(none)"}'
                        for r in ch_rows)
        valid = {ch} | {l.split(" | ")[0] for l in under[ch]}
        for p in ask(client, node_sys, sel):
            if p.get("node_id") in valid:            # reject anything not in the list
                nodes_picked[str(p["exchange_no"])] = p["node_id"]

    out = []
    for r in rows:
        p = by_no.get(r["exchange_no"], {})
        ch = p.get("chapter_id", "UNKNOWN")
        status = ch if ch in ("NOT_IN_TREE", "NOT_ACADEMIC", "UNKNOWN") else "TAGGED"
        out.append({**r,
                    "chapter_id": ch if status == "TAGGED" else "",
                    "node_id": nodes_picked.get(r["exchange_no"], ch if status == "TAGGED" else ""),
                    "status": status,
                    "confidence": p.get("confidence", ""),
                    "tag_source": "llm" if status == "TAGGED" else ""})
    return fill_blanks(out)


# ---------------------------------------------------------------- plain code

def fill_blanks(rows):
    """An untagged exchange borrows the tag before it, or the one after if it is first."""
    for i, r in enumerate(rows):
        if r["status"] == "TAGGED":
            continue
        donor = next((rows[j] for j in range(i - 1, -1, -1) if rows[j]["status"] == "TAGGED"), None) \
            or next((rows[j] for j in range(i + 1, len(rows)) if rows[j]["status"] == "TAGGED"), None)
        if donor and r["status"] == "UNKNOWN":
            r.update(chapter_id=donor["chapter_id"], node_id=donor["node_id"],
                     status="TAGGED", tag_source="carried")
    return rows


def rollup(rows):
    """Conversation tag = most-used node, counting only model-chosen tags.
    Carried tags are excluded; ties break towards the earliest exchange."""
    tagged = [r for r in rows if r["status"] == "TAGGED"]
    if not tagged:
        return {"conversation_id": rows[0]["conversation_id"], "user_id": rows[0].get("user_id", ""),
                "node_id": "", "chapter_id": "", "all_node_ids": "", "status": rows[0]["status"]}
    # a carried tag is a copy of its neighbour, not evidence — never let it outvote a real one
    voters = [r for r in tagged if r.get("tag_source") == "llm"] or tagged
    counts = collections.Counter(r["node_id"] for r in voters)
    top = max(counts, key=lambda n: (counts[n], -next(i for i, r in enumerate(voters) if r["node_id"] == n)))
    return {"conversation_id": rows[0]["conversation_id"], "user_id": rows[0].get("user_id", ""),
            "node_id": top,
            "chapter_id": next(r["chapter_id"] for r in tagged if r["node_id"] == top),
            "all_node_ids": "|".join(dict.fromkeys(r["node_id"] for r in tagged)),
            "status": "TAGGED"}


def evaluate(rows, gold_path, nodes, out_dir):
    """Chapter-level agreement against hand-checked exchanges."""
    def chapter_of(nid):
        seen = []
        while nid in nodes and nid not in seen:
            seen.append(nid)
            if nodes[nid]["level_type"] == "CHAPTER":
                return nid
            nid = nodes[nid]["parent_id"]
        return ""

    pred = {(r["conversation_id"], str(r["exchange_no"])): r for r in rows}
    hits, misses = 0, []
    gold = list(csv.DictReader(open(gold_path, encoding="utf-8")))
    for g in gold:
        p = pred.get((g["conversation_id"], str(g["exchange_no"])))
        if not p:
            continue
        want, got = chapter_of(g["node_id"]), chapter_of(p["node_id"])
        if want and want == got:
            hits += 1
        else:
            misses.append({**g, "predicted_node_id": p["node_id"], "predicted_chapter_id": got,
                           "gold_chapter_id": want, "status": p["status"],
                           "confidence": p["confidence"], "tag_source": p["tag_source"]})
    write_csv(os.path.join(out_dir, "disagreements.csv"), misses)
    total = hits + len(misses)
    print(f"chapter-level agreement: {hits}/{total} = {hits / total:.1%}" if total else "no overlap with gold")


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exchanges")
    ap.add_argument("catalogue")
    ap.add_argument("-o", "--out", default="exchange_topic_tags.csv")
    ap.add_argument("--eval")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    from anthropic import Anthropic
    client = Anthropic()

    nodes, chapters, under = load_catalogue(a.catalogue)
    convs = collections.defaultdict(list)
    for r in csv.DictReader(open(a.exchanges, encoding="utf-8")):
        convs[r["conversation_id"]].append(r)
    for rows in convs.values():
        rows.sort(key=lambda r: int(r["exchange_no"]))

    def run(rows):
        try:
            return tag_conversation(client, rows, chapters, under)
        except Exception as e:                       # one bad conversation must not sink the batch
            print(f'{rows[0]["conversation_id"]}: {e}', file=sys.stderr)
            return [{**r, "chapter_id": "", "node_id": "", "status": "ERROR",
                     "confidence": "", "tag_source": ""} for r in rows]

    with ThreadPoolExecutor(a.workers) as pool:
        results = list(pool.map(run, convs.values()))

    flat = [r for rows in results for r in rows]
    out_dir = os.path.dirname(os.path.abspath(a.out))
    write_csv(a.out, flat)
    write_csv(os.path.join(out_dir, "conversation_topic_tags.csv"), [rollup(r) for r in results])

    n = len(flat)
    share = collections.Counter(r["status"] for r in flat)
    carried = sum(r["tag_source"] == "carried" for r in flat)
    print(f"{n} exchanges / {len(results)} conversations -> {a.out}")
    print("  " + "  ".join(f"{k} {v / n:.1%}" for k, v in share.most_common()) + f"  carried {carried / n:.1%}")
    if a.eval:
        evaluate(flat, a.eval, nodes, out_dir)


def selftest():
    """The plain-code half: path building, blank fill, rollup."""
    import tempfile
    cat = "tree,node_id,level_type,node_name,parent_id\n" \
          "10_CBSE,sub,SUBJECT,Science,\n" \
          "10_CBSE,ch1,CHAPTER,Human Eye,sub\n" \
          "10_CBSE,t1,TOPIC,Accommodation,ch1\n" \
          "10_CBSE,t2,TOPIC,Myopia,ch1\n" \
          "10_CBSE,ch2,CHAPTER,Light,sub\n"
    p = os.path.join(tempfile.mkdtemp(), "c.csv")
    open(p, "w", encoding="utf-8").write(cat)
    nodes, chapters, under = load_catalogue(p)
    assert chapters["ch1"] == "ch1 | 10_CBSE > Science > Human Eye", chapters["ch1"]
    assert sorted(under["ch1"]) == ["t1 | Accommodation", "t2 | Myopia"], under["ch1"]
    assert under["ch2"] == []

    def row(n, node, status):
        return {"conversation_id": "c", "user_id": "u", "exchange_no": str(n), "node_id": node,
                "chapter_id": "ch1" if node else "", "status": status, "tag_source": "llm"}

    r = fill_blanks([row(1, "", "UNKNOWN"), row(2, "t1", "TAGGED"), row(3, "", "UNKNOWN")])
    assert [x["node_id"] for x in r] == ["t1", "t1", "t1"]          # borrows after, then before
    assert [x["tag_source"] for x in r] == ["carried", "llm", "carried"]
    assert fill_blanks([row(1, "", "NOT_ACADEMIC")])[0]["status"] == "NOT_ACADEMIC"  # never carried

    assert rollup([row(1, "t1", "TAGGED"), row(2, "t2", "TAGGED"), row(3, "t2", "TAGGED")])["node_id"] == "t2"
    assert rollup([row(1, "t1", "TAGGED"), row(2, "t2", "TAGGED")])["node_id"] == "t1"  # tie -> earliest
    assert rollup([row(1, "t1", "TAGGED"), row(2, "t2", "TAGGED")])["all_node_ids"] == "t1|t2"
    carried = {**row(1, "t1", "TAGGED"), "tag_source": "carried"}      # a borrowed tag does not vote
    assert rollup([carried, {**carried, "exchange_no": "2"}, row(3, "t2", "TAGGED")])["node_id"] == "t2"
    assert rollup([carried, {**carried, "exchange_no": "2"}])["node_id"] == "t1"   # unless it is all there is
    assert rollup([row(1, "", "NOT_ACADEMIC")])["status"] == "NOT_ACADEMIC"
    print("selftest ok")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
