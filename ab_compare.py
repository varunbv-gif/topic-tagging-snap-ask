"""A/B the two tagging methods on the same conversations.

    A  per-question   split the conversation into questions, then tag each one
                      (1 + 2n calls per conversation, n = questions found)
    B  four flat      summarise once, then subject, chapter, topic
                      (4 calls per conversation, whatever its length)

    python ab_compare.py                    # score the runs already on disk
    python ab_compare.py --cids FILE        # restrict to a set of conversations

A's output is out4/segments.jsonl, B's is out4/topic_mapping.csv + topics.jsonl.
To regenerate A: git checkout 892c6dc -- cascade.py prompts/ && python cascade.py ...
To regenerate B: the current cascade.py.

Agreement is not accuracy. Neither arm has been scored against a human-labelled
reference, so this says which method to ship, not whether either is right.
"""
import argparse, collections, csv, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(HERE, *a)


def load_a():
    """Per-question: many segments per conversation, aggregated the way A's stage 4 did."""
    out = collections.defaultdict(list)
    path = P("out4/segments.jsonl")
    if not os.path.exists(path):
        return {}
    for line in open(path, encoding="utf-8"):
        d = json.loads(line)
        out[d["conversation_id"][:8]].append(d)
    runs = {}
    for cid, segs in out.items():
        good = [s for s in segs if s.get("asked_chapter")]
        if not good:
            runs[cid] = {"reject": segs[0].get("reject") or "UNKNOWN", "chapters": [],
                         "topics": [], "questions": len(segs)}
            continue
        score = collections.Counter()
        for s in good:
            score[(s["asked_subject"], s["asked_chapter"])] += 2 + (s["confidence"] == "HIGH")
        primary = score.most_common(1)[0][0]
        chapters = [primary] + [k for k, _ in score.most_common() if k != primary]
        topics = []
        for s in good:
            t = (s["asked_chapter"], s["asked_topic"])
            if s["asked_topic"] and s["asked_topic"] != "CHAPTER_ONLY" and t not in topics:
                topics.append(t)
        runs[cid] = {"reject": None, "chapters": chapters, "topics": topics,
                     "questions": len(segs),
                     "calls": 1 + len(segs) + len(good)}
    return runs


def load_b():
    """Four flat calls: one row plus a topic list per conversation."""
    rows = P("out4/topic_mapping.csv")
    if not os.path.exists(rows):
        return {}
    tops = collections.defaultdict(list)
    if os.path.exists(P("out4/topics.jsonl")):
        for line in open(P("out4/topics.jsonl"), encoding="utf-8"):
            d = json.loads(line)
            tops[d["conversation_id"][:8]].append(d)
    covered = {}
    if os.path.exists(P("out4/summaries.jsonl")):
        for line in open(P("out4/summaries.jsonl"), encoding="utf-8"):
            d = json.loads(line)
            covered[d["conversation_id"][:8]] = len(d.get("covered") or [])
    runs = {}
    for r in csv.DictReader(open(rows, encoding="utf-8")):
        cid = r["conversation_id"][:8]
        if not r["chapter_id"]:
            runs[cid] = {"reject": r["subject"], "chapters": [], "topics": [],
                         "questions": covered.get(cid, 0), "calls": 4}
            continue
        chapters, topics = [], []
        for t in tops.get(cid, []):
            key = (t["subject"], t["chapter"])
            if key not in chapters:
                chapters.append(key)
            if t["topic"] != "CHAPTER_ONLY" and (t["chapter"], t["topic"]) not in topics:
                topics.append((t["chapter"], t["topic"]))
        if not chapters:
            chapters = [(r["subject"], r["chapter"])]
        runs[cid] = {"reject": None, "chapters": chapters, "topics": topics,
                     "questions": covered.get(cid, 0), "calls": 4}
    return runs


def jaccard(x, y):
    x, y = set(x), set(y)
    return 1.0 if not x and not y else len(x & y) / len(x | y)


