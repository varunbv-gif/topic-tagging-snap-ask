"""Resolve the tree from the central student profile (the GBT) instead of the
conversation snapshot, and measure what changes."""
import csv, json, collections
from trees import band_family

concept = {tuple(k.split("\t")): v for k, v in json.load(open("out2/concepts.json", encoding="utf-8")).items()}
all_trees = sorted({t for tm in concept.values() for t in tm})

gbt = {}
for l in open("out2/gbt.tsv", encoding="utf-8"):
    cid, uid, grade, board, stream, target = l.rstrip("\n").split("\t")
    gbt[cid] = {"user_id": uid, "grade": grade, "board": board, "stream": stream, "target": target}

# the profile board is a 7-value enum; STATE/OTHERS/NA/IB name no tree family
PROFILE_BOARD = {"CBSE": "CBSE", "ICSE": "ICSE", "MAHARASHTRA": "Maharashtra"}
# the conversation snapshot keeps the specific state board the profile flattens away
SNAPSHOT_BOARD = {"bieap": "AP", "bsed": "AP", "bse telangana": "Telangana",
                  "mh": "Maharashtra", "maharashtra": "Maharashtra",
                  "cbse": "CBSE", "icse": "ICSE"}

def families(g, grade, snap_board=""):
    """Tree families this student's GBT selects. CBSE+NCERT is always the backbone."""
    fams = {"CBSE", "NCERT"}
    b = PROFILE_BOARD.get(g["board"])
    if not b and snap_board:                       # profile said STATE/OTHERS - recover from the snapshot
        b = SNAPSHOT_BOARD.get(snap_board.strip().lower())
    if b: fams.add(b)
    t = g["target"]
    if t == "JEE":        fams.add("JEE" if grade >= 11 else "Foundation")
    elif t == "NEET":     fams.add("NEET" if grade >= 11 else "Foundation")
    elif t == "FOUNDATION": fams.add("Foundation")
    elif t == "OLYMPIAD": fams |= {"Olympiad", "SOF-IMO", "SOF-NSO"}
    if grade >= 13: fams |= {"Upskill", "VEDANTU_HIRING"}
    return fams

def shortlist(g, snap_board=""):
    grade = int(g["grade"]) if g["grade"].isdigit() else None
    if grade is None: return sorted(all_trees)
    fams = families(g, grade, snap_board)
    gr = 12 if grade == 13 else grade
    out = [t for t in all_trees
           if band_family(t)[1] in fams
           and (not band_family(t)[0] or gr in band_family(t)[0] or grade >= 13)]
    return sorted(out) or sorted(all_trees)

rows = list(csv.DictReader(open("conversation_topic_tags_v2.csv", encoding="utf-8")))
tagged = [r for r in rows if r["chapter_id"]]

for label, use_snap in [("profile GBT only", False), ("profile GBT + snapshot board", True)]:
    hit = miss = 0
    sizes = []
    missed = []
    for r in tagged:
        g = gbt[r["cid"]]
        sl = set(shortlist(g, r["board"] if use_snap else ""))
        sizes.append(sum(1 for (s, c), tm in concept.items() if sl & tm.keys()))
        if sl & concept[(r["subject"], r["chapter"])].keys(): hit += 1
        else:
            miss += 1
            missed.append((r["subject"], r["chapter"], r["tree"], g["grade"], g["board"], g["target"]))
    sizes.sort()
    print(f"\n=== {label} ===")
    print(f"  tagged chapter reachable from the student's own trees: {hit}/{len(tagged)} ({hit/len(tagged):.1%})")
    print(f"  candidate chapters per student: median {sizes[len(sizes)//2]}, max {sizes[-1]}")
    if not use_snap:
        continue
    print(f"  out of reach: {miss}")
    for m, n in collections.Counter(missed).most_common(12):
        print(f"     {n}x  {m[0]} | {m[1]}  (was {m[2]}; profile grade {m[3]} board {m[4]} target {m[5]})")

# how often does the profile disagree with the snapshot?
dg = sum(1 for r in rows if r["grade"] and gbt[r["cid"]]["grade"] != r["grade"])
noc = sum(1 for r in rows if not r["grade"])
print(f"\nprofile grade vs conversation snapshot: {dg} disagree, {noc} had no snapshot grade at all")
