"""Parse tree names into (grade band, family) and pick the candidate trees for a student."""
import re, json, collections

REGISTRY = """67c6dbe1e97ac5b1988cedcf|11_12_NEET|67c6dbe1e97ac5b1988cedf7|11_12_CBSE|67c6dbe0e97ac5b1988cedbc|11_12_JEE
67c6dbe2e97ac5b1988cee97|8_CBSE|67c6dbe1e97ac5b1988cee40|5_CBSE|67c6dbe1e97ac5b1988cee17|11_12_Commerce"""  # unused; names come from the catalogue

def band_family(tree):
    """'11_12_NEET' -> ([11,12], 'NEET');  'Level_9_Olympiad' -> ([], 'Olympiad')."""
    parts = tree.split("_")
    g = []
    while parts and parts[0].isdigit():
        g.append(int(parts.pop(0)))
    fam = "_".join(parts) if parts else tree
    if tree.startswith("Level_"):
        g, fam = [], "Olympiad"
    return g, fam

BOARD = {"cbse":"CBSE","icse":"ICSE","mh":"Maharashtra","maharashtra":"Maharashtra",
         "bse telangana":"Telangana","bieap":"AP","bsed":"AP"}
# BSER (Rajasthan), BHSIEUP (UP), IB, "State Board", "Others" have no tree -> CBSE/NCERT backbone

def target_families(target, exam_targets, grade):
    t = " ".join([target, exam_targets]).lower()
    fams = set()
    if "jee" in t or "engineering entrance" in t:
        fams |= {"JEE"} if grade and grade >= 11 else {"Foundation"}
    if "neet" in t:
        fams |= {"NEET"} if grade and grade >= 11 else {"Foundation"}
    if "foundation" in t:
        fams.add("Foundation")
    if "olympiad" in t:
        fams |= {"Olympiad", "SOF-IMO", "SOF-NSO"}
    if "cuet" in t:
        fams.add("CUET")
    return fams

def shortlist(rec, all_trees):
    """Candidate tree names for one conversation record. Empty grade -> every tree."""
    grade = int(rec["grade"]) if rec["grade"].isdigit() else None
    if grade is None:
        return sorted(all_trees)
    fams = {"CBSE", "NCERT"}                                   # backbone, always
    fams.add(BOARD.get(rec["board"].strip().lower(), "CBSE"))   # declared board
    fams |= target_families(rec["target"], rec["exam_targets"], grade)
    if grade >= 11:
        fams |= {"Commerce"} if "commerce" in (rec["stream"] + rec["target"]).lower() else set()
    if grade >= 13:
        fams |= {"Upskill", "VEDANTU_HIRING"}
    out = []
    for tr in all_trees:
        g, fam = band_family(tr)
        if fam not in fams:
            continue
        if g and grade not in g and grade < 13:
            continue
        out.append(tr)
    return sorted(out) or sorted(all_trees)

if __name__ == "__main__":
    ch = [l.rstrip("\n").split("\t") for l in open("out2/chapters_all.tsv", encoding="utf-8")]
    all_trees = sorted({c[0] for c in ch})
    by_tree = collections.Counter(c[0] for c in ch)
    conv = json.load(open("out2/conv_records.json", encoding="utf-8"))
    sizes, widened = [], 0
    picks = collections.Counter()
    for cid, rec in conv.items():
        s = shortlist(rec, all_trees)
        rec["trees"] = s
        n = sum(by_tree[t] for t in s)
        sizes.append(n)
        if len(s) == len(all_trees): widened += 1
        for t in s: picks[t] += 1
    sizes.sort()
    print(f"candidate chapters per conversation: median {sizes[len(sizes)//2]}  max {sizes[-1]}  min {sizes[0]}")
    print(f"conversations falling back to all 73 trees (no grade): {widened}")
    print("most-shortlisted trees:", picks.most_common(14))
    json.dump(conv, open("out2/conv_records.json","w",encoding="utf-8"), ensure_ascii=False)

    # sanity: the mapping must be stable and must never return an empty list
    assert band_family("11_12_NEET") == ([11,12], "NEET")
    assert band_family("9_10_Tamilnadu") == ([9,10], "Tamilnadu")
    assert band_family("Level_9_Olympiad") == ([], "Olympiad")
    assert band_family("13_VEDANTU_HIRING") == ([13], "VEDANTU_HIRING")
    assert all(rec["trees"] for rec in conv.values())
    print("selftest ok")
