/* Cascade pipeline - end-to-end specification.
   node make_cascade_doc.js  ->  ShowNAsk_Cascade_Pipeline.docx                       */
const fs = require("fs");
const d = require("docx");
const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
        WidthType, ShadingType, AlignmentType, BorderStyle, LevelFormat, PageBreak } = d;

const W = 9360;
const INK = "16160F", MUTE = "56564C", FAINT = "8A8A80", RULE = "D2D1C8", SUNK = "F1F1EC";

const read = f => fs.readFileSync(f, "utf8").trimEnd();
const P1 = read("prompts/1_segment.txt");
const P2 = read("prompts/2_chapter.txt");
const P2T = read("prompts/2_chapter_tail.txt");
const P3 = read("prompts/3_topic.txt");
const IMPACT = JSON.parse(read("out4/impact_data.json"));
const T = IMPACT.totals;

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
const WORKED = JSON.parse(fs.readFileSync("out4/worked.json", "utf8"));
const MAXSEG = 3;
const cut = (t, n) => { t = String(t ?? ""); return t.length > n ? t.slice(0, n) + "\u2026" : t; };
const val = v => (v === null || v === undefined || v === "") ? "(empty)"
               : typeof v === "boolean" ? (v ? "yes" : "no") : String(v);

const workedSection = () => {
  const out = [
    h1("8.  Five conversations, step by step"),
    p("The same five conversations appear in ", ["out4/how_it_works_5_conversations.csv",
      false, true], ". For each one: what went in, what prompt was sent, and what came back - the ",
      ["real values", true], ", not an illustration."),
    small("The prompts themselves are printed in full in sections 3, 4 and 5. What follows shows what was substituted into them and what each call returned. Where a conversation holds more than three questions, the first three are spelled out and the rest are summarised."),
  ];

  for (const e of WORKED) {
    out.push(pb(), h2(`8.${WORKED.indexOf(e) + 1}  Conversation ${e.cid}`), small(e.why));

    /* stage 0 */
    out.push(h3("Stage 0 - Assemble (no model)"));
    out.push(table(["Input parameter", "Source", "Value for this conversation"],
      e.stage0.inputs.map(([n, s, v]) => [n, s, cut(val(v), 300)]),
      [1700, 2600, 5060], { mono: [0, 1] }));
    out.push(gap(120));
    out.push(table(["Worked out from those", "How", "Value"],
      e.stage0.derived.map(([n, s, v]) => [n, s, cut(val(v), 260)]),
      [1700, 2600, 5060], { mono: [0] }));

    /* stage 1 */
    const s1 = JSON.parse(e.stage1.output);
    out.push(h3("Stage 1 - Split into questions (model call 1)"));
    out.push(p(["In:", true], " student, wanted, taught, response, earlier \u2014 the five content "
      + "fields from stage 0. ", ["Prompt:", true], " prompts/1_segment.txt. ", ["Out:", true],
      ` ${s1.segments.length} question${s1.segments.length === 1 ? "" : "s"}.`));
    out.push(table(["#", "posed  (what the student asked)", "delivered  (what the bot did)", "ask_source", "diverged"],
      s1.segments.slice(0, MAXSEG).map(s =>
        [String(s.i), cut(val(s.posed), 240), cut(val(s.delivered), 240),
         val(s.ask_source), val(s.diverged)])
        .concat(s1.segments.length > MAXSEG
          ? [["\u2026", `segments ${MAXSEG + 1} to ${s1.segments.length} follow the same shape`, "", "", ""]]
          : []),
      [420, 3400, 3400, 1300, 840], { mono: [3, 4] }));

    /* stages 2 and 3 */
    for (const seg of e.segments.slice(0, MAXSEG)) {
      const o2 = JSON.parse(seg.stage2.output);
      out.push(h3(`Question ${seg.i} \u2014 stage 2, find the chapter`));
      out.push(table(["Input parameter", "Value"],
        seg.stage2.inputs.map(([n, v]) => [n, cut(val(v), 300)]), [2300, 7060], { mono: [0] }));
      out.push(gap(110));
      out.push(p(["Prompt:", true], " prompts/2_chapter.txt as the cached prefix, then this tail:"));
      out.push(...code(cut(seg.stage2.prompt_tail, 900)));
      out.push(table(["Output parameter", "Value"],
        Object.entries(o2).map(([k, v]) => [k, cut(val(v), 300)]), [2300, 7060], { mono: [0] }));

      if (seg.stage3) {
        const o3 = JSON.parse(seg.stage3.output);
        out.push(gap(140), h3(`Question ${seg.i} \u2014 stage 3, find the exact topic`));
        out.push(table(["Input parameter", "Value"],
          seg.stage3.inputs.map(([n, v]) => [n, cut(val(v), 300)]), [2300, 7060], { mono: [0] }));
        out.push(gap(110));
        out.push(p(["Prompt:", true], " prompts/3_topic.txt, filled in:"));
        out.push(...code(cut(seg.stage3.prompt, 1100)));
        out.push(table(["Output parameter", "Value"],
          Object.entries(o3).map(([k, v]) => [k, cut(val(v), 300)]), [2300, 7060], { mono: [0] }));
      }
      out.push(gap(160));
    }
    if (e.segments.length > MAXSEG) {
      out.push(p([`Questions ${MAXSEG + 1} to ${e.segments.length}`, true],
        " go through stages 2 and 3 in exactly the same way. Every one is written to "
        + "out4/segments.jsonl, and they are all reflected in the final row below."));
    }

    /* stage 4 */
    out.push(h3("Stage 4 - The final row (no model)"));
    out.push(table(["Output column", "Value"],
      Object.entries(e.stage4).filter(([k, v]) => v !== "").map(([k, v]) => [k, cut(val(v), 420)]),
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
   ["Outputs", "out4/segments.jsonl (one row per question)\nout4/topic_mapping.csv (one row per conversation)"],
   ["This run", `${T.convs} conversations, ${T.segments} questions, ${T.invalid} invalid names written`],
   ["Written", "21 September 2026"]],
  [2400, 6960], { mono: [1] }),
gap(200),
small("This document specifies the pipeline as built. Where a step was executed by hand rather than by the script, section 7 says so at the point it applies."),
pb(),

/* --------------------------------- 1 --------------------------------- */
h1("1.  The flow"),
p("One user has many conversations. For one conversation the pipeline reads every turn from the first to the last, splits it into the questions the student actually asked, and tags each question against the tree."),
...code(FLOW),
gap(),
p(["Two of the five stages use no model at all", true], ", and they are the ones that make the output trustworthy. Stage 0 fixes the data faults that would otherwise reach the model; stage 4 refuses anything the model invents."),
gap(),
table(["Stage", "Kind", "Runs", "Produces"],
  [["0  Assemble", "code", "once per conversation", "the payload - nine input parameters"],
   ["1  Segment", "model", "once per conversation", "k questions, posed vs delivered"],
   ["2  Chapter", "model", "once per question", "subject + chapter"],
   ["3  Topic", "model", "once per question", "node id, and the tree that owns it"],
   ["4  Aggregate", "code", "once per conversation", "the CSV row + the segment rows"]],
  [1700, 900, 2700, 4060], { mono: [1] }),
gap(),
p(["Why there is no separate subject loop.", true], " An earlier design put subject before chapter. It was dropped: a wrong subject at that step cannot be recovered by the two steps after it, and conversations crossing a subject are 1 in 226. The catalogue is static, so it is cached and costs nothing to show in full. Subject comes back from stage 2 as a field, not before it as a gate."),
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
h1("3.  Stage 1 — Segment"),
p("Runs on every conversation. The unit is the question, never the turn: in Snap-and-Ask the photo goes in first and the bot answers all of it, so a single turn can carry a whole worksheet page. Turn count does not measure how many questions were asked."),
gap(),
table(["Conversation length", "Conversations", "Carry >1 topic"],
  [["1 exchange", "60", "1.7%"],
   ["2 to 3", "78", "10.3%"],
   ["4 to 9", "74", "24.3%"],
   ["10 or more", "29", "55.2%"]],
  [3400, 2900, 3060], { numeric: [1, 2] }),
small("Measured on the 241 tagged conversations of the earlier run. An earlier design gated this stage on exchange count; that was wrong, because the count says nothing about how many questions were inside the photo."),
gap(),
h3("Input parameters"),
table(["Sent", "From", "Role"],
  [["student", "payload 3", "the ask, where the student typed one"],
   ["wanted", "payload 5", "what the bot recorded the student as wanting"],
   ["taught", "payload 6", "primary signal - the only one for the 52 image-only conversations"],
   ["response", "payload 4", "fallback where taught is empty (26 conversations)"],
   ["earlier", "payload 7", "the rolled-up summary of older exchanges"]],
  [1700, 1700, 5960], { mono: [0, 1] }),
gap(),
h3("Prompt"),
...code(P1),
gap(),
h3("Output parameters"),
table(["Field", "Type", "Meaning"],
  [["i", "integer", "segment number within the conversation"],
   ["posed", "string | null", "the problem as the student brought it - the ASK"],
   ["delivered", "string", "what the bot explained - the SUPPLY"],
   ["ask_source", "enum", "student_text | bot_restatement"],
   ["diverged", "boolean", "posed and delivered describe different subject matter"],
   ["divergence", "string | null", "how they differ, one line"],
   ["evidence", "string", "the phrase POSED was taken from, so a bad split is visible"]],
  [1700, 1700, 5960], { mono: [0, 1] }),
gap(),
p(["Why posed and delivered are separate.", true], " The business question is what students ask, so tagging what the bot taught and calling it demand would measure the bot. But the obvious alternatives fail on this data: ", ["wanted", false, true], " records conversational behaviour, not topics (\"Student expressed readiness to work\"), and the student's own typed text names subject matter in only 82 of 271 conversations. The ask lives in the photo, which is not stored - its only transcript is the bot restating the problem, which sits in the same note as the teaching. Stage 1 separates the two; ", ["ask_source", false, true], " records which one a row rests on."),
pb(),

/* --------------------------------- 4 --------------------------------- */
h1("4.  Stage 2 — Chapter"),
p("Once per question. The catalogue - 2,031 subject and chapter rows - is identical on every call and goes in the cached prefix; the student's tree preference rides in the variable tail so the cache still hits."),
gap(),
h3("Input parameters"),
table(["Sent", "From"],
  [["posed (or delivered)", "stage 1"],
   ["grade, board, target", "payload 8-9"],
   ["preferred tree order", "computed - the 12 best-ranked trees for this student"],
   ["catalogue", "2,031 rows, cached, never reordered"]],
  [2600, 6760], { mono: [0] }),
gap(),
h3("Prompt — cached prefix"),
...code(P2.replace(/\{catalogue\}/, "Mathematics | Quadratic Equations\nMathematics | Real Numbers\nScience | Atoms and Molecules\n  ... 2,031 rows, identical on every call")),
h3("Prompt — variable tail"),
...code(P2T),
gap(),
h3("Output parameters"),
table(["Field", "Type", "Values"],
  [["subject", "string", "a subject name from the tree"],
   ["chapter", "string", "a chapter name, copied exactly"],
   ["confidence", "enum", "HIGH the text names it outright\nMED inferred from worked examples\nLOW a guess"],
   ["reject", "enum | null", "NOT_ACADEMIC | OUT_OF_SCOPE | UNKNOWN | null"],
   ["why", "string", "one line of reasoning; on a reject, what it was"]],
  [1700, 1700, 5960], { mono: [0, 1] }),
gap(),
p(["The model does not return a tree.", true], " It picks the chapter on content alone; which of the 73 trees carries that chapter is settled afterwards by stage 3. This halved the prompt and removed a decision the model was not well placed to make."),
gap(),
h3("Rank, never filter"),
p("The student's grade and board order the candidate trees. They never limit them. Both treatments were measured on the same 241 conversations:"),
table(["Treatment", "Conversations reaching their own tag", "Share"],
  [["Filter - only the student's own trees", "191 of 241", "79.3%"],
   ["Rank - the full tree stays reachable", "241 of 241", "88.9%"]],
  [4000, 3500, 1860], { numeric: [2] }),
small("85.5% of conversations sit in the student's own grade, 8.7% run above it, 5.8% below. A candidate list bound to the profile discards that 14.5%. Separately, the five unnamed trees - 2,202 nodes with no entry in cmdsquestiontagging - are excluded from ranking at every tier; left in, they outrank real trees for grade-10 students."),
pb(),

/* --------------------------------- 5 --------------------------------- */
h1("5.  Stage 3 — Topic"),
p("Once per question, skipped when stage 2 rejected. The node list is that chapter's nodes across ", ["every", false, true], " tree that carries it, de-duplicated on name with the student's preferred tree first. Median 8 nodes, maximum 55."),
gap(),
h3("Prompt"),
...code(P3.replace(/\{nodes\}/, "67d2a0221d8bb4fb6545d4be | Discriminant and Nature of Roots [TOPIC]\n67d2a0231d8bb4fb6545d4c1 | Word Problems based on Quadratic equations [TOPIC]\n  ... median 8 nodes")),
gap(),
h3("Output parameters"),
table(["Field", "Type", "Values"],
  [["topic_id", "string", "24-character node id; empty on CHAPTER_ONLY"],
   ["topic", "string", "the exact node name, or CHAPTER_ONLY"],
   ["topic_level", "enum", "TOPIC | SUB_TOPIC | empty"],
   ["confidence", "enum", "HIGH | MED | LOW"]],
  [1700, 1700, 5960], { mono: [0, 1] }),
gap(),
p(["Two reasons this stage returns an id and searches across trees.", true], " Fifty-two node rows are duplicated inside fifteen chapters, so a name alone cannot be resolved to one node. And committing to a tree before the node is known puts content in the wrong place: a grade-11 JEE student's class-10 word problem resolved to 11_12_JEE, whose Quadratic Equations chapter has no word-problem node, so it landed on \"Miscellaneous examples\". With the union list, the chosen node names the tree - 10_CBSE, Word Problems based on Quadratic equations."),
p(["A chapter whose nodes were never fetched says so.", true], " The node index covers the chapters expanded so far. Returning CHAPTER_ONLY silently would read as \"no node fits\" when it means \"never fetched\", so those are counted, named, and written to out4/chapters_needing_nodes.json to feed the node query."),
pb(),

/* --------------------------------- 6 --------------------------------- */
h1("6.  Stage 4 — Output parameters"),
p("Two files, because two consumers want different shapes."),
gap(),
h2("6.1  segments.jsonl — one row per question"),
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
"# provider: ANTHROPIC_API_KEY or GEMINI_API_KEY; model via CASCADE_MODEL.",
"# replies are cached by prompt hash, so a crashed run resumes instead of re-paying.",
].join("\n")),

...workedSection(),

  ]}],
});

Packer.toBuffer(doc).then(b => {
  fs.writeFileSync("ShowNAsk_Cascade_Pipeline.docx", b);
  console.log("ShowNAsk_Cascade_Pipeline.docx", (b.length / 1024).toFixed(0) + " KB");
});
