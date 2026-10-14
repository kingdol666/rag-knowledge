"""Count abstract words in main2.tex (cap: 250 for KBS)."""
import re
import pathlib

text = pathlib.Path(__file__).with_name("main2.tex").read_text(encoding="utf-8")
block = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.S).group(1)
block = re.sub(r"%.*", " ", block)
words = [w for w in block.split() if any(c.isalnum() for c in w)]
print("abstract words:", len(words))
