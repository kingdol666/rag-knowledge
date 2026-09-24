# 对照实验报告 — `run-20260924T052208Z-0968033`

同一问题集上，**项目（平台轨）** 与 **baseline** 逐题并列对照 + 资源监控。
生成时间 2026-09-24 05:22 UTC

## 方法清单

| method | 类型 | n |
|---|---|---:|
| `a2` | 项目（平台） | 1 |
| `bm25` | baseline | 1 |
| `rerank` | baseline | 1 |
| `rrf` | baseline | 1 |
| `vector` | baseline | 1 |

## 资源监控总表

| method | 时延 avg s | 时延 median s | tokens in | tokens out | 成本 $ | 成本/题 $ | 工具数 avg | CPU% peak | RSS MB peak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `a2` | 0.0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | — | — |
| `bm25` | 0.0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | — | — |
| `rerank` | 0.0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | — | — |
| `rrf` | 0.0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | — | — |
| `vector` | 0.0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | — | — |

## 功能验证（检索命中 / 引用命中 / 弃答）

| method | 检索金标命中率 | 引用金标命中率 | 弃答数 | error 数 |
|---|---:|---:|---:|---:|
| `a2` | 0.0 | 0.0 | 0 | 1 |
| `bm25` | 0.0 | 0.0 | 0 | 1 |
| `rerank` | 0.0 | 0.0 | 0 | 1 |
| `rrf` | 0.0 | 0.0 | 0 | 1 |
| `vector` | 0.0 | 0.0 | 0 | 1 |

## R2Q01

**Q:** Compared with prior Multi-Agent Transformer (MAT) models, what aspect of the agents' decision process does AOAD-MAT explicitly model?

**gold:** 2510.13343

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✗ | ✗ | 0 | None | None | 0 | 否 | (track failed: HTTPError: HTTP Error 401: Unauthorized) |
| `bm25` | ✗ | ✗ | 0 | None | None | 0 | 否 | (track failed: HTTPError: HTTP Error 401: Unauthorized) |
| `rerank` | ✗ | ✗ | 0 | None | None | 0 | 否 | (track failed: HTTPError: HTTP Error 401: Unauthorized) |
| `rrf` | ✗ | ✗ | 0 | None | None | 0 | 否 | (track failed: HTTPError: HTTP Error 401: Unauthorized) |
| `vector` | ✗ | ✗ | 0 | None | None | 0 | 否 | (track failed: HTTPError: HTTP Error 401: Unauthorized) |

<details><summary>逐字答案全文</summary>

**[a2]**

(track failed: HTTPError: HTTP Error 401: Unauthorized)

**[bm25]**

(track failed: HTTPError: HTTP Error 401: Unauthorized)

**[rerank]**

(track failed: HTTPError: HTTP Error 401: Unauthorized)

**[rrf]**

(track failed: HTTPError: HTTP Error 401: Unauthorized)

**[vector]**

(track failed: HTTPError: HTTP Error 401: Unauthorized)

</details>

## 一致性自检

| 检查 | 结果 | 详情 |
|---|---|---|
| 每 (qid,method) 都有结果 | ✅ | 0 缺失 |
| 无重复单元 | ✅ | ok |
| 无 error 单元 | ❌ | 5 个 error |
| 成本合计 = 各方法之和 | ✅ | sum(method)=0 · manifest=0 |
| 单元数 = 题数 × 方法数 | ✅ | rows=5 vs 1×5=5 |
| provenance 完整 | ✅ | prompt_version=v3-neutral seed=0 |

---

*数字来自本 run 目录工件；缺失写“—/缺失”，未做任何评价性改写。*