def main(cids=None):
    A, B = load_a(), load_b()
    shared = sorted(set(A) & set(B))
    if cids:
        want = json.load(open(P(cids), encoding="utf-8"))
        shared = [c for c in shared if any(c.startswith(w[:8]) for w in want)]
    if not shared:
        raise SystemExit("no conversation has a result from both methods - "
                         "run each arm first (see the docstring)")

    agree_subject = agree_primary = agree_reject = 0
    chap_j, top_j, moved = [], [], []
    for c in shared:
        a, b = A[c], B[c]
        if a["reject"] or b["reject"]:
            agree_reject += bool(a["reject"]) == bool(b["reject"])
            continue
        agree_subject += a["chapters"][0][0] == b["chapters"][0][0]
        same = a["chapters"][0] == b["chapters"][0]
        agree_primary += same
        if not same:
            moved.append((c, a["chapters"][0][1], b["chapters"][0][1]))
        chap_j.append(jaccard(a["chapters"], b["chapters"]))
        top_j.append(jaccard(a["topics"], b["topics"]))

    both_tagged = len(chap_j)
    mean = lambda xs: sum(xs) / len(xs) if xs else 0.0
    qa = [A[c]["questions"] for c in shared]
    qb = [B[c]["questions"] for c in shared]
    same_q = sum(1 for c in shared if A[c]["questions"] == B[c]["questions"])

    print(f"A/B on {len(shared)} conversations  (A = per-question, B = four flat calls)\n")
    print(f"{'':34}{'A':>10}{'B':>10}")
    print(f"{'  model calls':34}{sum(A[c].get('calls', 0) for c in shared):>10}"
          f"{sum(B[c].get('calls', 0) for c in shared):>10}")
    print(f"{'  calls per conversation':34}{mean([A[c].get('calls', 0) for c in shared]):>10.1f}"
          f"{mean([B[c].get('calls', 0) for c in shared]):>10.1f}")
    print(f"{'  tagged to a chapter':34}{sum(1 for c in shared if not A[c]['reject']):>10}"
          f"{sum(1 for c in shared if not B[c]['reject']):>10}")
    print(f"{'  distinct topics recorded':34}{sum(len(A[c]['topics']) for c in shared):>10}"
          f"{sum(len(B[c]['topics']) for c in shared):>10}")
    print(f"{'  questions / things covered':34}{sum(qa):>10}{sum(qb):>10}")
    print()
    print("agreement between the two")
    print(f"  same subject                     {agree_subject}/{both_tagged}"
          f"   {100 * agree_subject / max(both_tagged, 1):.0f}%")
    print(f"  same primary chapter             {agree_primary}/{both_tagged}"
          f"   {100 * agree_primary / max(both_tagged, 1):.0f}%")
    print(f"  chapter-set overlap (mean)       {mean(chap_j):.2f}")
    print(f"  topic-set overlap (mean)         {mean(top_j):.2f}")
    print(f"  same count of questions found    {same_q}/{len(shared)}")
    print(f"  agreed on rejecting              {agree_reject}")
    if moved:
        print("\nprimary chapter differs on:")
        for c, x, y in moved:
            print(f"  {c}   A: {x}\n           B: {y}")

    verdict = []
    ca, cb = sum(A[c].get("calls", 0) for c in shared), sum(B[c].get("calls", 0) for c in shared)
    verdict.append(f"B costs {ca / max(cb, 1):.1f}x less ({cb} calls against {ca})")
    verdict.append("B is flat: 4 calls per conversation regardless of length; "
                   f"A ranges {min(A[c].get('calls', 0) for c in shared)} to "
                   f"{max(A[c].get('calls', 0) for c in shared)}")
    if agree_primary == both_tagged:
        verdict.append("they agree on every primary chapter, so there is no quality "
                       "reason to prefer A")
    elif agree_primary / max(both_tagged, 1) >= 0.9:
        verdict.append(f"they agree on {100 * agree_primary / both_tagged:.0f}% of primary "
                       f"chapters; the differences are listed above - read them before deciding")
    else:
        verdict.append(f"they disagree on {both_tagged - agree_primary} primary chapters, "
                       f"which is too many to call on cost alone")
    print("\nverdict")
    for v in verdict:
        print(f"  - {v}")
    print("\n  Agreement is not accuracy. Neither arm has been scored against a human")
    print("  reference, so this says which method to ship, not whether either is right.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cids", metavar="FILE", help="JSON list of conversation ids to score")
    main(ap.parse_args().cids)
