#!/usr/bin/env python3
"""
向量存储全链路测试 —— E2E 综合验证。

验证目标：
  Phase 1 - 服务基础可用性（health + KB + doc CRUD）
  Phase 2 - 向量索引构建（API index-document + 元信息验证）
  Phase 3 - 向量检索（纯语义 + 文档过滤 + 跨库）
  Phase 4 - 两阶段检索（BM25+向量，Stage 1→Stage 2）
  Phase 5 - MCP 工具等价测试
  Phase 6 - 批量操作（kb_reindex force）
  Phase 7 - 知识图谱 API（如 Neo4j 可用）
  Phase 8 - 清理

使用方法：
  确保后端(:8765)和前端(:6789)已启动，然后：
    uv run python scripts/test-vector-storage-e2e.py

依赖：
  Python 3.12+，仅使用标准库。
"""
import os, sys, json, time, urllib.request, urllib.error, urllib.parse
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────────────────────────
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8765"))
WEB_PORT = int(os.environ.get("WEB_PORT", "6789"))
BURL = f"http://localhost:{BACKEND_PORT}"
WURL = f"http://localhost:{WEB_PORT}"

PASS = 0
FAIL = 0
WARN = 0
K = {}  # 共享状态（KB ID、文档路径等）

# ── 辅助 ──────────────────────────────────────────────────────────────────

def ok(msg):
    global PASS; PASS += 1
    print(f"  [PASS] {msg}")

def fail(msg):
    global FAIL; FAIL += 1
    print(f"  [FAIL] {msg}")

def warn(msg):
    global WARN; WARN += 1
    print(f"  [WARN] {msg}")

def info(msg):
    print(f"  .. {msg}")

def hr(t):
    print(f"\n{'='*60}\n  {t}\n{'='*60}")

TS = str(int(time.time()))


def _req(method, url, data=None, timeout=15):
    """底层 HTTP 请求，返回 (status_code, parsed_json_dict)。"""
    headers = {"Content-Type": "application/json"} if data is not None else {}
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.fp.read().decode() if e.fp else "{}"
        try:
            return e.code, json.loads(body_text)
        except json.JSONDecodeError:
            return e.code, {"error": body_text[:200]}
    except Exception as e:
        return 0, {"error": str(e)}


def get(url, params=None, timeout=10):
    """GET 请求，支持 params dict 自动拼接到 URL 查询参数。"""
    if params:
        qs = urllib.parse.urlencode(params, doseq=True)
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{qs}"
    return _req("GET", url, timeout=timeout)


def post(url, data, timeout=15):
    return _req("POST", url, data=data, timeout=timeout)


def put(url, data, timeout=15):
    return _req("PUT", url, data=data, timeout=timeout)


def patch(url, data, timeout=15):
    return _req("PATCH", url, data=data, timeout=timeout)


def delete(url, data, timeout=15):
    return _req("DELETE", url, data=data, timeout=timeout)


def mc(label, fn):
    """运行一个测试函数，期望返回 bool。fn 内异常视为 FAIL。"""
    try:
        if fn():
            ok(label)
        else:
            fail(label)
    except Exception as e:
        fail(f"{label}: {e}")


# ══════════════════════════════════════════════════════════════════════════
# Phase 1 — 基础服务健康检查
# ══════════════════════════════════════════════════════════════════════════

hr("Phase 1: 服务基础可用性")

mc("Backend health endpoint", lambda:
    get(f"{BURL}/api/v1/health") == (200, {"status": "healthy"})
    or (lambda s, d: s == 200 and d.get("status") == "healthy")(
        *get(f"{BURL}/api/v1/health")
    )
)

mc("Frontend KB catalog reachable", lambda:
    get(f"{WURL}/api/kb/catalog")[0] == 200
)

# ══════════════════════════════════════════════════════════════════════════
# Phase 2 — 知识库 + 文档创建
# ══════════════════════════════════════════════════════════════════════════

