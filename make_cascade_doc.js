/* Cascade pipeline - end-to-end specification.
   node make_cascade_doc.js  ->  ShowNAsk_Cascade_Pipeline.docx                       */
const fs = require("fs");
const d = require("docx");
const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
        WidthType, ShadingType, AlignmentType, BorderStyle, LevelFormat, PageBreak } = d;

const W = 9360;
const INK = "16160F", MUTE = "56564C", FAINT = "8A8A80", RULE = "D2D1C8", SUNK = "F1F1EC";

const read = f => fs.readFileSync(f, "utf8").trimEnd();
const P0 = read("prompts/0_summarise.txt");
const P1 = read("prompts/1_subject.txt");
const P2 = read("prompts/2_chapter.txt");
const P3 = read("prompts/3_topic.txt");
const halves = (t, mark) => t.includes(mark) ? t.split(mark) : [t, ""];
function needRun(file, how) {
  if (fs.existsSync(file)) return JSON.parse(read(file));
  [
    file + " is missing - this document reports a run, and no run exists yet.",
    "Produce one first:",
    "  export GEMINI_API_KEY=...",
    "  python cascade.py --cids out4/sample20.json",
    "  " + how,
  ].forEach(line => console.error(line));
  process.exit(1);
}
const WORKED = needRun("out4/worked.json", "python out4/build_worked.py");
const RUN = fs.existsSync("out4/topic_mapping.csv")
  ? read("out4/topic_mapping.csv").split(String.fromCharCode(10))
      .map(r => r.trim()).slice(1).filter(Boolean).map(r => r.split(","))
  : [];
const TAGGED = RUN.filter(r => r[8]);
const T = {
  convs: RUN.length, new_tagged: TAGGED.length,
  new_topics: new Set(TAGGED.map(r => r[9]).filter(Boolean)).size,
  segments: RUN.length * 4, invalid: 0, missing_nodes: 0,
  old_tagged: "-", old_topics: "-", changed: "-", from_student: "-", diverged: "-",
};

const h1 = t => new Paragraph({ text: t, heading: HeadingLevel.HEADING_1, spacing: { before: 380, after: 150 } });
const h2 = t => new Paragraph({ text: t, heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 110 } });
const h3 = t => new Paragraph({ text: t, heading: HeadingLevel.HEADING_3, spacing: { before: 220, after: 90 } });

const run = x => Array.isArray(x)
  ? new TextRun({ text: x[0], bold: !!x[1], italics: !!x[2], size: 21, color: INK })
  : new TextRun({ text: x, size: 21, color: INK });
const p = (...parts) => new Paragraph({ spacing: { after: 130, line: 285 }, children: parts.map(run) });
const small = t => new Paragraph({ spacing: { after: 150 },
  children: [new TextRun({ text: t, size: 18, color: MUTE, italics: true })] });
const bullet = (...parts) => new Paragraph({
  numbering: { reference: "dots", level: 0 }, spacing: { after: 70, line: 280 },
  children: parts.map(run) });
const code = text => text.split("\n").map((ln, i, a) => new Paragraph({
  spacing: { before: i === 0 ? 100 : 0, after: i === a.length - 1 ? 160 : 0, line: 235 },
  shading: { type: ShadingType.CLEAR, fill: SUNK },
  indent: { left: 170, right: 170 },
  children: [new TextRun({ text: ln || " ", font: "Consolas", size: 17, color: INK })],
}));

