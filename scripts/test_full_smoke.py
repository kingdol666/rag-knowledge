# -*- coding: utf-8 -*-
"""全功能冒烟测试：单次运行覆盖 KB / 文档 / 解析 / 检索 / 索引 / 经验 / 图谱 / SOUL。

设计原则：只走快路径（跳过需数分钟 LLM 的 soul_learn / train_rl / ask，
这几项在 TEST-REPORT 中已单独验证）；每步输出一行 PASS/FAIL，末尾汇总。
测试数据（临时库 + 临时人格）结束前自动清理。
"""
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "kb-mcp"))
import server  # noqa: E402

RESULT: list[tuple[str, bool, str]] = []


def deep_get(d, key):
    if isinstance(d, dict):
        if key in d and d[key]:
            return d[key]
        for v in d.values():
            r = deep_get(v, key)
            if r:
                return r
    elif isinstance(d, list):
        for v in d:
            r = deep_get(v, key)
            if r:
                return r
    return None


async def chk(name, coro, expect=None, limit=180):
    """执行一个工具调用并判定。expect: 可选 (key) 或 (key, minvalue) 断言。"""
    try:
        raw = await coro
        d = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception as e:
        RESULT.append((name, False, f"{type(e).__name__}: {str(e)[:70]}"))
        print(f"[FAIL] {name} — {type(e).__name__}: {str(e)[:70]}")
        return {}
    if isinstance(d, list):  # 少数工具直接返回数组（如 soul_list）
        ok, detail = len(d) > 0, "" if d else "empty list"
        if ok:
            RESULT.append((name, True, ""))
            print(f"[PASS] {name} ({len(d)} 项)")
            return d
        RESULT.append((name, False, detail))
        print(f"[FAIL] {name} — {detail}")
        return d
    ok = bool(d.get("success", True)) and not d.get("error")
    detail = ""
    if ok and expect:
        k, *rest = expect
        val = deep_get(d, k)
        if val in (None, [], {}, 0, False) or (rest and not (val >= rest[0])):
            ok, detail = False, f"{k}={str(val)[:40]}"
    if ok:
        RESULT.append((name, True, ""))
        print(f"[PASS] {name}")
    else:
        msg = d.get("error") or d.get("detail") or detail or str(d)[:70]
        RESULT.append((name, False, str(msg)[:70]))
        print(f"[FAIL] {name} — {str(msg)[:70]}")
    return d


