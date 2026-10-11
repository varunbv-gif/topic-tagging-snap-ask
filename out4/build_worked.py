"""out4/worked.json - for five conversations, the real input, prompt and output at
every one of the four calls.

Feeds both out4/how_it_works_5_conversations.csv and section 8 of the docx, so the
two cannot disagree.
"""
import csv, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cascade as C

PICK = [
    ("8d31eff5", "A straightforward one - one question, one topic"),
    ("4a74c906", "One photo, one turn, but two topics inside it"),
    ("57aa81aa", "Two questions from the same worksheet page"),
    ("c1aa54f2", "Forty exchanges across two chapters, in one summary"),
    ("3b17d1f8", "One we could not tag, and why"),
]

records = json.load(open(C.P("out2/conv_records.json"), encoding="utf-8"))
final = {r["conversation_id"][:8]: r for r in
         csv.DictReader(open(C.P("out4/topic_mapping.csv"), encoding="utf-8"))}
summaries = {}
if os.path.exists(C.P("out4/summaries.jsonl")):
    for line in open(C.P("out4/summaries.jsonl"), encoding="utf-8"):
        d = json.loads(line)
        summaries[d["conversation_id"][:8]] = d

cached = lambda prompt, prefix=None: C.CACHE.get(C.cache_key(prompt, prefix), "")

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
    summ = summaries.get(cid8, {})
    text = C.summary_text(summ) if summ else ""

    p1 = C.p_summarise(pay)
    entry = {
        "cid": cid8, "why": why,
        "models": {"summary": C.SUMMARY_MODEL, "narrowing": C.MODEL},
        "stage0": {
            "inputs": [[n, src, str(pay.get(n, ""))] for n, src in NINE],
            "derived": [
                ["exchanges", "counted from the turns", str(pay["exchanges"])],
                ["has_image", "input_parts where kind='image'", "yes" if pay["has_image"] else "no"],
                ["preferred trees", "computed from grade, board and target",
                 ", ".join(C.preferred_trees(pay, n=6)) + ", …"],
            ],
        },
        "call1": {
            "what": "Summarise the whole conversation, however many turns it ran. "
                    "Nothing after this sees the conversation again.",
            "model": C.SUMMARY_MODEL,
            "inputs": [[k, str(pay[k] or "(empty)")] for k in
                       ("student", "wanted", "taught", "response", "earlier")],
            "prompt": p1,
            "output": cached(p1),
        },
        "summary_as_the_tree_calls_see_it": text,
    }

    if summ.get("not_academic"):
        entry["call2"] = entry["call3"] = entry["call4"] = None
    else:
        subs = [c["subject"] for c in []] or None
        pre2, tail2 = C.p_subject(pay, text)
        out2_raw = cached(tail2, pre2)
        chosen = (json.loads(out2_raw).get("subjects") if out2_raw else []) or []
        entry["call2"] = {
            "what": f"Pick the subject from the {len(C.SUBJECTS)} in the tree.",
            "model": C.MODEL,
            "inputs": [["the summary", text],
                       ["grade", pay["grade"]], ["board", pay["board"]],
                       ["target", pay["target"]],
                       ["subjects", f"{len(C.SUBJECTS)} names"]],
            "cached_prefix": pre2, "prompt_tail": tail2, "output": out2_raw,
        }

        if chosen:
            pre3, tail3 = C.p_chapter(pay, text, chosen)
            out3_raw = cached(tail3, pre3)
            picks = []
            order = C.preferred_trees(pay, n=len(C.ALL_TREES))
            for c in (json.loads(out3_raw).get("chapters") if out3_raw else []) or []:
                carriers = C.CONCEPT.get((c.get("subject"), c.get("chapter")), {})
                if carriers:
                    picks.append({"subject": c["subject"], "chapter": c["chapter"],
                                  "trees": sorted(carriers, key=order.index),
                                  "tree": min(carriers, key=order.index),
                                  "confidence": c.get("confidence", "")})
            entry["call3"] = {
                "what": "Pick the chapter, or chapters, inside that subject.",
                "model": C.MODEL,
                "inputs": [["the summary", text],
                           ["subject chosen at call 2", ", ".join(chosen)],
                           ["chapters offered",
                            f'{sum(len(C.CONCEPT_BY_SUBJECT[s]) for s in chosen)} in {" and ".join(chosen)}'],
                           ["preferred tree order", ", ".join(C.preferred_trees(pay, n=6)) + ", …"]],
                "cached_prefix": pre3, "prompt_tail": tail3, "output": out3_raw,
            }

            if picks:
                p4 = C.p_topic(text, picks)
                entry["call4"] = {
                    "what": "Pick the exact node, or nodes, inside those chapters.",
                    "model": C.MODEL,
                    "inputs": [["the summary", text],
                               ["chapters chosen at call 3",
                                "; ".join(f'{p["subject"]} > {p["chapter"]}' for p in picks)],
                               ["nodes offered",
                                f'{sum(len(C.nodes_for(p)) for p in picks)} across those chapters, '
                                f'de-duplicated on name']],
                    "prompt": p4, "output": cached(p4),
                }
            else:
                entry["call4"] = None
        else:
            entry["call3"] = entry["call4"] = None

    entry["final_row"] = dict(final.get(cid8, {}))
    out.append(entry)

json.dump(out, open(C.P("out4/worked.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
for e in out:
    missing = [n for n in ("call1", "call2", "call3", "call4")
               if e.get(n) and not e[n].get("output")]
    print(f'{e["cid"]}  '
          + (f'MISSING: {", ".join(missing)}' if missing
             else "all four replies present" if e.get("call4")
             else "rejected before the tree calls"))