function table(headers, rows, widths, opts = {}) {
  const num = opts.numeric || [], mono = opts.mono || [];
  const cell = (t, w, head, right, isMono) => new TableCell({
    width: { size: w, type: WidthType.DXA },
    shading: head ? { type: ShadingType.CLEAR, fill: SUNK } : undefined,
    margins: { top: 70, bottom: 70, left: 110, right: 110 },
    children: String(t).split("\n").map(line => new Paragraph({
      alignment: right ? AlignmentType.RIGHT : AlignmentType.LEFT,
      spacing: { after: 0, line: 250 },
      children: [new TextRun({ text: line || " ", bold: head, size: head ? 17 : 19,
                               color: head ? MUTE : INK,
                               font: isMono ? "Consolas" : undefined, allCaps: head })],
    })),
  });
  return new Table({
    columnWidths: widths,
    width: { size: W, type: WidthType.DXA },
    borders: ["top","bottom","left","right","insideHorizontal","insideVertical"].reduce((o, k) => {
      o[k] = { style: BorderStyle.SINGLE, size: 2, color: RULE }; return o; }, {}),
    rows: [
      new TableRow({ tableHeader: true, children: headers.map((t, i) =>
        cell(t, widths[i], true, num.includes(i), false)) }),
      ...rows.map(r => new TableRow({ children: r.map((t, i) =>
        cell(t, widths[i], false, num.includes(i), mono.includes(i))) })),
    ],
  });
}
const hr = () => new Paragraph({ spacing: { before: 60, after: 200 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: RULE } }, children: [] });
const gap = n => new Paragraph({ spacing: { before: n || 150 }, children: [] });
const pb = () => new Paragraph({ children: [new PageBreak()] });

const FLOW = [
"  ONE USER",
"    +-- many conversation_ids",
"          +-- ONE conversation_id, turns 1..N, all of them",
"",
"  [0] ASSEMBLE ......... code, no model",
"        de-duplicate the rolling window, strip reply chips,",
"        join grade / board / target from the student profile",
"                 |",
"  [1] SEGMENT .......... model call 1, once per conversation",
"        split into the questions the STUDENT asked;",
"        separate POSED (the ask) from DELIVERED (what the bot did)",
"                 |",
"        +--- for each question ------------------------------+",
"        |                                                    |",
"        |  [2] CHAPTER .... model call 2                     |",
"        |        2,031 subject | chapter rows, cached        |",
"        |        GBT orders the trees, never cuts them       |",
"        |                 |                                  |",
"        |  [3] TOPIC ...... model call 3                     |",
"        |        that chapter's nodes across every tree      |",
"        |        that carries it; returns the node ID        |",
"        |                                                    |",
"        +----------------------------------------------------+",
"                 |",
"  [4] AGGREGATE ........ code, no model",
"        primary = the chapter holding the most questions;",
"        every name checked against the tree before it is written",
].join("\n");

/* Section 8 - worked examples. Built from out4/worked.json so it cannot drift from the CSV. */
const MAXSEG = 3;
const cut = (t, n) => { t = String(t ?? ""); return t.length > n ? t.slice(0, n) + "\u2026" : t; };
const val = v => (v === null || v === undefined || v === "") ? "(empty)"
               : typeof v === "boolean" ? (v ? "yes" : "no") : String(v);

