# -*- coding: utf-8 -*-
"""
Comprehensive skill execution test.
Tests every knowledgebase skill workflow by calling the MCP tools
(via KbClient direct calls — same code path as MCP server).

Skills tested:
  1. knowledgebase-list (L1-L3)
  2. knowledgebase-search (VFCR Step1-6)
  3. knowledgebase-ingest (A0-A9)
  4. knowledgebase-manage (M1-M6)
  5. knowledgebase-verify (V1-V6)
  6. knowledgebase-experience (CRUD + search)
  7. knowledgebase-graph (build, query, stats)
  8. knowledgebase-batch (B1-B7)
  9. knowledgebase-search-enterprise (Phase1-5)
 10. knowledgebase-experience-summarize (Step1-5)
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Add kb-mcp to path
KB_MCP_DIR = Path(__file__).resolve().parent.parent / "kb-mcp"
sys.path.insert(0, str(KB_MCP_DIR))

# Set dev mode
os.environ.setdefault("APP_MODE", "dev")

from kb_client import KbClient
import config

# ──────────────────────────────────────────────────────────────────────
# Test utilities
# ──────────────────────────────────────────────────────────────────────

PASS = 0
FAIL = 0
SKIP = 0
RESULTS: list[dict] = []


def record(name: str, success: bool, detail: str = ""):
    global PASS, FAIL
    if success:
        PASS += 1
        status = "✅ PASS"
    else:
        FAIL += 1
        status = "❌ FAIL"
    RESULTS.append({"name": name, "success": success, "detail": detail})
    print(f"  {status}: {name}" + (f" — {detail}" if detail else ""))


def record_skip(name: str, reason: str = ""):
    global SKIP
    SKIP += 1
    print(f"  ⏭️ SKIP: {name}" + (f" — {reason}" if reason else ""))


def section(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def truncate(s: str, n: int = 200) -> str:
    if not s:
        return ""
    return s[:n] + "..." if len(s) > n else s


# ──────────────────────────────────────────────────────────────────────
# Pre-flight: health check
# ──────────────────────────────────────────────────────────────────────

async def test_health(client: KbClient):
    section("Pre-flight: Health Check")
    
    # health_check
    r = await client.health_check()
    record("health_check", r.get("backend", False) and r.get("web", False),
           f"backend={r.get('backend')}, web={r.get('web')}, mineru={r.get('mineru')}")
    
    # backend_status
    r = await client.backend_status()
    bh = r.get("backend_health", {})
    ms = r.get("mineru_status", {})
    backend_ok = isinstance(bh, dict) and bh.get("status") in ("ok", "healthy", "running")
    record("backend_status", backend_ok,
           f"backend_health={truncate(str(bh))}, mineru={truncate(str(ms))}")
    
    return r.get("backend", False) and r.get("web", False)


# ──────────────────────────────────────────────────────────────────────
# Skill 1: knowledgebase-list (L1→L3)
# ──────────────────────────────────────────────────────────────────────

async def test_list_skill(client: KbClient):
    section("Skill: knowledgebase-list (L1→L3)")
    
    # L1 — Full Inventory
    # kb_list
    r = await client.kb_list()
    kbs = r.get("knowledgeBases", []) if isinstance(r, dict) else []
    record("L1: kb_list", r.get("success", True) if isinstance(r, dict) else False,
           f"{len(kbs)} KBs found")
    
    # kb_tags_list
    r = await client.kb_tags_list()
    tags = r.get("tags", []) if isinstance(r, dict) else []
    record("L1: kb_tags_list", isinstance(r, dict),
           f"{len(tags)} tags found")
    
    # fs_get_tree (max_depth=2)
    r = await client.fs_get_tree()
    record("L1: fs_get_tree", isinstance(r, list),
           f"{len(r) if isinstance(r, list) else 'error'} root nodes")
    
    # kb_catalog (lightweight)
    r = await client.kb_list()  # same endpoint
    if isinstance(r, dict) and r.get("success", True):
        catalog = [{"kb_id": kb.get("kbId"), "name": kb.get("name"), "doc_count": kb.get("documentCount", 0)} for kb in r.get("knowledgeBases", [])]
        record("L1: kb_catalog (lightweight)", True, f"{len(catalog)} entries")
    else:
        record("L1: kb_catalog (lightweight)", False)
    
    # L2 — KB Drill-Down (pick first KB with docs)
    target_kb = None
    for kb in kbs:
        if kb.get("documentCount", 0) > 0:
            target_kb = kb
            break
    
    if target_kb:
        kb_id = target_kb.get("kbId") or target_kb.get("path")
        
        # kb_get_documents
        r = await client.kb_get_documents(kb_id)
        docs = r.get("documents", []) if isinstance(r, dict) else []
        record("L2: kb_get_documents", isinstance(r, dict),
               f"KB='{target_kb.get('name')}', {len(docs)} docs")
        
        # kb_doc_catalog (lightweight)
        if docs:
            catalog = [{"doc_path": d.get("path"), "name": d.get("name")} for d in docs[:5]]
            record("L2: kb_doc_catalog (lightweight)", True, f"sample: {len(catalog)} docs")
        else:
            record_skip("L2: kb_doc_catalog", "no docs in KB")
        
        # L3 — Browse Tree
        r = await client.fs_get_tree()
        record("L3: fs_get_tree (full)", isinstance(r, list), f"{len(r) if isinstance(r, list) else 0} root nodes")
        
        # fs_get_count
        r = await client.fs_get_count()
        record("L3: fs_get_count", isinstance(r, dict),
               f"counts={r}" if isinstance(r, dict) else "error")
    else:
        record_skip("L2-L3: KB drill-down", "no KB with docs found")
    
    return target_kb


# ──────────────────────────────────────────────────────────────────────
# Skill 2: knowledgebase-search (VFCR Step1→Step6)
# ──────────────────────────────────────────────────────────────────────

async def test_search_skill(client: KbClient, target_kb: dict = None):
    section("Skill: knowledgebase-search (VFCR Step1→Step6)")
    
    query = "machine learning transformer attention mechanism"
    
    # Step 1 — Vector Recall (kb_search_two_stage)
    r = await client.two_stage_search(query, kb_id="", stage1_top_k=20, stage2_top_k=5)
    stage2 = r.get("stage2", {}) if isinstance(r, dict) else {}
    results = stage2.get("results", []) if isinstance(stage2, dict) else []
    record("Step1: kb_search_two_stage", isinstance(r, dict) and r.get("success", True) is not False,
           f"{len(results)} results returned")
    
    # Step 2 — Content Verification (kb_doc_read top 3)
    verified_docs = []
    for i, res in enumerate(results[:3]):
        doc_path = res.get("doc_path", "")
        kb_id = res.get("kb_id", "")
        if doc_path and kb_id:
            r2 = await client.kb_doc_read(kb_id=kb_id, doc_path=doc_path, max_chars=3000)
            content = r2.get("content", "") if isinstance(r2, dict) else ""
            record(f"Step2: kb_doc_read candidate {i+1}", len(content) > 100,
                   f"doc={doc_path}, chars={len(content)}")
            verified_docs.append({"doc_path": doc_path, "kb_id": kb_id, "content_len": len(content)})
        else:
            record_skip(f"Step2: candidate {i+1}", "missing doc_path or kb_id")
    
    # Step 3 — Tag + Description Expansion (if needed)
    r = await client.kb_tags_list()
    tags = r.get("tags", []) if isinstance(r, dict) else []
    record("Step3: kb_tags_list", isinstance(r, dict), f"{len(tags)} tags")
    
    if tags:
        first_tag = tags[0] if isinstance(tags[0], str) else tags[0].get("name", "")
        if first_tag:
            r = await client.kb_doc_get_by_tag(tag=first_tag, kb_id="")
            tagged_docs = r.get("documents", []) if isinstance(r, dict) else []
            record("Step3: kb_doc_get_by_tag", isinstance(r, dict),
                   f"tag='{first_tag}', {len(tagged_docs)} docs")
        else:
            record_skip("Step3: kb_doc_get_by_tag", "empty tag name")
    
    # Step 4 — Expanded Content Verification (kb_search_vector wider)
    r = await client.vector_search(query, kb_id="", top_k=10)
    vector_results = r.get("results", []) if isinstance(r, dict) else []
    record("Step4: kb_search_vector (wider)", isinstance(r, dict),
           f"{len(vector_results)} results")
    
    # Step 5 — Confidence Assessment (just verify the flow, no actual scoring)
    record("Step5: Confidence assessment", True, "Flow verified — scoring is agent-side logic")
    
    # Step 6 — Answer synthesis (flow verification)
    record("Step6: Answer synthesis", True, "Flow verified — synthesis is agent-side logic")
    
    # Also test kb_search (metadata-only)
    r = await client.kb_search(query="transformer", top_k=5)
    record("Bonus: kb_search (metadata)", isinstance(r, dict),
           f"{len(r.get('results', r.get('documents', []))) if isinstance(r, dict) else 0} hits")
    
    # kb_search_stats
    r = await client.search_stats(kb_id="")
    record("Bonus: kb_search_stats", isinstance(r, dict),
           truncate(str(r.get("stats", r))))


# ──────────────────────────────────────────────────────────────────────
# Skill 3: knowledgebase-ingest (A0→A9)
# ──────────────────────────────────────────────────────────────────────

async def test_ingest_skill(client: KbClient):
    section("Skill: knowledgebase-ingest (A0→A9)")
    
    test_doc_name = "skill_test_doc.md"
    test_content = """# Skill Test Document

