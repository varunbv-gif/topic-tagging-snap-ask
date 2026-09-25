"""Tree ranking from the nine input parameters only: grade, board, target.
No stream, no examTargets, no conversation-snapshot board."""
import csv, json, collections, sys
sys.path.insert(0, ".")
from trees import band_family

concept = {tuple(k.split("\t")): v for k, v in json.load(open("out2/concepts.json", encoding="utf-8")).items()}
all_trees = sorted({t for tm in concept.values() for t in tm})
gbt = {}
for l in open("out2/gbt.tsv", encoding="utf-8"):
    cid, uid, grade, board, stream, target = l.rstrip("\n").split("\t")
    gbt[cid] = {"user_id": uid, "grade": grade, "board": board, "target": target}

BOARD = {"CBSE": "CBSE", "ICSE": "ICSE", "MAHARASHTRA": "Maharashtra"}   # STATE/OTHERS/NA/IB name no tree
TARGET = {"JEE": ("JEE", "Foundation"), "NEET": ("NEET", "Foundation"),
          "FOUNDATION": ("Foundation", "Foundation"), "OLYMPIAD": ("Olympiad", "Olympiad")}

def pick(cid, trees):
    g = gbt[cid]
    grade = int(g["grade"]) if g["grade"].isdigit() else 10
    gr = 12 if grade == 13 else grade
    board_fam = BOARD.get(g["board"], "CBSE")
    fams = {"CBSE", "NCERT", board_fam}
    if g["target"] in TARGET:
        senior, junior = TARGET[g["target"]]
        fams.add(senior if grade >= 11 else junior)
        if g["target"] == "OLYMPIAD": fams |= {"SOF-IMO", "SOF-NSO"}
    if grade >= 13: fams |= {"Upskill", "VEDANTU_HIRING"}
    def rank(t):
        band, fam = band_family(t)
        in_grade = not band or gr in band
        tier = (0 if (fam == board_fam and in_grade) else
                1 if (fam in fams and in_grade) else
                2 if (fam in {"NCERT", "CBSE"} and in_grade) else
                3 if in_grade else 4)
        gap = 0 if in_grade or not band else (gr - max(band) if max(band) <= gr else 100 + min(band) - gr)
        return (t.startswith("UNNAMED_"), tier, 0 if fam in {"CBSE", "NCERT"} else 1, gap, t)
    return min(trees, key=rank)

rows = list(csv.DictReader(open("conversation_topic_tags_v3.csv", encoding="utf-8")))
tagged = [r for r in rows if r["chapter_id"]]
nodes = json.load(open("out2/nodes_by_chapter.json", encoding="utf-8"))
same, moved = 0, []
for r in tagged:
    tm = concept[(r["subject"], r["chapter"])]
    new = pick(r["cid"], list(tm))
    r["tree_9p"], r["chapter_id_9p"] = new, tm[new]
    if new == r["tree_gbt"]: same += 1
    else: moved.append((r["tree_gbt"], new))
print(f"tree vs the GBT+snapshot-board version: {same} unchanged, {len(moved)} changed")
for (a, b), n in collections.Counter(moved).most_common():
    print(f"   {n:>2}  {a:<18} -> {b}")
json.dump({r["cid"]: [r["tree_9p"], r["chapter_id_9p"]] for r in tagged},
          open("out3/tree_9p.json", "w", encoding="utf-8"))
