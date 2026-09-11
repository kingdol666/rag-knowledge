#!/usr/bin/env python3
"""FlashRAG 评测数据集下载器 — Track 1 公开可比轨数据获取.

下载 RUC-NLPIR/FlashRAG_datasets 中本基准所需的全部评测集（jsonl 原样保存，
不做任何改写，保证与论文社区同一份数据 → 可与 CRAG/Self-RAG/Adaptive-RAG/
HiRAG 数字直接对比）。

用法:
  python download_datasets.py            # 仅下载评测集 (~120MB)
  python download_datasets.py --corpus   # 额外下载 Wikipedia-18 100w 语料 (4.9GB zip)
  python download_datasets.py --verify   # 校验已下载文件的行数与必需字段
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

BASE = "https://huggingface.co/datasets/RUC-NLPIR/FlashRAG_datasets/resolve/main"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "flashrag"

# (repo 相对路径, 必需字段)  — 规模为官方 FlashRAG 预处理版
# FlashRAG 统一 schema: {id, question, golden_answers, metadata{supporting_facts, context}}
EVAL_FILES = [
    ("popqa/test.jsonl", ["question", "golden_answers"]),          # 14,267 单跳
    ("nq/test.jsonl", ["question", "golden_answers"]),             # 3,610 单跳
    ("triviaqa/test.jsonl", ["question", "golden_answers"]),       # 11,313 单跳
    ("hotpotqa/dev.jsonl", ["question", "golden_answers"]),        # 7,405 2跳
    ("2wikimultihopqa/dev.jsonl", ["question", "golden_answers"]), # 12,576 2-3跳
    ("musique/dev.jsonl", ["question", "golden_answers"]),         # 2,417 2-4跳
    ("bamboogle/test.jsonl", ["question", "golden_answers"]),      # 125 多跳难题
]
CORPUS_FILE = "retrieval-corpus/wiki18_100w.zip"                 # 21,015,324 docs, 4.9GB


def download(rel: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(rel).name
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  skip (exists): {rel}")
        return dest
    url = f"{BASE}/{rel}"
    print(f"  downloading: {url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)  # nosec — 固定公开数据源
    tmp.rename(dest)
    print(f"  -> {dest} ({dest.stat().st_size / 1048576:.1f} MB)")
    return dest


def verify(files: list[tuple[str, list[str]]]) -> int:
    ok = 0
    for rel, fields in files:
        path = DATA_DIR / rel
        if not path.exists():
            print(f"  MISSING: {path}")
            continue
        n, bad = 0, 0
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                n += 1
                rec = json.loads(line)
                if not all(k in rec for k in fields):
                    bad += 1
        status = "OK" if bad == 0 and n > 0 else "BAD"
        print(f"  [{status}] {rel}: {n} rows, {bad} missing-field rows")
        ok += status == "OK"
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", action="store_true", help="同时下载 wiki18_100w.zip (4.9GB)")
    ap.add_argument("--verify", action="store_true", help="只校验已下载文件")
    args = ap.parse_args()

    if args.verify:
        done = verify(EVAL_FILES)
        print(f"{done}/{len(EVAL_FILES)} datasets verified")
        return 0 if done == len(EVAL_FILES) else 1

    print(f"Downloading {len(EVAL_FILES)} eval datasets -> {DATA_DIR}")
    for rel, _ in EVAL_FILES:
        download(rel, DATA_DIR / Path(rel).parent)

    if args.corpus:
        print("Downloading Wikipedia corpus (4.9GB, 耐心等待)...")
        download(CORPUS_FILE, DATA_DIR / "retrieval-corpus")
        zip_path = DATA_DIR / CORPUS_FILE
        print("Extracting...")
        import zipfile
        extract_root = (DATA_DIR / "retrieval-corpus").resolve()
        with zipfile.ZipFile(zip_path) as z:
            for member in z.infolist():
                target = (extract_root / member.filename).resolve()
                # canonical zip-slip check: target must be strictly inside extract_root
                if target == extract_root or extract_root not in target.parents:
                    raise ValueError(f"zip 条目越界，拒绝解压: {member.filename}")
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(member) as src, open(target, "wb") as dst:
                    dst.write(src.read())
        print("Done:", list(extract_root.glob('*.jsonl')))

    print("\nAll downloads complete. Run with --verify to validate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
