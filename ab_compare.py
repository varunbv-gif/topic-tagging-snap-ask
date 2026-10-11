"""Compare two runs of the pipeline on the same conversations.

Use it to A/B anything that changes the output: two models, two prompt revisions,
two days. Each run is a directory holding what cascade.py writes - topic_mapping.csv,
topics.jsonl and summaries.jsonl.

    python ab_compare.py runs/flash runs/pro
    python ab_compare.py runs/flash runs/pro --cids out4/sample20.json

To produce two runs to compare:

    CASCADE_MODEL=gemini-2.5-flash python cascade.py --cids out4/sample20.json
    mv out4/topic_mapping.csv out4/topics.jsonl out4/summaries.jsonl runs/flash/
    CASCADE_MODEL=gemini-2.5-pro   python cascade.py --cids out4/sample20.json
    mv out4/topic_mapping.csv out4/topics.jsonl out4/summaries.jsonl runs/pro/

Agreement is not accuracy. Two runs agreeing says they are consistent, not that
either is right; only a human-labelled reference set answers that. See
goldset_instructions.md.
"""
import argparse, collections, csv, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(run_dir):
    """One run: conversation id -> what it was tagged, and what it cost."""
    rows = os.path.join(run_dir, "topic_mapping.csv")
    if not os.path.exists(rows):
        raise SystemExit(f"{rows} not found - a run directory needs topic_mapping.csv")

    tops = collections.defaultdict(list)
    jl = os.path.join(run_dir, "topics.jsonl")
    if os.path.exists(jl):
        for line in open(jl, encoding="utf-8"):
            d = json.loads(line)
            tops[d["conversation_id"][:8]].append(d)

    covered = {}
    sj = os.path.join(run_dir, "summaries.jsonl")
    if os.path.exists(sj):
        for line in open(sj, encoding="utf-8"):
            d = json.loads(line)
            covered[d["conversation_id"][:8]] = len(d.get("covered") or [])

    out = {}
    for r in csv.DictReader(open(rows, encoding="utf-8")):
        cid = r["conversation_id"][:8]
        if not r["chapter_id"]:
            out[cid] = {"reject": r["subject"], "subject": "", "chapters": [], "topics": [],
                        "covered": covered.get(cid, 0)}
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
        out[cid] = {"reject": None, "subject": chapters[0][0], "chapters": chapters,
                    "topics": topics, "covered": covered.get(cid, 0)}
    return out


def jaccard(x, y):
    x, y = set(x), set(y)
    return 1.0 if not x and not y else len(x & y) / len(x | y)


def main(dir_a, dir_b, cids=None):
    A, B = load(dir_a), load(dir_b)
    shared = sorted(set(A) & set(B))
    if cids:
        want = json.load(open(os.path.join(HERE, cids), encoding="utf-8"))
        shared = [c for c in shared if any(c.startswith(w[:8]) for w in want)]
    if not shared:
        raise SystemExit("the two runs share no conversation")

    only_a = sorted(set(A) - set(B))
    only_b = sorted(set(B) - set(A))

    agree_subject = agree_primary = agree_reject = 0
    chap_j, top_j, moved, both = [], [], [], 0
    for c in shared:
        a, b = A[c], B[c]
        if a["reject"] or b["reject"]:
            agree_reject += bool(a["reject"]) == bool(b["reject"])
            if bool(a["reject"]) != bool(b["reject"]):
                moved.append((c, a["reject"] or a["chapters"][0][1],
                              b["reject"] or b["chapters"][0][1]))
            continue
        both += 1
        agree_subject += a["subject"] == b["subject"]
        same = a["chapters"][0] == b["chapters"][0]
        agree_primary += same
        if not same:
            moved.append((c, a["chapters"][0][1], b["chapters"][0][1]))
        chap_j.append(jaccard(a["chapters"], b["chapters"]))
        top_j.append(jaccard(a["topics"], b["topics"]))

    mean = lambda xs: sum(xs) / len(xs) if xs else 0.0
    na, nb = os.path.basename(dir_a.rstrip("/\\")), os.path.basename(dir_b.rstrip("/\\"))
    pc = lambda n, d: f"{100 * n / d:.0f}%" if d else "-"

    print(f"{len(shared)} conversations in both runs"
          + (f"  ({len(only_a)} only in {na}, {len(only_b)} only in {nb})"
             if only_a or only_b else "") + "\n")
    print(f"{'':34}{na:>12}{nb:>12}")
    print(f"{'  tagged to a chapter':34}"
          f"{sum(1 for c in shared if not A[c]['reject']):>12}"
          f"{sum(1 for c in shared if not B[c]['reject']):>12}")
    print(f"{'  distinct topics recorded':34}{sum(len(A[c]['topics']) for c in shared):>12}"
          f"{sum(len(B[c]['topics']) for c in shared):>12}")
    print(f"{'  things the summary covered':34}{sum(A[c]['covered'] for c in shared):>12}"
          f"{sum(B[c]['covered'] for c in shared):>12}")
    print()
    print("agreement")
    print(f"  same subject                     {agree_subject}/{both}   {pc(agree_subject, both)}")
    print(f"  same primary chapter             {agree_primary}/{both}   {pc(agree_primary, both)}")
    print(f"  chapter-set overlap (mean)       {mean(chap_j):.2f}")
    print(f"  topic-set overlap (mean)         {mean(top_j):.2f}")
    print(f"  agreed on rejecting              {agree_reject}")
    print(f"  same count of things covered     "
          f"{sum(1 for c in shared if A[c]['covered'] == B[c]['covered'])}/{len(shared)}")

    if moved:
        print(f"\nthey differ on {len(moved)}:")
        for c, x, y in moved[:20]:
            print(f"  {c}   {na}: {x}\n           {nb}: {y}")
        if len(moved) > 20:
            print(f"  ... and {len(moved) - 20} more")

    print("\n  Agreement is not accuracy. Two runs agreeing says they are consistent,")
    print("  not that either is right - only a human-labelled reference set answers")
    print("  that. See goldset_instructions.md.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_a", help="directory holding one run's output")
    ap.add_argument("run_b", help="directory holding the other run's output")
    ap.add_argument("--cids", metavar="FILE", help="JSON list of conversation ids to score")
    a = ap.parse_args()
    main(a.run_a, a.run_b, a.cids)
