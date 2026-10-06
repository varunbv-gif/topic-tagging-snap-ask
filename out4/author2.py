"""Fill out4/cache.json for the four-call pipeline, on the 20-conversation sample.

No API key was available, so the four model calls were answered by a human following
the prompts in prompts/, and written into the cache the pipeline would otherwise fill
from the API. Stages 0 and 5 - assembly, validation, the row writer - are the real
code and were not touched.

Answers are keyed by the hash of the exact prompt cascade.py builds, and each call's
prompt is built from the previous call's answer, so the chain cannot be faked out of
order: change a prompt and every key downstream changes with it.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cascade as C

MA, SS, BI, PH, CH, EN, SC = ("Mathematics", "Social Science", "Biology", "Physics",
                              "Chemistry", "English", "Science")
GW, PC = "The Making of a Global World", "Print Culture and the Modern World"


def s(what, detail, aot="taught", weight="some"):
    return {"what": what, "detail": detail, "asked_or_taught": aot, "weight": weight}


# summary, then subjects, then chapters, then topics - one entry per conversation
WORK = {
"8d31eff5": {
 "summary": {
  "overview": "A class-8 ICSE student photographed question 14 from a factorisation "
              "exercise and worked through it with the bot. One problem throughout: "
              "dividing a four-term expression by a trinomial using algebraic identities "
              "rather than long division. The student asked a follow-up about one term "
              "and then proposed a wrong answer, which the bot corrected.",
  "covered": [s("Divided 4a^2 + 12ab + 9b^2 - 25c^2 by 2a + 3b + 5c by factorising the "
                "dividend instead of doing long division",
                "grouped the first three terms as (2a+3b)^2, rewrote as (2a+3b)^2 - (5c)^2, "
                "applied x^2 - y^2 = (x+y)(x-y) to get (2a+3b+5c)(2a+3b-5c), cancelled the "
                "divisor, quotient 2a+3b-5c", "both", "most")],
  "level": "class 8 ICSE factorisation using standard identities",
  "ask_source": "student_text", "not_academic": None,
  "notes": "The student stated the answer was 2A+3B+5C; the bot pointed out that is the "
           "divisor, not the quotient."},
 "subjects": [MA], "chapters": [(MA, "Factorisation")],
 "topics": [("Factorisation", "Methods of Factorisation")]},

"4a74c906": {
 "summary": {
  "overview": "A class-9 ICSE student sent one photo of a page of logarithm laws and asked "
              "for all of them to be explained. One turn, but the bot covered two distinct "
              "areas: the standard laws of logarithms, and the base-change relationships.",
  "covered": [s("Stated and explained the laws of logarithms",
                "product law, quotient law, power law, inverse property", "both", "most"),
              s("Explained changing the base of a logarithm",
                "base changing formula, product form, reciprocal relationship, reciprocal rule",
                "taught", "some")],
  "level": "class 9 ICSE logarithms",
  "ask_source": "student_text", "not_academic": None,
  "notes": "A single photo and a single turn, but two separate groups of results - the laws "
           "themselves and the base-change family."},
 "subjects": [MA], "chapters": [(MA, "Logarithms")],
 "topics": [("Logarithms", "Laws of Logarithm with use"),
            ("Logarithms", "More about Logarithms")]},

"57aa81aa": {
 "summary": {
  "overview": "A class-7 student asked for help with questions 17 and 18 from a chemistry "
              "worksheet. Two separate questions from the same page: counting atoms in a "
              "molecule, and why subscripts in a chemical formula matter.",
  "covered": [s("Counted the atoms in an ammonia molecule",
                "NH3: one nitrogen, three hydrogen, four atoms in total", "both", "some"),
              s("Explained what the subscripts in a chemical formula mean",
                "contrasted water H2O with hydrogen peroxide H2O2 to show the subscript "
                "changes the substance", "both", "some")],
  "level": "class 9 level atoms and molecules, asked by a class-7 student",
  "ask_source": "student_text", "not_academic": None, "notes": None},
 "subjects": [SC], "chapters": [(SC, "Atoms and Molecules")],
 "topics": [("Atoms and Molecules", "What is a Molecule"),
            ("Atoms and Molecules", "Writing Chemical Formulae")]},

"c1aa54f2": {
 "summary": {
  "overview": "A class-10 CBSE student revising the night before a history exam, over forty "
              "exchanges. It spans two separate chapters of the syllabus: the first third "
              "covers global trade and the pre-modern world, and the remaining two thirds "
              "cover the history of printing from woodblock in Asia through Gutenberg to "
              "the reading mania in Europe. The student also read passages back in their own "
              "words and asked what to write in the exam.",
  "covered": [
   s("What drove global interconnectedness before the modern era",
     "trade, migration and labour mobility; 3000 BCE coastal trade; cowrie shells as "
     "currency; a tenth-century memorial stone showing ships", "both", "some"),
   s("The Silk Routes", "goods (pottery, textiles, spices, metals), culture (missionaries, "
     "Buddhism), food (noodles, potatoes, soya, groundnuts, maize, tomatoes, chillies) "
     "moving between Asia, Europe and Africa", "both", "some"),
   s("What the discovery of the Americas changed",
     "new crops, precious metals, effects on global trade, diet and wealth", "taught"),
   s("El Dorado and what to write about it in an exam",
     "the fabled city of gold, its origin in a Muisca ritual, 16th-century expeditions, "
     "and that it was a myth", "both", "some"),
   s("How Spain conquered the Americas",
     "biological warfare - smallpox against populations with no immunity", "taught"),
   s("Why Europeans migrated to America in the nineteenth century",
     "poverty, hunger, overcrowding, disease and religious conflict", "taught"),
   s("What 'the world shrinking' means",
     "increased connection by sea route, not physical size; China's isolation; the westward "
     "shift of global trade from China and India to Europe", "both", "some"),
   s("How books were made before printing",
     "hand dictation, writing and illustration in royal workshops; slow, costly, few copies",
     "taught"),
   s("Woodblock printing in China, Japan and Korea",
     "used from AD 794; thin paper bleeding through; the accordion book folded and stitched "
     "on one side", "taught"),
   s("Why the Chinese imperial state was the main producer of print",
     "its bureaucracy and civil service examinations needed vast numbers of textbooks",
     "taught"),
   s("How print use widened in seventeenth-century China",
     "merchants using it for trade information; leisure reading, fiction and poetry", "taught"),
   s("How print reached Japan",
     "Buddhist missionaries around 768-770 AD; the Diamond Sutra of 868 AD as the oldest "
     "Japanese book", "taught"),
   s("How widespread print became in Japan",
     "textiles, playing cards and paper money; Edo's print culture by the late eighteenth "
     "century", "taught"),
   s("Kitagawa Utamaro and ukiyo-e",
     "'pictures of the floating world'; influence on Manet, Monet and van Gogh", "taught"),
   s("The woodblock carving process",
     "the carver pastes the drawing onto the block and carves it, destroying the original",
     "taught"),
   s("How printing reached Europe",
     "Marco Polo's return to Italy in 1295; Italians then producing books with woodblocks",
     "taught"),
   s("Why handwritten manuscripts were a problem in Europe",
     "cost, labour, time, fragility and awkward handling", "taught"),
   s("Gutenberg and the printing press",
     "adapted from the wine and olive press; his goldsmith's skill used to cast type; the "
     "system perfected by 1448; the Bible printed", "both", "some"),
   s("What the first printed books looked like",
     "they mimicked handwriting and were hand-illuminated; presses spread across Europe "
     "1450-1550", "taught"),
   s("What the printing press changed",
     "lower cost, faster production, a flood of books, a growing readership", "both"),
   s("How print reached people who could not read",
     "pictures in ballads and folk tales blurring the line between oral and reading publics",
     "taught"),
   s("Why authorities feared print",
     "it circulated ideas widely, fostering debate and dissent that worried the Church and "
     "monarchs", "taught"),
   s("Martin Luther and the Reformation",
     "the 95 Theses; the press spreading them rapidly; the Protestant Reformation", "taught"),
   s("Menocchio and the Index of Prohibited Books",
     "individual interpretation of the Bible, his heresy and execution; the Index in 1558",
     "taught"),
   s("How reading spread in seventeenth and eighteenth century Europe",
     "rising literacy, church-sponsored schools, 'reading mania', pedlars selling penny "
     "chapbooks", "taught")],
  "level": "class 10 CBSE history, two full chapters",
  "ask_source": "student_text", "not_academic": None,
  "notes": "Two chapters, not one. Roughly a third of the conversation is The Making of a "
           "Global World and the remaining two thirds is Print Culture and the Modern World, "
           "so Print Culture is the larger of the two."},
 "subjects": [SS],
 "chapters": [(SS, PC), (SS, GW)],
 "topics": [(PC, "Manuscripts Before the Age of Print"), (PC, "The First Printed Books"),
            (PC, "Print in Japan - Kitagawa Utamaro"), (PC, "Print Comes to Europe"),
            (PC, "Gutenberg and the Printing Press"),
            (PC, "Gutenberg's Bible, the First Printed Book in Europe"),
            (PC, "The Print Revolution and Its Impact"), (PC, "A New Reading Public"),
            (PC, "Religious Debates and the Fear of Print"),
            (PC, "Religious Reform and Public Debates"), (PC, "Print and Dissent"),
            (PC, "The Reading Mania"),
            (GW, "The Pre-modern World"), (GW, "Silk Routes Link the World"),
            (GW, "Conquest, Disease and Trade"), (GW, "The Nineteenth Century (1815-1914)")]},

"48a5a9dc": {
 "summary": {
  "overview": "A class-10 CBSE student working through a biology revision set over forty-one "
              "exchanges, mixing teaching with quiz questions. Most of it is Life Processes - "
              "nutrition, photosynthesis, respiration, transport and excretion - with a "
              "distinct run of questions on Control and Coordination covering hormones and "
              "the brain.",
  "covered": [
   s("Autotrophic nutrition and photosynthesis",
     "five steps with the chemical equation; a three-step summary", "both", "most"),
   s("How plants take in carbon dioxide",
     "stomata as pores controlled by guard cells; opening and closing; gas exchange against "
     "water loss; guard cell turgidity", "both"),
   s("Where the oxygen released in photosynthesis comes from",
     "photolysis - water splitting during the light reaction", "both"),
   s("The light-dependent reactions",
     "chlorophyll excitation, photolysis, NADPH production, ATP by chemiosmosis", "taught"),
   s("Whether plants respire only at night",
     "plants respire continuously; photosynthesis stores energy by day, respiration releases "
     "it always", "both"),
   s("Why starch and not glucose is tested for photosynthesis",
     "glucose is converted and stored as starch, so starch is the valid indicator", "both"),
   s("The parts of the nephron and what each does",
     "Bowman's capsule - ultrafiltration; PCT - glucose and amino acid reabsorption; Loop of "
     "Henle - concentration; distal tubule - blood balance", "both"),
   s("What happens when the thyroid gland is removed",
     "less thyroxine, lower metabolic rate, fatigue and weight gain", "both"),
   s("Which hormone stops seeds sprouting in humid weather",
     "abscisic acid, the stress hormone, inducing dormancy", "both"),
   s("Which brain region is damaged when a patient understands speech but cannot speak",
     "Broca's area in the cerebrum's frontal lobe; contrasted with Wernicke's area in the "
     "temporal lobe for comprehension", "both", "some"),
   s("How the fish heart works",
     "two chambers, unidirectional flow, single circulation - blood passes the heart once "
     "per cycle", "both"),
   s("Distinguishing aerobic from anaerobic respiration on an energy graph",
     "the higher energy output curve is aerobic, the lower anaerobic", "both"),
   s("An assertion-reason question on why plants have low energy needs",
     "both statements true but the reason is not the explanation", "both"),
   s("The plant hormones and their roles",
     "auxins, gibberellins, cytokinins, abscisic acid, ethylene; cell elongation, division, "
     "internode elongation, seed dormancy", "taught"),
   s("ATP yield from glucose",
     "one glucose gives 38 ATP, so 0.5 gives 19", "both"),
   s("Cellular respiration as a process",
     "breaking down glucose C6H12O6 by complete oxidation to release ATP", "taught")],
  "level": "class 10 CBSE biology board revision",
  "ask_source": "student_text", "not_academic": None,
  "notes": "Two chapters. Life Processes dominates; four of the questions - thyroxine, "
           "abscisic acid, Broca's area and the plant hormones - belong to Control and "
           "Coordination. The student also repeatedly asked the bot to stop using Hindi."},
 "subjects": [BI],
 "chapters": [(BI, "Life Processes"), (BI, "Control and Coordination")],
 "topics": [("Life Processes", "Autotrophic Nutrition"),
            ("Life Processes", "Experiments on Life Processes"),
            ("Life Processes", "Respiration"),
            ("Life Processes", "Types Of Respiration"),
            ("Life Processes", "Excretion in Human Beings"),
            ("Life Processes", "Heart"),
            ("Life Processes", "Introduction Of Life Processes"),
            ("Control and Coordination", "Hormones in Animals"),
            ("Control and Coordination", "Coordination in Plants"),
            ("Control and Coordination", "Human Brain")]},

"45759289": {
 "summary": {
  "overview": "A class-8 CBSE student asked for revision points for an SA-1 exam and then "
              "worked chapter by chapter through most of the syllabus, repeatedly asking for "
              "shorter, flashcard-style versions. Six distinct chapters were covered, none "
              "in depth - this is a revision sweep, not a worked problem.",
  "covered": [
   s("Revision points on squares and square roots",
     "ending digits, trailing zeros, odd and even squares, sum of odd numbers, square roots, "
     "Pythagorean triplets", "both", "some"),
   s("Revision points on cubes and cube roots",
     "prime factors, unit digits, the Hardy-Ramanujan number 1729, cube roots by prime "
     "factorisation and estimation", "both", "some"),
   s("Revision points on exponents and powers",
     "negative exponents; product, quotient, power-of-power, power-of-product and zero "
     "exponent laws; standard form against usual form", "both", "some"),
   s("Revision points on quadrilaterals",
     "angle sum property, parallelogram properties, rhombus, rectangle, square, sum of "
     "interior angles", "both", "some"),
   s("Revision points on playing with numbers",
     "generalised form of numbers, divisibility tests by 10, 5, 2, 3 and 9, cryptarithms",
     "both", "some"),
   s("Revision points on algebraic expressions",
     "expressions, terms and factors", "both", "little")],
  "level": "class 8 CBSE, SA-1 revision across the syllabus",
  "ask_source": "student_text", "not_academic": None,
  "notes": "Six chapters at summary depth. No single chapter dominates, so any primary tag "
           "is somewhat arbitrary; the chapter list matters more than the first entry."},
 "subjects": [MA],
 "chapters": [(MA, "Squares and square roots"), (MA, "Cubes and cube roots"),
              (MA, "Exponents and powers"), (MA, "Understanding Quadrilaterals"),
              (MA, "Number Play"), (MA, "Algebra Play")],
 "topics": [("Exponents and powers", "Use of exponents to express small numbers in standard form"),
            ("Understanding Quadrilaterals", "Introduction-Understanding Quadrilaterals")]},

"0b427a40": {
 "summary": {
  "overview": "A student sent a photo of question 15 from a geometry exercise: a figure with "
              "an isosceles trapezium and a kite sharing an edge, with two angles given and "
              "two unknowns to find. The student typed almost nothing legible; the bot "
              "restated the problem and solved it.",
  "covered": [s("Found the unknown angles x and y in a figure combining an isosceles "
                "trapezium ABCD with a kite ABEF",
                "given angle FAB = 43 and angle AFE = 137; kite property angle FAB = angle "
                "FEB gives x = 43; angle ABE = 43, angle ABC = 115 so angle EBC = 72; "
                "AB parallel to DC makes y and EBC alternate interior angles, y = 72",
                "both", "most")],
  "level": "class 8 level quadrilateral angle properties",
  "ask_source": "bot_restatement", "not_academic": None,
  "notes": "The student's only typed text was 'Proceedings are quite as.', which appears to "
           "be a transcription error and carries no topic signal. The whole question comes "
           "from the bot restating the photo."},
 "subjects": [MA], "chapters": [(MA, "Understanding Quadrilaterals")],
 "topics": [("Understanding Quadrilaterals", None)]},

"3257301d": {
 "summary": {
  "overview": "A class-11 CBSE student preparing for JEE sent one photo of a mechanics "
              "problem and nothing else. The bot restated the setup in full but the "
              "conversation ended before the solution was worked through.",
  "covered": [s("A wedge-and-block problem: find the time for the block to slide a given "
                "distance down the moving wedge",
                "wedge Y 10 kg, block X 2 kg, all surfaces frictionless, incline 37 degrees, "
                "constant horizontal force f = 24 N on the wedge, block slides 8.8 m from "
                "rest, tan 37 = 3/4, g = 10 m/s^2", "asked", "most")],
  "level": "class 11 JEE-style mechanics on a non-inertial frame",
  "ask_source": "bot_restatement", "not_academic": None,
  "notes": "The bot described the problem setup only - no solution was delivered, so the "
           "record is of what was asked rather than what was taught."},
 "subjects": [PH], "chapters": [(PH, "Laws of Motion")],
 "topics": [("Laws of Motion", "Equilibrium of a Particle")]},

"f8e29b17": {
 "summary": {
  "overview": "A class-11 CBSE student preparing for JEE asked about Example 18 from a "
              "textbook and then about a step they could not follow. One word problem "
              "throughout: forming and solving a quadratic for the dimensions of a pool.",
  "covered": [s("Formed and solved a quadratic for the dimensions of a rectangular pool",
                "length x, breadth x - 4; equation x^2 - 4x - 96 = 0; split the middle term, "
                "grouped, factored to (x-12)(x+8) = 0; rejected the negative root because a "
                "length must be positive; found the breadth", "both", "most")],
  "level": "class 10 level quadratic word problem, asked by a class-11 student",
  "ask_source": "student_text", "not_academic": None,
  "notes": "The content is class-10 board material even though the student is class 11 "
           "preparing for JEE."},
 "subjects": [MA], "chapters": [(MA, "Quadratic Equations")],
 "topics": [("Quadratic Equations", "Word Problems based on Quadratic equations")]},

"b3149de5": {
 "summary": {
  "overview": "A class-8 student said they were a beginner and asked to be taught sentence "
              "types, then worked through twenty-two exchanges of definitions, "
              "transformations and sentence-pattern analysis with the bot quizzing them.",
  "covered": [
   s("The four sentence types",
     "declarative, interrogative, imperative, exclamatory, with definitions", "both", "most"),
   s("Turning statements into questions",
     "'The sun is shining' to 'Is the sun shining?' by fronting 'is'; 'She can swim' to "
     "'Can she swim?' by fronting the modal", "both", "some"),
   s("The subject-verb-object pattern",
     "S + V + O; subject, verb and object identified in 'The chef cooked a delicious meal'",
     "both", "some"),
   s("The subject-verb-complement pattern",
     "S + V + C; linking verbs; contrasted with S + V + O", "both", "some")],
  "level": "class 8 English grammar, sentence types and patterns",
  "ask_source": "student_text", "not_academic": None,
  "notes": "The last two - S+V+O and S+V+C sentence patterns - are not the same thing as "
           "sentence type, and may not have a matching node."},
 "subjects": [EN], "chapters": [(EN, "The Sentence")],
 "topics": [("The Sentence", "Declarative Sentence"),
            ("The Sentence", "Question or interrogative Sentence")]},

"24a39006": {
 "summary": {
  "overview": "A class-11 student preparing for JEE asked two unrelated questions in one "
              "conversation, repeatedly asking for them in different character voices. One "
              "is a physics derivation on collisions, the other a chemistry question on the "
              "structure of the atom.",
  "covered": [
   s("Defined elastic and inelastic collisions and derived the final velocities in one "
     "dimension", "definitions, examples and a comparison table", "both", "some"),
   s("The three sub-atomic particles",
     "protons positive and in the nucleus, defining atomic number; neutrons neutral and in "
     "the nucleus; electrons negative and in orbits outside; summary table of symbol, charge "
     "and location", "both", "some")],
  "level": "class 11 physics and class 9 chemistry in one conversation",
  "ask_source": "student_text", "not_academic": None,
  "notes": "Two different subjects' material in one conversation - mechanics and atomic "
           "structure. The voice requests ('pushpa voice', 'cartoon voice') are format, not "
           "content."},
 "subjects": [PH, CH],
 "chapters": [(PH, "Work, Energy, and Power"), (CH, "Structure of the Atom")],
 "topics": [("Work, Energy, and Power", "Collisions in One Dimension"),
            ("Structure of the Atom", "Charged Particles in Matter")]},

"a9b424f7": {
 "summary": {
  "overview": "A class-10 CBSE student asked for question 23 to be explained and solved, a "
              "probability question with several parts over a 4x4 outcome space. The bot "
              "worked each part, and when the student asked for a similar question it "
              "introduced a polynomials question instead.",
  "covered": [
   s("Listed the sample space for the probability question",
     "all 16 outcomes (x, y) by the fundamental principle of counting", "both", "some"),
   s("Found the probability that the product xy is greater than 16",
     "6 favourable of 16, simplified to 3/8", "both", "some"),
   s("Found the probability that the product is less than 10",
     "total and favourable outcomes, then the fraction", "both", "some"),
   s("Found the probability that the product is a perfect square",
     "8 favourable of 16, probability 1/2", "both", "some")],
  "level": "class 10 CBSE probability, theoretical approach",
  "ask_source": "student_text", "not_academic": None,
  "notes": "The student asked for another probability question; the bot instead introduced "
           "Section B question 21 on the zeros and coefficients of a quadratic polynomial. "
           "That is the bot changing topic, not the student asking about polynomials."},
 "subjects": [MA], "chapters": [(MA, "Probability")],
 "topics": [("Probability", "Probability - A Theoretical Approach")]},

"2c19de19": {
 "summary": {
  "overview": "The student sent a photo of a room and asked what colour the wall is. The bot "
              "answered that the walls are white. No schoolwork of any kind.",
  "covered": [], "level": None, "ask_source": "student_text",
  "not_academic": "photo with no schoolwork", "notes": None},
 "subjects": [], "chapters": [], "topics": []},

"23bc1766": {
 "summary": {
  "overview": "A class-10 state-board student worked through a piecewise function question "
              "with the bot across nine exchanges, evaluating the function on each of its "
              "branches and then combining the values. Part of the conversation was in Tamil "
              "at the student's request.",
  "covered": [s("Evaluated a piecewise-defined function on each branch and combined the "
                "results",
                "f(x) = 2x+7 for x < -2, x^2-2 for -2 <= x < 3, 3x-2 for x >= 3; f(4) = 10, "
                "f(1) = -1, f(-2) = 2, f(-3) = 1; computed f(4) + 2f(1) = 8 and the "
                "expression f(1) - 3f(4) / f(-3)", "both", "most")],
  "level": "class 10 Tamil Nadu relations and functions",
  "ask_source": "student_text", "not_academic": None,
  "notes": "The request to speak in Tamil is a format request, not content."},
 "subjects": [MA], "chapters": [(MA, "Relations and Functions")],
 "topics": [("Relations and Functions", None)]},

"3b17d1f8": {
 "summary": {
  "overview": "The student sent one image and typed nothing. The bot replied that the image "
              "looked blurred or distorted. Nothing about the content is recoverable.",
  "covered": [], "level": None, "ask_source": "bot_restatement",
  "not_academic": "illegible", "notes": None},
 "subjects": [], "chapters": [], "topics": []},

"d1f95b08": {
 "summary": {
  "overview": "A class-6 CBSE student worked through Kaprekar's routine with the bot across "
              "nine exchanges, applying it to two different starting numbers and catching a "
              "subtraction error along the way.",
  "covered": [s("Applied Kaprekar's routine to four-digit numbers",
                "arrange the digits descending and ascending and subtract; 3524 gives 5432 - "
                "2345 = 3087, then 8730 - 0378 = 8352; repeated for 2015 giving 5210 - 0125 "
                "= 5085; the routine converges on the Kaprekar constant 6174", "both", "most")],
  "level": "class 6 CBSE number patterns",
  "ask_source": "student_text", "not_academic": None,
  "notes": "The bot flagged and corrected its own subtraction error, and had to tell the "
           "student the next step uses the previous result, not a new number."},
 "subjects": [MA], "chapters": [(MA, "Patterns in Mathematics")],
 "topics": [("Patterns in Mathematics", "Finding Patterns In Numbers")]},

"709cde42": {
 "summary": {
  "overview": "A class-7 ICSE student worked through the Delhi Sultanate with the bot over "
              "twenty-two exchanges, mixing explanation with a quiz the bot ran. The "
              "student's own question about why the Mughals are not part of the Sultanate "
              "drove a comparison between the two.",
  "covered": [
   s("What the Delhi Sultanate was",
     "five successive Muslim dynasties ruling India from Delhi, 1206-1526 AD", "both", "most"),
   s("The five dynasties of the Sultanate",
     "Mamluk (Slave), Khilji, Tughlaq, Sayyid, Lodi", "both", "some"),
   s("What the sultans changed in India",
     "new administrative structures and architectural styles; the reign ended at the First "
     "Battle of Panipat in 1526", "both", "some"),
   s("Why the Mughal Empire is counted separately from the Delhi Sultanate",
     "a single centralised imperial family replaced the rotating dynasties after Panipat "
     "in 1526, with new systems of governance and culture", "both", "some"),
   s("Quiz on the Sultanate",
     "the Battle of Panipat, the iqta system, Timur, domes, the Qutub Minar", "both", "some")],
  "level": "medieval Indian history, class 7 student working in a class 9-10 chapter",
  "ask_source": "student_text", "not_academic": None, "notes": None},
 "subjects": [SS], "chapters": [(SS, "State and Society in Medieval India")],
 "topics": [("State and Society in Medieval India", "Delhi Sultanate"),
            ("State and Society in Medieval India", "Mughals")]},

"0ac563e9": {
 "summary": {
  "overview": "A class-10 CBSE student sent a coordinate geometry question and asked for the "
              "solution with an example. Two related but distinct things: computing a "
              "distance between two points, and reading distances off the axes.",
  "covered": [
   s("Found the distance between two points",
     "A(3,4) and D(7,1); horizontal 7-3 = 4, vertical 4-1 = 3, Pythagoras sqrt(16+9) = 5",
     "both", "most"),
   s("Read a point's distance from each wall off its coordinates",
     "the door is 8 units from the left wall and 0 from the x-axis", "both", "some")],
  "level": "class 10 CBSE coordinate geometry",
  "ask_source": "student_text", "not_academic": None, "notes": None},
 "subjects": [MA], "chapters": [(MA, "Coordinate Geometry")],
 "topics": [("Coordinate Geometry", "Distance Formula"),
            ("Coordinate Geometry", "Cartesian System")]},

"802b913f": {
 "summary": {
  "overview": "A class-8 CBSE student asked for the formula and worked a problem on the "
              "distance light travels in a given time, with the answer required in standard "
              "form. One problem, with a practice question offered afterwards.",
  "covered": [s("Calculated a distance from speed and time and wrote it in standard form",
                "distance = speed x time using the speed of light; simplified the "
                "multiplication and converted to standard form; a follow-up practice problem "
                "on the speed of sound", "both", "most")],
  "level": "class 8 CBSE exponents and standard form",
  "ask_source": "student_text", "not_academic": None,
  "notes": "The 'distance formula' here is speed x time, not the coordinate-geometry "
           "distance formula - the chapter is exponents and powers."},
 "subjects": [MA], "chapters": [(MA, "Exponents and powers")],
 "topics": [("Exponents and powers", "Use of exponents to express small numbers in standard form")]},

"cdacab9b": {
 "summary": {
  "overview": "A class-8 CBSE student asked for help with question 10, finding the tiled area "
              "of a park with two square green plots cut out of it, in terms of two "
              "variables. The student sent their own working and the bot checked it, finding "
              "two multiplication errors.",
  "covered": [s("Found the tiled area of a park with two square plots removed, as an "
                "algebraic expression",
                "side of each green plot g ft; total width g + 2w, total length 2g + 3w; "
                "total area minus the two squares; the distributive property applied; final "
                "expression 8w^2 + 8wg sq ft", "both", "most")],
  "level": "class 8 CBSE algebraic expressions",
  "ask_source": "student_text", "not_academic": None,
  "notes": "The bot flagged two errors in the student's own expansion: 4w x 2w is 8w^2 not "
           "8w, and 2g x g is 2g^2 not g^2."},
 "subjects": [MA], "chapters": [(MA, "Algebraic expressions and Identities")],
 "topics": [("Algebraic expressions and Identities", "Multiplication of Algebraic expressions")]},
}


def main():
    records = json.load(open(C.P("out2/conv_records.json"), encoding="utf-8"))
    written, misses = 0, []

    for short, w in WORK.items():
        cid = next(k for k in records if k.startswith(short))
        pay = C.assemble(cid, records[cid])

        # call 1 - summarise
        summ = dict(w["summary"])
        C.CACHE[C.cache_key(C.p_summarise(pay), None)] = json.dumps(
            {k: summ.get(k) for k in ("overview", "covered", "level", "ask_source",
                                      "not_academic", "notes")}, ensure_ascii=False)
        written += 1
        if summ.get("not_academic"):
            continue
        text = C.summary_text({**summ, "thin": None})

        # call 2 - subject
        prefix, tail = C.p_subject(pay, text)
        C.CACHE[C.cache_key(tail, prefix)] = json.dumps(
            {"subjects": w["subjects"], "confidence": "HIGH", "reject": None,
             "why": "named outright in the summary"}, ensure_ascii=False)
        written += 1

        # call 3 - chapter
        prefix, tail = C.p_chapter(pay, text, w["subjects"])
        C.CACHE[C.cache_key(tail, prefix)] = json.dumps(
            {"chapters": [{"subject": s_, "chapter": c_, "covers": "", "confidence": "HIGH"}
                          for s_, c_ in w["chapters"]],
             "reject": None, "why": ""}, ensure_ascii=False)
        written += 1
        for s_, c_ in w["chapters"]:
            if (s_, c_) not in C.CONCEPT:
                misses.append(f"{short}: chapter not in the tree - {s_} > {c_}")

        # call 4 - topic
        order = C.preferred_trees(pay, n=len(C.ALL_TREES))
        picks = []
        for s_, c_ in w["chapters"]:
            carriers = C.CONCEPT.get((s_, c_), {})
            if not carriers:
                continue
            picks.append({"subject": s_, "chapter": c_,
                          "trees": sorted(carriers, key=order.index),
                          "tree": min(carriers, key=order.index), "confidence": "HIGH"})
        if not picks:
            continue
        index = {}
        for p in picks:
            for n in C.nodes_for(p):
                index[(p["chapter"], n["name"])] = n
        out = []
        for chap, name in w["topics"]:
            if name is None:
                out.append({"chapter": chap, "topic_id": "", "topic": "CHAPTER_ONLY",
                            "topic_level": "", "confidence": "HIGH"})
                continue
            n = index.get((chap, name))
            if not n:
                misses.append(f"{short}: node not in {chap} - {name}")
                continue
            out.append({"chapter": chap, "topic_id": n["id"], "topic": n["name"],
                        "topic_level": n["lvl"], "confidence": "HIGH"})
        if C.nodes_for(picks[0]) or any(C.nodes_for(p) for p in picks):
            C.CACHE[C.cache_key(C.p_topic(text, picks), None)] = json.dumps(
                {"topics": out}, ensure_ascii=False)
            written += 1

    C.save_cache()
    print(f"{written} replies cached across {len(WORK)} conversations")
    print(f"  {sum(len(w['summary'].get('covered') or []) for w in WORK.values())} "
          f"things covered in total across the 20 summaries")
    for m in misses:
        print("  MISS", m)


if __name__ == "__main__":
    main()
