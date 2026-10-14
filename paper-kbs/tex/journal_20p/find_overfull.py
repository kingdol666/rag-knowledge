import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
arg = sys.argv[1] if len(sys.argv) > 1 else "main_20p.log"
log_path = (BASE / arg).resolve()
# 路径边界：仅允许本论文目录内的日志文件（禁 ../ 逃逸）
if not log_path.is_relative_to(BASE):
    raise SystemExit(f"path escapes the paper directory: {arg}")
if not log_path.is_file():
    raise SystemExit(f"log not found: {log_path.name}")

log = open(log_path, encoding="utf-8", errors="replace").read()
BS = chr(92)
opens = [(m.start(), m.group(1))
         for m in re.finditer(r".(\./[A-Za-z0-9_]+\.tex)", log)]
pat = "Overfull " + BS + BS + "hbox .(([0-9.]+)pt too wide.) in paragraph at lines ([0-9]+)--([0-9]+)"
for m in re.finditer(pat, log):
    if float(m.group(2)) > 10:
        prior = [name for s, name in opens if s < m.start()]
        print("overfull", m.group(2), "pt at lines", m.group(3), "-",
              m.group(4), "file:", prior[-1] if prior else "main_20p.tex")
