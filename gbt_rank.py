"""GBT used to RANK the tree, not to RESTRICT it. Measures the change against the
snapshot-based resolver and reports how often students work outside their own grade."""
import csv, json, collections
from trees import band_family
from gbt_resolve import gbt, families, PROFILE_BOARD, SNAPSHOT_BOARD, concept, all_trees

def pick(cid, snap_board, trees):
    g = gbt[cid]
    grade = int(g["grade"]) if g["grade"].isdigit() else None
    gr = 12 if grade == 13 else grade
    fams = families(g, grade or 10, snap_board)
    board_fam = PROFILE_BOARD.get(g["board"]) or SNAPSHOT_BOARD.get(snap_board.strip().lower()) or "CBSE"
    def rank(t):
        band, fam = band_family(t)
        in_grade = gr is not None and (not band or gr in band)
        tier = (0 if (fam == board_fam and in_grade) else
                1 if (fam in fams and in_grade) else
                2 if (fam in {"NCERT","CBSE"} and in_grade) else
                3 if in_grade else 4)
        gap = 0 if in_grade or gr is None or not band else (
              gr - max(band) if max(band) <= gr else 100 + min(band) - gr)
        return (t.startswith("UNNAMED_"), tier, 0 if fam in {"CBSE","NCERT"} else 1, gap, t)
    return min(trees, key=rank)

rows = list(csv.DictReader(open("conversation_topic_tags_v2.csv", encoding="utf-8")))
tagged = [r for r in rows if r["chapter_id"]]

changed, same = [], 0
level = collections.Counter()
for r in tagged:
    tm = concept[(r["subject"], r["chapter"])]
    new = pick(r["cid"], r["board"], list(tm))
    r["tree_gbt"], r["chapter_id_gbt"] = new, tm[new]
    if new == r["tree"]: same += 1
    else: changed.append((r["tree"], new, r["subject"], r["chapter"]))
    # was the student working at their own GBT grade?
    g = gbt[r["cid"]]; gr = int(g["grade"]) if g["grade"].isdigit() else None
    band = band_family(new)[0]
    if gr is None or not band: level["unknown"] += 1
    elif gr in band or (gr == 13 and 12 in band): level["own grade"] += 1
    elif max(band) < gr: level["below their grade"] += 1
    else: level["above their grade"] += 1

print(f"tree assignment: {same} unchanged, {len(changed)} changed (of {len(tagged)})")
for (a, b), n in collections.Counter((c[0], c[1]) for c in changed).most_common(10):
    print(f"   {n:>2}  {a:<18} -> {b}")
print("\nwhat the student was actually taught, against their own GBT grade:")
for k, n in level.most_common():
    print(f"   {k:<20} {n:>3}  {n/len(tagged):5.1%}")

with open("conversation_topic_tags_v3.csv", "w", newline="", encoding="utf-8") as fh:
    cols = list(rows[0].keys())
    for c in ["user_id","gbt_grade","gbt_board","gbt_stream","gbt_target","tree_gbt","chapter_id_gbt"]:
        if c not in cols: cols.append(c)
    w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        g = gbt[r["cid"]]
        r.update(user_id=g["user_id"], gbt_grade=g["grade"], gbt_board=g["board"],
                 gbt_stream=g["stream"], gbt_target=g["target"])
        r.setdefault("tree_gbt", ""); r.setdefault("chapter_id_gbt", "")
        w.writerow(r)
print("\nwrote conversation_topic_tags_v3.csv")