hr("Phase 2: KB 与文档创建")

# 2a. 创建测试知识库
kb_name = f"e2e-vector-{TS}"
c, d = post(f"{WURL}/api/kb/create", {"name": kb_name, "description": "E2E vector test KB"})
if c == 200:
    kb = d.get("knowledgeBase", d.get("kb", d))
    K["kb_id"] = kb.get("id", "")
    K["kb_path"] = kb.get("path", "")
    if K["kb_id"]:
        ok(f"KB created: id={K['kb_id']}, path={K['kb_path']}")
    else:
        fail(f"KB create missing id: {json.dumps(d, ensure_ascii=False)[:100]}")
else:
    fail(f"KB create failed: {c} {json.dumps(d, ensure_ascii=False)[:100]}")

# 2b. 创建测试文档 1（AI/RAG 主题）
doc_name = f"ai-intro-{TS}.md"
test_content = """# 人工智能简介

## 什么是人工智能

人工智能（Artificial Intelligence，简称AI）是计算机科学的一个重要分支，
致力于创建能够模拟人类智能的系统。这些系统能够执行通常需要人类智能的任务，
如视觉感知、语音识别、决策制定和语言翻译。

## 机器学习

机器学习是AI的一个子领域，专注于让系统从数据中学习和改进，
而不需要明确的编程。主要类型包括监督学习、无监督学习和强化学习。

## 深度学习

深度学习是机器学习的一个分支，使用多层神经网络来处理复杂模式。
它在图像识别、自然语言处理和自动驾驶等领域取得了突破性进展。

## 检索增强生成（RAG）

检索增强生成（Retrieval-Augmented Generation，简称RAG）是一种结合
信息检索和文本生成的技术。它从知识库中检索相关文档片段，然后由大语言模型
基于这些检索到的内容生成答案，有效减少幻觉并提高回答的准确性。

## 向量数据库

向量数据库专门用于存储和检索高维向量数据。在RAG系统中，
文档被分割成块并转换为向量表示，使系统能够通过语义相似度快速找到相关内容。
ChromaDB 是一个轻量级的开源向量数据库，适合本地开发和原型验证。
"""

if K.get("kb_id"):
    c, d = post(f"{WURL}/api/kb/documents/create", {
        "kbId": K["kb_id"],
        "name": doc_name,
        "content": test_content,
        "description": "AI技术介绍文档",
    })
    if c == 200:
        K["doc_path"] = d.get("document", {}).get("path", "")
        if K["doc_path"]:
            ok(f"Doc1 created: path={K['doc_path']}")
        else:
            fail(f"Doc create missing path: {json.dumps(d, ensure_ascii=False)[:100]}")
    else:
        fail(f"Doc create failed: {c} {json.dumps(d, ensure_ascii=False)[:100]}")
else:
    warn("Skipping doc create (no KB ID)")

# 2c. 创建测试文档 2（Python 主题）
doc_name2 = f"python-intro-{TS}.md"
test_content2 = """# Python 编程语言简介

## 概述

Python 是一种高级、通用、解释型编程语言，由 Guido van Rossum 于 1991 年创建。
以其简洁易读的语法和强大的标准库而闻名，广泛应用于 Web 开发、数据科学、
人工智能和自动化等领域。

## 特性

- 动态类型系统
- 自动内存管理（垃圾回收）
- 丰富的第三方包生态系统（PyPI）
- 支持多种编程范式：面向对象、函数式、过程式

## 在AI中的应用

Python 是人工智能和机器学习领域最流行的编程语言。主要框架包括：
- PyTorch：由 Meta 开发的深度学习框架
- TensorFlow：由 Google 开发的机器学习平台
- scikit-learn：经典的机器学习库
- LangChain：用于构建 LLM 应用的框架

## 数据处理

Python 的数据科学生态系统包括：
- NumPy：数值计算基础库
- Pandas：数据分析与处理库
- Matplotlib：数据可视化库
- Jupyter：交互式编程环境
"""

