"""Map Snap-and-Ask conversations onto the Vedantu topic tree.

Five stages, three of them model calls:

    0  ASSEMBLE   code   turns 1..N            -> one payload per conversation
    1  SEGMENT    model  payload               -> k questions, posed vs delivered
    2  CHAPTER    model  question              -> subject + chapter + tree
    3  TOPIC      model  question + chapter    -> node id inside that chapter
    4  AGGREGATE  code   segments              -> one row per conversation

Stage 2's catalogue is identical on every call and goes in the cached prefix;
the student's tree preference rides in the variable tail so the cache still hits.

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
          for n in ("1_segment", "2_chapter", "2_chapter_tail", "3_topic")}

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


# ------------------------------------------------------------- 1  SEGMENT

def p_segment(pay):
    return PROMPT["1_segment"].format(
        student=pay["student"] or "(nothing typed - the photo is the question)",
        wanted=pay["wanted"] or "(none)", taught=pay["taught"] or "(none)",
        response=pay["response"][:4000] or "(none)", earlier=pay["earlier"] or "(none)")


def segment(pay):
    """No gate. A single turn can carry a whole worksheet page, so turn count is
    the wrong proxy for how many questions were asked."""
    raw = call_model(p_segment(pay))
    if raw == PENDING_JSON:
        return None                       # offline: stages 2-3 wait for the next round
    r = as_json(raw, {})
    segs = [s for s in r.get("segments") or [] if isinstance(s, dict)]
    if not segs:                                                  # never lose a conversation
        segs = [{"i": 1, "posed": pay["student"] or None, "delivered": pay["taught"],
                 "ask_source": "student_text" if pay["student"] else "bot_restatement",
                 "diverged": False, "divergence": None, "evidence": "fallback: segmenter returned nothing"}]
    for i, s in enumerate(segs, 1):
        s["i"] = i
    return segs


# ------------------------------------------------------------- 2  CHAPTER

def p_chapter(pay, label, text):
    return PROMPT["2_chapter_tail"].format(
        grade=pay["grade"] or "?", board=pay["board"] or "?", target=pay["target"] or "?",
        preferred=", ".join(preferred_trees(pay)), label=label, text=text)


def chapter(pay, label, text):
    raw = call_model(p_chapter(pay, label, text),
                     cached_prefix=PROMPT["2_chapter"].format(catalogue=CATALOGUE),
                     max_tokens=400)
    if raw == PENDING_JSON:
        return None
    r = as_json(raw, {"reject": "UNKNOWN", "why": "unparseable model output"})
    subj, chap = r.get("subject") or "", r.get("chapter") or ""
    carriers = CONCEPT.get((subj, chap), {})
    order = preferred_trees(pay, n=len(ALL_TREES))
    # A chapter can sit in a dozen trees. Committing to one here on the student's profile
    # alone put a grade-11 JEE student's class-10 word problem into 11_12_JEE, whose
    # Quadratic Equations has no word-problem node - so it landed on "Miscellaneous
    # examples". Stage 3 chooses the node from every carrier and the node names the tree.
    return {"subject": subj, "chapter": chap,
            "trees": sorted(carriers, key=order.index),
            "tree": min(carriers, key=order.index) if carriers else "",
            "confidence": r.get("confidence") or "LOW",
            "reject": r.get("reject") or None, "why": r.get("why") or ""}


# --------------------------------------------------------------- 3  TOPIC

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


def p_topic(pick, label, text):
    nodes = nodes_for(pick)
    return PROMPT["3_topic"].format(
        subject=pick["subject"], chapter=pick["chapter"],
        tree=" / ".join(dict.fromkeys(n["tree"] for n in nodes)) or pick["tree"],
        label=label, text=text,
        nodes="\n".join(f"{n['id']} | {n['name']} [{n['lvl']}]" for n in nodes) or "(none fetched)")


def topic(pick, label, text):
    nodes = nodes_for(pick)
    if not nodes:
        # the node index covers only the chapters expanded so far. Silently returning
        # CHAPTER_ONLY here would look like "no node fits" when it means "never fetched".
        CALLS["nodes_missing"] += 1
        return {"topic_id": "", "topic": "CHAPTER_ONLY", "topic_level": "",
                "confidence": pick["confidence"], "nodes_missing": True, "tree": pick["tree"]}
    raw = call_model(p_topic(pick, label, text), max_tokens=300)
    if raw == PENDING_JSON:
        return None
    r = as_json(raw, {})
    hit = next((n for n in nodes if n["id"] == r.get("topic_id")), None)
    return {"topic_id": r.get("topic_id") or "", "topic": r.get("topic") or "CHAPTER_ONLY",
            "topic_level": r.get("topic_level") or "", "confidence": r.get("confidence") or "LOW",
            "tree": hit["tree"] if hit else pick["tree"]}


# ------------------------------------------------------- 4  AGGREGATE  (no LLM)

VALID_CHAPTERS = {c for _, c in CONCEPT}
VALID_NODES = {n["id"]: n for v in NODES.values() for n in v}
REJECTS = {"NOT_ACADEMIC", "OUT_OF_SCOPE", "UNKNOWN"}


def validate(pick, tp):
    """A name the model invented is rejected, not written. This is the only reason
    the output can be trusted without a human reading all 271."""
    if pick.get("reject"):
        return None
    tree = tp.get("tree") or pick["tree"]
    cid = CONCEPT.get((pick["subject"], pick["chapter"]), {}).get(tree)
    if not cid:
        return "chapter not in the tree"
    if tp["topic"] != "CHAPTER_ONLY":
        node = VALID_NODES.get(tp["topic_id"])
        if not node or node["name"] != tp["topic"]:
            return "node id and name do not agree"
        if node not in NODES.get(cid, []):
            return "node is not inside that chapter"
    return None


def tag_segment(pay, seg):
    """Tag what was ASKED. Tag what was DELIVERED too when they differ - the gap
    between them is a bot-quality signal nothing else in the data exposes."""
    asked_text = seg.get("posed") or seg.get("delivered") or ""
    out = {"conversation_id": pay["conversation_id"], "user_id": pay["user_id"],
           "segment": seg["i"], "grade": pay["grade"], "board": pay["board"],
           "target": pay["target"], "ask_source": seg.get("ask_source") or "bot_restatement",
           "diverged": bool(seg.get("diverged")), "divergence": seg.get("divergence"),
           "posed": seg.get("posed"), "delivered": seg.get("delivered")}

    pick = chapter(pay, "POSED", asked_text)
    tp = topic(pick, "POSED", asked_text) if not pick["reject"] else \
        {"topic_id": "", "topic": "", "topic_level": "", "confidence": pick["confidence"]}
    bad = validate(pick, tp)
    tree = tp.get("tree") or pick["tree"]
    out.update(asked_subject=pick["subject"], asked_chapter=pick["chapter"],
               asked_chapter_id=CONCEPT.get((pick["subject"], pick["chapter"]), {}).get(tree, ""),
               asked_topic=tp["topic"], asked_topic_id=tp["topic_id"],
               asked_topic_level=tp["topic_level"], tree=tree,
               confidence=tp["confidence"], reject=pick["reject"], why=pick["why"],
               invalid=bad, nodes_missing=tp.get("nodes_missing", False))
    if bad:                                                       # refuse it rather than write it
        out.update(asked_subject="", asked_chapter="", asked_chapter_id="",
                   asked_topic="", asked_topic_id="", tree="", reject="UNKNOWN")

    if seg.get("diverged") and seg.get("delivered"):
        d_pick = chapter(pay, "DELIVERED", seg["delivered"])
        d_tp = topic(d_pick, "DELIVERED", seg["delivered"]) if d_pick and not d_pick["reject"] else \
            {"topic_id": "", "topic": "", "topic_level": "", "confidence": "LOW"}
        if not validate(d_pick, d_tp):
            out.update(taught_subject=d_pick["subject"], taught_chapter=d_pick["chapter"],
                       taught_topic=d_tp["topic"], taught_topic_id=d_tp["topic_id"])
    return out


def aggregate(pay, segs):
    """Primary chapter = the one holding the most segments; ties go to the one with
    more HIGH confidence. Everything else is kept, not discarded."""
    good = [s for s in segs if s["asked_chapter"]]
    if not good:
        r = segs[0]
        return {**{k: "" for k in ROW}, "user_id": pay["user_id"],
                "conversation_id": pay["conversation_id"], "grade": pay["grade"],
                "board": pay["board"], "target": pay["target"], "exchanges": pay["exchanges"],
                "subject": r.get("reject") or "UNKNOWN", "chapter": r.get("why", ""),
                "confidence": r.get("confidence", "LOW"), "n_topics": "0"}

    score = collections.Counter()
    for s in good:
        score[(s["asked_subject"], s["asked_chapter"], s["tree"])] += 2 + (s["confidence"] == "HIGH")
    (subj, chap, tree), _ = score.most_common(1)[0]
    primary = next(s for s in good if (s["asked_subject"], s["asked_chapter"], s["tree"]) == (subj, chap, tree))

    chapters, topics = [], []
    for s in good:
        if s["asked_chapter"] not in chapters:
            chapters.append(s["asked_chapter"])
        if s["asked_topic"] and s["asked_topic"] != "CHAPTER_ONLY" and s["asked_topic"] not in topics:
            topics.append(s["asked_topic"])
    chapters = [chap] + [c for c in chapters if c != chap]        # primary always first

    drift = [s for s in good if s.get("diverged")]
    return {"user_id": pay["user_id"], "conversation_id": pay["conversation_id"],
            "grade": pay["grade"], "board": pay["board"], "target": pay["target"],
            "exchanges": pay["exchanges"], "subject": subj, "chapter": chap,
            "chapter_id": primary["asked_chapter_id"], "topic": primary["asked_topic"],
            "topic_id": primary["asked_topic_id"], "topic_level": primary["asked_topic_level"],
            "tree": tree, "confidence": primary["confidence"],
            "note": primary["why"] if len(chapters) > 1 else "",
            "all_chapters": "|".join(chapters), "all_topics": "|".join(topics),
            "n_topics": str(len(topics)), "is_multi": "Y" if len(topics) > 1 or len(chapters) > 1 else "",
            "multi_note": f"{len(drift)} of {len(good)} segments: bot answered something else"
                          if drift else ""}


ROW = ["user_id", "conversation_id", "grade", "board", "target", "exchanges", "subject",
       "chapter", "chapter_id", "topic", "topic_id", "topic_level", "tree", "confidence",
       "note", "all_chapters", "all_topics", "n_topics", "is_multi", "multi_note"]


# ------------------------------------------------------------------------ run

def run(cids, records):
    rows, segments, waiting = [], [], 0
    for i, cid in enumerate(cids, 1):
        pay = assemble(cid, records[cid])
        raw_segs = segment(pay)
        segs = [x for x in (tag_segment(pay, s) for s in raw_segs or []) if x]
        if raw_segs is None or len(segs) != len(raw_segs):
            waiting += 1
            print(f"  [{i}/{len(cids)}] {cid[:8]}  waiting on a reply", flush=True)
            continue
        segments += segs
        rows.append(aggregate(pay, segs))
        print(f"  [{i}/{len(cids)}] {cid[:8]}  {len(segs)} segment(s)  "
              f"{rows[-1]['chapter'] or rows[-1]['subject']}", flush=True)
    save_cache()
    if waiting:
        print(f"\n{waiting} conversations waiting. {CALLS['pending']} prompts written to "
              f"out4/pending/ - answer them into out4/cache.json (key = filename) and run again.")

    os.makedirs(OUT, exist_ok=True)
    with open(P("out4/segments.jsonl"), "w", encoding="utf-8") as f:
        for s in segments:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    with open(P("out4/topic_mapping.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ROW, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    tagged = [r for r in rows if r["chapter_id"]]
    bad = [s for s in segments if s.get("invalid")]
    print(f"\n{len(rows)} conversations, {len(segments)} segments, {CALLS['total']} model calls"
          f"{f' ({CALLS[chr(114) + chr(101) + chr(116) + chr(114) + chr(121)]} retried)' if CALLS['retry'] else ''}")
    print(f"  tagged to a chapter   {len(tagged)}")
    print(f"  at an exact topic     {sum(1 for r in tagged if r['topic'] and r['topic'] != 'CHAPTER_ONLY')}")
    print(f"  more than one topic   {sum(1 for r in tagged if r['is_multi'])}")
    print(f"  ask from student text {sum(1 for s in segments if s['ask_source'] == 'student_text')} of {len(segments)} segments")
    print(f"  bot answered elsewhere{sum(1 for s in segments if s['diverged']):>4} segments")
    print(f"  rejected as invalid   {len(bad)}")
    if CALLS["nodes_missing"]:
        need = sorted({(s["asked_subject"], s["asked_chapter"]) for s in segments if s.get("nodes_missing")})
        print(f"\n  !! {CALLS['nodes_missing']} segments hit a chapter whose nodes were never fetched")
        print(f"     {len(need)} chapters need sql/07_nodes_for_chosen_chapters.sql before stage 3 can run:")
        for sub, ch in need[:8]:
            print(f"       {sub} > {ch}")
        if len(need) > 8:
            print(f"       ... and {len(need) - 8} more")
        json.dump([{"subject": a, "chapter": b} for a, b in need],
                  open(P("out4/chapters_needing_nodes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nout4/topic_mapping.csv  out4/segments.jsonl")


def dry_run(cid, records):
    pay = assemble(cid, records[cid])
    bar = lambda t: print("\n" + "=" * 72 + f"\n{t}\n" + "=" * 72)
    bar("STAGE 0  PAYLOAD")
    print(json.dumps(pay, ensure_ascii=False, indent=2))
    bar("STAGE 1  SEGMENT prompt")
    print(p_segment(pay))
    bar("STAGE 2  CHAPTER cached prefix")
    head = PROMPT["2_chapter"].format(catalogue=CATALOGUE)
    print(head[:head.index("Catalogue")] + "Catalogue - subject | chapter:\n"
          + "\n".join(CATALOGUE.split("\n")[:6])
          + f"\n  ... {len(CATALOGUE.splitlines()):,} rows, {len(head):,} chars, identical every call")
    bar("STAGE 2  CHAPTER variable tail")
    print(p_chapter(pay, "POSED", "<the posed text of one segment>"))
    bar("STAGE 3  TOPIC prompt")
    demo = {"subject": "Mathematics", "chapter": "Quadratic Equations", "tree": "10_CBSE",
            "confidence": "HIGH"}
    print(p_topic(demo, "POSED", "<the posed text of one segment>"))
    print("\n(no model was called)")


def self_check():
    """The code stages. Runs without a key - these are what the model cannot fix."""
    assert clean("Let's go 💪 || Okay 👍") == "", "chips must be stripped"
    assert clean("Solved for x || Solved for x || Then found y") == "Solved for x || Then found y", \
        "the rolling window must de-duplicate"
    assert clean("Proceedings are quite as. ~ I don't know. ~ Let's go") == "Proceedings are quite as.", \
        "student lines join with ' ~ ', not '||' - splitting on '||' alone leaves the chips in"
    assert ("?", "") not in CONCEPT, "the blank catalogue row must not be a legal answer"
    assert clean("Found N || found  n") == "Found N", "de-dup is case and punctuation blind"
    assert clean(None) == ""

    pay = {"grade": "8", "board": "CBSE", "target": "JEE"}
    pref = preferred_trees(pay)
    assert pref[0] == "8_CBSE", f"own grade+board first, got {pref[0]}"
    assert not any(t.startswith("UNNAMED_") for t in pref), "unnamed trees must never be preferred"
    assert len(preferred_trees({"grade": "12", "board": "STATE", "target": "NA"})) == 12, \
        "a board that names no tree still gets a full preference list"
    assert set(pref) <= set(ALL_TREES) and len(ALL_TREES) == 73

    ok = {"subject": "Mathematics", "chapter": "Quadratic Equations", "tree": "10_CBSE"}
    assert validate(ok, {"topic": "CHAPTER_ONLY", "topic_id": ""}) is None
    assert validate({"subject": "Mathematics", "chapter": "Invented Chapter", "tree": "10_CBSE"},
                    {"topic": "CHAPTER_ONLY", "topic_id": ""}) == "chapter not in the tree"
    assert validate(ok, {"topic": "Invented Node", "topic_id": "deadbeef"}) is not None, \
        "an invented node must be rejected"
    assert validate({"reject": "NOT_ACADEMIC"}, {}) is None

    assert as_json('```json\n{"a":1}\n```', {}) == {"a": 1}
    assert as_json('here you go {"a":1} hope that helps', {}) == {"a": 1}
    assert as_json("not json at all", {"fallback": True}) == {"fallback": True}

    print(f"self-check passed - {len(CONCEPT):,} concepts, {len(ALL_TREES)} trees, "
          f"{len(VALID_NODES):,} nodes, catalogue {len(CATALOGUE.splitlines()):,} rows")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", metavar="CID", help="print the payload and every prompt, call nothing")
    ap.add_argument("--limit", type=int, help="run only the first N conversations")
    ap.add_argument("--only", metavar="CID", help="run one conversation")
    ap.add_argument("--self-check", action="store_true", help="test the code stages, no key needed")
    ap.add_argument("--offline", action="store_true",
                    help="never call an API: serve from out4/cache.json, write misses to out4/pending/")
    ap.add_argument("--cids", metavar="FILE", help="JSON list of conversation ids to run")
    ap.add_argument("--source", default="out2/conv_records.json",
                    help="assembled conversations (production: sql/09_input_parameters.sql)")
    a = ap.parse_args()

    if a.self_check:
        self_check()
        raise SystemExit

    OFFLINE = a.offline
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