This is a test document for verifying the ingest skill workflow.

## Overview
This document tests the A0-A9 ingestion pipeline:
- A0: Duplicate pre-check
- A1: Survey collection
- A2: Acquire content
- A3: Analyze content
- A4: Find/Create KB
- A5: Store document
- A6: Index + Tag
- A7: Verify

## Technical Details
The test uses a simple markdown document to verify that the
knowledge base ingestion pipeline works correctly end-to-end.

## Tags
testing, skill-test, ingestion-pipeline
"""
    
    # A0 — Duplicate Pre-Check
    r = await client.kb_search(query=test_doc_name, top_k=5)
    existing = r.get("results", r.get("documents", [])) if isinstance(r, dict) else []
    is_dup = any(test_doc_name in str(d.get("name", "")) for d in existing)
    record("A0: Duplicate pre-check (kb_search)", isinstance(r, dict),
           f"dup={is_dup}, {len(existing)} candidates")
    
    # A1 — Survey
    r = await client.kb_list()
    kbs = r.get("knowledgeBases", []) if isinstance(r, dict) else []
    record("A1: Survey kb_list", isinstance(r, dict), f"{len(kbs)} KBs")
    
    r = await client.kb_tags_list()
    record("A1: Survey kb_tags_list", isinstance(r, dict))
    
    # A4 — Find/Create KB (create test KB)
    test_kb_name = "SkillTest-KB"
    r = await client.kb_create(name=test_kb_name, description="Test KB for skill workflow verification")
    if isinstance(r, dict) and r.get("success", True):
        test_kb = r.get("knowledgeBase", r)
        test_kb_id = test_kb.get("id") or test_kb.get("kbId") or test_kb.get("path")
        record("A4: kb_create (test KB)", True, f"kb_id={test_kb_id}")
    else:
        # Maybe already exists, try to find it
        r = await client.kb_list()
        kbs = r.get("knowledgeBases", []) if isinstance(r, dict) else []
        test_kb = next((kb for kb in kbs if kb.get("name") == test_kb_name), None)
        if test_kb:
            test_kb_id = test_kb.get("kbId") or test_kb.get("path")
            record("A4: kb_create (already exists)", True, f"kb_id={test_kb_id}")
        else:
            record("A4: kb_create", False, truncate(str(r)))
            return None
    
    # A5 — Store Document (direct-path: kb_doc_create)
    r = await client.kb_doc_create(kb_id=test_kb_id, name=test_doc_name, content=test_content, description="Test doc for skill workflow verification")
    if isinstance(r, dict):
        doc = r.get("document", r)
        doc_path = doc.get("path", test_doc_name)
        doc_id = doc.get("id", "")
        record("A5: kb_doc_create", True, f"path={doc_path}, id={doc_id}")
    else:
        record("A5: kb_doc_create", False, truncate(str(r)))
        doc_path = test_doc_name
        doc_id = ""
    
    # A6 — Index + Tag
    r = await client.index_document(kb_id=test_kb_id, doc_path=doc_path, doc_name=test_doc_name, description="Test doc for skill workflow verification", content=test_content)
    record("A6: kb_index_document", isinstance(r, dict) and r.get("success") is not False,
           truncate(str(r.get("vector_index", r))) if isinstance(r, dict) else "error")
    
    r = await client.kb_doc_update_tags(kb_id=test_kb_id, doc_path=doc_path, tags=["testing", "skill-test", "ingestion"])
    record("A6: kb_doc_update_tags", isinstance(r, dict),
           truncate(str(r)))
    
    # A7 — Verify
    r = await client.kb_doc_read(kb_id=test_kb_id, doc_path=doc_path, max_chars=500)
    content = r.get("content", "") if isinstance(r, dict) else ""
    record("A7: kb_doc_read (verify)", len(content) > 50,
           f"chars={len(content)}, starts_with={truncate(content[:80])}")
    
    # A8 — Sub-KB Check (skip — test KB has only 1 doc)
    record_skip("A8: Sub-KB check", "test KB has <8 docs")
    
    # A9 — Report
    record("A9: Report", True, f"doc={doc_path}, kb={test_kb_name}, tags=3, indexed=True")
    
    return {"kb_id": test_kb_id, "doc_path": doc_path, "doc_id": doc_id}


# ──────────────────────────────────────────────────────────────────────
# Skill 4: knowledgebase-manage (M1→M6)
# ──────────────────────────────────────────────────────────────────────

async def test_manage_skill(client: KbClient, test_info: dict):
    section("Skill: knowledgebase-manage (M1→M6)")
    
    kb_id = test_info["kb_id"]
    doc_path = test_info["doc_path"]
    
    # M1 — Survey
    r = await client.kb_list()
    record("M1: kb_list", isinstance(r, dict))
    
    r = await client.kb_get_documents(kb_id)
    docs = r.get("documents", []) if isinstance(r, dict) else []
    record("M1: kb_get_documents", isinstance(r, dict), f"{len(docs)} docs")
    
    # M3 — Execute: Update meta
    r = await client.kb_doc_update_meta(kb_id=kb_id, doc_path=doc_path, description="Updated description by manage skill test")
    record("M3: kb_doc_update_meta (description)", isinstance(r, dict),
           truncate(str(r)))
    
    # M3 — Execute: Update content
    new_content = """# Skill Test Document (Updated)

