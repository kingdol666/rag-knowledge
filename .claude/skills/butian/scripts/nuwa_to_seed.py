#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nuwa_to_seed.py — nuwa-skill 蒸馏产物 → 补天 SOUL 种子包

输入:  <perspective-skill-dir>   (nuwa-skill 产出的 [person]-perspective/ 目录, 含 SKILL.md)
输出:  <seed-dir>/               (默认 <perspective-skill-dir>/soul-seed/)
  meta.json    # 补天种子契约: {slug, name, display_name, character,
               #  research_profile, tags:{personality:[...]}, impression}
  persona.md   # 身份/性格/表达风格/诚实边界 → soul-definition.md 追加段
  work.md      # 职责/思维框架/决策启发式/工作流程 → thinking-style.md 追加段
  values.md    # 价值观与反模式 → values.md 追加段(可选, ragctl --values 消费)

用法:
  python3 nuwa_to_seed.py <perspective-skill-dir> [--out <seed-dir>] [--labels a,b]

与 dot-skill 产物契约完全对齐: 种子包可直接被 `ragctl soul distill` 消费
(meta.json + persona.md + work.md), values.md 为补天增强(ragctl --values)。
转换是确定性的章节拆分, 不调用任何 LLM。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ── 章节 → 目标文件映射(按 nuwa skill-template.md 定义的结构) ────────────
PERSONA_SECTIONS = {   # → persona.md(身份/风格/边界)
    "角色扮演规则": "角色扮演规则(摘要)",
    "身份卡": "身份卡",
    "表达DNA": "表达DNA",
    "诚实边界": "诚实边界",
    "核心心智模型": None,  # 模型在 work.md
}
WORK_SECTIONS = {      # → work.md(职责/思维/流程)
    "回答工作流": "回答工作流",
    "失败模式与 Fallback 树": "失败模式与降级规则",
    "核心心智模型": "核心心智模型",
    "决策启发式": "决策启发式",
    "人物时间线": "人物时间线(背景)",
    "智识谱系": "智识谱系",
}
VALUES_SECTIONS = {    # → values.md(价值观与反模式)
    "价值观与反模式": "价值观与反模式",
}
SKIP_SECTIONS = {      # 不进入种子(附录/调研来源留在 skill 目录)
    "附录：调研来源": True,
    "附录: 调研来源": True,
}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """解析 SKILL.md frontmatter, 返回 (meta, body)。"""
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return {}, text
    fm: dict = {}
    cur = None
    for line in m.group(1).splitlines():
        kv = re.match(r"^(\w+):\s*(.*)$", line)
        if kv:
            cur = kv.group(1)
            v = kv.group(2).strip()
            # YAML 块标量 `|`/`>`: 值在后续续行
            fm[cur] = "" if v in ("|", ">", "|-", ">-") else v
        elif cur and line.strip():
            fm[cur] += (" " + line.strip()) if fm.get(cur) else line.strip()
    return fm, text[m.end():]


def split_sections(body: str) -> list[tuple[str, str]]:
    """按 '## ' 二级标题拆分正文, 返回 [(标题, 内容)]。三级标题保留在内容内。"""
    parts = re.split(r"^##\s+(.+?)\s*$", body, flags=re.M)
    sections: list[tuple[str, str]] = []
    # parts[0] 是标题前内容; 之后成对 (标题, 内容)
    head = parts[0].strip()
    if head:
        sections.append(("", head))
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if content:
            sections.append((title, content))
    return sections


def model_names(body: str) -> list[str]:
    """提取 '### 模型N: 名称' 中的模型名(用于路由标签)。"""
    names = []
    for m in re.finditer(r"^###\s*模型\s*\d+\s*[:：]\s*(.+?)\s*$", body, flags=re.M):
        names.append(m.group(1).strip())
    return names


def first_sentence(text: str, limit: int = 40) -> str:
    """取第一句作为 impression。"""
    t = re.sub(r"\s+", " ", text).strip()
    m = re.match(r"^(.+?)[。.!?！？]", t)
    s = m.group(1) if m else t
    return s[:limit]


def build_persona(sections: dict) -> str:
    """身份/风格/边界 → persona.md(dot-skill 契约: 身份/风格/口头禅)。"""
    parts = []
    order = ["身份卡", "角色扮演规则(摘要)", "表达DNA", "诚实边界"]
    for key in order:
        if key in sections and sections[key]:
            if key == "角色扮演规则(摘要)":
                parts.append("## 角色扮演规则(摘要)\n\n" + sections[key])
            elif key == "诚实边界":
                parts.append("## 诚实边界\n\n" + sections[key])
            elif key == "身份卡":
                parts.append("## 身份卡\n\n" + sections[key])
            else:
                parts.append("## 表达DNA\n\n" + sections[key])
    return "\n\n---\n\n".join(parts)


def build_work(sections: dict) -> str:
    """职责/思维/流程 → work.md(dot-skill 契约: 职责范围/工作规范)。"""
    parts = []
    order = ["回答工作流", "核心心智模型", "决策启发式", "智识谱系", "人物时间线(背景)", "失败模式与降级规则"]
    for key in order:
        if key in sections and sections[key]:
            if key == "回答工作流":
                parts.append("## 回答工作流(Agentic Protocol)\n\n" + sections[key])
            else:
                parts.append(f"## {key}\n\n" + sections[key])
    return "\n\n---\n\n".join(parts)


def build_values(sections: dict) -> str:
    """价值观与反模式 → values.md(仅蒸馏内容, ragctl --values 融合模板)。"""
    v = sections.get("价值观与反模式", "")
    if not v:
        return ""
    return v


