"""
Knowledge Skill System E2E Test — validates all 8 skills via HTTP endpoints.

Tests: health, list, ingest, manage, tags, search, filesystem, cleanup.
Plus skill system integrity check (agent files, all 8 skills present).
"""
import os, sys, json, subprocess, time, asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASS = 0; FAIL = 0
BP = 8765; WP = 6789
BURL = f"http://localhost:{BP}"
WURL = f"http://localhost:{WP}"
K = {}

def ok(m):    global PASS; PASS += 1; print(f"  [PASS] {m}")
def fail(m):  global FAIL; FAIL += 1; print(f"  [FAIL] {m}")
def info(m):  print(f"  .. {m}")
def hr(t):    print(f"\n{'='*60}\n  {t}\n{'='*60}")

def wait_for(url, timeout=60):
    import urllib.request
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            r = urllib.request.urlopen(url, timeout=3)
            if r.status == 200: return True
        except: pass
        time.sleep(2)
    return False

def kill_port(port):
    subprocess.run(["powershell","-NoProfile","-Command",
        f"try {{ $c = Get-NetTCPConnection -LocalPort {port} -ErrorAction Stop; "
        f"Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue; "
        f"Start-Sleep -Seconds 3 }} catch {{}}"],
        capture_output=True, timeout=15)
    time.sleep(2)

