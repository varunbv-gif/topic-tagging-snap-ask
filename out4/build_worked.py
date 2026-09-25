"""out4/worked.json - for five conversations, the real input, prompt and output at every stage.

Feeds both out4/how_it_works_5_conversations.csv and section 8 of the docx, so the two
can never disagree.
"""
import csv, json, os, sys, collections

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cascade as C

PICK = [
    ("8d31eff5", "A straightforward one - one question, one topic"),
    ("4a74c906", "One photo, one turn, but two topics inside it"),
    ("57aa81aa", "Two questions from the same worksheet page"),
    ("c1aa54f2", "A long revision session across two chapters"),
    ("3b17d1f8", "One we could not tag, and why"),
]

records = json.load(open(C.P("out2/conv_records.json"), encoding="utf-8"))
final = {r["conversation_id"][:8]: r for r in
         csv.DictReader(open(C.P("out4/topic_mapping.csv"), encoding="utf-8"))}
segs = collections.defaultdict(list)
for l in open(C.P("out4/segments.jsonl"), encoding="utf-8"):
    s = json.loads(l)
    segs[s["conversation_id"][:8]].append(s)

cached = lambda prompt, prefix=None: C.CACHE.get(C.cache_key(prompt, prefix), "")
PREFIX = C.PROMPT["2_chapter"].format(catalogue=C.CATALOGUE)

# the nine input parameters, in the order section 2 of the doc lists them
NINE = [
    ("user_id", "conversations.user_id"),
    ("conversation_id", "conversations.conversation_id"),
    ("student", "input_parts where kind='text', user turns"),
    ("response", "response.text and .md, bot turns"),
    ("wanted", "prior_coverage_recent.student"),
    ("taught", "prior_coverage_recent.delivered"),
    ("earlier", "prior_coverage_older_delivered"),
    ("grade", "analytics_rag.student.grade"),
    ("board", "analytics_rag.student.board"),
    ("target", "analytics_rag.student.target"),
]

out = []
for cid8, why in PICK:
    cid = next(k for k in records if k.startswith(cid8))
    pay = C.assemble(cid, records[cid])
    mine = sorted(segs[cid8], key=lambda s: s["segment"])
    row = final[cid8]

    s1_prompt = C.p_segment(pay)
    entry = {
        "cid": cid8, "why": why,
        "stage0": {
            "inputs": [[name, src, str(pay.get(name, ""))] for name, src in NINE],
            "derived": [
                ["exchanges", "counted from the turns", str(pay["exchanges"])],
                ["has_image", "input_parts where kind='image'", "yes" if pay["has_image"] else "no"],
                ["preferred trees", "computed from grade, board, target",
                 ", ".join(C.preferred_trees(pay, n=6)) + ", …"],
            ],
        },
        "stage1": {
            "inputs": [[k, str(pay[k] or "(empty)")] for k in
                       ("student", "wanted", "taught", "response", "earlier")],
            "prompt": s1_prompt,
            "output": cached(s1_prompt),
        },
        "segments": [],
    }

    for s in mine:
        text = s["posed"] or s["delivered"] or ""
        p2 = C.p_chapter(pay, "POSED", text)
        pick = {"subject": s["asked_subject"], "chapter": s["asked_chapter"],
                "tree": s["tree"], "confidence": s["confidence"]}
        carriers = C.CONCEPT.get((pick["subject"], pick["chapter"]), {})
        order = C.preferred_trees(pay, n=len(C.ALL_TREES))
        pick["trees"] = sorted(carriers, key=order.index)
        nodes = C.nodes_for(pick) if carriers else []
        p3 = C.p_topic(pick, "POSED", text) if nodes else ""
        entry["segments"].append({
            "i": s["segment"],
            "stage2": {
                "inputs": [["the question (POSED)", text],
                           ["grade", pay["grade"]], ["board", pay["board"]],
                           ["target", pay["target"]],
                           ["preferred tree order", ", ".join(C.preferred_trees(pay, n=6)) + ", …"],
                           ["catalogue", f"{len(C.CATALOGUE.splitlines()):,} subject|chapter rows, "
                                         f"{len(PREFIX):,} characters, cached - identical on every call"]],
                "prompt_tail": p2,
                "output": cached(p2, PREFIX),
            },
            "stage3": {
                "inputs": [["the question (POSED)", text],
                           ["subject", pick["subject"]], ["chapter", pick["chapter"]],
                           ["trees carrying it", ", ".join(pick["trees"]) or "(none)"],
                           ["nodes offered", f"{len(nodes)} node(s) across those trees, "
                                             f"de-duplicated on name"]],
                "prompt": p3,
                "output": cached(p3) if p3 else
                          '{"topic_id":"","topic":"CHAPTER_ONLY","note":"nodes for this chapter '
                          'have never been fetched - stage 3 did not run"}',
            } if carriers else None,
            "result": {k: s[k] for k in ("posed", "delivered", "ask_source", "diverged",
                                         "asked_subject", "asked_chapter", "asked_chapter_id",
                                         "asked_topic", "asked_topic_id", "asked_topic_level",
                                         "tree", "confidence", "reject")},
        })

    entry["stage4"] = {k: row[k] for k in row}
    out.append(entry)

json.dump(out, open(C.P("out4/worked.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
for e in out:
    missing = [f"s1" if not e["stage1"]["output"] else ""]
    missing += [f's2.{s["i"]}' for s in e["segments"] if not s["stage2"]["output"]]
    missing += [f's3.{s["i"]}' for s in e["segments"]
                if s["stage3"] and not s["stage3"]["output"]]
    missing = [m for m in missing if m]
    print(f'{e["cid"]}  {len(e["segments"])} segment(s)'
          + (f'   MISSING: {", ".join(missing)}' if missing else "   all replies present"))
