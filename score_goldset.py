"""Run once the filled sheets come back: python score_goldset.py goldset_A.csv [goldset_B.csv]"""
import csv, sys, collections, json, re

norm = lambda s: re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()
key = {r["row"]: r for r in csv.DictReader(open("goldset_key.csv", encoding="utf-8"))}
# the real distribution, so the stressed sample can be weighted back to the day
full = list(csv.DictReader(open("topic_mapping.csv", encoding="utf-8")))
POP = collections.Counter()
for r in full:
    POP["not_placed" if not r["chapter_id"] else
        "chapter_only" if r["topic"] == "CHAPTER_ONLY" else
        r["confidence"].lower()] += 1
SAMP = collections.Counter(k["stratum"] for k in key.values())

def load(p):
    return {r["row"]: r for r in csv.DictReader(open(p, encoding="utf-8"))}

def agree(a_sub, a_ch, a_tp, a_off, b_sub, b_ch, b_tp, b_off):
    if a_off or b_off:
        return ("rej", a_off and b_off)
    return ("chapter", norm(a_sub) == norm(b_sub) and norm(a_ch) == norm(b_ch),
            "topic", norm(a_tp) == norm(b_tp))

def humanise(h):
    off = bool((h.get("not_on_the_tree_because") or "").strip())
    return h.get("your_subject",""), h.get("your_chapter",""), h.get("your_topic",""), off

def pipe(k):
    off = k["subject"] in ("NOT_ACADEMIC","OUT_OF_SCOPE","UNKNOWN")
    return k["subject"], k["chapter"], ("" if k["topic"] == "CHAPTER_ONLY" else k["topic"]), off

def score(A, B, label):
    per = collections.defaultdict(lambda: [0,0,0,0])   # chapter hit, chapter n, topic hit, topic n
    rej = [0,0]
    for row, ka in key.items():
        if row not in A or row not in B: continue
        s = ka["stratum"]
        a, b = A[row], B[row]
        if a[3] or b[3]:
            rej[1] += 1; rej[0] += int(a[3] and b[3]); continue
        per[s][1] += 1; per[s][0] += int(norm(a[0]) == norm(b[0]) and norm(a[1]) == norm(b[1]))
        if a[2] and b[2]:
            per[s][3] += 1; per[s][2] += int(norm(a[2]) == norm(b[2]))
    print(f"\n=== {label} ===")
    cw = tw = cn = tn = 0.0
    for s in sorted(per):
        ch, cN, tp, tN = per[s]
        w = POP[s] / SAMP[s] if SAMP[s] else 0
        cw += ch * w; cn += cN * w; tw += tp * w; tn += tN * w
        print(f"  {s:<15} chapter {ch:>2}/{cN:<2} {ch/cN if cN else 0:6.0%}   topic {tp:>2}/{tN:<2} {tp/tN if tN else 0:6.0%}")
    print(f"  {'WEIGHTED':<15} chapter {cw/cn if cn else 0:6.1%}   topic {tw/tn if tn else 0:6.1%}   (reweighted to all 271)")
    if rej[1]: print(f"  rejections agreed: {rej[0]}/{rej[1]}")

sheets = sys.argv[1:]
if not sheets:
    sys.exit("usage: python score_goldset.py goldset_A.csv [goldset_B.csv]")
As = {r: humanise(h) for r, h in load(sheets[0]).items()}
P  = {r: pipe(k) for r, k in key.items()}
score(P, As, f"pipeline vs {sheets[0]}")
if len(sheets) > 1:
    Bs = {r: humanise(h) for r, h in load(sheets[1]).items()}
    score(P, Bs, f"pipeline vs {sheets[1]}")
    score(As, Bs, "human vs human  <- the ceiling")
