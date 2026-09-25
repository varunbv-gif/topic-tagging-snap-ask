const fs = require("fs");
const d = require("docx");
const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
        WidthType, ShadingType, AlignmentType, BorderStyle, LevelFormat, PageBreak } = d;

const W = 9360;                       // Letter, 1in margins
const INK = "16160F", MUTE = "56564C", FAINT = "8A8A80", RULE = "D2D1C8", SUNK = "F1F1EC";

const PROMPT_V3 = fs.readFileSync("out3/PROMPT_v3.txt", "utf8").trimEnd();

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

const RULES_PROMPT = [
"You tag school-tutoring exchanges against the Vedantu CBSE topic tree.",
"",
"Each exchange is a note the tutor bot wrote about itself: `student` is what the student",
"asked, `delivered` is what the bot taught. Tag what was ACTUALLY TAUGHT (the delivered",
"side); the student side is only context for what they wanted.",
"",
"Rules:",
"- The node must cover everything in the note, not just part of it.",
"- Exchanges in one conversation usually continue the same chapter. Stay in the chapter",
"  already chosen for a neighbouring exchange unless the note clearly moved on.",
"- When several grades' trees cover the same content, pick the lowest grade that covers it,",
"  unless the student's grade is given and its tree covers it.",
"- A note with an empty or meaningless `delivered` (student sent only a photo, or typed",
"  gibberish): carry over the neighbouring exchange's chapter if the topic plainly continues,",
"  else answer UNKNOWN.",
"- Answer NOT_IN_TREE for real academics the tree has no chapter for, NOT_ACADEMIC for",
"  chit-chat, app questions, or anything non-academic.",
].join("\n");

const SQL1 = [
"WITH bot_turns AS (",
"  SELECT",
"    conversation_id,",
"    ROW_NUMBER() OVER (PARTITION BY conversation_id",
"                       ORDER BY message_index) AS exchange_no,",
"    ARRAY_REVERSE(prior_coverage_recent)[SAFE_OFFSET(0)] AS note",
"  FROM `...vedantu_aimentor_shownask.conversation_turns`",
"  WHERE role = 'bot'",
"    AND DATE(timestamp, 'Asia/Kolkata') BETWEEN '2026-09-20' AND '2026-09-20'",
")",
"SELECT b.conversation_id, c.user_id, c.state_user_grade AS grade,",
"       b.exchange_no, b.note.student, b.note.delivered",
"FROM bot_turns b",
"LEFT JOIN `...conversations` c USING (conversation_id)",
].join("\n");

const SQL3 = [
"WITH last_turn AS (",
"  SELECT conversation_id, prior_coverage_older_delivered AS older,",
"         prior_coverage_recent AS recent,",
"         ROW_NUMBER() OVER (PARTITION BY conversation_id",
"                            ORDER BY message_index DESC) AS rn",
"  FROM `...conversation_turns`",
"  WHERE role = 'bot' AND DATE(timestamp,'Asia/Kolkata') = '2026-09-20'",
")",
"SELECT conversation_id,",
"       TRIM(CONCAT(IFNULL(older, ''), ' ',",
"            (SELECT STRING_AGG(r.delivered, ' ')",
"             FROM UNNEST(recent) AS r))) AS coverage",
"FROM last_turn WHERE rn = 1",
].join("\n");

const SQL4 = [
"WITH bot AS (",
"  SELECT conversation_id, message_index, prior_coverage_recent,",
"         prior_coverage_older_delivered",
"  FROM `...conversation_turns`",
"  WHERE role = 'bot' AND DATE(timestamp, 'Asia/Kolkata') = '2026-09-20'",
"),",
"notes AS (",
"  SELECT conversation_id, r.delivered AS note, MIN(message_index) AS first_seen",
"  FROM bot, UNNEST(prior_coverage_recent) AS r",
"  WHERE r.delivered IS NOT NULL AND r.delivered != ''",
"  GROUP BY conversation_id, note",
"  UNION ALL",
"  SELECT conversation_id, prior_coverage_older_delivered, MIN(message_index)",
"  FROM bot WHERE prior_coverage_older_delivered != ''",
"  GROUP BY conversation_id, prior_coverage_older_delivered",
"),",
"dedup AS (",
"  SELECT conversation_id, note, MIN(first_seen) AS first_seen",
"  FROM notes GROUP BY conversation_id, note",
")",
"SELECT conversation_id, COUNT(*) AS notes,",
"       STRING_AGG(note, '  ' ORDER BY first_seen) AS coverage",
"FROM dedup GROUP BY conversation_id",
].join("\n");

