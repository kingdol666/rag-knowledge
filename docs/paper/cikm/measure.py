"""Estimate how much of main.tex is red review-marker text vs actual paper content."""
import re

src = open("main.tex", encoding="utf-8").read()

# capture \need{...} and \needblock{...} with balanced braces
def extract(cmd: str) -> list[str]:
    out, key = [], "\\" + cmd + "{"
    i = 0
    while True:
        j = src.find(key, i)
        if j < 0:
            break
        k, depth = j + len(key), 1
        while k < len(src) and depth:
            if src[k] == "{":
                depth += 1
            elif src[k] == "}":
                depth -= 1
            k += 1
        out.append(src[j:k])
        i = k
    return out


blocks = extract("need") + extract("needblock")
red_chars = sum(len(b) for b in blocks)

body = src.split("\\begin{document}", 1)[1]
body = re.sub(r"%.*", "", body)
total = len(body)

print(f"red markers      : {len(blocks)}  ({red_chars:,} chars)")
print(f"document body    : {total:,} chars")
print(f"red share        : {100*red_chars/total:.1f}%  (~{red_chars/3000:.2f} pages at 3000 chars/page)")

# per-section character counts
sections = re.split(r"\\section\{([^}]*)\}", body)
print("\nper-section body size (chars, excluding red markers):")
for i in range(1, len(sections), 2):
    name, txt = sections[i], sections[i + 1]
    for b in blocks:
        txt = txt.replace(b, "")
    print(f"  {name:<42} {len(txt):>6,}  ~{len(txt)/3000:.2f} pp")