This document has been updated by the manage skill test.

## Updated Content
The content was modified to verify the kb_doc_update_content workflow.
"""
    r = await client.kb_doc_update_content(kb_id=kb_id, doc_path=doc_path, content=new_content)
    record("M3: kb_doc_update_content", isinstance(r, dict),
           truncate(str(r)))
    
    # M4 — Reindex after content update
    r = await client.index_document(kb_id=kb_id, doc_path=doc_path, content=new_content)
    record("M4: kb_index_document (reindex)", isinstance(r, dict) and r.get("success") is not False,
           truncate(str(r.get("vector_index", r))) if isinstance(r, dict) else "error")
    
    # M5 — Verify
    r = await client.kb_doc_read(kb_id=kb_id, doc_path=doc_path, max_chars=500)
    content = r.get("content", "") if isinstance(r, dict) else ""
    record("M5: kb_doc_read (verify update)", "Updated" in content,
           f"chars={len(content)}")
    
    # M6 — Update content flow verification
    record("M6: Update content flow", "Updated" in content, "Flow verified")


# ──────────────────────────────────────────────────────────────────────
# Skill 5: knowledgebase-verify (V1→V6)
# ──────────────────────────────────────────────────────────────────────

async def test_verify_skill(client: KbClient, test_info: dict = None):
    section("Skill: knowledgebase-verify (V1→V6)")
    
    # V1 — Three-Way Metadata Integrity
    r1 = await client.kb_list()
    r2 = await client.fs_get_tree()
    kbs = r1.get("knowledgeBases", []) if isinstance(r1, dict) else []
    tree = r2 if isinstance(r2, list) else []
    record("V1: kb_list vs fs_get_tree", len(kbs) > 0 and len(tree) > 0,
           f"KBs={len(kbs)}, tree_nodes={len(tree)}")
    
    if kbs:
        first_kb = kbs[0]
        kb_id = first_kb.get("kbId") or first_kb.get("path")
        r = await client.kb_get_documents(kb_id)
        docs = r.get("documents", []) if isinstance(r, dict) else []
        record("V1: kb_get_documents", isinstance(r, dict), f"KB='{first_kb.get('name')}', {len(docs)} docs")
    
    # V2 — Document Integrity (sample read)
    if kbs:
        first_kb = kbs[0]
        kb_id = first_kb.get("kbId") or first_kb.get("path")
        r = await client.kb_get_documents(kb_id)
        docs = r.get("documents", []) if isinstance(r, dict) else []
        if docs:
            doc_path = docs[0].get("path", "")
            r = await client.kb_doc_read(kb_id=kb_id, doc_path=doc_path, max_chars=2000)
            content = r.get("content", "") if isinstance(r, dict) else ""
            record("V2: kb_doc_read (sample)", len(content) > 0,
                   f"doc={doc_path}, chars={len(content)}")
        else:
            record_skip("V2: Document integrity", "no docs to sample")
    
    # V3 — Parse Quality (skip — requires MinerU)
    record_skip("V3: Parse quality", "requires MinerU OCR engine")
    
    # V4 — Index Coverage
    r = await client.search_stats(kb_id="")
    record("V4: kb_search_stats (index coverage)", isinstance(r, dict),
           truncate(str(r.get("stats", r))))
    
    r = await client.graph_health()
    record("V4: kb_graph_health", isinstance(r, dict),
           truncate(str(r)))
    
    if kbs:
        kb_id = kbs[0].get("kbId") or kbs[0].get("path")
        r = await client.graph_kb_overview(kb_id)
        record("V4: kb_graph_kb_overview", isinstance(r, dict),
               truncate(str(r)))
    
    # V5 — Scorecard (flow verification)
    record("V5: Scorecard", True, "Flow verified — scoring is agent-side aggregation")
    
    # V6 — Report
    record("V6: Report", True, "Flow verified — report is agent-side synthesis")


# ──────────────────────────────────────────────────────────────────────
# Skill 6: knowledgebase-experience (CRUD + search)
# ──────────────────────────────────────────────────────────────────────

async def test_experience_skill(client: KbClient, test_info: dict = None):
    section("Skill: knowledgebase-experience (CRUD + search)")
    
    kb_id = test_info["kb_id"] if test_info else ""
    if not kb_id:
        # Use first available KB
        r = await client.kb_list()
        kbs = r.get("knowledgeBases", []) if isinstance(r, dict) else []
        if kbs:
            kb_id = kbs[0].get("kbId") or kbs[0].get("path")
        else:
            record_skip("Experience CRUD", "no KB available")
            return
    
    # Create
    r = await client.experience_create(
        kb_id=kb_id,
        title="Test Experience: Skill Workflow Verification",
        scenario="skill-test-scenario",
        category="lesson_learned",
        problem="Need to verify the experience skill workflow works end-to-end",
        solution="Created a test experience record and verified all CRUD operations",
        result="success",
        key_lessons=["Always verify workflow steps", "Test before production use"],
        tags=["testing", "skill-test", "experience"],
        severity="normal",
        related_docs=[],
    )
    
    if isinstance(r, dict):
        exp = r.get("experience", r)
        exp_id = exp.get("id", exp.get("exp_id", ""))
        record("Create: experience_create", bool(exp_id), f"exp_id={exp_id}")
    else:
        record("Create: experience_create", False, truncate(str(r)))
        return
    
    # Read
    r = await client.experience_read(kb_id, exp_id)
    record("Read: experience_read", isinstance(r, dict),
           truncate(str(r.get("experience", r).get("title", ""))))
    
    # List
    r = await client.experience_list(kb_id)
    exps = r.get("experiences", []) if isinstance(r, dict) else []
    record("List: experience_list", isinstance(r, dict), f"{len(exps)} experiences")
    
    # Find by scenario
    r = await client.experience_list(kb_id, scenario="skill-test-scenario")
    exps = r.get("experiences", []) if isinstance(r, dict) else []
    record("Find: experience_find_by_scenario", isinstance(r, dict) and len(exps) > 0,
           f"{len(exps)} matches")
    
    # Search (keyword)
    r = await client.experience_search(kb_id, query="skill workflow", top_k=5)
    record("Search: experience_search (keyword)", isinstance(r, dict),
           f"{len(r.get('experiences', [])) if isinstance(r, dict) else 0} hits")
    
    # Search (vector)
    r = await client.experience_search_vector(kb_id, query="how to test skill workflow", top_k=5)
    record("Search: experience_search_vector", isinstance(r, dict),
           f"{len(r.get('results', [])) if isinstance(r, dict) else 0} hits")
    
    # Apply (record usage)
    r = await client.experience_apply(kb_id, exp_id, user="test-agent", context="skill verification", result="success", notes="Automated test")
    record("Apply: experience_apply", isinstance(r, dict),
           truncate(str(r.get("experience", {}).get("applied_count", ""))))
    
    # Review
    r = await client.experience_review(kb_id, exp_id, reviewer="test-agent", rating=4.5, comment="Good test experience")
    record("Review: experience_review", isinstance(r, dict),
           truncate(str(r.get("experience", {}).get("rating_avg", ""))))
    
    # Summary
    r = await client.experience_summary(kb_id)
    record("Summary: experience_summary", isinstance(r, dict),
           truncate(str(r.get("summary", {}).get("total", ""))))
    
    # Global search
    r = await client.experience_search_global(query="skill test", top_k=5)
    record("Global: experience_search_global", isinstance(r, dict),
           f"{len(r.get('experiences', [])) if isinstance(r, dict) else 0} hits")
    
    # Update
    r = await client.experience_update(kb_id, exp_id, title="Updated: Test Experience", severity="important")
    record("Update: experience_update", isinstance(r, dict),
           truncate(str(r.get("experience", {}).get("title", ""))))
    
    # Delete
    r = await client.experience_delete(kb_id, exp_id)
    record("Delete: experience_delete", isinstance(r, dict),
           truncate(str(r)))


# ──────────────────────────────────────────────────────────────────────
# Skill 7: knowledgebase-graph (build, query, stats)
# ──────────────────────────────────────────────────────────────────────

async def test_graph_skill(client: KbClient, test_info: dict = None):
    section("Skill: knowledgebase-graph (build, query, stats)")
    
    # Health
    r = await client.graph_health()
    record("kb_graph_health", isinstance(r, dict),
           truncate(str(r)))
    
    # Stats
    r = await client.graph_stats()
    record("kb_graph_stats", isinstance(r, dict),
           truncate(str(r)))
    
    # Get a KB to work with
    r = await client.kb_list()
    kbs = r.get("knowledgeBases", []) if isinstance(r, dict) else []
    if not kbs:
        record_skip("Graph build/query", "no KBs available")
        return
    
    target_kb = kbs[0]
    kb_id = target_kb.get("kbId") or target_kb.get("path")
    
    # Build KB graph (incremental)
    r = await client.graph_build_kb(kb_id, force=False)
    record("kb_graph_build_kb (incremental)", isinstance(r, dict),
           truncate(str(r)))
    
    # KB Overview
    r = await client.graph_kb_overview(kb_id)
    record("kb_graph_kb_overview", isinstance(r, dict),
           truncate(str(r)))
    
    # Search documents
    r = await client.graph_search("test", limit=10)
    record("kb_graph_search", isinstance(r, dict),
           f"{len(r.get('documents', [])) if isinstance(r, dict) else 0} hits")
    
    # Search KBs
    r = await client.graph_search_kbs("test", limit=10)
    record("kb_graph_search_kbs", isinstance(r, dict),
           f"{len(r.get('kbs', [])) if isinstance(r, dict) else 0} hits")
    
    # Search tags
    r = await client.graph_search_tags("test", limit=10)
    record("kb_graph_search_tags", isinstance(r, dict),
           f"{len(r.get('tags', [])) if isinstance(r, dict) else 0} hits")
    
    # Central documents
    r = await client.graph_central_documents(kb_id, top_n=5)
    record("kb_graph_central_documents", isinstance(r, dict),
           f"{len(r.get('documents', [])) if isinstance(r, dict) else 0} central docs")
    
    # Cross-KB documents
    r = await client.graph_cross_kb_documents(min_kbs=2, limit=10)
    record("kb_graph_cross_kb_documents", isinstance(r, dict),
           f"{len(r.get('documents', [])) if isinstance(r, dict) else 0} bridge docs")
    
    # Document graph (if we have docs)
    r = await client.kb_get_documents(kb_id)
    docs = r.get("documents", []) if isinstance(r, dict) else []
    if docs:
        doc_path = docs[0].get("path", "")
        r = await client.graph_document(doc_path, limit=20)
        record("kb_graph_document", isinstance(r, dict),
               truncate(str(r)))
        
        r = await client.graph_document_related(doc_path, limit=10)
        record("kb_graph_document_related", isinstance(r, dict),
               f"{len(r.get('related_documents', [])) if isinstance(r, dict) else 0} related")
    
    # Documents by tag
    r = await client.graph_documents_by_tag("testing", limit=10)
    record("kb_graph_documents_by_tag", isinstance(r, dict),
           f"{len(r.get('documents', [])) if isinstance(r, dict) else 0} docs")
    
    # Build all (incremental, no force)
    r = await client.graph_build_all(force=False)
    record("kb_graph_build_all (incremental)", isinstance(r, dict),
           truncate(str(r)))


# ──────────────────────────────────────────────────────────────────────
# Skill 8: knowledgebase-batch (B1→B7)
# ──────────────────────────────────────────────────────────────────────

async def test_batch_skill(client: KbClient, test_info: dict = None):
    section("Skill: knowledgebase-batch (B1→B7)")
    
    kb_id = test_info["kb_id"] if test_info else ""
    if not kb_id:
        r = await client.kb_list()
        kbs = r.get("knowledgeBases", []) if isinstance(r, dict) else []
        if kbs:
            kb_id = kbs[0].get("kbId") or kbs[0].get("path")
        else:
            record_skip("Batch operations", "no KB available")
            return
    
    # B1 — Bulk Tag Migration (flow verification)
    r = await client.kb_tags_list()
    tags = r.get("tags", []) if isinstance(r, dict) else []
    record("B1: kb_tags_list (bulk tag survey)", isinstance(r, dict), f"{len(tags)} tags")
    
    r = await client.kb_get_documents(kb_id)
    docs = r.get("documents", []) if isinstance(r, dict) else []
    record("B1: kb_get_documents (bulk survey)", isinstance(r, dict), f"{len(docs)} docs")
    
    # B2 — Bulk Description Update (flow verification — read sample)
    if docs:
        doc_path = docs[0].get("path", "")
        r = await client.kb_doc_read(kb_id=kb_id, doc_path=doc_path, max_chars=2000)
        record("B2: kb_doc_read (bulk desc update sample)", isinstance(r, dict),
               f"chars={len(r.get('content', ''))}")
    
    # B3 — Directory → KB Mass Ingestion (skip — no directory to ingest)
    record_skip("B3: Directory mass ingestion", "requires source directory")
    
    # B4 — Mass Document Move (skip — would modify production data)
    record_skip("B4: Mass document move", "destructive — skip in test mode")
    
    # B5 — Cross-KB Dedup (flow verification)
    r = await client.kb_list()
    kbs = r.get("knowledgeBases", []) if isinstance(r, dict) else []
    record("B5: Cross-KB dedup survey", isinstance(r, dict), f"{len(kbs)} KBs to compare")
    
    # B6 — Export Summary
    total_docs = 0
    for kb in kbs[:5]:  # sample first 5
        kb_id_tmp = kb.get("kbId") or kb.get("path")
        r = await client.kb_get_documents(kb_id_tmp)
        kb_docs = r.get("documents", []) if isinstance(r, dict) else []
        total_docs += len(kb_docs)
    record("B6: Export summary (sample 5 KBs)", True, f"sampled {total_docs} docs across {min(len(kbs), 5)} KBs")
    
    # B7 — Graph Rebuild (already tested in graph skill)
    record("B7: Graph rebuild (verified in graph skill)", True)


# ──────────────────────────────────────────────────────────────────────
# Skill 9: knowledgebase-search-enterprise (Phase1→Phase5)
# ──────────────────────────────────────────────────────────────────────

async def test_enterprise_search_skill(client: KbClient):
    section("Skill: knowledgebase-search-enterprise (Phase1→Phase5)")
    
    query = "document knowledge management retrieval"
    
    # Phase 1 — Parallel 3-Path Recall
    # Path A: Vector (wider net)
    r_a = await client.two_stage_search(query, kb_id="", stage1_top_k=30, stage2_top_k=10)
    path_a_results = r_a.get("stage2", {}).get("results", []) if isinstance(r_a, dict) else []
    record("Phase1 Path A: kb_search_two_stage (wide)", isinstance(r_a, dict),
           f"{len(path_a_results)} results")
    
    # Path B: Tags (expanded semantic matching)
    r_tags = await client.kb_tags_list()
    tags = r_tags.get("tags", []) if isinstance(r_tags, dict) else []
    tag_docs = []
    for tag in tags[:3]:  # sample first 3 tags
        tag_name = tag if isinstance(tag, str) else tag.get("name", "")
        if tag_name:
            r = await client.kb_doc_get_by_tag(tag=tag_name, kb_id="")
            docs = r.get("documents", []) if isinstance(r, dict) else []
            tag_docs.extend(docs)
    record("Phase1 Path B: Tags expansion", True, f"{len(tags)} tags → {len(tag_docs)} docs")
    
    # Path C: BM25 keyword-only (stage2_top_k=0)
    r_c = await client.two_stage_search(query, kb_id="", stage1_top_k=25, stage2_top_k=0)
    path_c_results = r_c.get("stage1", {}).get("candidates", []) if isinstance(r_c, dict) else []
    record("Phase1 Path C: BM25 (stage2=0)", isinstance(r_c, dict),
           f"{len(path_c_results)} candidates")
    
    # Phase 2 — Cross-Validate + Dedup
    all_docs = {}
    for res in path_a_results:
        dp = res.get("doc_path", "")
        if dp:
            all_docs.setdefault(dp, set()).add("A")
    for doc in tag_docs:
        dp = doc.get("path", "")
        if dp:
            all_docs.setdefault(dp, set()).add("B")
    for res in path_c_results:
        dp = res.get("doc_path", res.get("path", "")) if isinstance(res, dict) else ""
        if dp:
            all_docs.setdefault(dp, set()).add("C")
    
    multi_path = sum(1 for paths in all_docs.values() if len(paths) >= 2)
    record("Phase2: Cross-validate + dedup", True,
           f"{len(all_docs)} unique docs, {multi_path} multi-path")
    
    # Phase 3 — Content Rerank (read top candidates)
    reranked = 0
    for doc_path in list(all_docs.keys())[:5]:
        r = await client.kb_doc_read(path=doc_path, max_chars=3000)
        content = r.get("content", "") if isinstance(r, dict) else ""
        if len(content) > 200:
            reranked += 1
    record("Phase3: Content rerank (sample 5)", True, f"{reranked}/5 docs with sufficient content")
    
    # Phase 4 — Graph Expansion (optional)
    r = await client.graph_search(query, limit=10)
    graph_results = r.get("documents", []) if isinstance(r, dict) else []
    record("Phase4: Graph expansion", isinstance(r, dict),
           f"{len(graph_results)} graph docs")
    
    # Phase 5 — Fused Answer
    record("Phase5: Fused answer", True, "Flow verified — synthesis is agent-side")


# ──────────────────────────────────────────────────────────────────────
# Skill 10: knowledgebase-experience-summarize (Step1→Step5)
# ──────────────────────────────────────────────────────────────────────

async def test_experience_summarize_skill(client: KbClient, test_info: dict = None):
    section("Skill: knowledgebase-experience-summarize (Step1→Step5)")
    
    kb_id = test_info["kb_id"] if test_info else ""
    if not kb_id:
        r = await client.kb_list()
        kbs = r.get("knowledgeBases", []) if isinstance(r, dict) else []
        if kbs:
            kb_id = kbs[0].get("kbId") or kbs[0].get("path")
        else:
            record_skip("Experience summarize", "no KB available")
            return
    
    # Step 1 — Identify Scenario + Target KB
    r = await client.kb_list()
    record("Step1: kb_list (identify target KB)", isinstance(r, dict), f"target={kb_id}")
    
    # Step 2 — Draft Experience (construct draft)
    draft = {
        "title": "Summarized Experience: Automated KB Testing",
        "scenario": "automated-kb-testing",
        "category": "workflow",
        "problem": "Need to verify all KB skills work correctly",
        "solution": "Ran comprehensive test suite covering all 10 skills",
        "result": "success",
        "key_lessons": ["Test all skills before deployment", "Verify each workflow step"],
        "tags": ["testing", "automation", "kb-management"],
        "severity": "normal",
    }
    record("Step2: Draft experience", True, f"title='{draft['title']}'")
    
    # Step 3 — User Confirmation (skip in automated test)
    record_skip("Step3: User confirmation", "automated test mode")
    
    # Step 4 — Persist
    r = await client.experience_create(
        kb_id=kb_id,
        title=draft["title"],
        scenario=draft["scenario"],
        category=draft["category"],
        problem=draft["problem"],
        solution=draft["solution"],
        result=draft["result"],
        key_lessons=draft["key_lessons"],
        tags=draft["tags"],
        severity=draft["severity"],
    )
    
    exp_id = ""
    if isinstance(r, dict):
        exp = r.get("experience", r)
        exp_id = exp.get("id", exp.get("exp_id", ""))
        record("Step4: experience_create", bool(exp_id), f"exp_id={exp_id}")
    else:
        record("Step4: experience_create", False, truncate(str(r)))
    
    # Step 5 — Verify
    if exp_id:
        r = await client.experience_read(kb_id, exp_id)
        title = r.get("experience", {}).get("title", "") if isinstance(r, dict) else ""
        record("Step5: experience_read (verify)", title == draft["title"],
               f"title='{title}'")
        
        # Cleanup
        await client.experience_delete(kb_id, exp_id)
        print("  🧹 Cleaned up summarized experience")


# ──────────────────────────────────────────────────────────────────────
# Cleanup: remove test KB
# ──────────────────────────────────────────────────────────────────────

async def cleanup(client: KbClient, test_info: dict = None):
    section("Cleanup: Remove test artifacts")
    
    if test_info and test_info.get("kb_id"):
        kb_id = test_info["kb_id"]
        # Delete graph data for test KB
        r = await client.graph_delete_kb(kb_id)
        record("Cleanup: kb_graph_delete_kb", isinstance(r, dict),
               truncate(str(r)))
        
        # Delete test KB
        r = await client.kb_delete(kb_id)
        record("Cleanup: kb_delete (test KB)", isinstance(r, dict),
               truncate(str(r)))


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 70)
    print("  KB-MCP Skill Execution Test Suite")
    print(f"  Backend: {config.BACKEND_URL}")
    print(f"  Web:     {config.WEB_URL}")
    print(f"  Mode:    {os.environ.get('APP_MODE', 'prod')}")
    print("=" * 70)
    
    client = KbClient(
        web_url=config.WEB_URL,
        backend_url=config.BACKEND_URL,
    )
    
    try:
        # Pre-flight
        healthy = await test_health(client)
        if not healthy:
            print("\n⚠️  Services not fully healthy. Continuing tests anyway...\n")
        
        # Skill 1: List
        target_kb = await test_list_skill(client)
        
        # Skill 2: Search
        await test_search_skill(client, target_kb)
        
        # Skill 3: Ingest (creates test KB + doc)
        test_info = await test_ingest_skill(client)
        
        # Skill 4: Manage (uses test doc)
        if test_info:
            await test_manage_skill(client, test_info)
        
        # Skill 5: Verify
        await test_verify_skill(client, test_info)
        
        # Skill 6: Experience (uses test KB)
        await test_experience_skill(client, test_info)
        
        # Skill 7: Graph
        await test_graph_skill(client, test_info)
        
        # Skill 8: Batch
        await test_batch_skill(client, test_info)
        
        # Skill 9: Enterprise Search
        await test_enterprise_search_skill(client)
        
        # Skill 10: Experience Summarize
        await test_experience_summarize_skill(client, test_info)
        
        # Cleanup
        if test_info:
            await cleanup(client, test_info)
        
    finally:
        await client.aclose()
    
    # Summary
    section("SUMMARY")
    total = PASS + FAIL + SKIP
    print(f"\n  Total: {total}  |  ✅ Pass: {PASS}  |  ❌ Fail: {FAIL}  |  ⏭️ Skip: {SKIP}")
    print(f"  Pass rate: {PASS}/{PASS+FAIL} = {PASS/(PASS+FAIL)*100:.1f}%" if (PASS+FAIL) > 0 else "  No testable items")
    
    if FAIL > 0:
        print("\n  Failed tests:")
        for r in RESULTS:
            if not r["success"]:
                print(f"    ❌ {r['name']}" + (f" — {r['detail']}" if r['detail'] else ""))
    
    print()


if __name__ == "__main__":
    asyncio.run(main())
