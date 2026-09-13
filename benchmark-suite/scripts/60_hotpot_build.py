#!/usr/bin/env python3
"""E8-1 · HotpotQA 多域公开基准 — 支撑文档拆主题 KB 入库（修 TODO-12）.

数据: HotpotQA dev-distractor (7,405 题, parquet, hf-mirror 下载)。
构造（确定性, 无 LLM 无 RNG）:
  1. 均匀抽取 50 题（按 id 排序等距采样）。
  2. 每题 context 的全部段落（2 官方支撑 + 8 同域干扰）按标题去重成文档，
     md 文件名 `Title [hotpot-<hash8>].md`。
  3. 标题+文本按关键词规则映射到 9 个主题 KB（8 主题 + General 兜底），
     同题两篇支撑文档常落入不同 KB → 金标天然跨库。
  4. 入库走生产 API（create → batch-index → vector ready）。
产出: results/run-*/hotpot_manifest.json + data/hotpotqa/{docs/<KB>/*.md, queries.jsonl}
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import WEB, http_get, http_post, env_fingerprint, now_iso, set_run  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
PARQUET = HERE / "data" / "hotpotqa" / "hotpot_dev.parquet"
DOCROOT = HERE / "data" / "hotpotqa"
N_QUESTIONS = 50

TOPICS: dict[str, list[str]] = {
    "KB-Hotpot-Geography": ["river", "mountain", "city", "island", "lake", "desert",
                             "country", "province", "state", "geograph", "continent",
                             "valley", "forest", "park", "climate"],
    "KB-Hotpot-History": ["war", "dynasty", "empire", "history", "ancient", "century",
                           "revolution", "treaty", "civilization", "medieval", "king",
                           "battle", "colonial"],
    "KB-Hotpot-Politics": ["president", "government", "election", "parliament",
                            "minister", "senate", "policy", "party", "congress",
                            "political", "governor", "mayor"],
    "KB-Hotpot-Music": ["music", "album", "song", "band", "singer", "orchestra",
                         "symphony", "record label", "guitar", "single (music)",
                         "composer", "opera"],
    "KB-Hotpot-FilmTV": ["film", "movie", "television", "actor", "actress", "director",
                          "cinema", "series", "drama", "hollywood", "screen"],
    "KB-Hotpot-Literature": ["novel", "writer", "author", "poet", "book", "literature",
                              "playwright", "novelist", "fiction", "magazine", "press"],
    "KB-Hotpot-Science": ["physic", "chemis", "biolog", "scientist", "planet", "energy",
                           "medicine", "disease", "space", "mathemat", "species",
                           "theory", "research", "university"],
    "KB-Hotpot-Sports": ["football", "soccer", "basketball", "baseball", "tennis",
                          "olympic", "sport", "league", "club", "cup", "champion",
                          "hockey", "cricket", "rugby"],
}
FALLBACK = "KB-Hotpot-General"
ALL_KBS = list(TOPICS) + [FALLBACK]


def classify(title: str, text: str) -> str:
    blob = f"{title} {text}".lower()
    best, best_n = FALLBACK, 0
    for kb, kws in TOPICS.items():
        n = sum(blob.count(k) for k in kws)
        if n > best_n:
            best, best_n = kb, n
    return best


def doc_id(title: str) -> str:
    return hashlib.sha256(title.encode()).hexdigest()[:8]


def sanitize(name: str) -> str:
    for ch in '\\/:*?"<>|\n\t':
        name = name.replace(ch, " ")
    return name.strip()[:110]


def ensure_kb(name: str) -> str:
    try:
        r = http_post(f"{WEB}/api/kb/create",
                      {"name": name, "description": "HotpotQA topic KB"},
                      timeout=90)
        return r["knowledgeBase"]["id"]
    except Exception as e:  # noqa: BLE001
        if "409" in str(e) or "exists" in str(e).lower():
            cat = http_get(f"{WEB}/api/kb/catalog", timeout=120)
            for k in cat.get("knowledgeBases") or []:
                if k.get("name") == name:
                    return k.get("kbId") or k.get("id")
        raise


def main() -> int:
    outdir = set_run()
    t = pq.read_table(PARQUET).to_pylist()
    t = sorted(t, key=lambda r: r["id"])
    step = max(1, len(t) // N_QUESTIONS)
    qs = t[::step][:N_QUESTIONS]

    titles: dict[str, dict] = {}   # title -> {text, kb}
    for q in qs:
        ctx_titles = q["context"]["title"]
        ctx_sents = q["context"]["sentences"]
        for ti, sents in zip(ctx_titles, ctx_sents):
            if ti not in titles:
                titles[ti] = {"text": "".join(sents)}
    for title, rec in titles.items():
        rec["kb"] = classify(title, rec["text"])

    gold_span = sum(1 for q in qs
                    if len({titles[ti]["kb"] for ti in set(q["supporting_facts"]["title"])
                            if ti in titles}) >= 2)
    print(f"questions={len(qs)} docs={len(titles)} cross-KB-gold={gold_span}/{len(qs)}",
          flush=True)

    # 写文档文件
    docroot = DOCROOT / "docs"
    for kb in ALL_KBS:
        (docroot / kb).mkdir(parents=True, exist_ok=True)
    for title, rec in titles.items():
        fn = docroot / rec["kb"] / f"{sanitize(title)} [hotpot-{doc_id(title)}].md"
        fn.write_text(f"# {title}\n\n{rec['text']}\n", encoding="utf-8")

    # queries.jsonl
    with (DOCROOT / "queries.jsonl").open("w", encoding="utf-8") as f:
        for q in qs:
            golds = sorted(set(q["supporting_facts"]["title"]))
            f.write(json.dumps({"qid": q["id"], "question": q["question"],
                                "answer": q["answer"], "type": q["type"],
                                "level": q["level"],
                                "golden_titles": golds,
                                "golden_kbs": sorted({titles[g]["kb"] for g in golds})},
                               ensure_ascii=False) + "\n")

    # 入库
    kb_ids: dict[str, str] = {}
    for kb in ALL_KBS:
        kb_ids[kb] = ensure_kb(kb)
        print(f"  KB ready: {kb} = {kb_ids[kb][:8]}…", flush=True)

    def wait_vector_ready(kb_id: str, timeout_s: int = 300) -> bool:
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            try:
                r = http_get(f"{WEB}/api/kb/vector-status?kb_id={kb_id}", timeout=60)
                if r.get("ready") or r.get("vector_ready"):
                    return True
            except Exception:  # noqa: BLE001
                pass
            time.sleep(6)
        return False

    n_created = n_exists = n_failed = 0
    for kb in ALL_KBS:
        files = sorted((docroot / kb).glob("*.md"))
        names = []
        for fn in files:
            content = fn.read_text(encoding="utf-8")
            name = fn.name
            try:
                http_post(f"{WEB}/api/kb/documents/create",
                          {"kbId": kb_ids[kb], "name": name, "content": content,
                           "description": "hotpotqa corpus"}, timeout=90)
                n_created += 1
            except Exception as e:  # noqa: BLE001
                if "409" in str(e):
                    n_exists += 1
                else:
                    n_failed += 1
                    print(f"  create failed {name[:40]}: {str(e)[:60]}", flush=True)
            names.append(name)
        for s in range(0, len(names), 40):
            try:
                http_post("http://localhost:8771/api/v1/search/batch-index",
                          {"kb_id": kb_ids[kb], "doc_paths": names[s:s+40],
                           "force": False}, timeout=600)
                print(f"  batch-index {kb} {len(names[s:s+40])} ok", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"  batch-index {kb} warn: {str(e)[:60]}", flush=True)
        ok = wait_vector_ready(kb_ids[kb])
        print(f"  [{kb}] files={len(files)} vector_ready={ok}", flush=True)

    manifest = {
        "experiment": "E8 multi-domain public benchmark (TODO-12)",
        "source": "HotpotQA dev-distractor (yang et al. 2018), parquet via hf-mirror",
        "n_questions": len(qs), "n_docs": len(titles),
        "n_created": n_created, "n_exists": n_exists, "n_failed": n_failed,
        "cross_kb_gold": f"{gold_span}/{len(qs)}",
        "topic_rule": "keyword-overlap argmax over title+text; fallback General",
        "kbs": kb_ids,
        "doc_per_kb": {kb: len(list((docroot / kb).glob('*.md'))) for kb in ALL_KBS},
        "meta": {"generated": now_iso(), "env": env_fingerprint()},
    }
    out = outdir / "hotpot_manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out}")
    print(json.dumps({k: v for k, v in manifest.items() if k != "env"},
                     ensure_ascii=False, indent=1)[:800])
    return 0


if __name__ == "__main__":
    sys.exit(main())
