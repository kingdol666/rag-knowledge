"""KBS initial-submission compliance checks for this source tree."""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
tex = (HERE / "main_20p.tex").read_text(encoding="utf-8")
ab = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, re.S).group(1)
words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'/-]*", ab))
print("abstract words:", words, "<=250:", words <= 250)
hl = (HERE / "highlights.tex").read_text(encoding="utf-8")
items = re.findall(r"\\item (.*)", hl)
print("highlights count:", len(items), "lengths:", [len(i) for i in items],
      "ok:", 3 <= len(items) <= 5 and all(len(i) <= 85 for i in items))
kw = re.search(r"\\begin\{keyword\}(.*?)\\end\{keyword\}", tex, re.S).group(1)
nkw = len(kw.split("\\sep"))
print("keywords:", nkw, "<=6:", nkw <= 6)
back = (HERE / "n_back.tex").read_text(encoding="utf-8").lower()
for d in ["credit", "competing interest", "funding", "ethics", "data availability",
          "acknowledgments", "generative ai"]:
    print("declaration", d, ":", d in back)
print("journal:", re.search(r"\\journal\{(.*?)\}", tex).group(1))
print("bibstyle num:", "elsarticle-num" in tex)