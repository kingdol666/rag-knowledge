"""jieba + BM25 倒排索引服务。

Stage 1 关键词检索：从 .knowledge-base.yml 读取文档元数据，
从磁盘读取 .md 正文前 8000 字（V2: 从 2000 提升到 8000），构建 BM25 索引。
长文档的 BM25 表示更完整，跨库搜索不再只命中短文档 KB。
"""
from __future__ import annotations

import logging
import math
from collections import Counter, defaultdict
from typing import Any

import jieba

logger = logging.getLogger(__name__)

# BM25 索引使用的最大正文字符数
# 从 2000 提升到 8000：2000 字符只覆盖摘要+引言，
# 8000 可以覆盖到方法部分，大幅提升跨库 BM25 检索准确率
_BM25_MAX_CONTENT_CHARS = 8000


class KeywordIndexService:
    def __init__(self) -> None:
        self._docs: list[dict[str, Any]] = []
        self._inverted: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self._doc_len: list[int] = []
        self._avg_len: float = 0.0
        self._doc_count: int = 0
        self._built: bool = False

    def build(self, documents: list[dict[str, Any]]) -> None:
        self._docs = []
        self._inverted = defaultdict(list)
        self._doc_len = []
        for idx, doc in enumerate(documents):
            text = " ".join([
                doc.get("name", ""),
                doc.get("description", ""),
                doc.get("content", "")[:_BM25_MAX_CONTENT_CHARS],
            ])
            tokens = self._tokenize(text)
            tf = Counter(tokens)
            for token, count in tf.items():
                self._inverted[token].append((idx, count))
            self._docs.append(doc)
            self._doc_len.append(len(tokens))

        self._doc_count = len(self._docs)
        self._avg_len = sum(self._doc_len) / max(1, self._doc_count)
        self._built = True
        logger.info("BM25 index built: %d docs, %d unique tokens",
                    self._doc_count, len(self._inverted))

    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        if not self._built or self._doc_count == 0:
            return []
        tokens = self._tokenize(query)
        scores: dict[int, float] = defaultdict(float)
        k1, b = 1.5, 0.75
        for token in tokens:
            postings = self._inverted.get(token, [])
            if not postings:
                continue
            idf = math.log(
                (self._doc_count - len(postings) + 0.5) / (len(postings) + 0.5) + 1
            )
            for doc_idx, tf in postings:
                dl = self._doc_len[doc_idx]
                denom = tf + k1 * (1 - b + b * dl / self._avg_len)
                score = idf * (tf * (k1 + 1)) / denom if denom > 0 else 0
                scores[doc_idx] += score

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [{"doc_path": self._docs[idx]["path"], "score": score,
                  "name": self._docs[idx].get("name", ""),
                  "kb_id": self._docs[idx].get("kb_id", "")}
                for idx, score in ranked[:top_k]]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        tokens = jieba.cut_for_search(text)
        return [t.strip().lower() for t in tokens if t.strip() and len(t.strip()) > 1]


keyword_index_service = KeywordIndexService()
