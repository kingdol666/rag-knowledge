---
created: 2026-07-01T17:32:35.218Z
title: 修复向量搜索不可用——torchvision 版本不兼容
area: backend
files:
  - backend/app/services/embedding_service.py
  - backend/app/services/vector_service.py
  - backend/pyproject.toml
---

## Problem

`sentence-transformers` 加载时因 `torchvision` 版本不兼容崩溃：
- `torchvision 0.19.1` 缺少 `torchvision::nms` 算子，导致 `sentence_transformers` → `transformers` → `torchvision` 调用链出错
- `/api/v1/search/vector` 返回 `vector service not ready`
- `/api/v1/search/two-stage` 仅能以 BM25 fallback 运行，无向量精排能力
- ChromaDB 持久化目录 `chroma_db/` 尚未初始化

## Solution

方案一（尝试）：升级 torchvision 到兼容版本
```bash
cd backend
uv pip install torchvision --upgrade
```

方案二（备选）：降级 torch 全家桶到已知兼容版本组合（如 torch 2.1.x + torchvision 0.16.x + sentence-transformers 2.2.x）
