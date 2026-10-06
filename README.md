# Snap-and-Ask → topic tree

Maps Vedantu Snap-and-Ask (ShowNAsk) tutor-bot conversations onto the Vedantu
topic tree: from a `conversation_id`, through the student behind it, to the exact
topic node they worked on.

The question it answers is **which topics students actually ask about**, at node
level, across all 73 syllabus trees.

## The pipeline

Five stages. Three are model calls; two are ordinary code, and those two are what
make the output trustworthy.

```
ONE USER
  └── many conversation_ids
        └── ONE conversation_id, turns 1..N, all of them

  [0] ASSEMBLE ......... code, no model
        de-duplicate the rolling coverage window, strip reply chips,
        join grade / board / target from the student profile
                 │
  [1] SEGMENT .......... model call 1, once per conversation
        split into the questions the STUDENT asked;
        separate POSED (the ask) from DELIVERED (what the bot did)
                 │
        ┌─── for each question ──────────────────────────────┐
        │  [2] CHAPTER .... model call 2                     │
        │        2,031 subject | chapter rows, cached        │
        │        grade/board/target ORDER the trees,         │
        │        they never cut them                         │
        │                 │                                  │
        │  [3] TOPIC ...... model call 3                     │
        │        that chapter's nodes across every tree      │
        │        that carries it; returns the node ID        │
        └────────────────────────────────────────────────────┘
                 │
  [4] AGGREGATE ........ code, no model
        primary = the chapter holding the most questions;
        every name checked against the tree before it is written
```

## Running it

```bash
python cascade.py --self-check              # the code stages, no API key needed
python cascade.py --dry-run 8d31eff5        # payload + every prompt, calls nothing
python cascade.py --cids out4/sample20.json # a named subset
python cascade.py                           # all of them
```

Provider is one function — set `ANTHROPIC_API_KEY` or `GEMINI_API_KEY`, and
`CASCADE_MODEL` to pick the model. Replies are cached by prompt hash, so a
crashed or rate-limited run resumes instead of paying twice, and `--offline`
writes cache misses to `out4/pending/` so a run can be completed by hand.

Stage 2's 2,031-row catalogue is byte-identical on every call and goes in the
cached prefix; the student's tree preference rides in the variable tail so the
cache still hits.

## Layout

| Path | What it is |
|---|---|
| `cascade.py` | the pipeline, all five stages |
| `trees.py` | parses tree names into a grade band and a family |
| `prompts/` | the three prompts, verbatim, as sent |
| `sql/` | the extraction queries, `01` to `09` (BigQuery) |
| `out3/` | scripts for the earlier one-tag-per-conversation run |
| `out4/` | scripts for the cascade run, the artifacts and the docs |

## Design decisions worth knowing

**Rank, never filter.** The student's grade and board order the candidate trees;
they never limit them. Measured on 241 tagged conversations: filtering to the
student's own trees reaches 191, ranking reaches all 241. 14.5% of students work
outside their own grade.

**The node picks the tree, not the profile.** A chapter can sit in a dozen trees.
Committing to one from the profile put a grade-11 JEE student's class-10 word
problem into `11_12_JEE`, whose Quadratic Equations chapter has no word-problem
node, so it landed on "Miscellaneous examples". Stage 3 now sees the chapter's
nodes across every carrier and the chosen node names the tree.

**Stage 3 returns an ID, not a name.** 52 node rows are duplicated inside 15
chapters; a name alone cannot be resolved.

**No subject loop.** An earlier design put subject before chapter. Dropped: a
wrong subject there is unrecoverable, and conversations crossing a subject are
1 in 226.

**Split, don't summarise.** One conversation is not one question. 43 of 241
cover more than one topic; 12 cross into a second chapter.

**Ask vs. taught.** The student's question and the bot's answer are tagged
separately when they differ. The student's own typed text names subject matter in
only 82 of 271 conversations — the ask usually lives in a photo, and its only
transcript is the bot restating it, so every row records which via `ask_source`.

## Known limits

- **Accuracy has not been measured.** "Tagged" means the tag landed on a real
  node, not the right one. No human-labelled reference set exists yet; a
  60-conversation blind labelling pack is prepared for two subject leads.
- **Tree faults cap accuracy** regardless of the tagger: 209 duplicate chapter
  rows across 14 trees, 52 duplicate node rows, 5 unnamed trees holding 2,202
  nodes, and "Miscellaneous examples" in every subject of `12_Tamilnadu`.
- **The board enum cannot name a state.** It is seven values — CBSE, ICSE, STATE,
  MAHARASHTRA, IB, OTHERS, NA. For 105 of 241 tagged conversations it names no
  tree at all and the CBSE/NCERT backbone carries them.
- **No image signal reaches the segmenter.** `has_image` is computed and then
  dropped, and the image count is per conversation rather than per turn, so a
  silent photo cannot be used as a question boundary.

## What you get on a clone, and what you have to regenerate

The topic tree ships with the repository. The student data does not.

| File | In the repo? | What it is | Regenerate with |
|---|---|---|---|
| `out2/concepts.json` | **yes** | subject + chapter to tree id | `sql/06_catalogue_all_trees.sql` |
| `out2/nodes_by_chapter.json` | **yes** | the nodes inside each chapter | `sql/07_nodes_for_chosen_chapters.sql` |
| `out2/conv_records.json` | no | the conversations themselves | `sql/05_conversation_full_record.sql` |
| `out2/gbt.tsv` | no | conversation to user, grade, board, target | `sql/08_gbt_from_conversation.sql` |

So this works immediately after cloning, with no warehouse access:

```bash
python cascade.py --self-check
```

It loads all 73 trees, 2,031 subject-and-chapter concepts and the node index,
builds the catalogue the prompts are sent with, and exercises the window
de-duplication, the chip stripping, the tree ranking and the validator.

Tagging real conversations needs the other two files. Without them the pipeline
does not crash; it tells you which query produces what is missing. Without
`gbt.tsv` alone it still runs, falling back to the CBSE/NCERT backbone for every
student and saying so.

**Why those two are excluded.** They carry what students typed, what the bot
replied, and 271 user ids. One conversation is a photo of a student's Aadhaar
card. That data stays on the machine that ran the pipeline.