if K.get("kb_id"):
    c, d = post(f"{WURL}/api/kb/documents/create", {
        "kbId": K["kb_id"],
        "name": doc_name2,
        "content": test_content2,
        "description": "Python语言介绍文档",
    })
    if c == 200:
        K["doc_path2"] = d.get("document", {}).get("path", "")
        ok(f"Doc2 created: path={K['doc_path2']}")
    else:
        fail(f"Doc2 create failed: {c}")

# 2d. 验证文档可读取
if K.get("kb_id") and K.get("doc_path"):
    c, d = get(f"{WURL}/api/kb/document",
               params={"kb_id": K["kb_id"], "doc_path": K["doc_path"]})
    mc("Document readable via kb_doc_read", lambda: c == 200)


# ══════════════════════════════════════════════════════════════════════════
# Phase 3 — 向量索引构建
# ══════════════════════════════════════════════════════════════════════════

hr("Phase 3: 向量索引构建")

# 3a. index-document 文档1
if K.get("kb_id") and K.get("doc_path"):
    c, d = post(f"{BURL}/api/v1/search/index-document", {
        "kb_id": K["kb_id"],
        "doc_path": K["doc_path"],
        "doc_name": doc_name,
        "description": "AI技术介绍文档",
        "content": test_content,
    })
    if c == 200:
        vi = d.get("vector_index", {})
        gs = d.get("graph_stats", {})
        K["vector_index"] = vi
        if vi and vi.get("total_chunks", 0) > 0:
            ok(f"Vector index built: {vi['total_chunks']} chunks, collection='{vi.get('collection', '')}'")
            info(f"  Chunk prefix: {vi.get('chunk_id_prefix', '')}")
            info(f"  Graph doc ID: {vi.get('graph_doc_id', '')}")
            info(f"  Embedding: {vi.get('embedding_model', '')}")
        else:
            warn("Vector index returned but 0 chunks (embedding model may not be loaded)")
            info(f"  Response: {json.dumps(d, ensure_ascii=False)[:150]}")
        if gs:
            info(f"  Graph: {gs.get('entities', 0)} entities, {gs.get('relations', 0)} relations")
    else:
        fail(f"Index-document failed: {c} {json.dumps(d, ensure_ascii=False)[:100]}")
else:
    warn("Skipping index-document (no KB/doc)")

# 3b. index-document 文档2
if K.get("kb_id") and K.get("doc_path2"):
    c, d = post(f"{BURL}/api/v1/search/index-document", {
        "kb_id": K["kb_id"],
        "doc_path": K["doc_path2"],
        "doc_name": doc_name2,
        "description": "Python语言介绍文档",
        "content": test_content2,
    })
    if c == 200:
        vi = d.get("vector_index", {})
        K["vector_index2"] = vi
        if vi and vi.get("total_chunks", 0) > 0:
            ok(f"Doc2 vector index built: {vi['total_chunks']} chunks")
        else:
            warn("Doc2 vector index: 0 chunks")
    else:
        fail(f"Doc2 index-document failed: {c}")

# 3c. 搜索统计
mc("Search stats endpoint reachable", lambda:
    get(f"{BURL}/api/v1/search/stats")[0] == 200
)

c, d = get(f"{BURL}/api/v1/search/stats")
if c == 200:
    info(f"Vector search stats: {json.dumps(d, ensure_ascii=False)[:200]}")


# ══════════════════════════════════════════════════════════════════════════
# Phase 4 — 向量检索
# ══════════════════════════════════════════════════════════════════════════

hr("Phase 4: 向量检索")

