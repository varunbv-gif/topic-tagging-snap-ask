# Labelling 60 Snap-and-Ask conversations

**Who should do this:** two people who know the Vedantu topic tree — a subject lead, a content
person, anyone who tags questions day to day. Two, working **separately**, not one.

**How long:** about 45 minutes each.

**Why two:** one labeller tells us how often the pipeline agrees with a human. Two tell us how
often *humans agree with each other*, which is the only way to know whether a disagreement means
the pipeline is wrong or the tree is ambiguous. If we can only get one, we still learn something,
just less.

---

## What to do

Open `goldset_blind.csv`. One row per conversation. Fill in four columns and nothing else.

| Column | What to write |
|---|---|
| `your_subject` | Mathematics, Physics, Social Science… |
| `your_chapter` | the chapter name as it appears in the topic tree |
| `your_topic` | the exact topic node inside that chapter |
| `not_on_the_tree_because` | only if it does not belong on the tree at all — see below |
| `your_notes` | optional, anything that made the call hard |

Read the `evidence` column. It holds what the student typed, the bot's own note on what it
taught, and where there is no note, the bot's actual reply. `grade`, `board` and `target` come
from the student's profile.

## The rules the pipeline was given — use the same ones

1. Tag **what was actually taught**, not what the student asked for. The two differ often.
2. The chapter must cover the **bulk** of the conversation, not just its first exchange. Where a
   conversation genuinely spans two chapters, pick the one with more exchanges and say so in
   `your_notes`.
3. The student's grade and board are **context, not a constraint**. Students work above and below
   their own grade all the time. If a grade-8 student is doing De Moivre's theorem, tag De
   Moivre's theorem.
4. Leave `your_topic` **blank** if the chapter is right but no node inside it fits.
5. Fill `not_on_the_tree_because` with one of:
   - `not academic` — chit-chat, app questions, a photo with no question
   - `no chapter covers it` — real academics the tree has no home for; say what it was
   - `nothing to go on` — genuinely illegible

## Please do not

- Look at the other labeller's sheet before you finish yours.
- Look up what the pipeline said. You are the reference, not the reviewer.
- Skip a row because it is hard. A blank row is a lost data point; a hard row with a note in
  `your_notes` is the most valuable row in the sheet.

## Send back

Both filled sheets, named `goldset_A.csv` and `goldset_B.csv`.

---

## What happens next

The sample is deliberately **not representative** — it over-weights the cases the pipeline
already flagged as shaky, so agreement on this set will read *lower* than on the full day. That is
the point: it stresses the weak spots. The scoring reweights back to the real distribution.

Three numbers come out:

- **chapter agreement** — pipeline vs each human, and human vs human
- **topic agreement** — the same, at node level
- **rejection agreement** — did the humans also think the 8 unplaced ones were unplaceable

If human-vs-human on topic is no better than pipeline-vs-human, the topic column is at the limit
of what the tree can express, not a tagging failure — and the honest thing is to report the
pipeline at chapter level and treat the topic as a hint.
