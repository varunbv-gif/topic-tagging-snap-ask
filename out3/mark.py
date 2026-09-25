"""mark.py <file> [cid8=chapters;topics ...]  -> appends every cid in the file,
single-topic unless overridden."""
import sys, re, csv
f = sys.argv[1]
over = {}
for a in sys.argv[2:]:
    cid8, rest = a.split("=", 1)
    ch, tp = (rest.split(";") + [""])[:2]
    over[cid8] = (ch, tp)
full = {r["conversation_id"][:8]: r["conversation_id"]
        for r in csv.DictReader(open("topic_mapping.csv", encoding="utf-8"))}
cids = [l.split()[1] for l in open(f, encoding="utf-8") if l.startswith("### ")]
done = {l.split("\t")[0] for l in open("out3/multi_result.tsv", encoding="utf-8") if l.strip()}
n = m = 0
with open("out3/multi_result.tsv", "a", encoding="utf-8") as out:
    for c8 in cids:
        cid = full[c8]
        if cid in done: continue
        ch, tp = over.get(c8, ("", ""))
        out.write(f"{cid}\t{ch}\t{tp}\n"); n += 1; m += bool(ch or tp)
print(f"{f}: {n} recorded, {m} multi")
