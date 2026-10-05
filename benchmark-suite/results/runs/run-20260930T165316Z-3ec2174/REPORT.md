# 实验报告 — `run-20260930T165316Z-3ec2174`

## Provenance

| 项 | 值 |
|---|---|
| git_commit | `3ec2174` |
| config_hash | `9fb259c0cf2b6dea` |
| prompt_version | `v4-neutral` |
| seed | `0` |
| max_turns | `12` |
| tracks | `['a2', 'bm25', 'vector', 'rrf', 'rerank']` |
| questions | `10` |
| shuffled | `True` |

## 主表（方法 × 指标）

| method | n | judge acc | quality | P@5 | R@10 | nDCG@10 | MRR | 时延 s | 成本 $ | 工具数 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a2 | 10 | — | — | — | — | — | — | 41.490 | 0.375 | 5.100 |

## 未测量项（如实标注）

- judge.json (L2 正确性)
- qrels_scores.json (IR 指标)
- stats.json (显著性)

---

*数字均来自本 run 目录工件；缺项写“未测量”，未做任何评价性改写。*