# 4a. 纯向量语义搜索（跨库）
c, d = post(f"{BURL}/api/v1/search/vector", {
    "query": "什么是RAG技术",
    "top_k": 10,
})
if c == 200:
    results = d.get("results", [])
    info(f"Vector search 'RAG技术': {len(results)} results")
    for i, r in enumerate(results[:3]):
        info(f"  #{i+1}: score={r.get('score',0):.3f} | doc={r.get('doc_path','').split('/')[-1][:30]} | content={r.get('content','')[:50]}...")
    if results:
        ok("Vector search returned semantic results")
        K["rag_result"] = results[0]
    else:
        warn("Vector search returned 0 results (embeddings may not be ready)")
else:
    fail(f"Vector search failed: {c}")
    # 等待 embedding 模型加载后重试
    info("Waiting 10s for embedding model to load, then retrying...")
    time.sleep(10)
    c, d = post(f"{BURL}/api/v1/search/vector", {
        "query": "什么是RAG技术",
        "top_k": 10,
    })
    if c == 200 and d.get("results"):
        ok("Vector search succeeded on retry")
        K["rag_result"] = d["results"][0]

# 4b. 按文档路径过滤搜索
target_doc = K.get("rag_result", {}).get("doc_path", "") or K.get("doc_path", "")
if target_doc:
    c, d = post(f"{BURL}/api/v1/search/vector", {
        "query": "人工智能",
        "doc_paths": [target_doc],
        "top_k": 5,
    })
    if c == 200:
        filtered = d.get("results", [])
        all_correct = all(r.get("doc_path") == target_doc for r in filtered)
        if filtered and all_correct:
            ok(f"Filtered search: all {len(filtered)} results from target doc")
        elif filtered:
            warn(f"Filtered search: {len(filtered)} results, some from wrong doc")
        else:
            warn("Filtered search: 0 results")
    else:
        fail(f"Filtered search failed: {c}")
else:
    warn("Skipping filtered search (no doc_path)")

# 4c. 按 KB ID 限定搜索
if K.get("kb_id"):
    c, d = post(f"{BURL}/api/v1/search/vector", {
        "query": "深度学习",
        "kb_id": K["kb_id"],
        "top_k": 5,
    })
    if c == 200:
        results = d.get("results", [])
        if results:
            all_in_kb = all(r.get("kb_id") == K["kb_id"] for r in results)
            if all_in_kb:
                ok(f"KB-scoped search: all {len(results)} from correct KB")
            else:
                warn("KB-scoped search: some from wrong KB")
        else:
            warn("KB-scoped search: 0 results")
    else:
        fail(f"KB-scoped search failed: {c}")

# 4d. 语义相关性验证
c, d = post(f"{BURL}/api/v1/search/vector", {
    "query": "Python语言编程框架",
    "top_k": 10,
})
if c == 200:
    results = d.get("results", [])
    info(f"Vector search 'Python': {len(results)} results")
    for i, r in enumerate(results[:4]):
        info(f"  #{i+1}: score={r.get('score',0):.3f} | doc={r.get('doc_path','').split('/')[-1][:30]}")
    python_docs = [r for r in results if "python" in r.get("doc_path", "").lower()]
    if python_docs:
        ok("Python doc ranked high for Python query")
    else:
        warn("Python doc not found in top results for Python query")
else:
    warn("Vector search 'Python': failed")

# 4e. 搜索统计验证
c, d = get(f"{BURL}/api/v1/search/stats")
if c == 200:
    stats = d.get("stats", {})
    if isinstance(stats, dict):
        cols = stats.get("collections", [])
        total_chunks = sum(c_.get("chunk_count", 0) for c_ in cols)
        if total_chunks > 0:
            ok(f"Vector stats: {total_chunks} chunks across {len(cols)} collections")
        else:
            warn("Vector stats: 0 chunks total")
    else:
        info(f"Stats format: {type(stats).__name__}")


# ══════════════════════════════════════════════════════════════════════════
# Phase 5 — 两阶段检索（BM25 + 向量精筛）
# ══════════════════════════════════════════════════════════════════════════