const doc = new Document({
  creator: "Vedantu ShowNAsk topic tagging",
  title: "ShowNAsk to CBSE Topic Tree - Prompt and Methodology",
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

/* ---------------------------- TITLE ---------------------------- */
new Paragraph({ spacing: { after: 60 }, children: [new TextRun({
  text: "VEDANTU  ·  SNAP AND ASK (SHOWNASK)", size: 17, bold: true, color: FAINT })] }),
new Paragraph({ spacing: { after: 120 }, children: [new TextRun({
  text: "Mapping bot coverage notes to the CBSE topic tree", size: 44, bold: true, color: INK })] }),
new Paragraph({ spacing: { after: 240 }, children: [new TextRun({
  text: "The prompt, the methodology, and what the run produced", size: 26, color: MUTE })] }),
hr(),
table(["Item", "Value"],
  [["Run date", "20 September 2026, IST day boundary"],
   ["Source table", "vedantu_aimentor_shownask.conversation_turns"],
   ["Source columns", "nine input parameters - see section 4.1"],
   ["Target tree", "vedantu_lms_vedantumoodle.topictree, all 73 trees"],
   ["Volume", "271 conversations / 1,256 exchanges"],
   ["Document written", "21 September 2026"]],
  [2600, 6760], { mono: [1] }),
gap(200),
small("Scope note: this document records the method exactly as it was executed. Where a step was run by hand rather than by the script, that is stated at the point it applies. Section 4 was revised on 21 September 2026 for the current run - one tag per conversation, nine input parameters, all 73 trees. Sections 5 to 9 still describe the earlier per-exchange CBSE-only run."),
pb(),

/* ---------------------------- 1 ---------------------------- */
h1("1.  Summary"),
p("The Snap and Ask tutor bot writes itself a short note after every reply: what the student asked, and what it taught. Those notes are the only structured record of what a conversation was about. This work takes those notes and maps each conversation onto a node of the Vedantu CBSE topic tree."),
p("The mapping is done by a language model in two stages: first pick the chapter from the full list of every CBSE chapter, then pick the exact topic from only that chapter's own topics. Everything around those two stages - extraction, de-duplication, filling blanks, rolling up, validation - is plain SQL and Python with no model involved."),
p("Three grains were built and compared, in this order:"),
bullet(["Per exchange", true], " - one tag for every question asked. 1,256 rows."),
bullet(["Per conversation, last turn only", true], " - one tag per conversation, read from the bot's final turn. 271 rows."),
bullet(["Per conversation, all N turns pooled", true], " - one tag per conversation, read from every turn's notes. 271 rows. This is the method now in use."),
p("All three agree on roughly 99% of conversations. The differences are confined to conversations that genuinely cover two chapters in about equal measure."),

/* ---------------------------- 2 ---------------------------- */
h1("2.  The source data"),
h2("2.1  What the bot records"),
p("Each row of ", ["conversation_turns", false, true], " is one message. Bot turns carry the coverage fields; user turns carry none."),
table(["Column", "Type", "What it holds"],
  [["prior_coverage_recent", "ARRAY<STRUCT<\nstudent,\ndelivered>>",
    "A rolling window of the last five exchanges. Each element is one exchange: what the student asked and what the bot delivered."],
   ["prior_coverage_\nolder_delivered", "STRING",
    "A running summary of everything before those five. Present only once a conversation exceeds five exchanges - 61 of 271 conversations on this day."],
   ["prior_coverage_\nolder_student", "STRING", "The same for the student side. Not used."]],
  [2500, 1800, 5060], { mono: [0, 1] }),
gap(),
p("Two facts about the window drive the whole extraction:"),
bullet("The window slides. A note written for exchange 3 appears again on the bot turns for exchanges 4, 5, 6 and 7, then falls out. Reading only the final turn therefore loses the early part of any long conversation."),
bullet(["The last element of the array on the Nth bot turn is always the note for exchange N.", true], " This was verified against a live 11-exchange conversation before anything was built on it."),

h2("2.2  The topic tree"),
p("The tree is ", ["vedantu_lms_vedantumoodle.topictree", false, true], ", a self-referential hierarchy: SUBJECT to CHAPTER to TOPIC to SUB_TOPIC, linked by ", ["parentId", false, true], ". Each tree root is identified by ", ["parentTreeId", false, true], ", which the table itself does not name. The readable name (", ["10_CBSE", false, true], ", ", ["11_12_CBSE", false, true], " and so on) lives in ", ["cmdsquestiontagging.parentTreeName", false, true], ", so the two are joined to select the CBSE trees."),
p(["Nine CBSE trees exist, not twelve.", true], " There is no 1_CBSE or 2_CBSE - grades 1 and 2 have topictree rows but under a different, non-CBSE root. Classes 11 and 12 share one tree."),
table(["Tree", "Chapters", "Topics", "Sub-topics"],
  [["3_CBSE", "64", "286", "471"], ["4_CBSE", "65", "367", "549"],
   ["5_CBSE", "80", "420", "869"], ["6_CBSE", "55", "321", "357"],
   ["7_CBSE", "80", "466", "540"], ["8_CBSE", "113", "868", "533"],
   ["9_CBSE", "107", "787", "451"], ["10_CBSE", "91", "786", "322"],
   ["11_12_CBSE", "111", "1,113", "1,155"], ["Total", "766", "5,414", "5,247"]],
  [3060, 2100, 2100, 2100], { numeric: [1, 2, 3], mono: [0] }),
gap(),
small("The tree carries some duplication of its own: several grades list both a \"Math\" and a \"Mathematics\" subject with the same chapters beneath them, and a few chapters appear twice within one tree. This was left as found and flagged rather than silently merged."),
pb(),

/* ---------------------------- 3 ---------------------------- */
h1("3.  Extraction"),
p("Three extraction queries were written, one per grain. All are pure SQL - no model, no parsing, nothing to stitch together in code."),

h2("3.1  Per exchange"),
p("The note for exchange N is the last element of the array on the Nth bot turn. Numbering runs across the whole conversation, so a thread that started the previous day keeps its original exchange numbers."),
...code(SQL1),
p("Because the window never drops a note before it has been written to a bot turn, this recovers all 1,256 exchanges with nothing lost - confirmed against a straight count of bot turns for the day."),

h2("3.2  Per conversation, last turn only"),
p("The bot's final turn already carries the whole conversation: the older running summary plus the last five notes. One row per conversation, no stitching."),
...code(SQL3),

h2("3.3  Per conversation, all N turns pooled"),
p(["This is the query now in use.", true], " Every turn contributes: each turn's five-note window and each turn's running summary. The union is de-duplicated - the window repeats a note up to five times - and kept in the order notes first appeared."),
...code(SQL4),
p("A second de-duplication pass in Python drops notes wholly contained in a note already kept, which the bot produces often when it restates an earlier explanation. Across the 67 long conversations this cut the pooled text from about 8 KB at worst to a median of 919 characters."),

h2("3.4  The node catalogue"),
p("Pulled once, and re-pulled only when the tree changes. The query returns every node flat, with its parent id; the path is rebuilt in Python by walking ", ["parent_id", false, true], " upward. That keeps the SQL trivial and avoids a three-way self-join."),
pb(),

/* ---------------------------- 4 ---------------------------- */
h1("4.  Input parameters, prompt and output parameters"),
small("Revised 21 September 2026. This section describes the run currently in use: one tag per conversation, every content-bearing column as input, and the whole 73-tree topic tree as the target. Sections 5 to 9 still describe the earlier per-exchange CBSE-only run and are marked where they differ."),
p("Classification is one model call per conversation. This section gives it as a contract: what goes in, what is sent, and what comes back."),

/* ---------------- 4.1 INPUT ---------------- */
h2("4.1  Input parameters"),
p("Nine parameters, assembled once per conversation. Seven come from the two ShowNAsk tables; grade, board and target are joined in from the central student profile on ", ["user_id", false, true], "."),
table(["#", "Parameter", "Source column", "Present on"],
  [["1", "user_id", "conversations.user_id", "271 / 271"],
   ["2", "conversation_id", "conversations.conversation_id", "271 / 271"],
   ["3", "what was the input", "conversation_turns.input_parts\nwhere kind = 'text'", "219 / 271"],
   ["4", "what did the bot respond", "conversation_turns.response.text\nand .md", "271 / 271"],
   ["5", "prior recent coverage\n(student side)", "prior_coverage_recent.student", "214 / 271"],
   ["6", "prior recent coverage\n(delivered side)", "prior_coverage_recent.delivered", "245 / 271"],
   ["7", "prior coverage older\ndelivered", "prior_coverage_older_delivered", "62 / 271"],
   ["8", "grade", "analytics_rag.student.grade", "271 / 271"],
   ["9", "board / target", "analytics_rag.student.board\nanalytics_rag.student.target", "271 / 271"]],
  [560, 2400, 3600, 2800], { mono: [1, 2] }),
gap(),
p(["The profile join is what makes parameters 8 and 9 complete.", true], " Taken from the conversation itself, grade was missing on 46 conversations, board on 56 and target on 47, and the values were free text with seventeen spellings of the board. Taken from the profile, all 271 carry all three and the values are closed enumerations. The two disagree on grade for 19 conversations; the profile is usually the one that matches the content."),
p(["One limit worth stating.", true], " The profile board is a seven-value enumeration - CBSE, ICSE, STATE, MAHARASHTRA, IB, OTHERS, NA - and does not say ", ["which", false, true], " state. For 119 of 271 conversations the board names no tree at all, and the CBSE and NCERT backbone carries them. The board captured on the conversation keeps the specific value (BIEAP, BSE Telangana, MH) and is used as a fallback where the profile is generic."),
gap(),

h3("Deliberately excluded"),
table(["Column", "Why it is not an input"],
  [["text, image", "Empty on all 2,517 turns of the day. The content lives in input_parts and response."],
   ["metadata_title", "A bare timestamp on all 271 - \"Conversation 2026-09-20 08:11 UTC\". No topic signal."],
   ["prior_coverage_\nolder_student", "The student side of the running summary. Dropped to keep the parameter set to nine; it repeats what the delivered side already covers."],
   ["state_user_stream,\nstate_user_examTargets", "Dropped with the same reasoning. Removing them moved 12 of 241 tree assignments, all state-board students falling back to CBSE."],
   ["user_id name fields,\nstate_user_role", "Identity, not topic."],
   ["state_current_image,\n_source", "Empty on all 271."],
   ["id, dpt_*, source,\nclient_info_*", "Pipeline plumbing."],
   ["feedback table\n(40 columns)", "Rates the answer; does not state the topic. Useful for quality work, not for tagging."]],
  [2600, 6760], { mono: [0] }),
pb(),

/* ---------------- 4.2 PROMPT ---------------- */
h2("4.2  The prompt"),
p("Sent verbatim as the system block, ahead of the candidate list:"),
...code(PROMPT_V3),
gap(),
p(["Three rules carry most of the weight.", true], " Tag what was taught rather than what was asked, because the two diverge often. Where notes and response disagree, the notes win - they are the bot's considered summary, the response is one turn of talk. And the candidate list is ranked by the student's profile but never limited to it."),
pb(),

/* ---------------- 4.3 CANDIDATES ---------------- */
h2("4.3  The candidate list"),
p("The whole tree is in scope: 73 trees, 42,476 nodes, 4,463 chapter rows collapsing to 2,032 distinct subject-and-chapter concepts. The student's grade, board and target ", ["rank", false, true], " that list; they do not cut it."),
p(["Why ranking and not filtering.", true], " Both were measured on the same 241 tagged conversations:"),
table(["Treatment", "Conversations that reach their own tag", "Share"],
  [["Filter - only the student's own trees", "191 of 241", "79.3%"],
   ["Rank - full tree stays reachable", "241 of 241", "88.9%"]],
  [4000, 3560, 1800], { numeric: [2] }),
gap(),
p("Filtering loses 50 conversations, and the losses are ordinary student behaviour rather than tagging error: ten grade-12 state-board students on Probability Distributions, a chapter that exists only in the Tamil Nadu tree their profile cannot name; four grade-11 JEE students revising class-10 Polynomials; three grade-8 students on complex numbers. Across the day, ", ["85.5% of conversations sit in the student's own grade, 8.7% run above it and 5.8% below", true], ". A candidate list bound to the profile discards that 14.5%."),
gap(),

h3("Tree selection, in order"),
table(["Rank", "Rule"],
  [["1", "A tree whose family matches the declared board and whose grade band contains the student's grade."],
   ["2", "A tree whose family matches the exam target (JEE, NEET, Foundation, Olympiad) and whose band contains the grade."],
   ["3", "The CBSE or NCERT tree for that grade band."],
   ["4", "Any tree whose band contains the grade."],
   ["5", "The tree whose band sits closest at or below the grade, CBSE and NCERT preferred."]],
  [900, 8460]),
gap(),
small("The five unnamed trees - 2,202 nodes with no entry in cmdsquestiontagging, three of them near-identical grade-10 clones - are excluded from selection at every rank. Left in, they outrank real trees for grade-10 students and pull class-11 physics into an orphan."),
pb(),

/* ---------------- 4.4 OUTPUT ---------------- */
h2("4.4  Output parameters"),
p("One row per conversation, written to ", ["topic_mapping.csv", false, true], ". The prompt's own output line is the middle five fields; the rest are joined back deterministically."),
table(["Column", "Type", "Values and meaning"],
  [["user_id", "string", "Carried through from the input."],
   ["conversation_id", "string", "Carried through. The primary key of the file."],
   ["grade, board, target", "string", "The profile values that ranked the candidate list, kept so any row can be re-judged without re-joining."],
   ["exchanges", "integer", "How many questions the conversation contained."],
   ["subject", "string", "A subject name from the tree, or one of three refusals:\nNOT_ACADEMIC - chit-chat, app questions, a photo with no question\nOUT_OF_SCOPE - real academics no chapter covers\nUNKNOWN - nothing legible to go on"],
   ["chapter", "string", "The chapter name, copied exactly from the tree. On a refusal row this holds the reason instead."],
   ["chapter_id", "string", "24-character chapter id. Empty on a refusal row."],
   ["topic", "string", "The exact node name inside that chapter, or CHAPTER_ONLY when the chapter is right but no node inside it fits."],
   ["topic_id", "string", "24-character node id. Empty when topic is CHAPTER_ONLY."],
   ["topic_level", "enum", "TOPIC | SUB_TOPIC. How deep into the tree the tag reached."],
   ["tree", "string", "Which of the 73 trees carries the chosen chapter - 10_CBSE, 11_12_JEE, 12_Tamilnadu."],
   ["confidence", "enum", "HIGH - the notes name the chapter's content outright\nMED - inferred from worked examples or the student's own words\nLOW - a guess"],
   ["note", "string", "Free text, written only where the call was not clean: a conversation spanning two chapters, a chapter borrowed from another board, a grade that contradicts the content."]],
  [2200, 1200, 5960], { mono: [0, 1] }),
gap(),

h3("What the run produced"),
table(["Outcome", "Conversations", "Share"],
  [["Tagged to a chapter", "241", "88.9%"],
   ["  of those, to an exact topic node", "232", "85.6%"],
   ["  of those, chapter only - no node fits", "9", "3.3%"],
   ["Not academic", "15", "5.5%"],
   ["Not in the tree", "13", "4.8%"],
   ["Nothing to go on", "2", "0.7%"]],
  [4600, 2560, 2200], { numeric: [1, 2] }),
gap(),
p("232 exact topics across 156 distinct nodes, 108 chapters and 21 trees. Confidence on the 241: 185 high, 53 medium, 3 low."),
pb(),

/* ---------------- 4.5 HOW IT RAN ---------------- */
h2("4.5  How this was executed"),
p(["The script exists and is complete, but it was not the thing that ran.", true], " ", ["tag.py", false, true], " needs an Anthropic API key, which was not available. Every tag reported here was produced by following the prompt above by hand, against the same candidate lists, with the same validity check: any subject-and-chapter pair not present in the tree is rejected. Zero invalid pairs survived into the output."),
p(["This remains the single largest caveat in the document.", true], " These numbers describe what the method produces when followed carefully by one reader, not what an unattended pipeline produces. The two should be expected to differ."),
p(["Accuracy has not been measured.", true], " 88.9% and 85.6% are coverage - the tag landed on a real node - not correctness. No human-labelled reference set exists. A 60-conversation blind labelling pack has been prepared for two subject leads to fill in independently; scoring it gives chapter agreement, topic agreement, and the human-versus-human ceiling that says whether a disagreement is a tagging error or an ambiguity in the tree."),
pb(),

/* ---------------------------- 5 ---------------------------- */
h1("5.  Deterministic post-processing"),
p("No model is involved past stage 2. Three rules, all in ", ["tag.py", false, true], " and all covered by its self-check, which runs without an API key."),
h3("Blank fill"),
p("An exchange the model returned as UNKNOWN borrows the tag of the exchange before it, or the one after it if it is the first. It is marked ", ["tag_source = carried", false, true], " so borrowed tags can always be excluded. NOT_IN_TREE and NOT_ACADEMIC are never overwritten - those are decisions, not gaps."),
h3("Roll-up"),
p("A conversation's tag is the node used by the most of its exchanges, ", ["counting only model-chosen tags", true], ". A carried tag is a copy of its neighbour, not evidence, so it does not vote; the fallback is to count everything, used only when a conversation has no model-chosen tag at all. Ties break towards the earliest exchange. Every distinct node is also kept in ", ["all_node_ids", false, true], "."),
p("This rule was corrected while the worked examples in section 6 were being written; before the change a conversation could be decided by tags that were themselves borrowed. See 6.3."),
h3("Guard rails"),
p("A failure in one conversation is caught and marked ERROR rather than being allowed to sink the batch. Node ids are validated against the candidate list before being written."),

/* -------------------- 6  WORKED EXAMPLES -------------------- */
h1("6.  Three worked examples"),
p("Three real conversations from 20 September, traced end to end: the note the bot wrote, the chapter stage 1 chose, the node stage 2 chose, and what the roll-up made of it. They were picked to show the common case, the awkward case, and the case that breaks a tie the wrong way."),

/* ---------- 6.1 ---------- */
h2("6.1  The common case - one chapter, several topics"),
table(["", ""],
  [["conversation_id", "21fa2541-a8f5-4e94-9014-ad5ea6e71439"],
   ["grade", "10"],
   ["exchanges", "7"],
   ["chapter (stage 1)", "10_CBSE > Physics > Light - Reflection and Refraction, on all seven"]],
  [2200, 7160], { mono: [1] }),
gap(),
table(["#", "What the bot delivered", "Node chosen by stage 2", "Source"],
  [["1", "Steps to solve for object distance u with the lens formula; sign conventions for concave lenses.", "Introduction to Lens Formula", "llm"],
   ["2", "1/v - 1/u = 1/f; calculated 1/u = -1/15 - 1/-20 = -1/60.", "Introduction to Lens Formula", "llm"],
   ["3", "Convex lens: object height +50cm, image height -20cm, image distance +10cm. Goal: focal length.", "Magnification of lens", "llm"],
   ["4", "Image distance v from object distance and object-screen distance; sign conventions.", "Introduction to Lens Formula", "llm"],
   ["5", "f = +16cm, image height h' = -2cm. Image real and inverted.", "Magnification of lens", "llm"],
   ["6", "Same values, plus the ray diagram: object at 2F1, image at 2F2, real, inverted, same size.", "Image Formation by Convex Lens", "llm"],
   ["7", "Focal length, magnification, image nature and ray diagram from the calculated values.", "Image Formation by Convex Lens", "llm"]],
  [500, 4500, 3360, 1000], { numeric: [0] }),
gap(),
p(["What it shows.", true], " Stage 1 held the same chapter across all seven exchanges, which is what the rules ask for. Stage 2 then discriminated inside it, moving from the lens formula to magnification to image formation as the tutoring progressed - three different nodes in one chapter. The per-exchange roll-up returns ", ["Introduction to Lens Formula", false, true], " (3 of 7); the conversation tag returns the chapter, ", ["Light - Reflection and Refraction", false, true], ". This is the case where every method agrees and nothing is lost."),

/* ---------- 6.2 ---------- */
h2("6.2  The awkward case - half the notes are empty"),
table(["", ""],
  [["conversation_id", "18c1facc-43aa-4156-9527-31436511c451"],
   ["grade", "10"],
   ["exchanges", "4, of which 2 have no delivered note at all"],
   ["chapter (stage 1)", "10_CBSE > Chemistry > Acids, Bases, and Salts, on all four"]],
  [2200, 7160], { mono: [1] }),
gap(),
table(["#", "What the bot delivered", "Node chosen by stage 2", "Source"],
  [["1", "(nothing)\nStudent asked for high quality questions on acid, base and salt.", "falls back to the chapter", "llm"],
   ["2", "(nothing)\nStudent said they don't know.", "falls back to the chapter", "carried"],
   ["3", "NaCl with concentrated H2SO4; evolved gas identified as HCl; balanced equation given.", "More about Salts", "llm"],
   ["4", "Reactants and gas identified; balanced equation; noted the reaction needs high temperature.", "More about Salts", "llm"]],
  [500, 4500, 3360, 1000], { numeric: [0] }),
gap(),
p(["What it shows.", true], " Two of the four exchanges are photo-only turns with nothing on the delivered side - this is the 23.4% blank rate in miniature. Exchange 2 has no usable note and borrows its tag from exchange 1, marked ", ["carried", false, true], " so it can be filtered out. Exchange 1 was tagged even though its delivered note is empty, because the student's own words named the chapter outright."),
p(["A documented deviation.", true], " The written rule says answer UNKNOWN when the delivered note is empty. Here the student side said \"high quality questions on acid base salt\", which names the chapter with no ambiguity, so it was tagged rather than discarded. The rule is the safer default for an unattended run; this run departed from it where the student side was unmistakable. Stage 2 could not run on either blank exchange, so both sit at chapter level - that is two of the 55 chapter-level stops."),
pb(),

/* ---------- 6.3 ---------- */
h2("6.3  The case that broke a tie the wrong way"),
table(["", ""],
  [["conversation_id", "376d59b0-3e4d-4515-8dd8-ec8ea1aaf335"],
   ["grade", "8"],
   ["exchanges", "6, spanning two chapters"],
   ["chapter (stage 1)", "changes halfway - see below"]],
  [2200, 7160], { mono: [1] }),
gap(),
table(["#", "What the bot delivered", "Chapter", "Node", "Source"],
  [["1", "(nothing)", "Vector Algebra", "Product of Two Vectors", "carried"],
   ["2", "Confirmed the scalar triple product proof and determinant expansion for Q2; inverse cosine and angle addition for Q4.", "Vector Algebra", "Product of Two Vectors", "llm"],
   ["3", "(nothing)\nStudent replied \"Okay\".", "Vector Algebra", "Product of Two Vectors", "carried"],
   ["4", "Located question 7 - find the square root of 6 - 8i - and walked through the general formula for sqrt(a + ib).", "Complex Numbers and Quadratic Equations", "Square Roots of Negative Real Numbers", "llm"],
   ["5", "General formula for sqrt(a + ib); modulus of z calculated as 10; values substituted.", "Complex Numbers and Quadratic Equations", "Square Roots of Negative Real Numbers", "llm"],
   ["6", "Same formula; modulus 10; simplified to sqrt(8) - i*sqrt(2).", "Complex Numbers and Quadratic Equations", "Square Roots of Negative Real Numbers", "llm"]],
  [420, 3340, 2100, 2400, 1100], { numeric: [0] }),
gap(),
p(["What it shows.", true], " The conversation genuinely changes chapter at exchange 4. Counted naively that is three exchanges each way - a tie, broken towards the earliest, giving ", ["Vector Algebra", false, true], ". But two of those three vector exchanges are ", ["carried", false, true], ": they have no note of their own and simply copied exchange 2. Only one exchange actually taught vectors, against three that taught complex numbers."),
p(["This was found while writing this document, and the roll-up was changed because of it.", true], " A carried tag is a copy of its neighbour, not evidence, so it no longer votes: ", ["rollup()", false, true], " now counts only model-chosen tags and falls back to counting everything only when a conversation has no model-chosen tag at all. Under that rule this conversation returns Complex Numbers and Quadratic Equations, which is what the pooled conversation-level tag had said all along."),
p("The fix is not specific to this conversation. ", ["113 of 226 conversations contain at least one carried tag", true], ", and excluding them from the vote raised agreement between the per-exchange roll-up and the pooled conversation tag from 98.7% to 99.6%, resolving two of the three standing disagreements. The change is covered by two new assertions in the ", ["tag.py", false, true], " self-check."),
pb(),

/* ---------------------------- 6 ---------------------------- */
h1("7.  What the run produced"),
h2("7.1  Per exchange"),
table(["Outcome", "Exchanges", "Share"],
  [["Tagged", "1,110", "88.4%"],
   ["      of which direct from the model", "874", "69.6%"],
   ["      of which carried from a neighbour", "236", "18.8%"],
   ["Not in the tree", "78", "6.2%"],
   ["Unknown", "44", "3.5%"],
   ["Not academic", "24", "1.9%"],
   ["Total", "1,256", "100%"]],
  [4760, 2300, 2300], { numeric: [1, 2] }),
gap(),
p("Node depth of the 1,110 tagged exchanges: 791 reached a topic, 264 reached a sub-topic, and 55 stopped at the chapter because no topic beneath it covered what was taught. 264 distinct nodes across 104 chapters were touched, and it takes 46 nodes to cover half the tagged exchanges."),
p(["294 of 1,256 exchanges (23.4%) arrived with an empty delivered note", true], " - almost always a photo-only question. These are the 236 carried plus most of the 44 unknown."),

h2("7.2  Per conversation"),
table(["Outcome", "Last turn only", "All N turns pooled"],
  [["Tagged to a chapter", "225", "225"],
   ["No coverage to read", "26", "26"],
   ["Not in the tree", "18", "18"],
   ["Not academic", "2", "2"],
   ["Distinct chapters hit", "95", "96"]],
  [4160, 2600, 2600], { numeric: [1, 2] }),
gap(),
p("Pooling all turns changed 2 tags out of the 67 conversations it could possibly affect. For the other 204 conversations the two methods read identical input: with five turns or fewer, the last turn's window already holds every note. Both changed tags moved towards the per-exchange answer."),

h2("7.3  Where the tree could not hold the content"),
p("The 78 not-in-tree exchanges are not scattered. Two holes account for more than half."),
table(["Gap", "Exchanges"],
  [["Sanskrit grammar (ktva / lyap suffixes)", "23"],
   ["Medieval and ancient Indian history (Delhi Sultanate, Mauryan)", "18"],
   ["Literature, translation and poetry outside the set texts", "13"],
   ["Logarithms", "10"],
   ["World history outside the CBSE syllabus", "6"],
   ["Tamil Nadu board calculus (partial derivatives)", "4"],
   ["Internet and computing basics", "3"],
   ["Multi-chapter revision sweeps", "1"]],
  [7060, 2300], { numeric: [1] }),
gap(),
p("Separately, several chapters exist in the tree but lack the node their content needs. ", ["11_12_CBSE > Complex Numbers and Quadratic Equations", false, true], " has 22 nodes, all about complex numbers and none about discriminants or the nature of roots, so 14 exchanges on exactly that had nowhere below the chapter to land. That is the main source of the 55 chapter-level stops."),
pb(),

/* ---------------------------- 7 ---------------------------- */
h1("8.  Validation"),
p("There is no external gold set for this day, so the three grains were used to check each other. That is weaker than an independent label set and should be read as a consistency check, not an accuracy measure."),
table(["Comparison", "Agreement"],
  [["All N turns pooled vs. per-exchange node roll-up", "224 / 225   (99.6%)"],
   ["All N turns pooled vs. per-exchange chapter majority", "224 / 225   (99.6%)"],
   ["Last turn only vs. per-exchange node roll-up", "222 / 225   (98.7%)"],
   ["Last turn only vs. per-exchange chapter majority", "223 / 225   (99.1%)"]],
  [6060, 3300]),
gap(),
p("These figures are after the roll-up correction described in 6.3. Before it the pooled figures were 99.1% and 98.7%; excluding carried tags from the vote resolved two of the three standing disagreements."),
p("What remains is two conversations, and neither is a clear error. Conversation 207 is a seven-question mixed revision quiz that touches four chapters with no majority worth the name. Conversation 203 is the node roll-up trap described below."),

h2("8.1  How safe is one tag per conversation"),
p("Measured against the per-exchange run, which is the only view that can see a conversation change subject."),
bullet(["12 of 226 conversations (5%) ever cross a chapter boundary.", true], " Only 3 cross a subject."),
bullet(["A single chapter per conversation mislabels 5.7% of questions.", true], " Acceptable."),
bullet(["A single topic per conversation mislabels 24.4% of questions.", true], " Not acceptable: 63 of 226 conversations touch more than one node."),
p(["Conclusion: roll a conversation up to a chapter, not to a node.", true], " If node-level detail is wanted, keep it at exchange level."),

h2("8.2  A trap in node-level roll-up"),
p("The most-used node is not always inside the most-used chapter. Conversation 203 spent 27 questions on ", ["Print Culture and the Modern World", false, true], " and 13 on ", ["The Making of a Global World", false, true], ", but Print Culture's 27 were spread thinly across twelve different nodes while Global World's 13 concentrated on one. Picking the single most-used node therefore reports the smaller chapter. This happens in 3 of 226 conversations, and is a further argument for rolling up at chapter level."),

/* ---------------------------- 8 ---------------------------- */
h1("9.  Chapter against student grade"),
p("Each conversation carries the student's class from ", ["conversations.state_user_grade", false, true], ". Crossing that with the tagged chapter shows whether students work at their own level."),
table(["Tree", "6", "7", "8", "9", "10", "11", "12", "13", "n/a", "All"],
  [["3_CBSE", "", "", "", "", "", "", "", "", "2", "2"],
   ["6_CBSE", "3", "", "", "", "", "", "", "", "1", "4"],
   ["7_CBSE", "1", "9", "1", "", "1", "1", "", "1", "", "14"],
   ["8_CBSE", "", "3", "12", "", "1", "", "", "1", "", "17"],
   ["9_CBSE", "", "1", "1", "10", "2", "", "", "", "3", "17"],
   ["10_CBSE", "", "", "", "", "59", "", "", "3", "5", "67"],
   ["11_12_CBSE", "", "", "5", "1", "8", "39", "20", "8", "23", "104"],
   ["All", "4", "13", "19", "11", "71", "40", "20", "13", "34", "225"]],
  [1860, 720, 720, 720, 720, 720, 720, 720, 720, 720, 1020],
  { numeric: [1,2,3,4,5,6,7,8,9,10], mono: [0] }),
gap(),
bullet(["160 of the 191 conversations with a grade on file (84%) sit in their own grade's tree.", true]),
bullet(["20 run ahead", true], " - eight grade-10 and five grade-8 students working in class 11-12 material, clustered in Relations and Functions, Complex Numbers and Limits."),
bullet(["11 run behind", true], " - mostly grade-13 students back in the class-10 tree."),
bullet(["34 have no grade on the profile at all", true], " (15% of tagged conversations). Nothing can be said about them, and this is the largest limit on this view."),
small("Grade 13 is a value the profile carries past class 12. Eight of those thirteen conversations sit in the 11-12 tree, which fits a repeat year, but this reading is inferred from the data rather than from a documented code list and should be confirmed with whoever owns the profile schema."),
pb(),

/* ---------------------------- 9 ---------------------------- */
h1("10.  Known limits"),
table(["Limit", "Effect", "What would fix it"],
  [["Classification was run by hand, not by tag.py",
    "The reported figures describe this run, not the unattended pipeline. No confidence scores were produced.",
    "An Anthropic API key. The script is complete and self-tested."],
   ["No independent gold set",
    "Validation is three methods checking each other, which shares any systematic bias between them.",
    "A subject expert labelling a sample, ideally the 141 hand-checked exchanges already prepared."],
   ["23.4% of exchanges have an empty delivered note",
    "236 exchanges carry only a borrowed tag; 44 stay unknown. Photo-only questions are the weak spot.",
    "The product saving a coverage note for image-only turns."],
   ["34 conversations have no grade on file",
    "15% of tagged conversations cannot appear in any grade analysis.",
    "Profile completeness, or inferring grade from content."],
   ["Grade influences the tag",
    "The tag is not a pure function of the note: where content spans grades, the student's grade pulls the choice. Intended, but worth knowing.",
    "Nothing - but do not treat the tag as grade-independent evidence."],
   ["The tree has duplicate subjects and chapters",
    "Math and Mathematics coexist under the same grade with the same chapters; a few chapters appear twice in one tree.",
    "A cleanup on the tree itself, not on the tagger."],
   ["Chapters missing nodes their content needs",
    "55 exchanges could only be placed at chapter level.",
    "Adding the missing topics, for example discriminant and nature of roots."]],
  [2500, 3800, 3060]),

/* ---------------------------- 10 ---------------------------- */
h1("11.  Files produced"),
table(["File", "Rows", "What it is"],
  [["sql/01_exchanges.sql", "-", "Per-exchange extraction."],
   ["sql/02_catalogue.sql", "-", "Flat node catalogue for the CBSE trees."],
   ["sql/03_conversation_summary.sql", "-", "Per conversation, last turn only."],
   ["sql/04_conversation_all_turns.sql", "-", "Per conversation, all N turns pooled. In use."],
   ["tag.py", "-", "Two-stage classifier, blank fill, roll-up, evaluation. Runs with --selftest without an API key."],
   ["exchange_topic_tags.csv", "1,256", "One row per exchange: node, chapter, status, tag source."],
   ["conversation_topic_tags.csv", "271", "Per-exchange run rolled up to conversations."],
   ["conversation_tags_simple.csv", "271", "Conversation tags, last turn only."],
   ["conversation_tags_all_turns.csv", "271", "Conversation tags, all N turns pooled. Current output."],
   ["chapter_by_grade.csv", "106", "Chapter by grade cross-tab plus tree totals."]],
  [3400, 1100, 4860], { mono: [0], numeric: [1] }),

h1("12.  Next steps"),
bullet(["Get an API key and run tag.py", true], " over this same day, then compare its output against this hand run. That is the cheapest available check on both."),
bullet(["Have a subject expert review a sample", true], ", starting with the conversations where the three grains disagree and with the 55 chapter-level stops."),
bullet(["Take the tree gaps to whoever owns the tree", true], " - Sanskrit and medieval Indian history are absent entirely, and several chapters are missing nodes their own content needs."),
bullet(["Ask engineering to persist a coverage note for image-only turns", true], ", which would close most of the 23.4% blank rate at source."),
bullet(["Decide when a conversation is finished", true], " before running this daily, and allow re-tagging - students return to a thread days later."),

    ],
  }],
});

Packer.toBuffer(doc).then(b => {
  fs.writeFileSync("ShowNAsk_Topic_Tagging_Methodology.docx", b);
  console.log("written", b.length, "bytes");
});