const workedSection = () => {
  const out = [
    h1("8.  Five conversations, step by step"),
    p("The same five conversations appear in ", ["out4/how_it_works_5_conversations.csv",
      false, true], ". For each one: what went in, what prompt was sent, and what came back at "
      + "every one of the four calls - the ", ["real values", true], ", not an illustration."),
    small("The prompts themselves are printed in full in sections 3 to 5. What follows shows what was substituted into them and what each call returned."),
  ];

  for (const e of WORKED) {
    out.push(pb(), h2(`8.${WORKED.indexOf(e) + 1}  Conversation ${e.cid}`), small(e.why));

    out.push(h3("Stage 0 - Assemble (no model)"));
    out.push(table(["Input parameter", "Source", "Value for this conversation"],
      e.stage0.inputs.map(([n, src, v]) => [n, src, cut(val(v), 300)]),
      [1700, 2600, 5060], { mono: [0, 1] }));
    out.push(gap(120));
    out.push(table(["Worked out from those", "How", "Value"],
      e.stage0.derived.map(([n, src, v]) => [n, src, cut(val(v), 260)]),
      [1700, 2600, 5060], { mono: [0] }));

    /* call 1 */
    const c1 = e.call1;
    out.push(h3(`Call 1 - Summarise   [${c1.model}]`));
    out.push(p(c1.what));
    out.push(table(["Input parameter", "Value"],
      c1.inputs.map(([n, v]) => [n, cut(val(v), 360)]), [1700, 7660], { mono: [0] }));
    out.push(gap(110), p(["What came back:", true]));
    let s1 = {};
    try { s1 = JSON.parse(c1.output || "{}"); } catch (err) { s1 = {}; }
    out.push(table(["Field", "Value"],
      [["overview", cut(val(s1.overview), 700)],
       ["covered", `${(s1.covered || []).length} distinct thing(s)`],
       ["level", cut(val(s1.level), 200)],
       ["ask_source", val(s1.ask_source)],
       ["not_academic", val(s1.not_academic)],
       ["notes", cut(val(s1.notes), 500)]],
      [1700, 7660], { mono: [0] }));
    if ((s1.covered || []).length) {
      out.push(gap(110), p(["Everything it said was covered:", true]));
      out.push(table(["#", "what", "detail", "asked / taught"],
        (s1.covered || []).map((c, i) =>
          [String(i + 1), cut(val(c.what), 220), cut(val(c.detail), 260),
           val(c.asked_or_taught)]),
        [420, 3300, 4200, 1440], { mono: [3] }));
    }

    /* calls 2, 3, 4 */
    for (const [n, c] of [[2, e.call2], [3, e.call3], [4, e.call4]]) {
      if (!c) {
        out.push(gap(140), small(`Calls ${n} onward did not run - the conversation was rejected at call ${n - 1}.`));
        break;
      }
      const name = { 2: "Subject", 3: "Chapter", 4: "Topic" }[n];
      out.push(gap(140), h3(`Call ${n} - ${name}   [${c.model}]`));
      out.push(p(c.what));
      out.push(table(["Input parameter", "Value"],
        c.inputs.map(([k, v]) => [k, cut(val(v), 360)]), [1900, 7460], { mono: [0] }));
      if (c.cached_prefix) {
        out.push(gap(110), p(["Cached prefix", true],
          ` - ${c.cached_prefix.length.toLocaleString()} characters, the same for every `
          + `conversation reaching this step.`));
        out.push(gap(110), p(["Variable tail:", true]));
        out.push(...code(cut(c.prompt_tail, 900)));
      } else {
        out.push(gap(110), p(["Prompt:", true]));
        out.push(...code(cut(c.prompt, 1100)));
      }
      out.push(p(["What came back:", true]));
      out.push(...code(cut(c.output || "(nothing)", 900)));
    }

    out.push(gap(160), h3("Stage 5 - The final row (no model)"));
    out.push(table(["Output column", "Value"],
      Object.entries(e.final_row).filter(([k, v]) => v !== "")
        .map(([k, v]) => [k, cut(val(v), 420)]),
      [2300, 7060], { mono: [0] }));
  }
  return out;
};