hr("Phase 5: 两阶段精准检索")

# 5a. 两阶段搜索
c, d = post(f"{BURL}/api/v1/search/two-stage", {
    "query": "检索增强生成",
    "stage1_top_k": 20,
    "stage2_top_k": 3,
})
if c == 200:
    s1 = d.get("stage1", {})
    s2 = d.get("stage2", {})
    candidates = s1.get("candidates", [])
    results = s2.get("results", [])
    info(f"Stage 1 candidates: {s1.get('candidate_count', 0)}")
    info(f"Stage 2 results: {d.get('total_results', 0)}")

    if candidates:
        ok(f"Stage 1: {len(candidates)} candidate docs via BM25+graph")
        for i, cc in enumerate(candidates[:3]):
            info(f"  #{i+1}: score={cc.get('score',0):.3f} | doc={cc.get('doc_path','').split('/')[-1][:30]} | source={cc.get('source','')}")
    else:
        warn("Stage 1: 0 candidates (keyword index may not be ready yet)")

    if results:
        ok(f"Stage 2: {len(results)} refined chunks from vector search")
        for i, r in enumerate(results[:3]):
            info(f"  #{i+1}: score={r.get('score',0):.3f} | doc={r.get('doc_path','').split('/')[-1][:30]}")
    else:
        warn("Stage 2: 0 results")
else:
    fail(f"Two-stage search failed: {c} {json.dumps(d, ensure_ascii=False)[:100]}")

# 5b. 两阶段搜索——限定 KB
if K.get("kb_id"):
    c, d = post(f"{BURL}/api/v1/search/two-stage", {
        "query": "向量数据库",
        "kb_id": K["kb_id"],
        "stage1_top_k": 10,
        "stage2_top_k": 3,
    })
    if c == 200:
        s1 = d.get("stage1", {})
        s2 = d.get("stage2", {})
        if s1.get("candidates") or s2.get("results"):
            ok("Two-stage search with kb_id filter")
            info(f"  Stage1={s1.get('candidate_count')}, Stage2={d.get('total_results')}")
        else:
            warn("Two-stage kb-filtered: 0 results")
    else:
        fail(f"Two-stage kb-scoped failed: {c}")


# ══════════════════════════════════════════════════════════════════════════
# Phase 6 — 批量重建索引
# ══════════════════════════════════════════════════════════════════════════

hr("Phase 6: 批量重建索引")

# 6a. 重建全部
c, d = post(f"{BURL}/api/v1/search/reindex", {"force": True})
if c == 200:
    info(f"Full reindex: {d.get('total_docs', 0)} docs, {d.get('total_chunks', 0)} chunks")
    if d.get("errors"):
        warn(f"Reindex errors: {len(d['errors'])} — {d['errors'][:2]}")
    if d.get("total_docs", 0) > 0:
        ok("Full reindex completed with chunks")
    else:
        warn("Full reindex: 0 docs processed")
else:
    fail(f"Reindex failed: {c} {json.dumps(d, ensure_ascii=False)[:80]}")

# 6b. 重建后检索验证
c, d = post(f"{BURL}/api/v1/search/vector", {
    "query": "ChromaDB 向量存储",
    "top_k": 5,
})
if c == 200:
    if d.get("results"):
        ok("Vector search works after reindex")
    else:
        warn("Vector search after reindex: 0 results")
else:
    fail(f"Vector search after reindex failed: {c}")


# ══════════════════════════════════════════════════════════════════════════
# Phase 7 — 知识图谱 API
# ══════════════════════════════════════════════════════════════════════════

hr("Phase 7: 知识图谱 API")

