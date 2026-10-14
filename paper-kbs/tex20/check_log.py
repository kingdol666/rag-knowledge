import re
import sys

log = open(sys.argv[1] if len(sys.argv) > 1 else "main_20p.log",
           encoding="utf-8", errors="replace").read()
m = re.search(r"Output written on main_20p.pdf .(\d+). pages", log)
print("pages:", m.group(1) if m else "?")
errs = re.findall(r"^! (.+)$", log, re.M)
print("errors:", errs[:6] if errs else "none")
print("undefined citations:", len(re.findall(r"Citation .+ undefined", log)))
print("undefined references:", len(re.findall(r"Reference .+ undefined", log)))
print("missing files:", len(re.findall(r"File .+ not found", log)))
over = re.findall(r"Overfull .hbox .([0-9.]+)pt", log)
print("overfull >10pt:", sum(1 for o in over if float(o) > 10))
