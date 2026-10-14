"""Repair the three spots damaged by the cp936 round-trip, drop the BOM."""
from pathlib import Path
import ast

P = Path(__file__).with_name("figures.py")
raw = P.read_bytes()
text = raw[3:].decode("utf-8") if raw[:3] == b"\xef\xbb\xbf" else raw.decode("utf-8")

REPAIRS = [
    ("(paper-kbs ??3.3)", "(paper-kbs \u00a73.3)"),
    ("subject ?? attribute ?? constraints",
     "subject \u00d7 attribute \u00d7 constraints"),
    ("kb_laya_judge batch ?? server fetches",
     "kb_laya_judge batch \u2264 6; server fetches"),
    ("batch ??refs; threshold", "batch \u2264 6 refs; threshold"),
    ("kb_doc_read ??00 chars", "kb_doc_read \u2265 500 chars"),
    ("keep ??est??15 with", "keep \u2265 best\u2212 15 with"),
    ("??00 chars each", "\u2265 500 chars each"),
]

for old, new in REPAIRS:
    hits = text.count(old)
    text = text.replace(old, new)
    print("%-42s -> %-34s x%d" % (repr(old), repr(new), hits))

P.write_bytes(text.encode("utf-8"))
print("BOM removed; '?' remaining:", text.count("?"))

check = P.read_bytes()
assert not check.startswith(b"\xef\xbb\xbf")
body = check.decode("utf-8")
ast.parse(body)
print("valid utf-8, parses OK; lines:", body.count("\n") + 1)
for ch, name in (("\u2014", "em dash"), ("\u00a7", "section"),
                 ("\u00d7", "times"), ("\u2192", "rarrow"),
                 ("\u2264", "leq"), ("\u2265", "geq"),
                 ("\u2212", "minus")):
    print("  %-9s %d" % (name, body.count(ch)))
