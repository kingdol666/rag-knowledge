# BEIR SciFact + SQuAD 标准语料赛道 — 使用说明

本目录的 `data/standard2/` 存放从**官方标准评测数据集**下载并确定性子集化后的语料:

| 数据集 | 用途 | 来源 | 子集规模 |
|---|---|---|---|
| BEIR SciFact | 标准**检索**基准(带 qrels 相关性判定, 支持标准 Recall/nDCG 指标) | public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip | 30 查询 / 148 篇文献(28 金标 + 120 干扰) |
| SQuAD v1.1 dev | 标准**抽取式问答**基准(含标准答案) | rajpurkar/SQuAD-explorer dev-v1.1.json | 8 篇文章 / 16 问题 |

## 复现下载

```bash
python scripts/20_standard_download.py   # 官方源下载 + 确定性子集化(manifest 记录 sha256)
```

## 执行测试(与自建赛道步骤完全一致)

```bash
python scripts/21_std2_ingest.py 1       # 入库 KB-SciFact / KB-SQuAD + 模块A指标
python scripts/22_std2_retrieval.py 1    # QDCVR 内容检索 vs 向量 baseline (标准 IR 指标)
python scripts/22_std2_retrieval.py 2    # 第二轮复现校验
```

## 关键数字(2026-09-13 实测, 双轮逐位一致)

- 入库(184 文档): 归属正确率 **1.0**, 存储完整率 **1.0**
- SciFact 检索: 内容检索 Hit@3 **0.83** / nDCG@10 **0.81** vs 向量 baseline 0.90 / 0.83
  (Step2.5 阈值 0.35 的精度/召回权衡; 阈值可调)
- SQuAD: 内容检索与向量 baseline 均 Hit@3 = nDCG@10 = 1.0
