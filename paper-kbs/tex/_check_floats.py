"""Read-only check: every tab:/fig: label must be referenced at least once."""
import glob
import os
import re

TEX = os.path.dirname(os.path.abspath(__file__))
SOURCES = [f for f in glob.glob(os.path.join(TEX, "*.tex"))]

body = ""
labels = {}
for path in SOURCES:
    text = open(path, encoding="utf-8", errors="ignore").read()
    body += text
    for m in re.finditer(r"\\label\{(tab:[^}]+|fig:[^}]+)\}", text):
        labels[m.group(1)] = os.path.basename(path)

uncited = []
for label, src in sorted(labels.items()):
    refs = len(re.findall(r"\\ref\{" + re.escape(label) + r"\}", body))
    if refs == 0:
        uncited.append((label, src))

print("float labels:", len(labels), "uncited:", len(uncited))
for label, src in uncited:
    print("  UNCITED", label, "in", src)
