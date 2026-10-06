"""Map Snap-and-Ask conversations onto the Vedantu topic tree.

Four model calls per conversation, however many turns it ran:

    0  ASSEMBLE   code    turns 1..N          -> one payload
    1  SUMMARISE  model   the whole thing     -> one rich summary
    2  SUBJECT    model   summary             -> the subject, from 30
    3  CHAPTER    model   summary + subject   -> the chapter(s) inside it
    4  TOPIC      model   summary + chapters  -> the exact node id(s)
    5  WRITE      code    validate            -> one row per conversation

The cascade narrows: 30 subjects, then that subject's chapters, then those
chapters' nodes. Each call sees only what the one before it chose, so no call
carries the whole tree. Everything after call 1 reads the summary, never the
conversation - which is why the summary has to be rich.

    python cascade.py --dry-run 0b427a40      # payload + every prompt, no calls
    python cascade.py --limit 5               # run 5 conversations
    python cascade.py                         # run all of them
    python cascade.py --self-check            # the code stages, no model needed
"""
import argparse, collections, csv, io, json, os, re, sys, time, urllib.request

# Tamil, Devanagari and the reply-button emoji all appear in this data; the Windows
# console is cp1252 and will not print them.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trees import band_family

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(HERE, *a)
OUT = P("out4")

# ---------------------------------------------------------------- tree sources

# one catalogue row is "? | (blank)" - a tree fault, not a chapter. Left in, it is a
# legal-looking answer the model can return and the validator would then accept.
CONCEPT = {tuple(k.split("\t")): v
           for k, v in json.load(open(P("out2/concepts.json"), encoding="utf-8")).items()
           if all(part.strip() and part.strip() != "?" for part in k.split("\t"))}
NODES = json.load(open(P("out2/nodes_by_chapter.json"), encoding="utf-8"))
ALL_TREES = sorted({t for tm in CONCEPT.values() for t in tm})

# the catalogue is fixed and cached - never reordered per student. One row per
# distinct subject+chapter: which tree carries it is resolved in code afterwards,
# so the model never guesses a tree and the prompt halves.
CATALOGUE = "\n".join(f"{s} | {c}" for s, c in sorted(CONCEPT))

# The student profile table is the one input that carries personal data, so it is not
# in the repository. Without it the tree, the catalogue and the validator still work -
# only the stages that need a real student do not. Importing must not fail for someone
# who has cloned the code and not yet run sql/08.
GBT = {}
if os.path.exists(P("out2/gbt.tsv")):
    for _l in open(P("out2/gbt.tsv"), encoding="utf-8"):
        if not _l.strip():
            continue
        _cid, _uid, _g, _b, _st, _tg = _l.rstrip("\n").split("\t")
        GBT[_cid] = {"user_id": _uid, "grade": _g, "board": _b, "target": _tg}


def need(path, query):
    """Fail with the query that produces the file, not with a FileNotFoundError."""
    if not os.path.exists(P(path)):
        raise SystemExit(f"{path} is missing - it holds student data and is not in the "
                         f"repository.\nRegenerate it with {query}, then run this again.")
    return P(path)

# ------------------------------------------------------- 0  ASSEMBLE  (no LLM)

# tapped reply buttons: ~15% of student input lines, zero topic signal
CHIP = re.compile(r"^(let'?s go|okay|ok|yes!?|bring it on|sure thing|got it|next|"
                  r"thanks?|hi+|hello|hmm+|yeah|yep|nope?|no|continue|more|"
                  r"i don'?t know|idk|done|cool|nice|great)[\s\W]*$", re.I)


