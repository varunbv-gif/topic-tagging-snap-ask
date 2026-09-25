"""Payload with exactly the nine requested input parameters."""
import json, os, glob, csv

CAPS = {"input": 900, "response": 1600, "wanted": 500, "taught": 2200, "earlier": 900}
cut = lambda s, n: s if len(s) <= n else s[:n] + " …"

conv = json.load(open("out2/conv_records.json", encoding="utf-8"))
gbt = {}
for l in open("out2/gbt.tsv", encoding="utf-8"):
    cid, uid, grade, board, stream, target = l.rstrip("\n").split("\t")
    gbt[cid] = (uid, grade, board, target)

def block(cid):
    r, (uid, grade, board, target) = conv[cid], gbt[cid]
    # "what did the bot respond" - the spoken reply plus the written worked solution
    response = " ".join(x for x in (r["answer"], r["md"]) if x)
    fields = [("INPUT", cut(r["student_typed"], CAPS["input"])),
              ("RESPONSE", cut(response, CAPS["response"])),
              ("WANTED(note)", cut(r["wanted"], CAPS["wanted"])),
              ("TAUGHT(note)", cut(r["taught"], CAPS["taught"])),
              ("EARLIER(note)", cut(r["older_delivered"], CAPS["earlier"]))]
    L = [f"USER: {uid}", f"CONVERSATION: {cid}",
         f"PROFILE: grade={grade} board={board} target={target}"]
    L += [f"{k}: {v}" for k, v in fields if v]
    return "\n".join(L)

os.makedirs("out3/payloads", exist_ok=True)
for f in glob.glob("out3/payloads/*"): os.remove(f)
blocks = {cid: block(cid) for cid in sorted(conv)}
cur, n, i = [], 0, 0
for cid, b in blocks.items():
    if cur and n + len(b) > 15000:
        open(f"out3/payloads/p{i:02d}.txt", "w", encoding="utf-8").write("\n\n".join(cur)); cur, n, i = [], 0, i+1
    cur.append(b); n += len(b)
if cur: open(f"out3/payloads/p{i:02d}.txt", "w", encoding="utf-8").write("\n\n".join(cur)); i += 1
kb = sum(len(b) for b in blocks.values()) / 1024
print(f"{len(blocks)} conversation payloads, {kb:.0f} KB, {i} files")
present = {k: sum(1 for cid in conv if (block(cid).find(k) >= 0)) for k in
           ["INPUT:", "RESPONSE:", "WANTED(note):", "TAUGHT(note):", "EARLIER(note):"]}
print("field present on:", present)
