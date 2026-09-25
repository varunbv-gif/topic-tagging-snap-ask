import csv, collections, json
CH={}
for ln in open("chapters.tsv",encoding="utf-8"):
    code,cid,tree,subj,name=ln.rstrip("\n").split("\t"); CH[cid]=(code,tree,subj,name)
nodes=collections.defaultdict(list)
for r in csv.DictReader(open("nodes.tsv",encoding="utf-8"),delimiter="\t"):
    nodes[r["chcode"]].append(r)
full={(r["conversation_id"],r["exchange_no"]):r["delivered"]
      for r in csv.DictReader(open("notes_full.tsv",encoding="utf-8"),delimiter="\t")}
tags=list(csv.DictReader(open("exchange_topic_tags.csv",encoding="utf-8")))
todo=collections.defaultdict(list)
for r in tags:
    if r["status"]=="TAGGED" and r["tag_source"]=="llm":
        todo[CH[r["chapter_id"]][0]].append(r)
order=sorted(todo, key=lambda c:-len(todo[c]))
json.dump({c:[[r["conversation_id"],r["exchange_no"]] for r in todo[c]] for c in todo}, open("todo.json","w"))
with open("view2.txt","w",encoding="utf-8") as f:
    for chcode in order:
        cid=next(k for k,v in CH.items() if v[0]==chcode); _,tree,subj,name=CH[cid]
        f.write(f"\n=== CH{chcode} {tree} > {subj} > {name}  [{len(todo[chcode])} exchanges, {len(nodes[chcode])} nodes]\n")
        for n in nodes[chcode]:
            f.write(f'  {n["ncode"]} {"T" if n["level"]=="T" else "s"} {n["topic"]+" / " if n["topic"] else ""}{n["name"]}\n')
        for i,r in enumerate(todo[chcode],1):
            f.write(f'  #{i} {full[(r["conversation_id"],r["exchange_no"])][:400] or "(none)"}\n')
print(len(order),"chapter blocks;",sum(len(v) for v in todo.values()),"exchanges to node-tag")