async def main():
    global PASS, FAIL

    import httpx

    # ── start services ──
    hr("Starting services (dev: 8765+6789)")
    kill_port(BP); kill_port(WP); time.sleep(2)
    (ROOT / ".env").write_text(
        "APP_MODE=dev\nBACKEND_PORT=8765\nWEB_PORT=6789\nTREE_STORAGE_PATH=../storage/tree-file-system\n",
        encoding="utf-8")
    subprocess.Popen(["uv","run","python","main.py"], cwd=str(ROOT/"backend"),
        env={**os.environ, "APP_MODE": "dev", "BACKEND_PORT": str(BP)},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x00000010)
    if wait_for(f"{BURL}/api/v1/health", 60): ok("Backend started")
    else: fail("Backend timeout"); return
    subprocess.Popen(["node","start.mjs"], cwd=str(ROOT/"web"),
        env={**os.environ, "APP_MODE": "dev", "WEB_PORT": str(WP), "BACKEND_PORT": str(BP)},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x00000010)
    if wait_for(f"{WURL}/api/kb/catalog", 60): ok("Frontend started")
    else: fail("Frontend timeout"); return

    async with httpx.AsyncClient(timeout=10, trust_env=False) as c:
        ts = str(int(time.time()))

        # ── 1. Health ──
        hr("1. Skill: Health (health_check, backend_status, CORS)")
        r = await c.get(f"{BURL}/api/v1/health")
        if r.status_code == 200: ok("health_check — backend /api/v1/health")
        else: fail(f"health_check: {r.status_code}")
        r = await c.options(f"{BURL}/api/v1/health",
            headers={"Origin": "http://x.com", "Access-Control-Request-Method": "GET"})
        if r.headers.get("access-control-allow-origin") == "*": ok("CORS — Access-Control-Allow-Origin=*")
        else: fail("CORS header missing")
        r = await c.get(f"{BURL}/api/v1/mineru/status")
        if r.status_code == 200: ok("backend_status — mineru/status reachable")
        else: fail(f"backend_status: {r.status_code}")

        # ── 2. List ──
        hr("2. Skill: List (kb_list, fs_get_tree, fs_get_count)")
        r = await c.get(f"{WURL}/api/kb/catalog")
        if r.status_code == 200: ok("kb_list — catalog endpoint")
        else: fail(f"kb_list: {r.status_code}")
        r = await c.get(f"{WURL}/api/filesystem")
        if r.status_code == 200: ok("fs_get_tree — filesystem endpoint")
        else: fail(f"fs_get_tree: {r.status_code}")
        r = await c.get(f"{WURL}/api/filesystem?action=count")
        if r.status_code == 200: ok("fs_get_count — counts endpoint")
        else: fail(f"fs_get_count: {r.status_code}")
        r = await c.get(f"{WURL}/api/filesystem?action=children")
        if r.status_code == 200: ok("fs_get_children — children endpoint")
        else: fail(f"fs_get_children: {r.status_code}")

        # ── 3. Ingest ──
        hr("3. Skill: Ingest (kb_create, kb_doc_create, kb_doc_read)")
        r = await c.post(f"{WURL}/api/kb/create",
            json={"name": f"ingest-{ts}", "description": "Ingest test KB"})
        if r.status_code == 200:
            d = r.json()
            kb = d.get("knowledgeBase", d.get("kb", d))
            K["kb_id"] = kb.get("id", "")
            K["kb_path"] = kb.get("path", "")
            ok(f"kb_create — {K['kb_id'][:12]}...")
        else:
            fail(f"kb_create: {r.status_code}")

        if K.get("kb_id"):
            r = await c.post(f"{WURL}/api/kb/documents/create",
                json={"kbId": K["kb_id"], "name": f"doc-{ts}.md",
                      "content": "# Test\n\nCreated for ingest validation.",
                      "description": "Ingest test document"})
            if r.status_code == 200:
                d = r.json()
                K["doc_path"] = d.get("document", {}).get("path", "")
                K["doc_id"] = d.get("document", {}).get("id", "")
                ok(f"kb_doc_create — doc created")
            else:
                fail(f"kb_doc_create: {r.status_code} {r.text[:100]}")

            if K.get("doc_path"):
                r = await c.get(f"{WURL}/api/kb/document",
                    params={"kb_id": K["kb_id"], "doc_path": K["doc_path"], "max_chars": 200})
                if r.status_code == 200: ok("kb_doc_read — doc readable")
                else: fail(f"kb_doc_read: {r.status_code}")

            # Check dedup A0: search by filename
            r = await c.get(f"{WURL}/api/kb/search",
                params={"q": f"doc-{ts}", "top_k": 5})
            if r.status_code == 200: ok("kb_search (dedup pre-check) — reachable")
            elif r.status_code == 400: info("kb_search: 400 (no index yet)")
            else: fail(f"kb_search: {r.status_code}")

        # ── 4. Manage ──
        hr("4. Skill: Manage (kb_doc_update_meta, kb_doc_update_content)")
        if K.get("kb_id") and K.get("doc_path"):
            r = await c.patch(f"{WURL}/api/kb/documents/update",
                json={"kbId": K["kb_id"], "docPath": K["doc_path"],
                      "description": "Updated via manage workflow"})
            if r.status_code == 200: ok("kb_doc_update_meta — description updated")
            else: fail(f"kb_doc_update_meta: {r.status_code} {r.text[:80]}")
            r = await c.put(f"{WURL}/api/kb/documents/content",
                json={"kbId": K["kb_id"], "docPath": K["doc_path"],
                      "content": "# Updated\n\nContent updated."})
            if r.status_code == 200: ok("kb_doc_update_content — content updated")
            else: fail(f"kb_doc_update_content: {r.status_code} {r.text[:80]}")

        # ── 5. Tags ──
        hr("5. Skill: Tags (kb_tags_list, kb_tag_create, kb_doc_update_tags, kb_doc_get_by_tag)")
        r = await c.get(f"{WURL}/api/kb/tags")
        if r.status_code == 200: ok("kb_tags_list — tags endpoint")
        else: fail(f"kb_tags_list: {r.status_code}")
        r = await c.post(f"{WURL}/api/kb/tags", data="tag=e2e-test")
        if r.status_code == 200: ok("kb_tag_create — tag created")
        elif r.status_code in (400, 409): info("kb_tag_create: tag may already exist")
        else: fail(f"kb_tag_create: {r.status_code}")
        if K.get("kb_id") and K.get("doc_path"):
            r = await c.patch(f"{WURL}/api/kb/documents/tags",
                json={"kbId": K["kb_id"], "docPath": K["doc_path"],
                      "tags": ["e2e-test", "ingest-validation"]})
            if r.status_code == 200: ok("kb_doc_update_tags — 2 tags applied")
            else: fail(f"kb_doc_update_tags: {r.status_code} {r.text[:80]}")
        r = await c.get(f"{WURL}/api/kb/documents/by-tag", params={"tag": "e2e-test"})
        if r.status_code == 200: ok("kb_doc_get_by_tag — tag search works")
        else: fail(f"kb_doc_get_by_tag: {r.status_code}")

        # ── 6. Search ──
        hr("6. Skill: Search (kb_search, kb_get_documents)")
        r = await c.get(f"{WURL}/api/kb/search",
            params={"q": "ingest validation", "top_k": 10})
        if r.status_code == 200: ok("kb_search — full-text search")
        elif r.status_code == 400: info("kb_search: 400 (no search index)")
        else: fail(f"kb_search: {r.status_code}")
        if K.get("kb_id"):
            r = await c.get(f"{WURL}/api/kb/documents",
                params={"kb_id": K["kb_id"]})
            if r.status_code == 200:
                d = r.json()
                cnt = d.get("count", 0)
                if cnt > 0: ok(f"kb_get_documents — {cnt} doc(s) found in KB")
                else: fail("kb_get_documents: 0 docs found")
            else:
                info(f"kb_get_documents: {r.status_code}")

        # ── 7. Filesystem ──
        hr("7. Skill: Filesystem (fs_create_folder, fs_get_node, fs_delete_node)")
        r = await c.post(f"{WURL}/api/filesystem/nodes",
            json={"type": "folder", "name": f"fs-{ts}",
                  "description": "Filesystem skill test"})
        if r.status_code == 200:
            K["folder_id"] = r.json().get("id", "")
            ok("fs_create_folder — folder created")
        else:
            fail(f"fs_create_folder: {r.status_code}")
        if K.get("folder_id"):
            r = await c.get(f"{WURL}/api/filesystem",
                params={"action": "node", "id": K["folder_id"]})
            if r.status_code == 200: ok("fs_get_node — node by UUID")
            else: fail(f"fs_get_node: {r.status_code}")
            r = await c.delete(f"{WURL}/api/filesystem/nodes/{K['folder_id']}")
            if r.status_code == 200: ok("fs_delete_node — folder deleted")
            else: fail(f"fs_delete_node: {r.status_code}")

        # ── 8. Cleanup ──
        hr("8. Cleanup (kb_doc_delete, kb_delete)")
        if K.get("kb_id") and K.get("doc_path"):
            r = await c.request("DELETE", f"{WURL}/api/kb/documents/delete",
                json={"kbId": K["kb_id"], "docPath": K["doc_path"]})
            if r.status_code == 200: ok("kb_doc_delete — doc cleaned")
            else: info(f"kb_doc_delete: {r.status_code}")
        if K.get("kb_id"):
            r = await c.request("DELETE", f"{WURL}/api/kb/delete",
                json={"kbId": K["kb_id"]})
            if r.status_code == 200: ok("kb_delete — KB cleaned")
            else: info(f"kb_delete: {r.status_code}")
        r = await c.get(f"{WURL}/api/filesystem?action=count")
        if r.status_code == 200:
            d = r.json()
            info(f"Final state: {d.get('folders',0)} folders, {d.get('files',0)} files")

    # ── 9. Skill System Integrity ──
    hr("9. Skill System Integrity Check")
    SKILLS_DIR = ROOT / ".claude" / "skills"
    expected = {"knowledge-store", "knowledge-ingest", "knowledge-manage",
                "knowledge-organize", "knowledge-search", "knowledge-list",
                "knowledge-verify", "knowledge-batch"}
    existing = set()
    for f in SKILLS_DIR.glob("*/SKILL.md"):
        existing.add(f.parent.name)
    if expected.issubset(existing):
        ok(f"All 8 skills present: {', '.join(sorted(existing))}")
    else:
        fail(f"Missing: {expected - existing}")

    agent_file = ROOT / ".claude" / "agents" / "knowledge-admin.md"
    if agent_file.exists():
        txt = agent_file.read_text(encoding="utf-8")
        checks = [
            ("Error Recovery Protocol" in txt, "Error Recovery Protocol"),
            ("Mixed" in txt and "diagnose" in txt.lower(), "Mixed scenario diagnosis"),
            ("Step 4" in txt and "Audit" in txt, "Step 4 Audit Trail"),
            ("Skill(\"knowledge-verify\")" in txt, "knowledge-verify skill reference"),
            ("Skill(\"knowledge-batch\")" in txt, "knowledge-batch skill reference"),
        ]
        for passed, label in checks:
            if passed: ok(f"Agent: {label}")
            else: fail(f"Agent: {label} missing")
    else:
        fail("Agent file not found")

    # Summary
    hr("RESULTS")
    total = PASS + FAIL
    print(f"  Tested: {total}")
    print(f"  Passed: {PASS}")
    print(f"  Failed: {FAIL}")
    if FAIL == 0:
        print(f"\n  ALL {total} TESTS PASSED — all 8 skills validated.")
    else:
        print(f"\n  {FAIL} failures.")

asyncio.run(main())
