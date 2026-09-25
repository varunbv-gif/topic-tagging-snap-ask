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
