import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
t=[l for l in open("view4.txt",encoding="utf-8").read().split("\n") if l.strip()]
a,b=int(sys.argv[1]),int(sys.argv[2]); print("\n".join(t[a:b]))
