#!/usr/bin/env python3
"""构建固定评测子集 + qrels（可复现的样本冻结步骤）.

从已下载的 FlashRAG 原始 jsonl 中，按固定随机种子(seed=42)抽取子集，
生成带相关性标签(qrels)的评测文件。qrels 三种来源：
  A. multi-hop (hotpotqa/2wiki/musique): metadata.supporting_facts.title = golden wiki 页面
  B. popqa: metadata.s_wiki_title = golden subject wiki 页面（CRAG 论文同款用法）
  C. nq/triviaqa/bamboogle: 无 golden title → 仅端到端 QA(EM/F1)用，
     检索 gold 用 "answer 子串命中" 规则（Self-RAG 论文同款协议）

产物:
  data/benchmarks/{name}.jsonl      评测样本
  data/benchmarks/qrels_{name}.tsv  qid \t 0 \t doc_title \t 1  (TREC 格式)
  data/benchmarks/MANIFEST.json     每个文件的 SHA256 + 行数 + seed → 复现凭证

用法: python build_benchmark_sets.py [--seed 42]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

FLASHRAG_DIR = Path(__file__).resolve().parent.parent / "data" / "flashrag"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "benchmarks"

# (数据集名, 源文件, 抽样数, 单跳|多跳, golden_title 字段路径)
SPECS = [
    ("popqa",   "popqa/test.jsonl",           2000, "single", ["metadata", "s_wiki_title"]),
    ("nq",      "nq/test.jsonl",              1000, "single", None),
    ("triviaqa","triviaqa/test.jsonl",        1000, "single", None),
    ("hotpotqa","hotpotqa/dev.jsonl",         1000, "multi",  ["metadata", "supporting_facts", "title"]),
    ("2wiki",   "2wikimultihopqa/dev.jsonl",  1000, "multi",  ["metadata", "supporting_facts", "title"]),
    # musique: golden 标签按跳存于 question_decomposition[*].support_paragraph.title
    ("musique", "musique/dev.jsonl",           500, "multi",  "@musique"),
    ("bamboogle","bamboogle/test.jsonl",       125, "multi",  None),  # 无 metadata, 仅端到端 QA
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def get_field(rec: dict, path: list[str] | None):
    if not path:
        return None
    cur = rec
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    # 固定种子是本脚本的功能性要求（样本冻结/可复现），非加密用途——禁改 secrets
    rng = random.Random(args.seed)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = {"seed": args.seed, "source": "RUC-NLPIR/FlashRAG_datasets", "files": {}}

    for name, rel, n, hop, title_path in SPECS:
        src = FLASHRAG_DIR / rel
        rows = [json.loads(l) for l in src.open(encoding="utf-8") if l.strip()]
        sampled = rng.sample(rows, min(n, len(rows)))

        out_path = OUT_DIR / f"{name}.jsonl"
        qrels_path = OUT_DIR / f"qrels_{name}.tsv"
        n_qrels = 0
        with out_path.open("w", encoding="utf-8") as fo, qrels_path.open("w", encoding="utf-8") as fq:
            for rec in sampled:
                qid = rec["id"]
                item = {
                    "qid": qid,
                    "question": rec["question"],
                    "golden_answers": rec["golden_answers"],
                    "hop": hop,
                }
                if name == "2wiki" and "type" in rec.get("metadata", {}):
                    item["reasoning_type"] = rec["metadata"]["type"]
                if title_path == "@musique":
                    titles = [d["support_paragraph"]["title"]
                              for d in rec.get("metadata", {}).get("question_decomposition", [])
                              if isinstance(d, dict) and d.get("support_paragraph", {}).get("title")]
                else:
                    titles = get_field(rec, title_path)
                if isinstance(titles, str):
                    titles = [titles]
                if titles:
                    titles = [t for t in titles if t]
                    item["golden_titles"] = titles
                    for t in titles:
                        fq.write(f"{qid}\t0\t{t}\t1\n")
                        n_qrels += 1
                fo.write(json.dumps(item, ensure_ascii=False) + "\n")

        manifest["files"][out_path.name] = {"sha256": sha256(out_path), "rows": len(sampled)}
        manifest["files"][qrels_path.name] = {"sha256": sha256(qrels_path), "rows": n_qrels}
        print(f"[{name}] sampled {len(sampled)} (hop={hop}), qrels entries={n_qrels}")

    (OUT_DIR / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nMANIFEST.json written — 把它提交进 git，评测报告必须引用它")


if __name__ == "__main__":
    main()
