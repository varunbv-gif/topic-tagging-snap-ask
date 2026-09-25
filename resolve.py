"""Validate tags, resolve each chapter concept to one tree instance, score the three scopes."""
import json, collections, csv, re
from trees import band_family, BOARD, target_families

SENTINELS = {"OUT_OF_SCOPE", "NOT_ACADEMIC", "UNKNOWN"}
conv = json.load(open("out2/conv_records.json", encoding="utf-8"))
concept = {tuple(k.split("\t")): v for k, v in json.load(open("out2/concepts.json", encoding="utf-8")).items()}

tags = []
for line in open("out2/tags.tsv", encoding="utf-8"):
    if not line.strip(): continue
    p = (line.rstrip("\n").split("\t") + ["", "", "", "", ""])[:5]
    tags.append(dict(zip(["cid", "subject", "chapter", "confidence", "note"], p)))

bad = [t for t in tags if t["subject"] not in SENTINELS and (t["subject"], t["chapter"]) not in concept]
print("invalid (subject, chapter) pairs:", len(bad))
for t in bad[:20]: print("   ", t["cid"], "|", t["subject"], "|", t["chapter"])

# ---- scope definitions -------------------------------------------------
all_trees = sorted({t for tm in concept.values() for t in tm})
def fam(t): return band_family(t)[1]
SCOPE_A = {t for t in all_trees if fam(t) == "CBSE"}                          # the original run
SCOPE_B = {t for t in all_trees if fam(t) in {"CBSE", "Foundation", "NCERT"}}  # the asked-for middle
SCOPE_C = set(all_trees)                                                      # everything
print(f"scopes: A={len(SCOPE_A)} trees  B={len(SCOPE_B)} trees  C={len(SCOPE_C)} trees")

def pick_tree(rec, trees):
    """Deterministic tree choice: declared board, then exam target, then NCERT/CBSE,
    then the tree whose grade band sits closest below the student's grade.
    The five UNNAMED trees are unretired duplicates and always rank last."""
    grade = int(rec["grade"]) if rec["grade"].isdigit() else None
    if grade == 13:            # 13 = the post-school / upskill band; treat as senior secondary
        grade = 12
    board_fam = BOARD.get(rec["board"].strip().lower(), "CBSE")
    tgt = target_families(rec["target"], rec["exam_targets"], grade)

    def rank(t):
        g, f = band_family(t)
        in_grade = grade is not None and (not g or grade in g)
        tier = (0 if (f == board_fam and in_grade) else
                1 if (f in tgt and in_grade) else
                2 if (f in {"NCERT", "CBSE"} and in_grade) else
                3 if in_grade else 4)
        # among out-of-grade trees, prefer the band closest at or below the student's grade
        gap = 0 if in_grade or grade is None or not g else (
              grade - max(g) if max(g) <= grade else 100 + min(g) - grade)
        # when no tree matches the declared grade, the CBSE/NCERT backbone beats a
        # nearer-grade tree from another board: the declared grade is often wrong
        # (grade-8 students doing De Moivre, grade-10 students doing JEE pulleys)
        return (t.startswith("UNNAMED_"), tier,
                0 if f in {"CBSE", "NCERT"} else 1, gap, t)
    return min(trees, key=rank)

rows = []
for t in tags:
    rec = conv[t["cid"]]
    key = (t["subject"], t["chapter"])
    if t["subject"] in SENTINELS:
        rows.append({**t, "tree": "", "chapter_id": "", "in_A": "", "in_B": "", "in_C": "",
                     "grade": rec["grade"], "board": rec["board"], "target": rec["target"],
                     "exchanges": rec["exchanges"]})
        continue
    tm = concept[key]
    rows.append({**t,
                 "tree": pick_tree(rec, list(tm)),
                 "chapter_id": tm[pick_tree(rec, list(tm))],
                 "in_A": "Y" if set(tm) & SCOPE_A else "N",
                 "in_B": "Y" if set(tm) & SCOPE_B else "N",
                 "in_C": "Y",
                 "grade": rec["grade"], "board": rec["board"], "target": rec["target"],
                 "exchanges": rec["exchanges"]})

with open("out2/conversation_tags_v2.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["cid","subject","chapter","confidence","tree","chapter_id",
                                       "in_A","in_B","in_C","grade","board","target","exchanges","note"])
    w.writeheader(); w.writerows(rows)

tagged = [r for r in rows if r["subject"] not in SENTINELS]
print(f"\ntagged to a chapter: {len(tagged)}/271 ({len(tagged)/271:.1%})")
for s in sorted(SENTINELS):
    n = sum(1 for r in rows if r["subject"] == s)
    ex = sum(r["exchanges"] for r in rows if r["subject"] == s)
    print(f"  {s:<14} {n:>3} conversations, {ex:>4} exchanges")
print("\nreachable under each scope (of the 271):")
for k, lab in [("in_A","CBSE only (9 trees)"), ("in_B","CBSE+Foundation+NCERT (14)"), ("in_C","all 73 trees")]:
    n = sum(1 for r in tagged if r[k] == "Y")
    print(f"  {lab:<32} {n:>3} = {n/271:.1%} of all conversations")
print("\nconfidence:", dict(collections.Counter(r["confidence"] for r in tagged)))
print("subjects:", dict(collections.Counter(r["subject"] for r in tagged).most_common()))