def build_meta(fm: dict, sections: dict, model_names_: list, extra_labels: list) -> dict:
    """meta.json(dot-skill 契约: name/slug/tags/impression + 补天扩展字段)。"""
    raw_name = (fm.get("name") or "").strip()
    slug = raw_name[:-len("-perspective")] if raw_name.endswith("-perspective") else raw_name or "soul-seed"

    # display_name: 优先身份卡「我是谁」, 其次 frontmatter name
    identity = sections.get("身份卡", "") or ""
    m = re.search(r"我是谁\s*\*{0,2}\s*[:：]\s*(.+?)(?:\n|$)", identity)
    display = ""
    if m:
        raw_d = m.group(1).strip()
        raw_d = re.sub(r"^我是", "", raw_d)  # 「我是Steve Jobs」→「Steve Jobs」
        display = first_sentence(raw_d, limit=30)
    if not display:
        display = raw_name or slug.replace("-", " ").title()
    if display.endswith("-perspective"):
        display = display[:-len("-perspective")]

    desc = fm.get("description", "") or ""
    impression = first_sentence(desc) or first_sentence(identity) or display

    # 路由标签: 人名 + 心智模型名 + 显式 --labels
    tags = []
    if display and display not in tags:
        tags.append(display)
    if slug and slug not in tags:
        tags.append(slug)
    for n in model_names_:
        if n and n not in tags:
            tags.append(n)
    for l in extra_labels:
        if l and l not in tags:
            tags.append(l)
    # frontmatter name 中的域关键词(如 feynman-perspective)不再重复

    return {
        "slug": slug,
        "name": display,
        "display_name": display,
        "character": "celebrity",          # 与 dot-skill celebrity 族同构
        "research_profile": "budget-unfriendly",  # nuwa 为深度调研蒸馏
        "tags": {"personality": tags[:8]},
        "impression": impression,
        "source": "nuwa-skill",
    }


def convert(skill_dir: Path, out_dir: Path, extra_labels: list[str]) -> Path:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md 不存在: {skill_md}")

    text = skill_md.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    sections = {}
    for title, content in split_sections(body):
        if not title:
            continue
        if title in SKIP_SECTIONS:
            continue
        if title in PERSONA_SECTIONS:
            sections.setdefault(PERSONA_SECTIONS[title] or title, content)
        elif title in WORK_SECTIONS:
            sections.setdefault(WORK_SECTIONS[title] or title, content)
        elif title in VALUES_SECTIONS:
            sections.setdefault(VALUES_SECTIONS[title], content)
        # 未映射章节(如「最新动态」)忽略 — 种子只取宪法层相关结构

    # 角色扮演规则截取关键约束(规则条目到「退出角色」前)
    rp = sections.get("角色扮演规则", "")
    if rp:
        cut = rp.find("**退出角色**")
        if cut > 0:
            rp = rp[:cut].rstrip()
        sections["角色扮演规则(摘要)"] = rp

    meta = build_meta(fm, sections, model_names(body), extra_labels)
    persona = build_persona(sections)
    work = build_work(sections)
    values = build_values(sections)

    if not persona and not work:
        raise ValueError(f"未提取到 persona/work 内容, 请检查 SKILL.md 章节结构: {skill_md}")

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "persona.md").write_text(persona, encoding="utf-8")
    (out_dir / "work.md").write_text(work, encoding="utf-8")
    if values:
        (out_dir / "values.md").write_text(values, encoding="utf-8")

    # 调研原始材料引用(可选: 入库后作为该人格初始学习素材)
    research_dir = skill_dir / "references" / "research"
    if research_dir.is_dir():
        note = ("\n\n---\n\n## 调研原始材料\n"
                "nuwa 深研的 6 维原始素材位于本 skill 目录 references/research/ "
                "(01-writings … 06-timeline)。可选高级玩法: 入库到独立知识库后加入该人格 "
                "kb_scope, 让人格后天再消化一次自己的调研素材(见 butian-architecture.md §7)。\n")
        with (out_dir / "work.md").open("a", encoding="utf-8") as f:
            f.write(note)
    return out_dir


def main() -> int:
    ap = argparse.ArgumentParser(description="nuwa perspective SKILL.md → 补天 SOUL 种子包")
    ap.add_argument("skill_dir", type=Path, help="nuwa 产物目录(含 SKILL.md)")
    ap.add_argument("--out", type=Path, default=None, help="种子包输出目录(默认 <skill_dir>/soul-seed)")
    ap.add_argument("--labels", default="", help="额外路由标签, 逗号分隔(追加到 meta.tags.personality)")
    args = ap.parse_args()

    out = args.out or (args.skill_dir / "soul-seed")
    extra = [x.strip() for x in args.labels.split(",") if x.strip()]
    out = convert(args.skill_dir, out, extra)

    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    print(f"✅ 补天种子已生成: {out}")
    print(f"   slug:       {meta['slug']}")
    print(f"   display:    {meta['display_name']}")
    print(f"   路由标签:    {', '.join(meta['tags']['personality']) or '—'}")
    print(f"   persona.md: {(out/'persona.md').stat().st_size} bytes | "
          f"work.md: {(out/'work.md').stat().st_size} bytes"
          + (f" | values.md: {(out/'values.md').stat().st_size} bytes" if (out/'values.md').exists() else ""))
    print("\n下一步(补天落地):")
    print(f"  ragctl soul distill {out} --name soul-{meta['slug']} --scope <kb1,kb2>"
          + (" --values " + str(out / "values.md") if (out / "values.md").exists() else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
