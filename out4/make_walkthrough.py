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
     "Read every turn of the conversation and build the nine input parameters. Strip the "
     "tap-to-reply buttons, remove the repetition, and join the student's class, board and "
     "goal from their profile."),
 1: ("CALL 1 - SUMMARISE THE WHOLE CONVERSATION",
     "One summary of the entire conversation, however many turns it ran. This is the only "
     "call that sees the conversation; the three after it read the summary and nothing else, "
     "so anything left out here is lost."),
 2: ("CALL 2 - FIND THE SUBJECT",
     "Pick the subject from the 30 in the system. The two calls after this only ever see "
     "what is inside the subject chosen here."),
 3: ("CALL 3 - FIND THE CHAPTER",
     "Pick the chapter, or chapters, inside that subject. The student's class and board set "
     "the order the candidates are shown in; nothing is ruled out."),
 4: ("CALL 4 - FIND THE EXACT TOPIC",
     "Pick the exact topic inside those chapters. Returns the topic's ID, not just its name, "
     "because some chapters list the same name twice."),
 5: ("STAGE 5 - WRITE THE ANSWER (no AI, ordinary code)",
     "Check every name against the real syllabus tree and throw away anything invented. The "
     "main tag is the first chapter returned; everything else is kept beside it."),
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

    name, what = PLAIN[0]
    rows += [[cid, name, "WHAT IT DOES", "", what]]
    for n, src, v in e["stage0"]["inputs"]:
        rows.append([cid, name, "INPUT PARAMETER", n, clip(v) or "(empty)"])
    for n, src, v in e["stage0"]["derived"]:
        rows.append([cid, name, "WORKED OUT FROM THEM", n, clip(v)])

    for key, (name, what) in [("call1", PLAIN[1]), ("call2", PLAIN[2]),
                              ("call3", PLAIN[3]), ("call4", PLAIN[4])]:
        c = e.get(key)
        if not c:
            rows += [[], [cid, name, "DID NOT RUN", "",
                          "the conversation was rejected before this call"]]
            break
        rows += [[], [cid, name, "WHAT IT DOES", "", what],
                 [cid, name, "MODEL", "", c.get("model", "")]]
        for n, v in c["inputs"]:
            rows.append([cid, name, "INPUT PARAMETER", n, clip(v, 600)])
        if c.get("cached_prefix"):
            rows.append([cid, name, "PROMPT SENT", "cached prefix",
                         f'{len(c["cached_prefix"]):,} characters, identical for every '
                         f'conversation reaching this step'])
            rows.append([cid, name, "PROMPT SENT", "variable tail", clip(c["prompt_tail"], 1500)])
        else:
            rows.append([cid, name, "PROMPT SENT", "the prompt", clip(c["prompt"], 2500)])
        try:
            got = json.loads(c.get("output") or "{}")
        except json.JSONDecodeError:
            got = {}
        for k, v in got.items():
            if isinstance(v, list):
                rows.append([cid, name, "OUTPUT PARAMETER", k, f"{len(v)} item(s)"])
                for i, item in enumerate(v[:8], 1):
                    rows.append([cid, name, "OUTPUT PARAMETER", f"{k}[{i}]",
                                 clip(json.dumps(item, ensure_ascii=False)
                                      if isinstance(item, dict) else item, 500)])
                if len(v) > 8:
                    rows.append([cid, name, "OUTPUT PARAMETER", f"{k}[...]",
                                 f"and {len(v) - 8} more"])
            else:
                rows.append([cid, name, "OUTPUT PARAMETER", k, clip(v) if v not in (None, "") else "(none)"])

    name, what = PLAIN[5]
    rows += [[], [cid, name, "WHAT IT DOES", "", what]]
    for k, v in e.get("final_row", {}).items():
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
