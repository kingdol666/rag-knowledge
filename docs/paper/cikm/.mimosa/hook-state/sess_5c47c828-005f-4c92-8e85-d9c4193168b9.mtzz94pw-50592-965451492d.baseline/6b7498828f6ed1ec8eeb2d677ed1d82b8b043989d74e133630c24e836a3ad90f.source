"""Report lines of main.tex whose $ delimiters do not balance."""
import re

lines = open("main.tex", encoding="utf-8").read().split("\n")
run = 0
for i, l in enumerate(lines, 1):
    t = l.replace(r"\$", "")
    n = t.count("$")
    if n:
        run += n
    if n % 2:
        print(f"{i}: {l.strip()[:160]}")
print("total $ tokens:", sum(l.replace(r'\$','').count('$') for l in lines))