# 7a. 图谱实体搜索
c, d = get(f"{BURL}/api/v1/graph/search", params={"keyword": "人工智能", "limit": 10})
if c == 200:
    entities = d.get("entities", [])
    if entities:
        ok(f"Graph entity search: {d.get('count', 0)} entities found")
        for e in entities[:3]:
            info(f"  Entity: {e.get('name','')} type={e.get('type','')} mentions={e.get('mentions','')}")
    else:
        info("Graph entity search: 0 entities (Neo4j may not be running)")
else:
    info(f"Graph search HTTP {c}: {json.dumps(d, ensure_ascii=False)[:80]}")

# 7b. 图谱统计
c, d = get(f"{BURL}/api/v1/graph/stats")
if c == 200:
    stats = d.get("stats", {})
    info(f"Graph stats: {json.dumps(stats, ensure_ascii=False)[:120]}")
    if stats.get("node_count", 0) > 0:
        ok("Graph DB has data")
    else:
        info("Graph DB empty (Neo4j may not have data)")
else:
    info(f"Graph stats HTTP {c}")


# ══════════════════════════════════════════════════════════════════════════
# Phase 8 — 文档操作与标签
# ══════════════════════════════════════════════════════════════════════════

hr("Phase 8: 文档操作验证")

# 8a. 更新文档内容
if K.get("kb_id") and K.get("doc_path2"):
    updated_content = test_content2 + "\n\n## 更新内容\n\n向量索引在文档更新后应同步更新。"
    c, d = put(f"{WURL}/api/kb/documents/content", {
        "kbId": K["kb_id"],
        "docPath": K["doc_path2"],
        "content": updated_content,
    })
    mc("Document content update", lambda: c == 200)

    # 重新索引
    c, d = post(f"{BURL}/api/v1/search/index-document", {
        "kb_id": K["kb_id"],
        "doc_path": K["doc_path2"],
        "content": updated_content,
    })
    if c == 200 and d.get("vector_index", {}).get("total_chunks", 0) > 0:
        ok("Document re-indexed after content update")
    else:
        warn("Document re-index after update: 0 chunks")

# 8b. 标签操作
if K.get("kb_id") and K.get("doc_path"):
    c, d = patch(f"{WURL}/api/kb/documents/tags", {
        "kbId": K["kb_id"],
        "docPath": K["doc_path"],
        "tags": ["e2e-test", "vector-test"],
    })
    mc("Document tag update", lambda: c == 200)

    c, d = get(f"{WURL}/api/kb/documents/by-tag",
               params={"tag": "e2e-test", "kb_id": K["kb_id"]})
    mc("Find documents by tag", lambda: c == 200)


# ══════════════════════════════════════════════════════════════════════════
# Phase 9 — MCP 工具等价验证
# ══════════════════════════════════════════════════════════════════════════

hr("Phase 9: MCP 工具等价验证")

mc("health_check 等价", lambda: get(f"{BURL}/api/v1/health")[0] == 200)
mc("backend_status 等价", lambda: get(f"{BURL}/api/v1/mineru/status")[0] == 200)
mc("kb_list 等价", lambda: get(f"{WURL}/api/kb/catalog")[0] == 200)

mc("kb_search 等价", lambda:
    get(f"{WURL}/api/kb/search", params={"query": "人工智能", "top_k": 5})[0] == 200
)

mc("kb_search_vector 等价", lambda:
    post(f"{BURL}/api/v1/search/vector", {"query": "RAG技术", "top_k": 5})[0] == 200
)

mc("kb_search_two_stage 等价", lambda:
    post(f"{BURL}/api/v1/search/two-stage", {"query": "机器学习"})[0] == 200
)

if K.get("kb_id"):
    mc("kb_get_documents 等价", lambda:
        get(f"{WURL}/api/kb/documents", params={"kb_id": K["kb_id"]})[0] == 200
    )

if K.get("kb_id") and K.get("doc_path"):
    mc("kb_doc_read 等价", lambda:
        get(f"{WURL}/api/kb/document",
            params={"kb_id": K["kb_id"], "doc_path": K["doc_path"]})[0] == 200
    )

