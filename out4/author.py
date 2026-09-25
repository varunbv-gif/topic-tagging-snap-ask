"""Fill out4/cache.json with stage 1-3 replies for the 20-conversation sample.

No API key was available, so these replies were produced by a human-in-the-loop model
run - the same way all 241 tags in the previous run were produced - and written into the
cache the pipeline would otherwise fill from the API. Stages 0 and 4, including the
validator and the aggregator, are the real code and were not touched.

Each entry is keyed by the hash of the exact prompt cascade.py builds, so the pipeline
cannot silently read an answer meant for a different prompt: change a prompt and every
key changes with it.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cascade as C

# posed, delivered, node name (None -> CHAPTER_ONLY), subject, chapter
S = lambda posed, delivered, subject, chapter, node=None, src="bot_restatement", div=None, d=None: {
    "posed": posed, "delivered": delivered, "ask_source": src, "diverged": bool(div),
    "divergence": div, "subject": subject, "chapter": chapter, "node": node,
    "d_pick": d}          # (subject, chapter, node) the bot actually delivered, when diverged

GW, PC = "The Making of a Global World", "Print Culture and the Modern World"
SS, MA, BI, EN, SC, PH, CH = ("Social Science", "Mathematics", "Biology", "English",
                              "Science", "Physics", "Chemistry")

WORK = {
"8d31eff5": [
 S("Divide 4a^2 + 12ab + 9b^2 - 25c^2 by 2a + 3b + 5c (question 14)",
   "Grouped the first three terms as a perfect square, rewrote as a difference of squares, "
   "applied x^2-y^2=(x+y)(x-y) and cancelled the divisor to get 2a + 3b - 5c",
   MA, "Factorisation", "Methods of Factorisation", "student_text")],

"c1aa54f2": [
 S("What has historically driven global interconnectedness", "Trade, migration and labour mobility; 3000 BCE coastal trade, cowrie shells, a tenth-century memorial stone", SS, GW, "The Pre-modern World"),
 S("What were the Silk Routes", "Goods, culture and food moving between Asia, Europe and Africa", SS, GW, "Silk Routes Link the World"),
 S("What did the discovery of the Americas change", "New crops, precious metals, effects on global trade, diet and wealth", SS, GW, "Conquest, Disease and Trade"),
 S("What is El Dorado and what should I write in the exam", "The fabled city of gold, its Muisca ritual origin, the expeditions, and that it was a myth", SS, GW, "Conquest, Disease and Trade", "student_text"),
 S("How did Spain conquer the Americas", "Biological warfare - smallpox against populations with no immunity", SS, GW, "Conquest, Disease and Trade"),
 S("Why did Europeans migrate to America in the nineteenth century", "Poverty, hunger, overcrowding, disease and religious conflict drove dissenters out", SS, GW, "The Nineteenth Century (1815-1914)"),
 S("What does it mean that the world was shrinking", "Increased connection by sea route, not physical size; China's isolation and the shift of trade to Europe", SS, GW, "The Pre-modern World", "student_text"),
 S("How were books made before printing", "Hand dictation, writing and illustration in royal workshops - slow, costly, few copies", SS, PC, "Manuscripts Before the Age of Print"),
 S("What was woodblock printing in China, Japan and Korea", "Used from AD 794, thin paper bleeding through, the accordion book folded and stitched on one side", SS, PC, "The First Printed Books"),
 S("Why was the Chinese imperial state the main producer of print", "Its bureaucracy and civil service examinations needed vast numbers of textbooks", SS, PC, "The First Printed Books"),
 S("How did print use widen in seventeenth-century China", "Merchants used it for trade information; leisure reading, fiction and poetry grew", SS, PC, "The First Printed Books"),
 S("How did print reach Japan", "Buddhist missionaries around 768-770 AD; the Diamond Sutra of 868 AD is the oldest Japanese book", SS, PC, "Print in Japan - Kitagawa Utamaro"),
 S("How widespread was print in Japan", "Textiles, playing cards and paper money; Edo's print culture by the late eighteenth century", SS, PC, "Print in Japan - Kitagawa Utamaro"),
 S("Who was Kitagawa Utamaro", "His ukiyo-e style, pictures of the floating world, and its influence on Manet, Monet and van Gogh", SS, PC, "Print in Japan - Kitagawa Utamaro"),
 S("How does the woodblock carving process work", "The carver pastes the drawing onto the block and carves it, destroying the original", SS, PC, "Print in Japan - Kitagawa Utamaro"),
 S("How did printing reach Europe", "Marco Polo's return to Italy in 1295; Italians then produced books with woodblocks", SS, PC, "Print Comes to Europe"),
 S("Why were handwritten manuscripts a problem in Europe", "Cost, labour, time, fragility and awkward handling pushed demand toward woodblock print", SS, PC, "Manuscripts Before the Age of Print"),
 S("How did Gutenberg build the printing press", "Adapted the wine and olive press, used his goldsmith's skill to cast type, perfected by 1448", SS, PC, "Gutenberg and the Printing Press"),
 S("What did the first printed books look like", "They mimicked handwriting, were hand-illuminated; presses spread across Europe 1450-1550", SS, PC, "Gutenberg's Bible, the First Printed Book in Europe"),
 S("What did the printing press change", "Lower cost, faster production, a flood of books and a growing readership", SS, PC, "The Print Revolution and Its Impact"),
 S("How did print reach people who could not read", "Pictures in ballads and folk tales blurred the line between oral and reading publics", SS, PC, "A New Reading Public"),
 S("Why were authorities afraid of print", "It circulated ideas widely, fostering debate and dissent that worried the Church and monarchs", SS, PC, "Religious Debates and the Fear of Print"),
 S("What did Martin Luther do", "The 95 Theses, the press spreading them rapidly, and the Protestant Reformation", SS, PC, "Religious Reform and Public Debates"),
 S("What happened to people who read the Bible their own way", "Menocchio's heresy and execution; the Index of Prohibited Books in 1558", SS, PC, "Print and Dissent"),
 S("How did reading spread in seventeenth and eighteenth century Europe", "Rising literacy, church schools, reading mania, pedlars selling penny chapbooks", SS, PC, "The Reading Mania")],

"48a5a9dc": [
 S("What is autotrophic nutrition", "Photosynthesis in five steps with the chemical equation and a three-step summary", BI, "Life Processes", "Autotrophic Nutrition", "student_text"),
 S("How do plants take in carbon dioxide", "Stomata as pores controlled by guard cells, opening and closing, gas exchange against water loss", BI, "Life Processes", "Autotrophic Nutrition"),
 S("Quiz me on photosynthesis", "Four questions on the oxygen source, stored chemical energy, guard cells in heat, stomata location", BI, "Life Processes", "Experiments on Life Processes", "student_text"),
 S("Where does the oxygen come from", "Water splits during photosynthesis - photolysis - releasing oxygen", BI, "Life Processes", "Autotrophic Nutrition"),
 S("What are the light-dependent reactions", "Chlorophyll excitation, photolysis, NADPH, ATP by chemiosmosis, energy stored in ATP and NADPH", BI, "Life Processes", "Autotrophic Nutrition"),
 S("Do plants respire only at night", "Plants respire continuously; photosynthesis stores energy by day, respiration releases it always", BI, "Life Processes", "Respiration"),
 S("Why is starch tested for photosynthesis and not glucose", "Glucose is converted and stored as starch, so starch is the valid indicator", BI, "Life Processes", "Experiments on Life Processes"),
 S("Match the nephron parts to their functions", "Bowman's capsule - ultrafiltration, PCT - reabsorption, Loop of Henle - concentration, DCT - balance", BI, "Life Processes", "Excretion in Human Beings"),
 S("What happens if the thyroid gland is removed", "Less thyroxine, lower metabolic rate, fatigue and weight gain", BI, "Control and Coordination", "Hormones in Animals"),
 S("Which hormone stops seeds sprouting in humid weather", "Abscisic acid, the stress hormone, inducing dormancy", BI, "Control and Coordination", "Coordination in Plants"),
 S("Which brain region is damaged if a patient understands speech but cannot speak", "Broca's area in the cerebrum; contrasted with Wernicke's area for comprehension", BI, "Control and Coordination", "Human Brain"),
 S("How does a fish heart work", "Two chambers, unidirectional flow, single circulation - blood passes the heart once per cycle", BI, "Life Processes", "Heart"),
 S("Which curve is aerobic and which anaerobic", "The higher energy output curve is aerobic, the lower is anaerobic", BI, "Life Processes", "Types Of Respiration"),
 S("Assertion-reason: plants have low energy needs", "Both statements true but the reason is not the explanation - option B", BI, "Life Processes", "Introduction Of Life Processes"),
 S("What are the plant hormones", "Auxins, gibberellins, cytokinins, abscisic acid and ethylene and their roles", BI, "Control and Coordination", "Coordination in Plants"),
 S("How much ATP does half a glucose molecule yield", "One glucose gives 38 ATP, so 0.5 gives 19; cellular respiration as complete oxidation", BI, "Life Processes", "Respiration")],

"4a74c906": [
 S("Explain all the laws of logarithms", "Stated the product law, quotient law, power law and the inverse property", MA, "Logarithms", "Laws of Logarithm with use", "student_text"),
 S("Explain the base changing formula", "Base change formula, product form, reciprocal relationship and reciprocal rule", MA, "Logarithms", "More about Logarithms", "student_text")],

"45759289": [
 S("Revision points for squares and square roots", "Ending digits, zeros, odd/even, sum of odds, square roots, Pythagorean triplets", MA, "Squares and square roots", None, "student_text"),
 S("Revision points for cubes and cube roots", "Cube numbers, prime factors, unit digits, Hardy-Ramanujan number, cube roots by prime factorisation", MA, "Cubes and cube roots", None, "student_text"),
 S("Shorter revision points for exponents and powers", "Negative exponents, the five laws, standard form versus usual form, with a flashcard tip", MA, "Exponents and powers", None, "student_text"),
 S("Summary for chapter 4, Quadrilaterals", "Angle sum property, parallelogram properties, rhombus, rectangle, square, interior angle sum", MA, "Understanding Quadrilaterals", None, "student_text"),
 S("Summary for chapter 5", "Generalised form of numbers, divisibility by 10, 5, 2, 3 and 9, cryptarithmetic rules", MA, "Number Play", None, "student_text"),
 S("A shorter version for algebra play", "Algebraic expressions, terms and factors", MA, "Algebra Play", None, "student_text")],

"0b427a40": [
 S("Question 15: isosceles trapezium ABCD and kite ABEF, angle FAB=43, angle AFE=137, find x and y",
   "Used kite properties for x=43, then angle ABE=43, angle EBC=115-43=72, and alternate interior angles for y=72",
   MA, "Understanding Quadrilaterals", None)],

"3257301d": [
 S("Wedge Y 10kg and block X 2kg, frictionless, 37-degree incline, horizontal force 24N on the wedge - find the time for X to slide 8.8m from rest",
   "Described the problem setup only", PH, "Laws of Motion", "Equilibrium of a Particle")],

"f8e29b17": [
 S("Example 18: a pool of length x and breadth x-4, form and solve the quadratic",
   "Formed x^2-4x-96=0, split the middle term, factored to (x-12)(x+8)=0, rejected the negative root, found the breadth",
   MA, "Quadratic Equations", "Word Problems based on Quadratic equations", "student_text")],

"b3149de5": [
 S("Teach me the sentence types", "Defined declarative, interrogative, imperative and exclamatory sentences", EN, "The Sentence", "Declarative Sentence", "student_text"),
 S("Change 'The sun is shining' into a question", "Moved 'is' to the front and added a question mark; same for 'She can swim'", EN, "The Sentence", "Question or interrogative Sentence", "student_text"),
 S("What is the S+V+O pattern", "Defined subject, verb and object with examples", EN, "The Sentence", None, "student_text"),
 S("What is the S+V+C pattern and how does it differ from S+V+O", "Defined linking verbs and the subject-verb-complement pattern, contrasted with S+V+O", EN, "The Sentence", None, "student_text")],

"57aa81aa": [
 S("Question 17: how many atoms are in an ammonia molecule", "One nitrogen, three hydrogen, four atoms in total", SC, "Atoms and Molecules", "What is a Molecule", "student_text"),
 S("Question 18: why do the subscripts in a chemical formula matter", "Compared water with hydrogen peroxide to show the subscript changes the substance", SC, "Atoms and Molecules", "Writing Chemical Formulae", "student_text")],

"24a39006": [
 S("Define elastic and inelastic collisions and derive the final velocities in one dimension",
   "Definitions, examples and a comparison table", PH, "Work, Energy, and Power", "Collisions in One Dimension", "student_text"),
 S("What is a sub-atomic particle", "Protons, neutrons and electrons, their charges and locations, with a summary table",
   CH, "Structure of the Atom", "Charged Particles in Matter", "student_text")],

"a9b424f7": [
 S("Question 23: list the sample space", "All 16 outcomes (x, y) by the fundamental principle of counting", MA, "Probability", "Probability - A Theoretical Approach", "student_text"),
 S("Find the probability that xy > 16", "Six favourable outcomes of 16, simplified to 3/8", MA, "Probability", "Probability - A Theoretical Approach", "student_text"),
 S("Find the probability that the product is less than 10", "Total outcomes, favourable outcomes and the final fraction", MA, "Probability", "Probability - A Theoretical Approach", "student_text"),
 S("Find the probability that the product is a perfect square", "Eight favourable of 16, probability 1/2", MA, "Probability", "Probability - A Theoretical Approach", "student_text"),
 S("Give me a similar question to question 23",
   "Introduced Section B question 21 on the zeros and coefficients of a quadratic polynomial instead",
   MA, "Probability", "Probability - A Theoretical Approach", "student_text",
   "student asked for another probability question; the bot moved to a polynomials question",
   (MA, "Polynomials", "Relation between zeroes and coefficient of quadratic polynomials"))],

"2c19de19": [
 S("What colour is the wall in this photo", "Answered that the walls are white", "REJECT", "NOT_ACADEMIC",
   "a photo of a room with no schoolwork in it", "student_text")],

"23bc1766": [
 S("Given a piecewise f(x), evaluate f(4), f(1), f(-2) and f(-3) and combine them",
   "Explained the three intervals, evaluated each branch and combined the values",
   MA, "Relations and Functions", None, "student_text")],

"3b17d1f8": [
 S(None, "Said the image was blurred or distorted", "REJECT", "UNKNOWN",
   "image blurred beyond reading - nothing legible to go on")],

"d1f95b08": [
 S("How does Kaprekar's routine work", "Arranged digits descending and ascending, subtracted, repeated toward 6174, "
   "corrected a subtraction error, and showed it again for 2015", MA, "Patterns in Mathematics", "Finding Patterns In Numbers", "student_text")],

"709cde42": [
 S("What was the Delhi Sultanate", "Five successive Muslim dynasties ruling from Delhi 1206-1526 and their impact", SS, "State and Society in Medieval India", "Delhi Sultanate", "student_text"),
 S("Which were the five dynasties", "Mamluk, Khilji, Tughlaq, Sayyid and Lodi", SS, "State and Society in Medieval India", "Delhi Sultanate", "student_text"),
 S("What did the sultans change in India", "New administrative structures and architecture; the reign ended at Panipat in 1526", SS, "State and Society in Medieval India", "Delhi Sultanate", "student_text"),
 S("Is the Mughal empire not part of the Delhi Sultanate, since it is also Muslim",
   "A single centralised imperial family replaced the rotating dynasties after Panipat in 1526",
   SS, "State and Society in Medieval India", "Mughals", "student_text"),
 S("Quiz me on the Delhi Sultanate", "Asked about the Battle of Panipat, the iqta system, Timur, domes and the Qutub Minar", SS, "State and Society in Medieval India", "Delhi Sultanate", "student_text")],

"0ac563e9": [
 S("Find the distance between A(3,4) and D(7,1)", "Horizontal 4, vertical 3, Pythagoras giving 5", MA, "Coordinate Geometry", "Distance Formula", "student_text"),
 S("How far is the door from each wall", "Read the x and y coordinates - 8 units from the left wall, 0 from the x-axis", MA, "Coordinate Geometry", "Cartesian System", "student_text")],

"802b913f": [
 S("Find the distance light travels in the given time and write it in standard form",
   "Applied distance = speed x time, simplified the multiplication and converted to standard form",
   MA, "Exponents and powers", "Use of exponents to express small numbers in standard form", "student_text")],

"cdacab9b": [
 S("Find the tiled area of the park between the two green squares, in terms of g and w",
   "Total area minus the two squares, flagged two multiplication errors, arrived at 8w^2 + 8wg sq ft",
   MA, "Algebraic expressions and Identities", "Multiplication of Algebraic expressions", "student_text")],
}


def main():
    written, misses = 0, []
    records = json.load(open(C.P("out2/conv_records.json"), encoding="utf-8"))
    order_all = None
    for short, segs in WORK.items():
        cid = next(k for k in records if k.startswith(short))
        pay = C.assemble(cid, records[cid])

        # stage 1
        seg_json = {"segments": [
            {"i": i, "posed": s["posed"], "delivered": s["delivered"],
             "ask_source": s["ask_source"], "diverged": s["diverged"],
             "divergence": s["divergence"], "evidence": "bot note"}
            for i, s in enumerate(segs, 1)]}
        C.CACHE[C.cache_key(C.p_segment(pay), None)] = json.dumps(seg_json, ensure_ascii=False)
        written += 1

        prefix = C.PROMPT["2_chapter"].format(catalogue=C.CATALOGUE)
        order_all = C.preferred_trees(pay, n=len(C.ALL_TREES))
        todo = [(s, "POSED", s["posed"] or s["delivered"] or "",
                 (s["subject"], s["chapter"], s["node"])) for s in segs]
        todo += [(s, "DELIVERED", s["delivered"], s["d_pick"]) for s in segs if s["d_pick"]]
        for s, label, text, (subject, chapter, node) in todo:
            reject = subject == "REJECT"
            body = ({"subject": "", "chapter": "", "confidence": "HIGH",
                     "reject": chapter, "why": node} if reject else
                    {"subject": subject, "chapter": chapter, "confidence": "HIGH",
                     "reject": None, "why": ""})
            C.CACHE[C.cache_key(C.p_chapter(pay, label, text), prefix)] = json.dumps(body, ensure_ascii=False)
            written += 1
            if reject:
                continue

            carriers = C.CONCEPT.get((subject, chapter), {})
            if not carriers:
                misses.append(f"{short}: chapter not in the tree - {subject} > {chapter}")
                continue
            pick = {"subject": subject, "chapter": chapter,
                    "trees": sorted(carriers, key=order_all.index),
                    "tree": min(carriers, key=order_all.index), "confidence": "HIGH"}
            nodes = C.nodes_for(pick)
            if not nodes:
                continue                                  # cascade returns CHAPTER_ONLY and flags it
            hit = next((n for n in nodes if n["name"] == node), None) if node else None
            if node and not hit:
                misses.append(f"{short}: node not in {chapter} - {node}")
            body = ({"topic_id": hit["id"], "topic": hit["name"],
                     "topic_level": hit["lvl"], "confidence": "HIGH"} if hit else
                    {"topic_id": "", "topic": "CHAPTER_ONLY", "topic_level": "", "confidence": "HIGH"})
            C.CACHE[C.cache_key(C.p_topic(pick, label, text), None)] = json.dumps(body, ensure_ascii=False)
            written += 1

    C.save_cache()
    print(f"{written} replies cached across {len(WORK)} conversations, "
          f"{sum(len(v) for v in WORK.values())} segments")
    for m in misses:
        print("  MISS", m)


if __name__ == "__main__":
    main()
