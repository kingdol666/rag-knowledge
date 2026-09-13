"""Report every \\need/\\needblock marker with its length, so long ones can be trimmed."""
import re

src = open("main.tex", encoding="utf-8").read()
key_marks = []


def extract(cmd):
    key = "\\" + cmd + "{"
    out, i = [], 0
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
        line = src[:j].count("\n") + 1
        out.append((line, cmd, src[j + len(key):k - 1]))
        i = k
    return out


items = extract("need") + extract("needblock")
items.sort()
total = sum(len(b) for _, _, b in items)
print(f"{len(items)} markers, {total:,} chars total (~{total/3000:.2f} pages)\n")
for line, cmd, body in items:
    todo = re.search(r"TODO-\d+", body)
    flag = "  <-- TRIM" if len(body) > 320 else ""
    print(f"  L{line:<5} {cmd:<10} {len(body):>5} ch  {todo.group(0) if todo else '(no id)':<9}{flag}")
    print(f"          {body.strip()[:110]}...")