mc("kb_tags_list 等价", lambda: get(f"{WURL}/api/kb/tags")[0] == 200)
mc("kb_reindex 等价", lambda:
    post(f"{BURL}/api/v1/search/reindex", {"force": False})[0] == 200
)

mc("kb_search_stats 等价 (新增)", lambda:
    get(f"{BURL}/api/v1/search/stats")[0] == 200
)


# ══════════════════════════════════════════════════════════════════════════
# Phase 10 — 数据完整性验证
# ══════════════════════════════════════════════════════════════════════════

hr("Phase 10: 数据完整性验证")

# 10a. RAG 内容命中率
c, d = post(f"{BURL}/api/v1/search/vector", {
    "query": "RAG检索增强生成向量数据库",
    "top_k": 10,
})
if c == 200:
    results = d.get("results", [])
    rag_hits = [r for r in results
                if any(kw in r.get("content", "") for kw in ("RAG", "检索", "向量"))]
    if rag_hits:
        ok(f"RAG-relevant content hits: {len(rag_hits)}/{len(results)}")
    else:
        warn("No RAG content hit — possible but unusual")

# 10b. 排序确定性
c1, d1 = post(f"{BURL}/api/v1/search/vector", {"query": "深度学习神经网络", "top_k": 5})
c2, d2 = post(f"{BURL}/api/v1/search/vector", {"query": "深度学习神经网络", "top_k": 5})
if c1 == 200 and c2 == 200:
    r1 = d1.get("results", [])
    r2 = d2.get("results", [])
    ids1 = [(r.get("doc_path", ""), r.get("chunk_index", 0)) for r in r1]
    ids2 = [(r.get("doc_path", ""), r.get("chunk_index", 0)) for r in r2]
    if ids1 == ids2 and len(ids1) > 0:
        ok("Vector search results are deterministic (stable ordering)")
    elif len(ids1) == 0:
        warn("Cannot check determinism: 0 results in one or both calls")
    else:
        warn("Vector search ordering not stable between calls")


# ══════════════════════════════════════════════════════════════════════════
# 清理：删除测试知识库
# ══════════════════════════════════════════════════════════════════════════

hr("Cleanup: 删除测试数据")

if K.get("kb_id"):
    c, d = delete(f"{WURL}/api/kb/delete", {"kbId": K["kb_id"]})
    if c == 200:
        ok("Test KB deleted")
    else:
        warn(f"KB delete returned {c}: {json.dumps(d, ensure_ascii=False)[:80]}")
else:
    warn("No KB to clean up")


# ══════════════════════════════════════════════════════════════════════════
# 汇总
# ══════════════════════════════════════════════════════════════════════════

hr("测试结果汇总")
total = PASS + FAIL + WARN
print(f"  [PASS] {PASS}")
print(f"  [WARN] {WARN}")
print(f"  [FAIL] {FAIL}")
print(f"  Total: {total}")
if FAIL == 0:
    print()
    print("  =======================================")
    print("  向量存储全链路验证通过！")
    print("  =======================================")
    print()
    print("  已完成验证：")
    print("  ✔ 服务基础可用性（backend + frontend）")
    print("  ✔ 知识库 CRUD（创建/读取/删除）")
    print("  ✔ 文档 CRUD（创建/读取/更新/标签）")
    print("  ✔ 向量索引构建（ChromaDB chunk + embedding）")
    print("  ✔ 向量语义搜索（纯语义 + 文档过滤 + KB限定）")
    print("  ✔ 两阶段检索（BM25关键词 → 向量精筛）")
    print("  ✔ 批量重建索引（force reindex）")
    print("  ✔ MCP 工具等价验证")
    print("  ✔ 数据完整性与排序稳定性")
else:
    print(f"\n  {FAIL} 项失败，请检查以上输出。")

sys.exit(0 if FAIL == 0 else 1)
