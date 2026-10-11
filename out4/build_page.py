"""Assemble a standalone HTML page from a template and its data.

    python out4/build_page.py funnel     -> conversation_funnel.html

The templates carry no data: they hold a __DATA__ placeholder that the matching
_data.json is inlined into. The assembled page is one self-contained file - every
style, script and value inlined, one external font link - so it opens from a disk,
a web server or anywhere else without claude.ai or any other host.

The assembled page is NOT committed. It lists every conversation of the run with a
fragment of its id, a fragment of the student's id, their class and board, so it
carries student data and stays out of the repository.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = {"funnel": ("funnel_body.html", "funnel_data.json", "conversation_funnel.html")}

name = sys.argv[1] if len(sys.argv) > 1 else "funnel"
if name not in PAGES:
    raise SystemExit(f"unknown page {name!r} - try one of: {', '.join(PAGES)}")

body_f, data_f, out_f = PAGES[name]
for f in (body_f, data_f):
    if not os.path.exists(os.path.join(HERE, f)):
        raise SystemExit(f"out4/{f} is missing - run out4/build_{name}.py first")

body = open(os.path.join(HERE, body_f), encoding="utf-8").read()
data = open(os.path.join(HERE, data_f), encoding="utf-8").read()
out = os.path.join(os.path.dirname(HERE), out_f)
open(out, "w", encoding="utf-8").write(body.replace("__DATA__", data))
print(f"{out_f}  {os.path.getsize(out):,} bytes")
print("  one self-contained file - no host required, and not committed: it lists "
      "every conversation.")