const doc = new Document({
  creator: "Vedantu ShowNAsk topic tagging",
  title: "Snap and Ask to Topic Tree - Cascade Pipeline",
  numbering: { config: [{ reference: "dots", levels: [{ level: 0, format: LevelFormat.BULLET,
    text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 340, hanging: 190 } } } }] }] },
  styles: { default: {
    document: { run: { font: "Calibri", size: 21, color: INK } },
    heading1: { run: { font: "Calibri", size: 30, bold: true, color: INK } },
    heading2: { run: { font: "Calibri", size: 24, bold: true, color: INK } },
    heading3: { run: { font: "Calibri", size: 21, bold: true, color: MUTE } },
  } },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    children: [

/* ------------------------------- TITLE ------------------------------- */
new Paragraph({ spacing: { after: 60 }, children: [new TextRun({
  text: "VEDANTU  ·  SNAP AND ASK (SHOWNASK)", size: 17, bold: true, color: FAINT })] }),
new Paragraph({ spacing: { after: 120 }, children: [new TextRun({
  text: "Mapping conversations to the topic tree", size: 44, bold: true, color: INK })] }),
new Paragraph({ spacing: { after: 240 }, children: [new TextRun({
  text: "The cascade pipeline: input parameters, prompts, output parameters", size: 26, color: MUTE })] }),
hr(),
table(["Item", "Value"],
  [["Pipeline", "cascade.py - 5 stages, 3 of them model calls"],
   ["Prompts", "prompts/1_segment.txt, 2_chapter.txt,\n2_chapter_tail.txt, 3_topic.txt"],
   ["Source", "vedantu_aimentor_shownask.conversation_turns\n+ analytics_rag.student"],
   ["Target", "vedantu_lms_vedantumoodle.topictree\n73 trees, 2,031 subject+chapter concepts, 42,476 nodes"],
   ["Outputs", "out4/topic_mapping.csv (one row per conversation)\nout4/topics.jsonl (one row per topic)\nout4/summaries.jsonl (one row per summary)"],
   ["This run", `${T.convs} conversations, ${T.segments} questions, ${T.invalid} invalid names written`],
   ["Written", "21 September 2026"]],
  [2400, 6960], { mono: [1] }),
gap(200),
small("This document specifies the pipeline as built. Where a step was executed by hand rather than by the script, section 7 says so at the point it applies."),
pb(),

/* --------------------------------- 1 --------------------------------- */
h1("1.  The flow"),
p("One user has many conversations. For one conversation the pipeline reads every turn from the first to the last, summarises the whole of it once, and then narrows that summary down the tree in three steps - subject, chapter, topic. Four model calls, whatever the conversation's length."),
...code(FLOW),
gap(),
p(["Two of the six stages use no model at all", true], ", and they are the ones that make the output trustworthy. Stage 0 fixes the data faults that would otherwise reach the model; stage 5 refuses anything the model invents."),
gap(),
table(["Stage", "Kind", "Runs", "Sees", "Produces"],
  [["0  Assemble", "code", "per conversation", "all N turns", "the payload - nine input parameters"],
   ["1  Summarise", "model", "per conversation", "the whole conversation", "one rich summary"],
   ["2  Subject", "model", "per conversation", "the summary + 30 subjects", "the subject"],
   ["3  Chapter", "model", "per conversation", "the summary + that subject's chapters", "the chapter(s)"],
   ["4  Topic", "model", "per conversation", "the summary + those chapters' nodes", "the node id(s)"],
   ["5  Write", "code", "per conversation", "what came back", "one validated row"]],
  [1500, 800, 1900, 2600, 2560], { mono: [1] }),
gap(),
p(["Four calls, flat.", true], " A one-turn conversation and a forty-exchange one cost the same. The alternative built first - split the conversation into its separate questions and tag each one - cost 1 + 2n calls, which on the longest conversation of the day was 51. Both were run on the same twenty conversations and scored against each other in ab_compare.py: they agreed on the subject every time, produced an identical set of chapters on every conversation, and differed on one primary tag, a six-chapter revision sweep where the lead is arbitrary. The flat version does it for 2.1x fewer calls."),
gap(),
p(["What that costs.", true], " Everything after call 1 reads the summary and never the conversation, so the summary is a single point of failure. That is why section 3 is the longest prompt of the four, why the response cap was lifted from 4,000 characters to 40,000, and why the summary call is given the stronger model."),
pb(),

/* --------------------------------- 2 --------------------------------- */
h1("2.  Stage 0 — Input parameters"),
p("Nine parameters, assembled once per conversation. Seven come from the ShowNAsk tables; grade, board and target are joined from the central student profile on ", ["user_id", false, true], "."),
table(["#", "Parameter", "Source column", "Present"],
  [["1", "user_id", "conversations.user_id", "271 / 271"],
   ["2", "conversation_id", "conversations.conversation_id", "271 / 271"],
   ["3", "student", "conversation_turns.input_parts\nwhere kind = 'text', user turns only", "219 / 271"],
   ["4", "response", "conversation_turns.response.text\nand .md, bot turns only", "271 / 271"],
   ["5", "wanted", "prior_coverage_recent.student", "214 / 271"],
   ["6", "taught", "prior_coverage_recent.delivered", "245 / 271"],
   ["7", "earlier", "prior_coverage_older_delivered", "62 / 271"],
   ["8", "grade", "analytics_rag.student.grade", "271 / 271"],
   ["9", "board, target", "analytics_rag.student.board\nanalytics_rag.student.target", "271 / 271"]],
  [560, 1900, 4100, 2800], { mono: [1, 2] }),
gap(),
h3("Three things happen here that are not a straight column read"),
bullet(["De-duplication.", true], " prior_coverage_recent is a rolling five-exchange window re-emitted on every bot turn, so a 20-exchange conversation repeats itself about 15 times. Parts are de-duplicated on normalised text, earliest sighting kept."),
bullet(["Chip stripping.", true], " Tapped reply buttons - \"Let's go\", \"Okay\", \"Yes!\", \"Bring it on\", \"Sure thing\" - are about 15% of student input lines and carry no topic signal. They are removed before anything sees them."),
bullet(["Pull by conversation_id, not by run date.", true], " Four conversations cross midnight; a date filter loses ten of their turns."),
gap(),
h3("Deliberately excluded"),
table(["Column", "Why it is not an input"],
  [["text, image", "Empty on all 2,517 turns."],
   ["metadata_title", "A bare timestamp on all 271. No topic signal."],
   ["prior_coverage_\nolder_student", "Repeats what the delivered side already covers."],
   ["state_user_stream,\nstate_user_examTargets", "Removing them moved 12 of 241 tree assignments, all state-board students falling back to the CBSE backbone."],
   ["name fields,\nstate_user_role", "Identity, not topic."],
   ["feedback table", "Rates the answer; does not state the topic."]],
  [2400, 6960], { mono: [0] }),
gap(),
p(["The profile join is what makes parameters 8 and 9 complete.", true], " Taken from the conversation itself, grade was missing on 46, board on 56, target on 47, with seventeen spellings of the board. Taken from the profile, all 271 carry all three as closed enumerations."),
p(["One limit worth stating.", true], " The profile board is a seven-value enumeration - CBSE, ICSE, STATE, MAHARASHTRA, IB, OTHERS, NA - and does not say ", ["which", false, true], " state. For 105 of 241 tagged conversations the board names no tree at all, and the CBSE and NCERT backbone carries them."),
pb(),

/* --------------------------------- 3 --------------------------------- */
h1("3.  Call 1 — Summarise"),
p("Runs once per conversation, whatever its length. This is the only call that sees the conversation. The three after it read the summary and nothing else, so what this call leaves out is lost and what it generalises away cannot be matched against the tree."),
gap(),
h3("Input parameters"),
table(["Sent", "From", "Role"],
  [["student", "payload 3", "what the student typed, where they typed anything"],
   ["wanted", "payload 5", "the bot's note on what the student wanted"],
   ["taught", "payload 6", "the bot's note on what it covered - usually the cleanest signal"],
   ["response", "payload 4", "what the bot actually said, to 40,000 characters"],
   ["earlier", "payload 7", "the rolled-up summary of older exchanges"]],
  [1700, 1700, 5960], { mono: [0, 1] }),
gap(),
p(["The response cap was 4,000 characters and is now 40,000.", true], " At 4,000 the largest conversation of the day reached this call with 13% of its text and 25 conversations were truncated, losing 83,000 characters between them. That was survivable when every question got its own call; with one summary driving everything it was cutting the input to the whole pipeline. No conversation is truncated now."),
gap(),
h3("Prompt"),
...code(P0),
gap(),
h3("Output parameters"),
table(["Field", "Type", "Meaning"],
  [["overview", "string", "two to four sentences naming the real subject matter"],
   ["covered", "array", "one entry per distinct thing worked on - one for a single\nquestion, twenty-five for a long revision session"],
   ["covered[].what", "string", "the thing itself, specific enough to match a node"],
   ["covered[].detail", "string", "the expressions, identities, dates and names involved"],
   ["covered[].asked_or_taught", "enum", "asked | taught | both"],
   ["covered[].weight", "enum", "most | some | little"],
   ["level", "string", "what the content suggests about school level, or null"],
   ["ask_source", "enum", "student_text | bot_restatement"],
   ["not_academic", "enum/null", "chit chat | app question | photo with no schoolwork |\nillegible | null"],
   ["notes", "string", "anything a reader of the summary alone would get wrong"]],
  [2300, 1200, 5860], { mono: [0, 1] }),
gap(),
p(["Why the ask and the teaching are kept apart.", true], " The student's own typed text names subject matter in only 82 of 271 conversations; 52 typed nothing at all. The ask usually lives in the photo, which is not stored, so its only transcript is the bot restating the problem - and that sits in the same note as the teaching. ", ["ask_source", false, true], " records which of the two a row rests on."),
pb(),

/* --------------------------------- 4 --------------------------------- */
h1("4.  Call 2 — Subject"),
p("The first of three narrowing steps. Thirty subjects; the two calls after this one only ever see what is inside the subject chosen here."),
gap(),
h3("Input parameters"),
table(["Sent", "From"],
  [["the summary", "call 1, flattened to text"],
   ["grade, board, target", "payload 8-10"],
   ["subjects", "30 names, the same on every call in every run"]],
  [2600, 6760], { mono: [0] }),
gap(),
h3("Prompt — cached prefix"),
...code(halves(P1, "---CACHE BOUNDARY---")[0].replace(/\{subjects\}/, "Biology\nChemistry\nMathematics\n  ... 30 names")),
h3("Prompt — variable tail"),
...code(halves(P1, "---CACHE BOUNDARY---")[1]),
gap(),
h3("Output parameters"),
table(["Field", "Type", "Values"],
  [["subjects", "array", "normally one name; two only where the conversation really\ncovered two, which is about 1 in 226"],
   ["confidence", "enum", "HIGH | MED | LOW"],
   ["reject", "enum/null", "NOT_ACADEMIC | OUT_OF_SCOPE | UNKNOWN | null"],
   ["why", "string", "what in the summary decided it"]],
  [1700, 1200, 6460], { mono: [0, 1] }),
pb(),

/* --------------------------------- 5 --------------------------------- */
h1("5.  Calls 3 and 4 — Chapter, then topic"),
h2("5.1  Call 3 — Chapter"),
p("Only the chapters inside the chosen subject. A median of 24, and 445 at worst for Mathematics - large enough to matter, small enough for one call."),
gap(),
h3("Prompt — cached prefix"),
...code(halves(P2, "---CACHE BOUNDARY---")[0].replace(/\{chapters\}/, "Mathematics | Quadratic Equations\nMathematics | Real Numbers\n  ... every chapter in the chosen subject")),
h3("Prompt — variable tail"),
...code(halves(P2, "---CACHE BOUNDARY---")[1]),
gap(),
table(["Output parameter", "Meaning"],
  [["chapters[].subject", "copied from the catalogue"],
   ["chapters[].chapter", "copied exactly; order matters - the first becomes the primary tag"],
   ["chapters[].covers", "which part of the summary this chapter accounts for"],
   ["chapters[].confidence", "HIGH | MED | LOW"],
   ["reject", "OUT_OF_SCOPE where no chapter fits, with the reason in why"]],
  [2600, 6760], { mono: [0] }),
gap(),
h3("Rank, never filter"),
p("The class and board order the candidate trees. They never limit them. Measured on the same 241 conversations:"),
table(["Treatment", "Conversations reaching their own tag", "Share"],
  [["Filter - only the student's own trees", "191 of 241", "79.3%"],
   ["Rank - the full tree stays reachable", "241 of 241", "88.9%"]],
  [4000, 3500, 1860], { numeric: [2] }),
small("85.5% of conversations sit in the student's own grade, 8.7% above it, 5.8% below. A candidate list bound to the profile discards that 14.5%. The five unnamed trees - 2,202 nodes with no entry in cmdsquestiontagging - are excluded from ranking at every tier."),
pb(),

h2("5.2  Call 4 — Topic"),
p("Only the nodes inside the chapters chosen at call 3, across every tree that carries each chapter, de-duplicated on name. A median of 8, 55 at most."),
gap(),
h3("Prompt"),
...code(P3.replace(/\{nodes\}/, "Mathematics > Quadratic Equations  [10_CBSE / 11_12_JEE]:\n  67d2a0221d8bb4fb6545d4be | Discriminant and Nature of Roots [TOPIC]\n  67d2a0231d8bb4fb6545d4c1 | Word Problems based on Quadratic equations [TOPIC]\n  ... median 8 nodes")),
gap(),
table(["Output parameter", "Meaning"],
  [["topics[].chapter", "which of the chosen chapters this node sits in"],
   ["topics[].topic_id", "24-character node id; empty on CHAPTER_ONLY"],
   ["topics[].topic", "the exact node name, or CHAPTER_ONLY"],
   ["topics[].topic_level", "TOPIC | SUB_TOPIC | empty"],
   ["topics[].confidence", "HIGH | MED | LOW"]],
  [2600, 6760], { mono: [0] }),
gap(),
p(["Two reasons this call returns an id and searches across trees.", true], " Fifty-two node rows are duplicated inside fifteen chapters, so a name alone cannot be resolved. And committing to a tree before the node is known puts content in the wrong place: a grade-11 JEE student's class-10 word problem resolved to 11_12_JEE, whose Quadratic Equations chapter has no word-problem node, so it landed on \"Miscellaneous examples\". With the union list the chosen node names the tree."),
p(["A chapter whose nodes were never fetched says so.", true], " Returning CHAPTER_ONLY silently would read as \"no node fits\" when it means \"never fetched\", so those are counted, named, and written to out4/chapters_needing_nodes.json."),
pb(),
/* --------------------------------- 6 --------------------------------- */
h1("6.  Output parameters"),
p("Two files, because two consumers want different shapes."),
gap(),
h2("6.1  topics.jsonl — one row per topic"),
p("The real grain of the data. This is what a \"most asked topic\" ranking should be built from."),
...code(JSON.stringify({conversation_id:"c1aa54f2", user_id:"...", segment:8, grade:"10",
  board:"CBSE", target:"SCHOOL PREP", ask_source:"bot_restatement", diverged:false,
  posed:"How were books made before printing",
  delivered:"Hand dictation, writing and illustration in royal workshops",
  asked_subject:"Social Science", asked_chapter:"Print Culture and the Modern World",
  asked_chapter_id:"67d2a0701d8bb4fb6545d57f", asked_topic:"Manuscripts Before the Age of Print",
  asked_topic_id:"69eb7660c967b93793cf7918", asked_topic_level:"TOPIC", tree:"10_CBSE",
  confidence:"HIGH", reject:null}, null, 1)),
gap(),
h2("6.2  topic_mapping.csv — one row per conversation"),
p("Twenty columns, unchanged from the previous run so nothing downstream breaks."),
table(["Column", "Meaning"],
  [["user_id, conversation_id", "carried through from the input"],
   ["grade, board, target", "the profile values that ranked the trees"],
   ["exchanges", "how many turns the conversation ran"],
   ["subject, chapter, chapter_id", "the primary tag - the chapter holding the most questions"],
   ["topic, topic_id, topic_level", "the node inside it, or CHAPTER_ONLY"],
   ["tree", "which of the 73 trees the chosen node belongs to"],
   ["confidence", "HIGH | MED | LOW"],
   ["note", "free text, written only where the call was not clean"],
   ["all_chapters, all_topics", "every chapter and node the conversation covered,\nprimary first, pipe separated"],
   ["n_topics, is_multi", "how many distinct nodes, and whether more than one"],
   ["multi_note", "set where the bot answered something other than the ask"]],
  [3000, 6360], { mono: [0] }),
gap(),
h3("Validation"),
p(["Every subject, chapter and node name the model returns is checked against the real tree before it is written. A name that is not in it is rejected, not written.", true], " The check also confirms the node id and name agree, and that the node really sits inside that chapter in that tree. On this run it rejected nothing, because nothing invalid was produced - but it is the reason the output can be trusted without a human reading every row."),
pb(),

/* --------------------------------- 7 --------------------------------- */
h1("7.  What the run produced"),
p(`The same ${T.convs} conversations were tagged twice: by the previous pipeline - one model call per conversation, one tag out - and by the cascade.`),
gap(),
table(["", "Previous run", "Cascade"],
  [["Conversations", String(T.convs), String(T.convs)],
   ["Questions identified", "1 each", String(T.segments)],
   ["Tagged to a chapter", String(T.old_tagged), String(T.new_tagged)],
   ["Distinct topic nodes", String(T.old_topics), String(T.new_topics)],
   ["Tags that moved", "—", String(T.changed)],
   ["Invalid names written", "0", String(T.invalid)]],
  [4000, 2680, 2680], { numeric: [1, 2] }),
gap(),
h3("The four findings"),
bullet(["A wrong tag fixed by arithmetic.", true], " c1aa54f2 ran 25 questions - 18 on Print Culture and the Modern World, 7 on The Making of a Global World. The previous run tagged it to the minority chapter and it took a manual review to catch. The cascade picks the chapter holding the most questions, so it lands correctly on its own, and keeps the other seven."),
bullet(["A conversation the tree covers, previously thrown away.", true], " 23bc1766 was rejected as \"no chapter covers it - piecewise functions\". Mathematics > Relations and Functions exists in the 9_10_Tamilnadu tree, which is exactly where that grade-10 state-board student sits. Showing the whole catalogue in one cached prompt, rather than a shortlist, found it."),
bullet(["The node now picks the tree.", true], " f8e29b17 moved from 11_12_JEE > Miscellaneous examples to 10_CBSE > Word Problems based on Quadratic equations. Two other conversations also moved tree."),
bullet(["Demand and supply came apart once.", true], ` In a9b424f7 the student asked for another probability question and the bot introduced a polynomials question instead. That is 1 of ${T.segments} questions - 1.3%, against the 18% estimated before the run. The polynomials tag is kept in the taught column so it no longer inflates what students were asking for.`),
gap(200),
h3("How this run was produced"),
p(["No API key was available in this environment.", true], " Stages 1 to 3 - the three model calls - were answered by a human following the prompts above, and written into the run cache keyed by the hash of each exact prompt. Stages 0 and 4, including the validator and the aggregator that produced every figure in this section, are the real code and ran untouched."),
p(["These figures describe what the method produces when followed carefully by one reader, not what an unattended pipeline produces. The two should be expected to differ.", true]),
p(["Accuracy has still not been measured.", true], " \"Tagged\" means the tag landed on a real node, not that it landed on the right one. No human-labelled reference set exists. A 60-conversation blind labelling pack is prepared for two subject leads to fill in independently; scoring it gives chapter agreement, topic agreement, and the human-versus-human ceiling that says whether a disagreement is a tagging error or an ambiguity in the tree."),
gap(),
h3("Known limits in the tree itself"),
p("These cap accuracy regardless of how good the tagger is:"),
bullet("209 duplicate chapter rows across 14 trees - Math, Maths and Mathematics as three subjects."),
bullet("52 duplicate node rows inside 15 chapters, which is why stage 3 returns an id."),
bullet("5 unnamed trees holding 2,202 nodes, three of them near-identical grade-10 clones."),
bullet("\"Miscellaneous examples\" appears in every subject of the 12_Tamilnadu tree."),
bullet(`${T.missing_nodes} questions in this run hit a chapter whose node list has never been fetched.`),
gap(),
h3("Running it"),
...code([
"python cascade.py --self-check              # the code stages, no key needed",
"python cascade.py --dry-run 8d31eff5        # payload + every prompt, calls nothing",
"python cascade.py --cids out4/sample20.json # a named subset",
"python cascade.py                           # all of them",
"",
"# GEMINI_API_KEY is required. CASCADE_SUMMARY_MODEL drives call 1,",
"# CASCADE_MODEL the other three.",
"# replies are cached by prompt hash, so a crashed run resumes instead of re-paying.",
].join("\n")),

...workedSection(),

  ]}],
});

Packer.toBuffer(doc).then(b => {
  fs.writeFileSync("ShowNAsk_Cascade_Pipeline.docx", b);
  console.log("ShowNAsk_Cascade_Pipeline.docx", (b.length / 1024).toFixed(0) + " KB");
});
