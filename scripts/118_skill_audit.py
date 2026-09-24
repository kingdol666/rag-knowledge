#!/usr/bin/env python3
"""Skill 结构审计 — 静态检查全部知识库 skill 的完整性（不调用任何 API）。

检查项：
  1. frontmatter：每个 SKILL.md 有 `name` + `description`；name 与目录名一致
  2. 文件引用：markdown 相对链接 `](../x.md)` 真实存在
  3. skill 引用：`skill://name` 指向的 skill 目录存在
  4. 工具引用：反引号里的 kb_*/experience_*/soul_*/fs_*/parse_*/backend_* 名称
     在 kb-mcp/server.py 注册表中真实存在（参数名如 kb_id 自动豁免）
  5. 核心 skill（ingest / search / organize）必备结构标记齐全
  6. 重复 name / 目录名不一致

用法（仓库根目录）：
    python scripts/118_skill_audit.py
    python scripts/118_skill_audit.py --out benchmark-suite/results/SKILL-AUDIT.md
退出码：有 FAIL → 1；否则 0。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / ".claude" / "skills"
SERVER = REPO / "kb-mcp" / "server.py"

# 参数/概念名（会被反引号包住但不是工具），显式豁免
PARAM_BLOCKLIST = {
    "kb_id", "kb_name", "kb_names", "kb_uuid", "kb_type", "kb_path",
    "doc_path", "doc_name", "doc_id", "soul_id", "fs_path", "task_id",
    "parse_id", "backend_url", "kb_dir",
}
TOOL_RE = re.compile(r"`((?:kb|experience|soul|fs|parse|backend)_[a-z0-9_]+)`")
LINK_RE = re.compile(r"\]\((\.[^)\s]+\.md)[^)]*\)")
# `skill://knowledgebase-<scenario>` is a template placeholder, not a link.
SKILLREF_RE = re.compile(r"skill://([a-zA-Z0-9\-_]+)(?![a-zA-Z0-9\-_<])")
# A tool named on a line that also says it was removed / is empty is *correct*
# documentation, not a broken reference.
REMOVED_HINTS = ("removed", "deprecated", "已移除", "已删除", "returns empty",
                 "不存在", "no longer", "not actually populated")

CORE = {
    "knowledgebase-ingest": [
        ("A0", "去重"), ("A2", "解析质量"), ("A3b", "标签"),
        ("A3c", "描述"), ("A5", "存储"), ("A6", "索引"), ("A7", "终检"),
        ("kb_doc_save_parsed", "存储工具"), ("kb_index_document", "索引工具"),
    ],
    "knowledgebase-search": [
        ("Phase 0", "查询预处理"), ("Phase 1", "向量优先"), ("Phase 2", "兜底"),
        ("Phase 3", "作答"), ("0-8", "内容评分"), ("kb_search_vector", "召回工具"),
        ("kb_doc_read", "读正文"), ("Blind Spots", "盲点声明"),
    ],
    "knowledgebase-organize": [
        ("kb_list", "盘点"), ("kb_doc_read", "内容审计"), ("kb_doc_move", "移动"),
        ("kb_batch_index", "重建索引"),
        ("regression", "检索回归"), ("O5-C", "回归记录"),
    ],
}


def frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fm = text[3:end]
    out: dict = {}
    for line in fm.splitlines():
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def tool_names() -> set[str]:
    """Only @mcp.tool()-decorated functions are real tools (94, not every def)."""
    if not SERVER.exists():
        return set()
    src = SERVER.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"@mcp\.tool\([^)]*\)\s*\n(?:async )?def (\w+)", src, re.S))


def _documented_as_removed(text: str, name: str) -> bool:
    for line in text.splitlines():
        if name in line and any(h in line for h in REMOVED_HINTS):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    tools = tool_names()
    rows = []
    fails = 0
    warns = 0

    skill_dirs = sorted(p for p in SKILLS.iterdir()
                        if p.is_dir() and (p / "SKILL.md").exists())
    names: dict[str, list[str]] = {}

    for d in skill_dirs:
        md = d / "SKILL.md"
        text = md.read_text(encoding="utf-8", errors="replace")
        fm = frontmatter(text)
        issues, warnings = [], []

        # 1 frontmatter
        if not fm.get("name"):
            issues.append("frontmatter 缺 name")
        elif fm["name"] != d.name:
            issues.append(f"name({fm['name']}) != dir({d.name})")
        if not fm.get("description"):
            issues.append("frontmatter 缺 description")
        names.setdefault(fm.get("name", d.name), []).append(str(d))

        # 2 file links
        missing_files = []
        for rel in set(LINK_RE.findall(text)):
            if not (d / rel).resolve().exists():
                missing_files.append(rel)
        if missing_files:
            warnings.append(f"断链 {len(missing_files)}: {missing_files[:3]}")

        # 3 skill:// refs
        bad_sk = [s for s in set(SKILLREF_RE.findall(text))
                  if not (SKILLS / s).exists()]
        if bad_sk:
            issues.append(f"skill:// 指向不存在: {bad_sk}")

        # 4 tool refs
        cand = {t for t in TOOL_RE.findall(text) if t not in PARAM_BLOCKLIST}
        unknown = sorted(c for c in cand
                         if c not in tools and not _documented_as_removed(text, c))
        if unknown:
            warnings.append(f"未注册工具引用: {unknown[:4]}")

        rows.append({"skill": d.name, "name": fm.get("name", ""),
                     "desc_len": len(fm.get("description", "")),
                     "lines": text.count("\n") + 1,
                     "tools_ref": len(cand), "missing_files": len(missing_files),
                     "unknown_tools": len(unknown),
                     "issues": issues, "warnings": warnings})
        fails += len(issues)
        warns += len(warnings)

    dup = {k: v for k, v in names.items() if len(v) > 1}

    # 5 core skill structure
    core_rows = []
    for sk, markers in CORE.items():
        p = SKILLS / sk / "SKILL.md"
        if not p.exists():
            core_rows.append((sk, "MISSING", [m for m, _ in markers]))
            fails += 1
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        missing = [f"{m}({why})" for m, why in markers if m not in t]
        core_rows.append((sk, "OK" if not missing else "INCOMPLETE", missing))
        fails += len(missing)

    # ── report ──────────────────────────────────────────────────────────────
    L = ["# Skill 结构审计报告（静态检查，未调用任何 API）", "",
         f"- skill 目录：**{len(skill_dirs)}** 个 · 注册 MCP 工具：**{len(tools)}** 个",
         f"- 问题(FAIL)：**{fails}** · 警告(WARN)：**{warns}**", ""]
    if dup:
        L += ["## ❌ 重复 name", ""] + [f"- `{k}` → {v}" for k, v in dup.items()] + [""]
    L += ["## 核心三 skill", "", "| skill | 结论 | 缺失标记 |", "|---|---|---|"]
    for sk, st, miss in core_rows:
        L.append(f"| `{sk}` | {'✅ ' if st == 'OK' else '❌ '}{st} | "
                 f"{', '.join(miss) if miss else '—'} |")
    L += ["", "## 全部 skill", "",
          "| skill | name | 行数 | 工具引用 | 断链 | 未注册工具 | 问题 | 警告 |",
          "|---|---|---:|---:|---:|---:|---|---|"]
    for r in rows:
        L.append(f"| `{r['skill']}` | {r['name']} | {r['lines']} | {r['tools_ref']} | "
                 f"{r['missing_files']} | {r['unknown_tools']} | "
                 f"{'; '.join(r['issues']) if r['issues'] else '—'} | "
                 f"{'; '.join(r['warnings']) if r['warnings'] else '—'} |")
    md = "\n".join(L)

    print(md)
    if args.out:
        out = Path(args.out)
        if not out.is_absolute():
            out = REPO / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"\n[audit] → {out}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