async def main():
    t0 = time.time()
    PDF = str(ROOT / "tmp" / "test-parse.pdf")
    kb_id = soul_id = None

    print("\n══ 1. 系统与项目 ══")
    await chk("backend_status", server.backend_status())
    await chk("kb_project_status", server.kb_project_status())
    await chk("kb_search_stats", server.kb_search_stats())
    await chk("kb_graph_stats", server.kb_graph_stats(), expect=("node_count", 1))

    print("\n══ 2. 知识库 CRUD ══")
    # 前置清理：上一次异常退出可能留下同名库（P0-2 重名校验会拦住重建）
    for stale in ("ZZ冒烟测试库", "soul-冒烟测试"):
        try:
            cat = json.loads(await server.kb_list(lightweight=True))
            for k in cat.get("catalog", []):
                if k.get("name") == stale:
                    await server.kb_delete(kb_id=k.get("kb_id"))
                    print(f"  (清理残留库: {stale})")
        except Exception as e:
            print(f"  (清理 {stale} 失败: {type(e).__name__})")

    r = await chk("kb_create", server.kb_create(
        name="ZZ冒烟测试库", description="全功能冒烟测试临时库"))
    kb_id = deep_get(r, "kb_id")
    if not kb_id:
        print("!! 无 kb_id，终止")
        return
    await chk("kb_list", server.kb_list(lightweight=True), expect=("count", 1))
    await chk("kb_update", server.kb_update(kb_id=kb_id, description="已更新描述"))

    print("\n══ 3. 文档 CRUD ══")
    r1 = await chk("kb_doc_create(d1)", server.kb_doc_create(
        kb_id=kb_id, name="冒烟-工艺.md",
        content="# 冒烟测试\n\n纵向拉伸比 3.6，横向拉伸比 3.8。破膜对策：降低拉伸比。",
        description="工艺"), expect=("path",))
    doc1 = deep_get(r1, "path") or deep_get(r1, "doc_path")
    await chk("kb_doc_create(d2)", server.kb_doc_create(
        kb_id=kb_id, name="冒烟-检索.md",
        content="# 检索策略\n\n混合检索结合 BM25 与稠密向量，用 RRF 融合。",
        description="检索"))
    await chk("kb_get_documents", server.kb_get_documents(kb_id=kb_id), expect=("count", 2))
    if doc1:
        await chk("kb_doc_read", server.kb_doc_read(kb_id=kb_id, doc_path=doc1), expect=("content",))
        await chk("kb_doc_update_meta", server.kb_doc_update_meta(
            kb_id=kb_id, doc_path=doc1, description="已更新"))
        await chk("kb_doc_update_content", server.kb_doc_update_content(
            kb_id=kb_id, doc_path=doc1, content="# 冒烟测试(已更新)\n\n纵向拉伸比 3.6"))
        await chk("kb_doc_update_tags", server.kb_doc_update_tags(
            kb_id=kb_id, doc_path=doc1, tags=["冒烟", "工艺"]))
    await chk("kb_doc_get_by_tag", server.kb_doc_get_by_tag(tag="冒烟"), expect=("documents",))
    await chk("kb_tags_list", server.kb_tags_list())

    print("\n══ 4. PDF 解析入库 ══")
    pr = await chk("parse_doc", server.parse_doc(file_path=PDF))
    ptask = deep_get(pr, "task_id")
    if ptask:
        pres = {}
        for _ in range(40):
            await asyncio.sleep(3)
            pres = json.loads(await server.parse_task_status(task_id=ptask))
            if pres.get("status") in ("done", "completed", "failed", "error"):
                break
        ok = pres.get("status") == "done"
        RESULT.append(("parse_task_status", ok, ""))
        print(f"[{'PASS' if ok else 'FAIL'}] parse_task_status")
        if ok:
            sr = await chk("kb_doc_save_parsed", server.kb_doc_save_parsed(
                parent_id=kb_id, task_id=ptask), expect=("savedCount",))
            if not sr.get("success"):
                # MinerU 重启后 result 可能省略 markdown 字段 → 手动模式兜底
                inner = (pres.get("result") or {})
                mp = inner.get("markdown_path") or ""
                md = Path(mp).read_text(encoding="utf-8", errors="ignore") if mp and Path(mp).exists() else ""
                if md:
                    print("   (task_id 模式失败 → 手动模式兜底)")
                    sr = await chk("kb_doc_save_parsed", server.kb_doc_save_parsed(
                        parent_id=kb_id, markdown=md, source_filename="test-parse.pdf"),
                        expect=("savedCount",))
                else:
                    sr = {}
            pdoc = deep_get(sr, "path")
            if pdoc:
                await chk("kb_index_document", server.kb_index_document(
                    kb_id=kb_id, doc_path=pdoc), expect=("vector_index",))
                await chk("kb_batch_index", server.kb_batch_index(
                    kb_id=kb_id, doc_paths=[pdoc]))

    print("\n══ 5. 检索（关键词/向量/两阶段/图谱/查重）══")
    await chk("kb_search(关键词)", server.kb_search(query="拉伸比", top_k=3), expect=("hits",))
    await chk("kb_search_vector(向量)", server.kb_search_vector(
        query="拉伸温度怎么控制", kb_id=kb_id, top_k=3), expect=("results",))
    await chk("kb_search_two_stage(两阶段)", server.kb_search_two_stage(
        query="如何提高检索准确率", kb_id=kb_id, stage1_top_k=8, stage2_top_k=2),
        expect=("stage2",))
    await chk("kb_find_duplicates(查重)", server.kb_find_duplicates(kb_id=kb_id))
    await chk("kb_cleanup_orphan_collections(dry)", server.kb_cleanup_orphan_collections(dry_run=True))

    print("\n══ 6. 知识图谱 ══")
    await chk("kb_graph_build", server.kb_graph_build(kb_id=kb_id))
    await chk("kb_graph_kb_overview", server.kb_graph_kb_overview(kb_id=kb_id))
    await chk("kb_graph_document", server.kb_graph_document(doc_path=doc1 or "", limit=5))
    await chk("kb_graph_central_documents", server.kb_graph_central_documents(kb_id=kb_id, top_n=3))
    await chk("kb_graph_cross_kb_documents", server.kb_graph_cross_kb_documents(min_kbs=2, limit=3))
    await chk("kb_graph_search", server.kb_graph_search(keyword="拉伸", limit=3))

    print("\n══ 7. 经验全生命周期 ══")
    er = await chk("experience_create", server.experience_create(
        kb_id=kb_id, title="冒烟-破膜处置经验", scenario="smoke-film",
        category="troubleshooting", problem="拉伸过程频繁破膜",
        solution="降低拉伸比至 3.6、提高拉伸区温度至 95 度",
        result="success", key_lessons=["拉伸比超 4.0 风险上升"], tags=["冒烟"]),
        expect=("experience",))
    exp_id = deep_get(er, "exp_id") or deep_get(er, "id")
    if exp_id:
        await chk("experience_read", server.experience_read(kb_id=kb_id, exp_id=exp_id))
        await chk("experience_update", server.experience_update(
            kb_id=kb_id, exp_id=exp_id, severity="important"))
        await chk("experience_apply", server.experience_apply(kb_id=kb_id, exp_id=exp_id))
        await chk("experience_review", server.experience_review(
            kb_id=kb_id, exp_id=exp_id, reviewer="smoke", rating=5))
        await chk("experience_delete", server.experience_delete(kb_id=kb_id, exp_id=exp_id))
    await chk("experience_list", server.experience_list(kb_id=kb_id))
    await chk("experience_summary", server.experience_summary(kb_id=kb_id), expect=("summary",))
    await chk("experience_extract(dry)", server.experience_extract(kb_id=kb_id, dry_run=True))
    await chk("experience_drafts_list", server.experience_drafts_list(kb_id=kb_id))
    await chk("experience_search_smart", server.experience_search_smart(query="破膜", top_k=3))
    await chk("experience_search_global", server.experience_search_global(query="拉伸", top_k=3))
    await chk("experience_dashboard", server.experience_dashboard(kb_id=kb_id))
    await chk("experience_check_stale", server.experience_check_stale(kb_id=kb_id))
    await chk("experience_meditation_config_get", server.experience_meditation_config_get(kb_id=kb_id))
    await chk("experience_meditation_status", server.experience_meditation_status(kb_id=kb_id))

    print("\n══ 8. 文件树与索引 ══")
    await chk("fs_get_tree", server.fs_get_tree(max_depth=2), expect=("tree",))
    await chk("kb_reindex(单库)", server.kb_reindex(kb_id=kb_id))

    print("\n══ 9. SOUL 人格（快路径）══")
    await chk("soul_list", server.soul_list())
    sr = await chk("soul_init", server.soul_init(
        soul_name="soul-冒烟测试", kb_scope=[kb_id],
        domain_labels=["冒烟"], supported_task_types=["知识问答"]))
    soul_id = deep_get(sr, "kb_id")
    if soul_id:
        await chk("soul_status", server.soul_status(soul_kb_id=soul_id))
        await chk("soul_config_update", server.soul_config_update(
            soul_kb_id=soul_id, kb_scope=[kb_id]))
        await chk("soul_export", server.soul_export(soul_kb_id=soul_id))
    await chk("soul_router", server.soul_router(query="薄膜拉伸工艺怎么设定"))
    await chk("soul_learn_all(dry_run)", server.soul_learn_all(
        soul_kb_id=soul_id or "", max_docs=1, dry_run=True))

    print("\n══ 10. 清理 ══")
    if soul_id:
        await chk("soul_delete", server.soul_delete(soul_kb_id=soul_id, purge_experiences=True))
    if kb_id:
        await chk("kb_doc_batch_delete", server.kb_doc_batch_delete(
            kb_id=kb_id, doc_paths=[doc1] if doc1 else []))
        await chk("kb_delete", server.kb_delete(kb_id=kb_id))

    passed = sum(1 for _, ok, _ in RESULT if ok)
    total = len(RESULT)
    print("\n" + "=" * 60)
    print(f"汇总: {passed}/{total} 通过   耗时 {time.time()-t0:.0f}s")
    for n, ok, m in RESULT:
        if not ok:
            print(f"  未通过: {n} — {m}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
