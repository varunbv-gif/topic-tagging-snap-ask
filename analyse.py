import csv, collections, json
rows = list(csv.DictReader(open("out2/conversation_tags_v2.csv", encoding="utf-8")))
tagged = [r for r in rows if r["in_C"] == "Y"]

print("=== what widening the catalogue bought ===")
onlyC = [r for r in tagged if r["in_A"] == "N"]
onlyB = [r for r in tagged if r["in_A"] == "N" and r["in_B"] == "Y"]
print(f"reachable only outside CBSE-9 : {len(onlyC)} conversations, {sum(int(r['exchanges']) for r in onlyC)} exchanges")
print(f"   ...of which Foundation/NCERT covers: {len(onlyB)}")
print("   chapters unlocked:")
for (s, c), n in collections.Counter((r["subject"], r["chapter"]) for r in onlyC).most_common():
    trees = {r["tree"] for r in tagged if (r["subject"], r["chapter"]) == (s, c)}
    print(f"     {n:>2}x {s} | {c:<45} -> {','.join(sorted(trees))}")

print("\n=== tree actually chosen ===")
for t, n in collections.Counter(r["tree"] for r in tagged).most_common():
    print(f"  {t:<22} {n:>3}")

print("\n=== top chapters ===")
for (s, c), n in collections.Counter((r["subject"], r["chapter"]) for r in tagged).most_common(15):
    print(f"  {n:>3}  {s} | {c}")

print("\n=== chapter x declared grade ===")
g = collections.Counter((r["grade"] or "?", r["subject"]) for r in tagged)
grades = sorted({k[0] for k in g}, key=lambda x: (x == "?", int(x) if x.isdigit() else 0))
subs = sorted({k[1] for k in g}, key=lambda s: -sum(v for k, v in g.items() if k[1] == s))
print("  subject".ljust(18) + "".join(x.rjust(5) for x in grades) + "  tot")
for s in subs:
    row = [g.get((gr, s), 0) for gr in grades]
    print(f"  {s:<16}" + "".join(str(v or '').rjust(5) for v in row) + str(sum(row)).rjust(5))

print("\n=== what the extra columns rescued ===")
conv = json.load(open("out2/conv_records.json", encoding="utf-8"))
thin = [r for r in tagged if len(conv[r["cid"]]["taught"]) + len(conv[r["cid"]]["older_delivered"]) < 150]
print(f"conversations whose coverage note was empty/near-empty but still tagged: {len(thin)}")
print(f"  of those, tagged from response.text / input_parts alone: {sum(1 for r in thin if not conv[r['cid']]['taught'])}")
