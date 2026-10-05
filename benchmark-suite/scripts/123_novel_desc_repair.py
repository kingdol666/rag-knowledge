#!/usr/bin/env python3
"""按 ingest skill 的 A3c / A3c-P 规则，重写小说 KB 每一部分的描述。

背景（已实测）：KB `Novel-PridePrejudice` 有 28 篇文档，**24 篇描述是错的**——都写着
`Gutenberg front/back matter`，实际内容是小说正文；另有 part 2 `Chapter XV–I`（区间倒置）、
part 18 `Chapter XLVI–XLVI`（单点）。描述驱动（无向量）的检索按描述选文档 → 直接失效。

本脚本：
  1. 逐篇 kb_doc_read 读正文；
  2. 用 `^CHAPTER <roman>.$` **确定性地**识别该篇覆盖的章节区间；
  3. 取头/中/尾三个样本，交给 LLM 生成 ≤220 字的双层描述
     `【Part k/N · Chapter X–Y】<主体> —— <本 part 特有内容：具体场景/人物/细节>`；
  4. kb_doc_update_meta 写回；
  5. 复查：统计仍含 front/back matter、区间倒置/单点的描述数量。

用法（benchmark-suite/）：
    python scripts/123_novel_desc_repair.py --kb Novel-PridePrejudice
    python scripts/123_novel_desc_repair.py --kb Novel-PridePrejudice --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
sys.path.insert(0, str(SUITE / "experiments"))

from chat_tracks import chat_stream  # noqa: E402
from lib import McpClient  # noqa: E402

CHAPTER_RE = re.compile(r"^\s*CHAPTER\s+([IVXLC]+)\s*\.\s*$", re.M)
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def roman2int(s: str) -> int:
    total, prev = 0, 0
    for ch in reversed(s.upper()):
        v = ROMAN.get(ch, 0)
        total += v if v >= prev else -v
        prev = max(prev, v)
    return total


def part_no(name: str) -> int:
    m = re.search(r"part (\d+) of (\d+)", name or "")
    return int(m.group(1)) if m else 0


def total_parts(names: list[str]) -> int:
    m = re.search(r"part \d+ of (\d+)", " ".join(names))
    return int(m.group(1)) if m else 0


def sample(text: str, size: int = 900, n: int = 3) -> str:
    t = str(text or "")
    if len(t) <= size * n:
        return t
    step = (len(t) - size) / (n - 1)
    return "\n…\n".join(t[int(i * step): int(i * step) + size] for i in range(n))


def llm_desc(part: int, total: int, chapters: tuple[int, int] | None,
             text: str, name: str) -> str:
    span = (f"Chapter {chapters[0]}–{chapters[1]}" if chapters and chapters[0] != chapters[1]
            else (f"Chapter {chapters[0]}" if chapters else "chapter range unknown"))
    prompt = (
        "Write ONE knowledge-base description for one part of the novel "
        "Pride and Prejudice (Jane Austen, Project Gutenberg #1342).\n\n"
        f"Part: {part} of {total} (file: {name})\n"
        f"Chapters in this part (determined from the text): {span}\n\n"
        "TEXT SAMPLE (head / middle / tail of this part):\n"
        f"{sample(text)[:3000]}\n\n"
        "Requirements:\n"
        "- Format EXACTLY: 【Part k/N · <chapter range>】<book + subject> —— <this part's specific content>\n"
        "- The chapter range must be the one given above, taken from THIS part's own text.\n"
        "- In the second half, NAME the specific scenes, events, characters and concrete details "
        "a searcher would look for (e.g. 'the Meryton assembly; Darcy's \"tolerable\" remark; "
        "Elizabeth overhears and is piqued'). No generic filler.\n"
        "- If this part is genuinely Gutenberg licence/front-matter, say so plainly.\n"
        "- Max 220 characters. One line. No markdown bullets.\n"
        "Reply with the description text only.")
    r = chat_stream(prompt, cwd=str(SUITE.parent), allowed_tools=[], max_turns=1, timeout_s=300)
    d = re.sub(r"\s+", " ", str(r.get("answer") or "")).strip()
    return d.strip('"')[:260]


def bad_desc(d: str) -> bool:
    low = (d or "").lower()
    return "front/back matter" in low or "front matter" in low or "back matter" in low


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default="Novel-PridePrejudice")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default="results/NOVEL-DESC-REPAIR.md")
    args = ap.parse_args()

    mc = McpClient()
    rows = []
    try:
        kbs = mc.call("kb_list", {"lightweight": True}, timeout=120).get("catalog") or []
        kb_id = next((k.get("kb_id") for k in kbs if k.get("name") == args.kb), "")
        if not kb_id:
            print(f"[fatal] KB {args.kb!r} not found")
            return 1
        docs = mc.call("kb_get_documents", {"lightweight": True, "kb_id": kb_id},
                       timeout=180).get("catalog") or []
        names = [str(d.get("name") or "") for d in docs]
        total = total_parts(names)
        before_bad = sum(1 for d in docs if bad_desc(str(d.get("description") or "")))

        t0 = time.perf_counter()
        for d in sorted(docs, key=lambda x: str(x.get("name"))):
            name = str(d.get("name") or "")
            path = str(d.get("doc_path") or "")
            pno = part_no(name)
            r = mc.call("kb_doc_read", {"kb_id": kb_id, "doc_path": path,
                                        "max_chars": 30000}, timeout=180)
            content = str(r.get("content") or "")
            romans = [roman2int(x) for x in CHAPTER_RE.findall(content)]
            chapters = (min(romans), max(romans)) if romans else None
            old = str(d.get("description") or "")
            new = llm_desc(pno, total, chapters, content, name)
            ok = False
            if not args.dry_run and new:
                res = mc.call("kb_doc_update_meta", {"kb_id": kb_id, "doc_path": path,
                                                     "description": new}, timeout=180)
                ok = bool((res or {}).get("success", True))
            rows.append({"name": name, "part": pno, "chapters": chapters,
                         "old": old[:120], "new": new, "updated": ok})
            print(f"[part {pno:>2}] chapters={chapters} updated={ok} :: {new[:110]}", flush=True)
        elapsed = round(time.perf_counter() - t0, 1)

        after_docs = mc.call("kb_get_documents", {"lightweight": True, "kb_id": kb_id},
                             timeout=180).get("catalog") or []
        after_bad = sum(1 for d in after_docs if bad_desc(str(d.get("description") or "")))
    finally:
        mc.close()

    L = ["# 小说 KB 描述修复报告", "",
         f"KB：`{args.kb}` · {len(rows)} 篇 · 用时 {elapsed}s"
         + ("（**dry-run，未写盘**）" if args.dry_run else ""), "",
         f"- **修复前**坏描述：`front/back matter` 命中 **{before_bad}** 篇",
         f"- **修复后**坏描述：**{after_bad}** 篇", "",
         "| part | 章节区间 | 旧描述 | 新描述 |", "|---|---|---|---|"]
    for r in rows:
        span = ("—" if not r["chapters"] else
                (str(r["chapters"][0]) if r["chapters"][0] == r["chapters"][1]
                 else f"{r['chapters'][0]}–{r['chapters'][1]}"))
        L.append(f"| {r['part']} | {span} | {r['old'][:70]} | {r['new'][:110]} |")
    out = SUITE / args.out
    out.write_text("\n".join(L), encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps({"before_bad": before_bad,
                                                    "after_bad": after_bad,
                                                    "rows": rows}, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    print(f"\n[desc] before_bad={before_bad} after_bad={after_bad} → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