def clean(field):
    """Split the '||'-joined field, drop chips, de-duplicate keeping first sight.

    prior_coverage_recent is a rolling 5-exchange window re-emitted on every bot
    turn, so a 20-exchange conversation repeats itself about 15 times.
    """
    seen, out = set(), []
    # the two joins used in this data: " || " between bot notes, " ~ " between student lines
    for part in re.split(r"\s*\|\|\s*|\s+~\s+|\n", field or ""):
        part = part.strip()
        if not part or CHIP.match(part):
            continue
        key = re.sub(r"\W+", " ", part.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(part)
    return " || ".join(out)


def assemble(cid, rec):
    """The nine input parameters, as one payload. No model involved."""
    g = GBT.get(cid, {})
    return {
        "user_id": g.get("user_id", ""),
        "conversation_id": cid,
        "exchanges": rec.get("exchanges", 0),
        "has_image": bool(rec.get("images")),
        "grade": g.get("grade", ""),
        "board": g.get("board", ""),
        "target": g.get("target", ""),
        "student": clean(rec.get("student_typed")),
        "wanted": clean(rec.get("wanted")),
        "taught": clean(rec.get("taught")),
        "response": clean(rec.get("answer") or rec.get("md")),
        "earlier": clean(rec.get("older_delivered")),
    }


BOARD_TREE = {"CBSE": "CBSE", "ICSE": "ICSE", "MAHARASHTRA": "Maharashtra"}
TARGET_FAM = {"JEE": ("JEE", "Foundation"), "NEET": ("NEET", "Foundation"),
              "FOUNDATION": ("Foundation", "Foundation"), "OLYMPIAD": ("Olympiad", "Olympiad")}


def preferred_trees(pay, n=12):
    """Rank every tree for this student. Ranks - never filters: filtering the
    candidate list to the student's own trees reaches 191 of 241 conversations,
    ranking reaches 241 of 241."""
    grade = int(pay["grade"]) if str(pay["grade"]).isdigit() else 10
    gr = 12 if grade == 13 else grade
    board_fam = BOARD_TREE.get(pay["board"], "CBSE")
    fams = {"CBSE", "NCERT", board_fam}
    if pay["target"] in TARGET_FAM:
        senior, junior = TARGET_FAM[pay["target"]]
        fams.add(senior if grade >= 11 else junior)
        if pay["target"] == "OLYMPIAD":
            fams |= {"SOF-IMO", "SOF-NSO"}
    if grade >= 13:
        fams |= {"Upskill", "VEDANTU_HIRING"}

    def rank(t):
        band, fam = band_family(t)
        in_grade = not band or gr in band
        tier = (0 if (fam == board_fam and in_grade) else
                1 if (fam in fams and in_grade) else
                2 if (fam in {"NCERT", "CBSE"} and in_grade) else
                3 if in_grade else 4)
        gap = 0 if in_grade or not band else (gr - max(band) if max(band) <= gr else 100 + min(band) - gr)
        # UNNAMED_* trees have no entry in cmdsquestiontagging; left unpenalised they
        # outrank real trees and pull class-11 physics into an orphan
        # ponytail: Level_N_Olympiad parses to an empty band, so a grade-13 olympiad
        # student sees Level_7 ranked as "in grade". Harmless - this orders, never
        # filters - fix by parsing N out of the name if olympiad volume ever matters.
        return (t.startswith("UNNAMED_"), tier, 0 if fam in {"CBSE", "NCERT"} else 1, gap, t)

    return sorted(ALL_TREES, key=rank)[:n]


# --------------------------------------------------------------- model client

PROMPT = {n: open(P("prompts", f"{n}.txt"), encoding="utf-8").read()
          for n in ("0_summarise", "1_subject", "2_chapter", "3_topic")}

# How much of the bot's raw replies reaches the summariser. The summary is the only
# thing the three tree calls ever see, so cutting here is cutting the whole pipeline:
# 25 of 271 conversations ran past 4,000 and the largest lost 87% of its text.
RESPONSE_CAP = int(os.environ.get("CASCADE_RESPONSE_CAP", "40000"))

CALLS = collections.Counter()

# Replies are cached by prompt hash so a crashed or rate-limited run resumes instead of
# re-paying, and so a run can be replayed exactly. --offline turns a cache miss into a
# file under out4/pending/ and carries on, which is how a run is produced without a key.
CACHE_PATH = P("out4/cache.json")
CACHE = json.load(open(CACHE_PATH, encoding="utf-8")) if os.path.exists(CACHE_PATH) else {}
OFFLINE = False
PENDING_JSON = '{"__pending__":true}'


def cache_key(prompt, cached_prefix):
    import hashlib
    return hashlib.sha256(((cached_prefix or "") + "\x00" + prompt).encode()).hexdigest()[:16]


def save_cache():
    os.makedirs(OUT, exist_ok=True)
    json.dump(CACHE, open(CACHE_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def call_model(prompt, cached_prefix=None, max_tokens=2000, retries=3):
    """One function, both providers. ANTHROPIC_API_KEY or GEMINI_API_KEY.

    cached_prefix is the block that is identical on every call (stage 2's 2,032-row
    catalogue). Anthropic caches it explicitly; Gemini's implicit cache picks it up
    from the shared prefix, which is why it goes first.
    """
    k = cache_key(prompt, cached_prefix)
    if k in CACHE:
        CALLS["cached"] += 1
        return CACHE[k]
    if OFFLINE:
        CALLS["pending"] += 1
        os.makedirs(P("out4/pending"), exist_ok=True)
        with open(P("out4/pending", f"{k}.txt"), "w", encoding="utf-8") as f:
            f.write(((cached_prefix + "\n\n") if cached_prefix else "") + prompt)
        return PENDING_JSON

    CALLS["total"] += 1
    if key := os.environ.get("ANTHROPIC_API_KEY"):
        blocks = []
        if cached_prefix:
            blocks.append({"type": "text", "text": cached_prefix,
                           "cache_control": {"type": "ephemeral"}})
        blocks.append({"type": "text", "text": prompt})
        body = {"model": os.environ.get("CASCADE_MODEL", "claude-sonnet-5"),
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": blocks}]}
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(body).encode(), method="POST",
            headers={"content-type": "application/json", "x-api-key": key,
                     "anthropic-version": "2023-06-01"})
        pick = lambda r: r["content"][0]["text"]
    elif key := os.environ.get("GEMINI_API_KEY"):
        model = os.environ.get("CASCADE_MODEL", "gemini-2.5-flash")
        text = f"{cached_prefix}\n\n{prompt}" if cached_prefix else prompt
        body = {"contents": [{"parts": [{"text": text}]}],
                "generationConfig": {"maxOutputTokens": max_tokens,
                                     "responseMimeType": "application/json"}}
        req = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            data=json.dumps(body).encode(), method="POST",
            headers={"content-type": "application/json", "x-goog-api-key": key})
        pick = lambda r: r["candidates"][0]["content"]["parts"][0]["text"]
    else:
        raise SystemExit("set ANTHROPIC_API_KEY or GEMINI_API_KEY (or use --dry-run)")

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                CACHE[k] = pick(json.load(r))
                return CACHE[k]
        except Exception as e:                                    # rate limit, 5xx, timeout
            if attempt == retries - 1:
                raise
            CALLS["retry"] += 1
            time.sleep(2 ** attempt)


CACHE_MARK = "---CACHE BOUNDARY---"


def split_cache(prompt):
    """(cached prefix, variable tail). Prompts put their invariant block first and mark
    where it ends, so that block is cached across every conversation reaching the same
    step: one subject list for the whole run, one chapter list per subject."""
    if CACHE_MARK not in prompt:
        return None, prompt
    prefix, tail = prompt.split(CACHE_MARK, 1)
    return prefix.rstrip() + "\n", tail.lstrip("\n")


def as_json(text, default):
    """Models add fences and prose however firmly you ask them not to."""
    text = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        try:
            return json.loads(m.group(0)) if m else default
        except json.JSONDecodeError:
            return default

# ---------------------------------------------------- 1  SUMMARISE  (model call 1)

def p_summarise(pay):
    """The whole conversation, however many turns, into one prompt."""
    return PROMPT["0_summarise"].format(
        student=pay["student"] or "(nothing typed - the photo was the question)",
        wanted=pay["wanted"] or "(none)",
        taught=pay["taught"] or "(none)",
        response=pay["response"][:RESPONSE_CAP] or "(none)",
        earlier=pay["earlier"] or "(none)")


def summarise(pay):
    raw = call_model(p_summarise(pay), max_tokens=4000)
    if raw == PENDING_JSON:
        return None
    s = as_json(raw, {})
    s.setdefault("overview", "")
    s.setdefault("covered", [])
    s.setdefault("ask_source", "bot_restatement")
    s.setdefault("not_academic", None)
    s["thin"] = thin_summary(pay, s)
    if s["thin"]:
        CALLS["thin"] += 1
    return s


def thin_summary(pay, s):
    """The summary is the only thing the three tree calls ever see, so anything it drops
    is lost permanently and silently. This flags the one case that is unambiguous.

    It used to compare the number of things covered against the number of per-exchange
    notes the bot wrote, on the theory that 2 against 17 meant something was dropped.
    Measured on the 20-conversation sample against a per-question run that found the
    same topics independently, that ratio runs from 0.5 to 8.0 on summaries that are
    completely correct - the bot writes a note per exchange, and one topic routinely
    spans several. The median was 3.0, so a 3x rule flagged 5 of 18 good summaries.
    There is no threshold on that ratio that separates a dropped topic from a
    conversation that simply took a while; the yardstick was wrong, so it is gone."""
    if s.get("not_academic"):
        return None
    if not (s.get("covered") or []):
        notes = len([x for x in (pay["taught"] or "").split(" || ") if x.strip()])
        if notes or pay["response"]:
            return "the summary covered nothing, but the conversation has content"
    return None


def summary_text(s):
    """The summary as the three tree calls see it. They never see the conversation."""
    out = [s.get("overview") or ""]
    for c in s.get("covered") or []:
        if isinstance(c, dict):
            out.append(f'  - {c.get("what", "")}'
                       + (f'  [{c.get("detail")}]' if c.get("detail") else "")
                       + (f'  ({c.get("asked_or_taught")})' if c.get("asked_or_taught") else ""))
    if s.get("level"):
        out.append(f'  level suggested by the content: {s["level"]}')
    if s.get("notes"):
        out.append(f'  note: {s["notes"]}')
    return "\n".join(x for x in out if x.strip())


# ------------------------------------------------------ 2  SUBJECT  (model call 2)

SUBJECTS = sorted({s for s, c in CONCEPT})


def p_subject(pay, summary):
    return split_cache(PROMPT["1_subject"].format(
        grade=pay["grade"] or "?", board=pay["board"] or "?", target=pay["target"] or "?",
        summary=summary, subjects="\n".join(SUBJECTS)))


def subject(pay, summary):
    prefix, tail = p_subject(pay, summary)
    raw = call_model(tail, cached_prefix=prefix, max_tokens=400)
    if raw == PENDING_JSON:
        return None
    r = as_json(raw, {"reject": "UNKNOWN", "why": "unparseable model output"})
    subs = [s for s in (r.get("subjects") or []) if s in CONCEPT_BY_SUBJECT]
    return {"subjects": subs, "confidence": r.get("confidence") or "LOW",
            "reject": r.get("reject") or (None if subs else "UNKNOWN"),
            "why": r.get("why") or ""}


CONCEPT_BY_SUBJECT = collections.defaultdict(list)
for (_s, _c) in CONCEPT:
    CONCEPT_BY_SUBJECT[_s].append(_c)


# ------------------------------------------------------ 3  CHAPTER  (model call 3)

def p_chapter(pay, summary, subs):
    listing = "\n".join(f"{s} | {c}" for s in subs for c in sorted(CONCEPT_BY_SUBJECT[s]))
    return split_cache(PROMPT["2_chapter"].format(
        grade=pay["grade"] or "?", board=pay["board"] or "?", target=pay["target"] or "?",
        preferred=", ".join(preferred_trees(pay)), summary=summary,
        subject_list=" and ".join(subs), chapters=listing))


def chapter(pay, summary, subs):
    prefix, tail = p_chapter(pay, summary, subs)
    raw = call_model(tail, cached_prefix=prefix, max_tokens=1200)
    if raw == PENDING_JSON:
        return None
    r = as_json(raw, {"reject": "UNKNOWN", "why": "unparseable model output"})
    order = preferred_trees(pay, n=len(ALL_TREES))
    out = []
    for c in r.get("chapters") or []:
        if not isinstance(c, dict):
            continue
        key = (c.get("subject"), c.get("chapter"))
        carriers = CONCEPT.get(key, {})
        if not carriers:                                  # not in the tree - dropped, not written
            continue
        out.append({"subject": key[0], "chapter": key[1],
                    "trees": sorted(carriers, key=order.index),
                    "tree": min(carriers, key=order.index),
                    "covers": c.get("covers") or "",
                    "confidence": c.get("confidence") or "LOW"})
    return {"chapters": out, "reject": r.get("reject") or (None if out else "OUT_OF_SCOPE"),
            "why": r.get("why") or ""}


# -------------------------------------------------------- 4  TOPIC  (model call 4)

def p_topic(summary, picks):
    blocks = []
    for p in picks:
        ns = nodes_for(p)
        blocks.append(f'{p["subject"]} > {p["chapter"]}'
                      + (f'  [{" / ".join(dict.fromkeys(n["tree"] for n in ns))}]' if ns else "")
                      + ":\n"
                      + ("\n".join(f'  {n["id"]} | {n["name"]} [{n["lvl"]}]' for n in ns)
                         or "  (no nodes fetched for this chapter)"))
    return PROMPT["3_topic"].format(summary=summary, nodes="\n\n".join(blocks))


def topic(summary, picks):
    live = [p for p in picks if nodes_for(p)]
    if not live:
        CALLS["nodes_missing"] += len(picks)
        return [{"chapter": p["chapter"], "topic_id": "", "topic": "CHAPTER_ONLY",
                 "topic_level": "", "confidence": p["confidence"], "tree": p["tree"],
                 "subject": p["subject"], "nodes_missing": True} for p in picks]
    raw = call_model(p_topic(summary, picks), max_tokens=1600)
    if raw == PENDING_JSON:
        return None
    r = as_json(raw, {})
    by_chapter = {p["chapter"]: p for p in picks}
    index = {n["id"]: (n, p) for p in picks for n in nodes_for(p)}
    out = []
    for t in r.get("topics") or []:
        if not isinstance(t, dict):
            continue
        hit = index.get(t.get("topic_id"))
        pick = (hit[1] if hit else by_chapter.get(t.get("chapter")))
        if not pick:
            continue
        out.append({"subject": pick["subject"], "chapter": pick["chapter"],
                    "tree": hit[0]["tree"] if hit else pick["tree"],
                    "topic_id": t.get("topic_id") or "",
                    "topic": t.get("topic") or "CHAPTER_ONLY",
                    "topic_level": t.get("topic_level") or "",
                    "confidence": t.get("confidence") or "LOW"})
    seen = {o["chapter"] for o in out}
    for p in picks:                                       # a chapter the model said nothing about
        if p["chapter"] not in seen:
            out.append({"subject": p["subject"], "chapter": p["chapter"], "tree": p["tree"],
                        "topic_id": "", "topic": "CHAPTER_ONLY", "topic_level": "",
                        "confidence": p["confidence"],
                        "nodes_missing": not nodes_for(p)})
            if not nodes_for(p):
                CALLS["nodes_missing"] += 1
    return out


def nodes_for(pick):
    """Every node of this chapter across every tree that carries it, de-duplicated on
    name, the student's preferred tree first. The chosen node then names the tree."""
    seen, out = set(), []
    carriers = CONCEPT.get((pick["subject"], pick["chapter"]), {})
    for tree in pick.get("trees") or ([pick["tree"]] if pick.get("tree") else []):
        for n in NODES.get(carriers.get(tree, ""), []):
            if n["name"] in seen:
                continue
            seen.add(n["name"])
            out.append({**n, "tree": tree})
    return out


# --------------------------------------------------- 5  WRITE IT OUT  (no model)

VALID_CHAPTERS = {c for _, c in CONCEPT}
VALID_NODES = {n["id"]: n for v in NODES.values() for n in v}


def validate(t):
    """A name the model invented is rejected, not written. This is the only reason
    the output can be trusted without a human reading every row."""
    cid = CONCEPT.get((t["subject"], t["chapter"]), {}).get(t["tree"])
    if not cid:
        return "chapter is not in that tree"
    if t["topic"] != "CHAPTER_ONLY":
        node = VALID_NODES.get(t["topic_id"])
        if not node or node["name"] != t["topic"]:
            return "node id and name do not agree"
        if node not in NODES.get(cid, []):
            return "node is not inside that chapter"
    return None


ROW = ["user_id", "conversation_id", "grade", "board", "target", "exchanges", "subject",
       "chapter", "chapter_id", "topic", "topic_id", "topic_level", "tree", "confidence",
       "note", "all_chapters", "all_topics", "n_topics", "is_multi", "multi_note"]

REJECT_ROW = {"chit chat": "NOT_ACADEMIC", "app question": "NOT_ACADEMIC",
              "photo with no schoolwork": "NOT_ACADEMIC", "illegible": "UNKNOWN"}


def write_row(pay, summary, topics, reject=None, why=""):
    base = {k: "" for k in ROW}
    base.update(user_id=pay["user_id"], conversation_id=pay["conversation_id"],
                grade=pay["grade"], board=pay["board"], target=pay["target"],
                exchanges=pay["exchanges"], n_topics="0")
    if reject:
        base.update(subject=reject, chapter=why or (summary or {}).get("overview", "")[:160])
        return base

    first = topics[0]
    chapters, nodes = [], []
    for t in topics:
        if t["chapter"] not in chapters:
            chapters.append(t["chapter"])
        if t["topic"] != "CHAPTER_ONLY" and t["topic"] not in nodes:
            nodes.append(t["topic"])
    base.update(subject=first["subject"], chapter=first["chapter"],
                chapter_id=CONCEPT[(first["subject"], first["chapter"])][first["tree"]],
                topic=first["topic"], topic_id=first["topic_id"],
                topic_level=first["topic_level"], tree=first["tree"],
                confidence=first["confidence"],
                note=" / ".join(x for x in [(summary or {}).get("notes"),
                                           (summary or {}).get("thin")] if x),
                all_chapters="|".join(chapters), all_topics="|".join(nodes),
                n_topics=str(len(nodes)),
                is_multi="Y" if len(nodes) > 1 or len(chapters) > 1 else "",
                multi_note=f"{len(chapters)} chapters, {len(topics)} topics"
                           if len(chapters) > 1 else "")
    return base


# ------------------------------------------------------------------------ run

def tag_one(pay):
    """Four model calls, whatever the conversation's length: summarise, then
    subject, chapter, topic. Returns (row, summary, topics) or None while waiting."""
    s = summarise(pay)
    if s is None:
        return None
    if s.get("not_academic"):
        return (write_row(pay, s, [], REJECT_ROW.get(s["not_academic"], "NOT_ACADEMIC"),
                          s["not_academic"]), s, [])

    text = summary_text(s)
    sub = subject(pay, text)
    if sub is None:
        return None
    if sub["reject"]:
        return write_row(pay, s, [], sub["reject"], sub["why"]), s, []

    ch = chapter(pay, text, sub["subjects"])
    if ch is None:
        return None
    if ch["reject"] or not ch["chapters"]:
        return write_row(pay, s, [], ch["reject"] or "OUT_OF_SCOPE", ch["why"]), s, []

    tps = topic(text, ch["chapters"])
    if tps is None:
        return None
    good, bad = [], []
    for t in tps:
        why = validate(t)
        (bad if why else good).append({**t, "invalid": why})
    if not good:
        return write_row(pay, s, [], "UNKNOWN", "every name returned failed validation"), s, bad
    return write_row(pay, s, good), s, good + bad


def run(cids, records):
    rows, summaries, tags, waiting = [], [], [], 0
    for i, cid in enumerate(cids, 1):
        pay = assemble(cid, records[cid])
        got = tag_one(pay)
        if got is None:
            waiting += 1
            print(f"  [{i}/{len(cids)}] {cid[:8]}  waiting on a reply", flush=True)
            continue
        row, s, tps = got
        rows.append(row)
        summaries.append({"conversation_id": cid, **s})
        tags += [{"conversation_id": cid, **t} for t in tps]
        print(f"  [{i}/{len(cids)}] {cid[:8]}  {len(s.get('covered') or [])} covered -> "
              f"{len(tps)} topic(s)  {row['chapter'] or row['subject']}", flush=True)
    save_cache()
    if waiting:
        print(f"\n{waiting} conversations waiting. {CALLS['pending']} prompts written to "
              f"out4/pending/ - answer them into out4/cache.json (key = filename) and run again.")

    os.makedirs(OUT, exist_ok=True)
    for name, data in (("summaries.jsonl", summaries), ("topics.jsonl", tags)):
        with open(P("out4", name), "w", encoding="utf-8") as f:
            for d in data:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
    with open(P("out4/topic_mapping.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ROW, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    tagged = [r for r in rows if r["chapter_id"]]
    invalid = [t for t in tags if t.get("invalid")]
    print(f"\n{len(rows)} conversations, {CALLS['total']} model calls"
          f"  ({4 * len(rows)} expected: 4 per conversation)")
    print(f"  tagged to a chapter   {len(tagged)}")
    print(f"  at an exact topic     {sum(1 for r in tagged if r['topic'] != 'CHAPTER_ONLY')}")
    print(f"  more than one topic   {sum(1 for r in tagged if r['is_multi'])}")
    print(f"  topic records         {sum(int(r['n_topics'] or 0) for r in tagged)}")
    print(f"  rejected as invalid   {len(invalid)}")
    if CALLS["thin"]:
        print(f"  !! thin summaries     {CALLS['thin']}  - carried far less than the bot's "
              f"own notes did\n"
              f"                           (tagged, but not to be read as complete)")
    if CALLS["nodes_missing"]:
        need = sorted({(t["subject"], t["chapter"]) for t in tags if t.get("nodes_missing")})
        print(f"\n  !! {len(need)} chapters have no node list - run "
              f"sql/07_nodes_for_chosen_chapters.sql for them")
        for s, c in need[:8]:
            print(f"       {s} > {c}")
        json.dump([{"subject": a, "chapter": b} for a, b in need],
                  open(P("out4/chapters_needing_nodes.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(f"\nout4/topic_mapping.csv  out4/summaries.jsonl  out4/topics.jsonl")


def dry_run(cid, records):
    pay = assemble(cid, records[cid])
    bar = lambda t: print("\n" + "=" * 72 + f"\n{t}\n" + "=" * 72)
    bar("STAGE 0  PAYLOAD  (no model)")
    print(json.dumps(pay, ensure_ascii=False, indent=2))
    bar("CALL 1  SUMMARISE  - the whole conversation, however many turns")
    print(p_summarise(pay))
    demo = "<the summary from call 1 goes here>"
    for title, built in [
            (f"CALL 2  SUBJECT  - {len(SUBJECTS)} to choose from", p_subject(pay, demo)),
            ("CALL 3  CHAPTER  - only the chosen subject's chapters",
             p_chapter(pay, demo, ["Mathematics"]))]:
        prefix, tail = built
        bar(title)
        print(f"--- cached prefix: {len(prefix):,} chars, identical for every "
              f"conversation reaching this step")
        print(prefix[:900] + ("\n  ..." if len(prefix) > 900 else ""))
        print(f"\n--- variable tail: {len(tail):,} chars")
        print(tail)
    bar("CALL 4  TOPIC  - only the chosen chapters' nodes")
    pick = {"subject": "Mathematics", "chapter": "Quadratic Equations",
            "trees": ["10_CBSE"], "tree": "10_CBSE", "confidence": "HIGH"}
    print(p_topic(demo, [pick]))
    print("\n(no model was called - 4 calls is the whole budget for this conversation)")


def self_check():
    """The code stages. Runs without a key - these are what the model cannot fix."""
    assert clean("Let's go || Okay") == "", "chips must be stripped"
    assert clean("Solved for x || Solved for x || Then found y") == "Solved for x || Then found y", \
        "the rolling window must de-duplicate"
    assert clean("Proceedings are quite as. ~ I don't know. ~ Let's go") == "Proceedings are quite as.", \
        "student lines join with ' ~ ', not '||'"
    assert ("?", "") not in CONCEPT, "the blank catalogue row must not be a legal answer"

    pay = {"grade": "8", "board": "CBSE", "target": "JEE"}
    pref = preferred_trees(pay)
    assert pref[0] == "8_CBSE", f"own grade+board first, got {pref[0]}"
    assert not any(t.startswith("UNNAMED_") for t in pref), "unnamed trees must never be preferred"
    assert len(preferred_trees({"grade": "12", "board": "STATE", "target": "NA"})) == 12

    ok = {"subject": "Mathematics", "chapter": "Quadratic Equations", "tree": "10_CBSE"}
    assert validate({**ok, "topic": "CHAPTER_ONLY", "topic_id": ""}) is None
    assert validate({"subject": "Mathematics", "chapter": "Invented", "tree": "10_CBSE",
                     "topic": "CHAPTER_ONLY", "topic_id": ""}) == "chapter is not in that tree"
    assert validate({**ok, "topic": "Invented Node", "topic_id": "deadbeef"}) is not None

    assert as_json('```json\n{"a":1}\n```', {}) == {"a": 1}
    assert as_json('here you go {"a":1} hope that helps', {}) == {"a": 1}
    assert as_json("not json at all", {"fallback": True}) == {"fallback": True}

    s = {"overview": "Worked through two quadratics.",
         "covered": [{"what": "factorised x^2-4x-96", "detail": "(x-12)(x+8)",
                      "asked_or_taught": "taught"}]}
    assert "factorised x^2-4x-96" in summary_text(s) and "(x-12)(x+8)" in summary_text(s), \
        "the summary must carry its detail into the three tree calls"

    assert len(SUBJECTS) == len(CONCEPT_BY_SUBJECT)
    biggest = max(CONCEPT_BY_SUBJECT, key=lambda s: len(CONCEPT_BY_SUBJECT[s]))
    print(f"self-check passed - {len(CONCEPT):,} concepts, {len(SUBJECTS)} subjects, "
          f"{len(ALL_TREES)} trees, {len(VALID_NODES):,} nodes")
    print(f"  call 2 sees {len(SUBJECTS)} subjects")
    print(f"  call 3 sees {len(CONCEPT_BY_SUBJECT[biggest])} chapters at worst ({biggest})")
    print(f"  call 4 sees a median of "
          f"{sorted(len(v) for v in NODES.values())[len(NODES) // 2]} nodes")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", metavar="CID", help="print the payload and all four prompts")
    ap.add_argument("--limit", type=int, help="run only the first N conversations")
    ap.add_argument("--only", metavar="CID", help="run one conversation")
    ap.add_argument("--cids", metavar="FILE", help="JSON list of conversation ids to run")
    ap.add_argument("--self-check", action="store_true", help="test the code stages, no key needed")
    ap.add_argument("--offline", action="store_true",
                    help="never call an API: serve from out4/cache.json, write misses to out4/pending/")
    ap.add_argument("--source", default="out2/conv_records.json",
                    help="assembled conversations (production: sql/05_conversation_full_record.sql)")
    a = ap.parse_args()

    if a.self_check:
        self_check()
        raise SystemExit

    globals()["OFFLINE"] = a.offline
    records = json.load(open(need(a.source, "sql/05_conversation_full_record.sql"),
                             encoding="utf-8"))
    if not GBT:
        print("note: out2/gbt.tsv is absent, so no grade, board or target is available.\n"
              "      Tree ranking falls back to the CBSE/NCERT backbone for every student.\n"
              "      Regenerate it with sql/08_gbt_from_conversation.sql.\n")
    match = lambda c: [k for k in records if k.startswith(c)]

    if a.dry_run:
        hit = match(a.dry_run)
        raise SystemExit(dry_run(hit[0], records) if hit else f"no conversation starts with {a.dry_run}")

    if a.cids:
        want = json.load(open(P(a.cids), encoding="utf-8"))
        cids = [k for k in records if any(k.startswith(w) for w in want)]
    else:
        cids = match(a.only) if a.only else list(records)
    run(cids[:a.limit] if a.limit else cids, records)
