# -*- coding: utf-8 -*-
"""合并既有 KB_SPECS（18 篇）与扩充 spec（corpus_spec.json）→ corpus_spec_final.json。

输出结构（S2/S4/manifest 的单一事实源）：
  [ {slug, kb_name, kb_desc, docs: [{file, name, desc, anchor, question}]} ]  × 11 域
运行: python merge_spec.py
"""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ART = BASE.parent / "artifacts"
sys.path.insert(0, str(BASE))
from s2_ingest_corpus import KB_SPECS as OLD_SPECS  # noqa: E402  既有 18 篇（含描述）

NEW_DOMAIN_META = {
    "philosophy-en": ("MD语料-哲学-英文",
                      "Gutenberg 公版哲学整本：Meditations、Republic、The Prince、Zarathustra、Art of War、Walden、Common Sense、Beyond Good and Evil"),
    "economics-en": ("MD语料-经济-英文",
                     "Gutenberg 公版经济学经典整本：Wealth of Nations、Theory of the Leisure Class、On Liberty、Malthus 人口论"),
}

merged = {}
for spec in OLD_SPECS:
    merged[spec["slug"]] = dict(
        slug=spec["slug"], kb_name=spec["name"], kb_desc=spec["desc"],
        docs=[dict(file=fp, name=nm, desc=d, anchor=None, question=None)
              for fp, nm, d in spec["docs"]])

# 并集保护：上一版 corpus_spec_final 的条目先行并入（防跨轮 spec 有损）
final_prev = ART / "corpus_spec_final.json"
if final_prev.exists():
    for m in json.loads(final_prev.read_text(encoding="utf-8")):
        slot = merged.setdefault(m["slug"], dict(slug=m["slug"], kb_name=m["kb_name"],
                                                 kb_desc=m["kb_desc"], docs=[]))
        have = {d["file"] for d in slot["docs"]}
        for d in m["docs"]:
            if d["file"] not in have:
                slot["docs"].append(d)

spec_new = json.loads((ART / "corpus_spec.json").read_text(encoding="utf-8"))
for slug, docs in (spec_new.get("docs") or {}).items():
    if slug not in merged:
        kb_name, kb_desc = NEW_DOMAIN_META[slug]
        merged[slug] = dict(slug=slug, kb_name=kb_name, kb_desc=kb_desc, docs=[])
    have = {d["file"] for d in merged[slug]["docs"]}
    for d in docs:
        if d["file"] not in have:
            merged[slug]["docs"].append(d)

out = ART / "corpus_spec_final.json"
final = list(merged.values())
out.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
total_docs = sum(len(m["docs"]) for m in final)
print(f"domains={len(final)} docs={total_docs}")
for m in final:
    print(f"  {m['slug']:14s} {len(m['docs']):3d} docs  {m['kb_name']}")
print(f"→ {out}")
