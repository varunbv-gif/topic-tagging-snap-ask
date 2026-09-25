"""The five-conversation walkthrough CSV, split into input parameters, prompt and output
parameters at every stage.

    python out4/make_walkthrough.py  ->  out4/how_it_works_5_conversations.csv
"""
import csv, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cascade as C

W = json.load(open(C.P("out4/worked.json"), encoding="utf-8"))
MAX_SEG = 3          # spell out this many questions per conversation; summarise the rest

HEAD = ["Conversation", "Stage", "Part", "Parameter", "Value"]
PLAIN = {
 0: ("STAGE 0 - ASSEMBLE (no AI, ordinary code)",
     "Pull every turn of the conversation and build the nine input parameters. Strip the "
     "tap-to-reply buttons, remove the repetition, and join the student's class, board and goal "
     "from their profile."),
 1: ("STAGE 1 - SPLIT INTO QUESTIONS (AI call 1)",
     "One chat is not one question. Break it into the separate things the student wanted to know, "
     "keeping the question asked (POSED) apart from the answer given (DELIVERED)."),
 2: ("STAGE 2 - FIND THE CHAPTER (AI call 2, once per question)",
     "Show every chapter in the system and ask which one this question belongs to. The student's "
     "class and board only set the order the list is shown in - nothing is ruled out."),
 3: ("STAGE 3 - FIND THE EXACT TOPIC (AI call 3, once per question)",
     "Look only inside that one chapter and pick the exact topic. Return the topic's ID, not just "
     "its name, because some chapters list the same name twice."),
 4: ("STAGE 4 - WRITE THE ANSWER (no AI, ordinary code)",
     "Check every name against the real syllabus tree and throw away anything invented. The main "
     "tag is the chapter most of the questions belong to; everything else is kept beside it."),
}

def clip(t, n=900):
    if isinstance(t, bool):
        return "yes" if t else "no"          # False must print, not vanish into an empty cell
    t = str(t if t is not None else "").replace("\r", "")
    return (t[:n] + f"\n[... {len(t) - n:,} more characters, full text in the doc]") if len(t) > n else t

rows = [HEAD]
for e in W:
    cid = e["cid"]
    rows += [[], [f"=== CONVERSATION {cid} ===", e["why"], "", "", ""]]

    # ---- stage 0
    name, what = PLAIN[0]
    rows += [[cid, name, "WHAT IT DOES", "", what]]
    for n, src, v in e["stage0"]["inputs"]:
        rows.append([cid, name, "INPUT PARAMETER", n, clip(v) or "(empty)"])
    for n, src, v in e["stage0"]["derived"]:
        rows.append([cid, name, "WORKED OUT FROM THEM", n, clip(v)])

    # ---- stage 1
    name, what = PLAIN[1]
    rows += [[], [cid, name, "WHAT IT DOES", "", what]]
    for n, v in e["stage1"]["inputs"]:
        rows.append([cid, name, "INPUT PARAMETER", n, clip(v, 500)])
    rows.append([cid, name, "PROMPT SENT", "1_segment.txt, filled in", clip(e["stage1"]["prompt"], 2500)])
    out = json.loads(e["stage1"]["output"])
    rows.append([cid, name, "OUTPUT PARAMETER", "segments",
                 f'{len(out["segments"])} question(s) found'])
    for s in out["segments"][:MAX_SEG]:
        for k in ("posed", "delivered", "ask_source", "diverged"):
            rows.append([cid, name, "OUTPUT PARAMETER", f'segment {s["i"]} - {k}', clip(s.get(k), 400)])
    if len(out["segments"]) > MAX_SEG:
        rows.append([cid, name, "OUTPUT PARAMETER", "the rest",
                     f'segments {MAX_SEG + 1} to {len(out["segments"])} follow the same shape'])

    # ---- stages 2 and 3, per question
    for seg in e["segments"][:MAX_SEG]:
        i = seg["i"]
        name, what = PLAIN[2]
        tag = f"{name} - question {i}"
        rows += [[], [cid, tag, "WHAT IT DOES", "", what]]
        for n, v in seg["stage2"]["inputs"]:
            rows.append([cid, tag, "INPUT PARAMETER", n, clip(v, 500)])
        rows.append([cid, tag, "PROMPT SENT", "2_chapter.txt (cached) + 2_chapter_tail.txt",
                     clip(seg["stage2"]["prompt_tail"], 1200)])
        o2 = json.loads(seg["stage2"]["output"])
        for k, v in o2.items():
            rows.append([cid, tag, "OUTPUT PARAMETER", k, clip(v) if v not in (None, "") else "(none)"])

        if seg["stage3"]:
            name, what = PLAIN[3]
            tag = f"{name} - question {i}"
            rows += [[], [cid, tag, "WHAT IT DOES", "", what]]
            for n, v in seg["stage3"]["inputs"]:
                rows.append([cid, tag, "INPUT PARAMETER", n, clip(v, 500)])
            rows.append([cid, tag, "PROMPT SENT", "3_topic.txt, filled in",
                         clip(seg["stage3"]["prompt"], 1800)])
            o3 = json.loads(seg["stage3"]["output"])
            for k, v in o3.items():
                rows.append([cid, tag, "OUTPUT PARAMETER", k, clip(v) if v not in (None, "") else "(none)"])

    if len(e["segments"]) > MAX_SEG:
        rows += [[], [cid, "QUESTIONS " + f'{MAX_SEG + 1} TO {len(e["segments"])}', "SAME TWO STAGES",
                      "", f'{len(e["segments"]) - MAX_SEG} more question(s) go through stages 2 and 3 '
                          f'exactly as above. Their results are in the final answer below, and every '
                          f'one is listed in out4/segments.jsonl.']]

    # ---- stage 4
    name, what = PLAIN[4]
    rows += [[], [cid, name, "WHAT IT DOES", "", what]]
    for k, v in e["stage4"].items():
        rows.append([cid, name, "OUTPUT PARAMETER", k, clip(v) if v else "(empty)"])

rows += [[], ["=== HOW TO READ THIS ===", "", "", "", ""],
         ["", "", "INPUT PARAMETER", "", "a value going in to that stage"],
         ["", "", "PROMPT SENT", "", "the exact text the model was given, with the values filled in"],
         ["", "", "OUTPUT PARAMETER", "", "a field the model gave back, or that stage wrote"],
         ["", "", "WHAT IT DOES", "", "the stage explained in plain English"],
         [], ["", "", "", "Stages 0 and 4 use no AI at all.",
              "They are ordinary code. Stage 0 fixes the data before anything sees it; stage 4 "
              "refuses any name that is not in the real syllabus tree. Those two are what make "
              "the result trustworthy."],
         ["", "", "", "No API key was available.",
          "The three AI calls were answered by a human following the same prompts, exactly as "
          "shown here. Stages 0 and 4 are the real code and ran untouched."]]

path = C.P("out4/how_it_works_5_conversations.csv")
with open(path, "w", newline="", encoding="utf-8-sig") as f:
    csv.writer(f).writerows(rows)
print(f"{path}\n{len(W)} conversations, {len(rows)} rows")
