#!/usr/bin/env python3
"""把 .claude/skills 的 frontmatter 规范化到 skill-creator 的标准格式。

skill-creator 的 quick_validate.py 要求：
  1. SKILL.md 以 `---` 开头，frontmatter 含 `name:` 与 `description:`
  2. `name` 为 hyphen-case
  3. **description 必须写在同一行**（`description: >` 块标量会被解析成 `>`，含 `>` → 判失败）
  4. description 不得含尖括号 `<` `>`

本脚本据此：
  - 把 `description: >` / `|` 块标量合并为**单行双引号标量**（转义 `\\` 与 `"`）
  - 去掉 description 里的 `<` `>`（保留括号内文字）
  - 补齐 `agent_created: true`（skill_manage 后续可修改）
  - 保留其余 frontmatter 键与正文不动

用法（仓库根）
    python scripts/skill_normalize.py            # 规范化全部
    python scripts/skill_normalize.py --check    # 只报告不写
退出码：仍有不达标 → 1；否则 0。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / ".claude" / "skills"
VALIDATOR = Path(
    "D:/Program Files/WorkBuddy_f/WorkBuddyAI/resources/app.asar.unpacked/"
    "resources/plugins/workbuddy-builtin/skills/skill-creator/scripts/quick_validate.py")
BLOCK = (">", "|", ">-", "|-", ">+", "|+")
KEY_RE = re.compile(r"^([A-Za-z_][\w-]*):\s*(.*)$")


def split_front(text: str) -> tuple[str, str] | None:
    if not text.startswith("---"):
        return None
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.S)
    if not m:
        return None
    return m.group(1), text[m.end():]


def parse_fm(fm: str) -> tuple[dict, list[str]]:
    """→ ({key: value}, [key order])，支持块标量。"""
    data: dict[str, str] = {}
    order: list[str] = []
    key, buf = None, []
    for ln in fm.splitlines():
        m = KEY_RE.match(ln)
        if m and not ln.startswith((" ", "\t")):
            if key:
                data[key] = " ".join(buf).strip()
            key = m.group(1)
            val = m.group(2).strip()
            order.append(key)
            buf = [] if val in BLOCK else [val]
        elif key and ln[:1] in (" ", "\t"):
            buf.append(ln.strip())
    if key:
        data[key] = " ".join(buf).strip()
    return data, order


def clean_desc(s: str) -> str:
    """Undo any already-applied double-quoted YAML wrapping.

    The first version of this script was not idempotent: re-running it escaped the previous
    run's quotes, producing `description: "\\\"\\\\\\\"…"`. Unwrap until stable.
    """
    s = (s or "").strip()
    for _ in range(6):
        if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
            inner = s[1:-1]
            s = inner.replace("\\\\", "\\").replace('\\"', '"').strip()
        else:
            break
    return s


def yaml_dq(s: str) -> str:
    """安全输出 YAML 双引号标量。"""
    s = clean_desc(s)
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    s = re.sub(r"\s+", " ", s).strip()
    return f'"{s}"'


def normalize_one(md: Path, dry: bool) -> tuple[bool, str]:
    text = md.read_text(encoding="utf-8")
    sp = split_front(text)
    if not sp:
        return False, "无 frontmatter"
    fm_raw, body = sp
    data, order = parse_fm(fm_raw)
    name = data.get("name") or md.parent.name
    desc = clean_desc(data.get("description", ""))
    changed = []

    if not re.match(r"^[a-z0-9-]+$", name) or "--" in name:
        return False, f"name 非法: {name!r}"
    if "<" in desc or ">" in desc:
        desc = desc.replace("<", "").replace(">", "")
        changed.append("desc 去尖括号")
    if not desc.strip():
        return False, "description 为空"

    # rebuild: name / description / agent_created / rest
    # NOTE: agent_created must be emitted unconditionally — an earlier version skipped it when
    # already present AND skipped it in the "rest" loop, so it was dropped on the 2nd run.
    lines = [f"name: {name}", f"description: {yaml_dq(desc)}", "agent_created: true"]
    if data.get("agent_created") != "true":
        changed.append("+agent_created")
    for k in order:
        if k in ("name", "description", "agent_created"):
            continue
        v = data.get(k, "")
        lines.append(f"{k}: {v}" if v not in BLOCK else f"{k}: {v}")
    new = "---\n" + "\n".join(lines) + "\n---\n" + body.lstrip("\n")
    if new != text:
        if not dry:
            md.write_text(new, encoding="utf-8")
        changed.append("frontmatter 重写")
    return True, ", ".join(changed) or "已合规"


def validate(md: Path) -> tuple[bool, str]:
    if not VALIDATOR.exists():
        return True, "validator 缺失（跳过）"
    r = subprocess.run([sys.executable, str(VALIDATOR), str(md.parent)],
                       capture_output=True, text=True)
    return r.returncode == 0, (r.stdout or r.stderr).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    rows, fails = [], 0
    for d in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
        md = d / "SKILL.md"
        if not md.exists():
            continue
        ok, note = normalize_one(md, dry=args.check)
        vok, vmsg = validate(md) if not args.check else (ok, "check 模式")
        rows.append((d.name, ok, note, vok, vmsg))
        if not (ok and vok):
            fails += 1

    print(f"{'skill':<36}{'规范化':<8}{'校验':<8}说明")
    print("-" * 100)
    for name, ok, note, vok, vmsg in rows:
        print(f"{name:<36}{'✓' if ok else '✗':<8}{'✓' if vok else '✗':<8}{note}"
              + ("" if vok else f"  ← {vmsg}"))
    print("-" * 100)
    print(f"共 {len(rows)} 个 skill · 不达标 {fails} 个"
          + ("（--check 未写盘）" if args.check else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
