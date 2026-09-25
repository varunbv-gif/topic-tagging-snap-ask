import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
t = open("view2.txt", encoding="utf-8").read().split("\n")
idx = [i for i, l in enumerate(t) if l.startswith("=== CH")] + [len(t)]
a, b = int(sys.argv[1]), int(sys.argv[2])
print("\n".join(t[idx[a]:idx[min(b, len(idx)-1)]]))
