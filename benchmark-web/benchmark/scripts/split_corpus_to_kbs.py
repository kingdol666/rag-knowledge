#!/usr/bin/env python3
"""Wikipedia 语料按主题拆分为多知识库 — 本系统独有的多 KB 评测协议.

输入: data/flashrag/retrieval-corpus/ 下的 wiki-18.jsonl（FlashRAG 官方 wiki18_100w）
输出: data/benchmarks/kb_split/
  ├── kb_assignments.json     golden title → 主题 KB 映射（qrels 引用的 7,034 个）
  ├── pages_KB-*.jsonl        每 KB 一个分片, 每行一个 wiki 页面 {title, kb, content}
  ├── kb_pages_stats.json     每 KB 页面数统计（golden 数 + 干扰页数）
  └── corpus_stats.json       语料指纹（行数/sha256 前 16 位/采样参数）→ 复现凭证

确定性设计（任何人重跑得到逐字节一致结果）:
  * golden 页面: qrels 引用的 title 全量保留（拆成页面, 每页 = 该 title 的全部 passage 拼接）
  * 干扰页面: 每 KB 取 sha256(title) 排序后的前 --pages-per-kb 个（与内容无关的稳定序）
  * wiki18 id 形如 "{Title}_passage{N}"（下划线代空格）→ 标题还原: 去后缀 + 下划线转空格

用法:
  python split_corpus_to_kbs.py --sample-only            # 仅映射 qrels titles（无需语料）
  python split_corpus_to_kbs.py --pages-per-kb 1000      # 默认: 每KB 1000干扰页+全量golden页
  python split_corpus_to_kbs.py --pages-per-kb 200       # 快速冒烟规模
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent.parent / "data" / "benchmarks"
CORPUS_DIR = Path(__file__).resolve().parent.parent / "data" / "flashrag" / "retrieval-corpus"
OUT_DIR = BENCH_DIR / "kb_split"
SEED = 42  # 保留参数位: 采样本身用 sha256 稳定序, 与种子无关; 修改采样规则时递增 CORPUS_SCHEMA 版本

# 主题 KB 关键词规则（标题匹配, 顺序即优先级）
RULES = [
    ("KB-Film-TV",          r"film|movie|television|series|actor|actress|cinema|season \d"),
    ("KB-Music",            r"band|album|singer|song|music|orchestra|guitar|discography"),
    ("KB-Sports",           r"football|soccer|basketball|baseball|tennis|olympic|cricket|club|hockey|rugby|f\.c\."),
    ("KB-Politics-History", r"war|battle|president|prime minister|election|dynasty|empire|kingdom|republic|revolution|treaty|politic|government"),
    ("KB-Geography",        r"river|mountain|island|lake|city|province|county|region|desert|forest|glacier|station\b"),
    ("KB-Bio-Medicine",     r"protein|gene|disease|virus|cancer|cell\b|medical|hospital|medicine|enzyme|syndrome|vaccine"),
    ("KB-Science-Tech",     r"telescope|planet|star|physics|chemistry|quantum|nuclear|satellite|spacecraft|mathematic|algorithm|software|computer"),
    ("KB-Transport",        r"railway|railroad|airline|airport|ship|locomotive|highway|aircraft|submarine|carrier"),
    ("KB-Literature-Arts",  r"novel|writer|poet|painter|artist|sculptor|museum|architect|philosoph|theolog"),
    ("KB-Economy-Law",      r"company|bank|university|school|college|court|law|economy|industry|corporation"),
    ("KB-Military",         r"army|navy|air force|military|division \(military\)|regiment|battalion|fleet"),
    ("KB-People",           r"^[A-Z][a-z]+(?: [A-Z][a-z]+)+$"),  # 人名模式兜底
]
FALLBACK_KB = "KB-Other"
COMPILED = [(kb, re.compile(pat, re.IGNORECASE)) for kb, pat in RULES]
_PASSAGE_SUFFIX = re.compile(r"_passage_?\d+$|_\d{1,4}$")


def classify_title(title: str) -> str:
    for kb, pat in COMPILED:
        if pat.search(title):
            return kb
    return FALLBACK_KB


def id_to_title(doc_id: str) -> str:
    """FlashRAG 旧式 id 兜底: "{Title}_passage{N}" → 标题（下划线转空格）。"""
    t = _PASSAGE_SUFFIX.sub("", doc_id)
    return t.replace("_", " ").strip()


def passage_title(rec: dict) -> str:
    """wiki18_100w 行 → 页面标题。

    实测格式（2026-09-10 解压产物）: {"id": <数字>, "contents": "\\"标题\\"\\n标题 正文..."}
    标题 = contents 首行去掉引号。兼容 FlashRAG 其他版本 "{Title}_passage{N}" id 风格。
    """
    contents = rec.get("contents") or rec.get("content") or ""
    if "\n" in contents:
        first_line = contents.split("\n", 1)[0].strip()
        if first_line.startswith('"') and first_line.endswith('"'):
            title = first_line.strip('"')
            if title:
                return title
    return id_to_title(str(rec.get("id", "")))


def golden_titles() -> set[str]:
    titles: set[str] = set()
    for q in sorted(BENCH_DIR.glob("qrels_*.tsv")):
        for line in q.open(encoding="utf-8"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 3:
                titles.add(parts[2])
    return titles


def find_corpus_file() -> Path | None:
    if not CORPUS_DIR.exists():
        return None
    for name in ("wiki-18.jsonl", "wiki18_100w.jsonl", "wiki-18.zip.jsonl"):
        p = CORPUS_DIR / name
        if p.exists():
            return p
    for p in sorted(CORPUS_DIR.rglob("*.jsonl")):  # zip 解压后位置不确定, 兜底搜索
        if p.stat().st_size > 1024 * 1024:
            return p
    return None


def sha256_16(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-only", action="store_true",
                    help="只映射 qrels 引用的 title（无需 4.9GB 语料）")
    ap.add_argument("--pages-per-kb", type=int, default=1000,
                    help="每 KB 干扰页面数（golden 页面不受影响, 全量保留）")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    golden = golden_titles()
    assignments = {t: classify_title(t) for t in sorted(golden)}
    print(f"qrels unique golden titles: {len(golden)}")
    stats = Counter(assignments.values())
    for kb, c in stats.most_common():
        print(f"  {kb:<22} {c}")

    if args.sample_only:
        (OUT_DIR / "kb_assignments.json").write_text(
            json.dumps(assignments, indent=1, ensure_ascii=False), encoding="utf-8")
        (OUT_DIR / "kb_stats.json").write_text(
            json.dumps(dict(stats.most_common()), indent=1, ensure_ascii=False),
            encoding="utf-8")
        print("✓ sample-only 模式: kb_assignments.json / kb_stats.json 已写出")
        return

    corpus = find_corpus_file()
    if corpus is None:
        raise SystemExit(
            f"❌ 未找到语料文件（先运行 download_datasets.py --corpus）; "
            f"已搜索: {CORPUS_DIR}")

    # ── Pass 1: 只收集标题集合（不驻留正文 → 内存可控 ~500MB）──
    print(f"corpus: {corpus.name} ({corpus.stat().st_size / 1048576:.0f} MB), pass 1/2 "
          f"(收集标题) ...", flush=True)
    all_titles: set[str] = set()
    n_lines = 0
    import time as _time
    t0 = _time.perf_counter()
    with corpus.open(encoding="utf-8") as f:
        for line in f:
            n_lines += 1
            if not line.strip():
                continue
            t = passage_title(json.loads(line))
            if t:
                all_titles.add(t)
            if n_lines % 1_000_000 == 0:
                rate = n_lines / max(_time.perf_counter() - t0, 1)
                eta = (21015324 - n_lines) / max(rate, 1) / 60
                print(f"  scanned {n_lines:,} lines, {len(all_titles):,} titles "
                      f"({rate:,.0f} lines/s, ETA {eta:.0f} min)", flush=True)
    print(f"pass 1 done: {n_lines:,} passages -> {len(all_titles):,} pages "
          f"({_time.perf_counter() - t0:.0f}s)", flush=True)

    pages_ci = {t.casefold(): t for t in all_titles}
    found = sum(1 for t in golden if t in all_titles)
    found_ci = found + sum(1 for t in golden
                           if t not in all_titles and t.casefold() in pages_ci)
    print(f"golden 命中: 精确+大小写不敏感 {found_ci}/{len(golden)}", flush=True)

    # ── 选择页面: golden 全量 + 每 KB 干扰页 (sha256 稳定序取前 K) ──
    golden_ci = {t.casefold() for t in golden}
    distractors: dict[str, list[str]] = defaultdict(list)  # kb -> [titles]
    for title in all_titles:
        if title in golden or title.casefold() in golden_ci:
            continue
        distractors[classify_title(title)].append(title)
    selected: set[str] = {t for t in golden if t in all_titles}
    for t in golden:  # 大小写不敏感的补充匹配
        if t not in selected and t.casefold() in pages_ci:
            selected.add(pages_ci[t.casefold()])
    dist_stats: Counter = Counter()
    for kb, titles in distractors.items():
        titles.sort(key=lambda t: hashlib.sha256(t.encode("utf-8")).hexdigest())
        pick = titles[:args.pages_per_kb]
        selected.update(pick)
        dist_stats[kb] = len(pick)
    selected_ci = {t.casefold(): t for t in selected}
    print(f"selected pages: {len(selected):,} (golden {len(selected) - sum(dist_stats.values()):,}"
          f" + distractor {sum(dist_stats.values()):,})", flush=True)

    # ── Pass 2: 流式重扫, 仅对选中标题累积正文（内存 = 选中页文本 ~200MB）──
    print("pass 2/2 (抽取选中页正文) ...", flush=True)
    bodies: dict[str, list[str]] = defaultdict(list)
    with corpus.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            title = passage_title(rec)
            key = title if title in selected else selected_ci.get(title.casefold())
            if key is None:
                continue
            body = rec.get("contents") or rec.get("content") or ""
            # 去掉每个 passage 开头重复的标题行（内容以 "\"标题\"\n" 或 "标题 " 开头）
            if body.startswith(f'"{key}"'):
                body = body.split("\n", 1)[1] if "\n" in body else ""
            elif body.startswith(key):
                body = body[len(key):].lstrip()
            bodies[key].append(body)

    # ── 写出每 KB 分片 ──
    streams: dict[str, object] = {}
    page_stats: Counter = Counter()
    for title in sorted(selected):
        if title not in bodies:
            continue  # 语料中不存在该标题（qrels 引用但语料缺失）
        kb = assignments.get(title) or classify_title(title)
        w = streams.get(kb)
        if w is None:
            w = (OUT_DIR / f"pages_{kb}.jsonl").open("w", encoding="utf-8")
            streams[kb] = w
        content = "\n\n".join(b for b in bodies[title] if b)
        w.write(json.dumps({"title": title, "kb": kb, "content": content},
                           ensure_ascii=False) + "\n")
        page_stats[kb] += 1
    for w in streams.values():
        w.close()

    corpus_stats = {
        "corpus_file": corpus.name,
        "corpus_sha256_16": sha256_16(corpus),
        "passages": n_lines,
        "pages_total": len(all_titles),
        "golden_titles": len(golden),
        "golden_found": found_ci,
        "distractors_per_kb": args.pages_per_kb,
        "sampling": "sha256(title) stable order",
        "pages_selected": sum(page_stats.values()),
        "schema_version": 2,
    }
    (OUT_DIR / "kb_assignments.json").write_text(
        json.dumps(assignments, indent=1, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "kb_pages_stats.json").write_text(json.dumps({
        "per_kb": {kb: {"golden": stats.get(kb, 0) + 0, "distractor": dist_stats.get(kb, 0),
                        "pages_written": page_stats.get(kb, 0)}
                   for kb in sorted(set(stats) | set(dist_stats))},
        "corpus": corpus_stats}, indent=1, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "corpus_stats.json").write_text(
        json.dumps(corpus_stats, indent=1, ensure_ascii=False), encoding="utf-8")

    print("\n每 KB 页面数 (golden+干扰):")
    for kb in sorted(page_stats, key=lambda k: -page_stats[k]):
        print(f"  {kb:<22} golden={stats.get(kb,0):<5} distractor={dist_stats.get(kb,0):<6} "
              f"written={page_stats[kb]}")
    print(f"\n✓ 共 {sum(page_stats.values()):,} 页 -> {OUT_DIR}/pages_KB-*.jsonl")


if __name__ == "__main__":
    main()
