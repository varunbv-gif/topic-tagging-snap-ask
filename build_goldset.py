"""Blind labelling pack: a stratified sample of conversations with the evidence the
tagger saw, and no tag. The pipeline's answer is held back in a separate key file."""
import csv, json, random, collections, re
random.seed(20260920)

rows = {r["conversation_id"]: r for r in csv.DictReader(open("topic_mapping.csv", encoding="utf-8"))}
conv = json.load(open("out2/conv_records.json", encoding="utf-8"))
tagged = [r for r in rows.values() if r["chapter_id"]]
nodes  = json.load(open("out2/nodes_by_chapter.json", encoding="utf-8"))

def dup_name(r):
    c = collections.Counter(n["name"] for n in nodes.get(r["chapter_id"], []))
    return bool(r["topic"]) and c.get(r["topic"], 0) > 1

strata = {
  "chapter_only":   [r for r in tagged if r["topic"] == "CHAPTER_ONLY"],
  "duplicate_node": [r for r in tagged if dup_name(r)],
  "low":            [r for r in tagged if r["confidence"] == "LOW"],
  "med":            [r for r in tagged if r["confidence"] == "MED" and r["topic"] != "CHAPTER_ONLY"],
  "high":           [r for r in tagged if r["confidence"] == "HIGH" and r["topic"] != "CHAPTER_ONLY"],
  "not_placed":     [r for r in rows.values() if not r["chapter_id"]],
}
QUOTA = {"chapter_only": 9, "duplicate_node": 8, "low": 3, "med": 14, "high": 18, "not_placed": 8}

picked, seen = [], set()
for k in ("chapter_only", "duplicate_node", "low", "not_placed", "med", "high"):
    pool = [r for r in strata[k] if r["conversation_id"] not in seen]
    # spread across subjects so one stratum is not all Mathematics
    pool.sort(key=lambda r: (collections.Counter(x["subject"] for x in picked)[r["subject"]], random.random()))
    take = pool[:QUOTA[k]]
    for r in take:
        seen.add(r["conversation_id"]); picked.append({**r, "stratum": k})

def evidence(cid, n=1100):
    c = conv[cid]
    parts = []
    if c["student_typed"]:    parts.append("STUDENT TYPED: " + c["student_typed"][:420])
    if c["taught"]:           parts.append("BOT'S NOTE ON WHAT IT TAUGHT: " + c["taught"][:900])
    if c["older_delivered"]:  parts.append("EARLIER IN THE CONVERSATION: " + c["older_delivered"][:400])
    if not c["taught"]:       parts.append("BOT'S REPLY: " + (c["answer"] or "(none)")[:700])
    return "  ||  ".join(parts)[:2200]

random.shuffle(picked)                       # hide the strata from the labeller
with open("goldset_blind.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["row","conversation_id","grade","board","target","exchanges","evidence",
                "your_subject","your_chapter","your_topic","not_on_the_tree_because","your_notes"])
    for i, r in enumerate(picked, 1):
        w.writerow([i, r["conversation_id"], r["grade"], r["board"], r["target"], r["exchanges"],
                    evidence(r["conversation_id"]), "", "", "", "", ""])

with open("goldset_key.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["row","conversation_id","stratum","subject","chapter",
                                       "topic","topic_level","tree","confidence","note"])
    w.writeheader()
    for i, r in enumerate(picked, 1):
        w.writerow({"row": i, **{k: r[k] for k in ("conversation_id","stratum","subject","chapter",
                                                   "topic","topic_level","tree","confidence","note")}})
print(f"{len(picked)} conversations sampled")
for k, v in collections.Counter(r["stratum"] for r in picked).items(): print(f"   {k:<16}{v}")
print("subjects:", dict(collections.Counter(r["subject"] for r in picked).most_common()))
print("median evidence length:", sorted(len(evidence(r["conversation_id"])) for r in picked)[len(picked)//2], "chars")
