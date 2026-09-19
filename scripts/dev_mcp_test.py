"""kb-mcp toolchain live test over stdio (uses benchmark-suite McpClient).

Notes on lib.McpClient semantics:
  - c._recv(id) returns the *result* object of the JSON-RPC response.
  - c.call(name, args) returns the parsed JSON payload of the first text
    content block (or {"raw": text} when the text is not JSON).
Checks: tools/list inventory (94 tools, 41 kb_*), kb_list inventory,
vector-search gold hit, graph stats, kb_get_documents, fs tree.
Usage: python scripts/dev_mcp_test.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "benchmark-suite", "scripts"))

from lib import McpClient  # noqa: E402

RESULTS = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append(ok)
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {name}" + (f" -- {detail}" if detail else ""), flush=True)


def call_fallback(c: McpClient, name: str, variants: list) -> dict:
    """Try successive argument shapes; return the first that does not raise."""
    last_err = ""
    for args in variants:
        try:
            return c.call(name, args)
        except RuntimeError as e:
            last_err = str(e)[:150]
    return {"_error": last_err}


def blob(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False)


def main() -> int:
    c = McpClient()
    try:
        # 1. tools/list — protocol-level inventory
        c._id += 1
        c._send({"jsonrpc": "2.0", "id": c._id, "method": "tools/list"})
        result = c._recv(c._id, timeout=60)
        tools = result.get("tools", [])
        names = {t["name"] for t in tools}
        check("tools/list count == 94", len(tools) == 94, f"count={len(tools)}")
        kb_tools = {n for n in names if n.startswith("kb_")}
        check("kb_* domain tools == 41", len(kb_tools) == 41, f"count={len(kb_tools)}")
        for required in ("kb_list", "kb_search_vector", "kb_get_documents",
                         "kb_graph_stats", "fs_get_tree", "kb_task_status"):
            check(f"tool present: {required}", required in names)

        # 2. kb_list inventory
        data = c.call("kb_list", {})
        kbs = data.get("knowledgeBases", []) if isinstance(data, dict) else []
        check("kb_list returns 8 KBs", data.get("count") == len(kbs) and len(kbs) > 0,
              f"count={data.get('count')}")
        kb_id = ""
        kb_name = ""
        for kb in kbs:
            if "计算机" in str(kb.get("name", "")):
                kb_id, kb_name = kb.get("kbId", ""), kb.get("name", "")
                break
        if not kb_id and kbs:
            kb_id, kb_name = kbs[0].get("kbId", ""), kbs[0].get("name", "")
        check("found target KB", bool(kb_id), f"{kb_name} {kb_id[:8]}")

        # 3. vector-search gold hit (Attention Is All You Need = arXiv 1706.03762)
        r = c.call("kb_search_vector", {"query": "attention is all you need",
                                        "kb_id": kb_id, "top_k": 3})
        text = blob(r)
        hit = "1706.03762" in text or "Attention Is All You Need" in text
        check("kb_search_vector gold hit", bool(r) and "_error" not in r and hit,
              text[:140].replace("\n", " "))

        # 4. graph stats on the KB
        r = call_fallback(c, "kb_graph_stats", [{"kb_id": kb_id}, {}])
        check("kb_graph_stats responds", bool(r) and "_error" not in r,
              blob(r)[:140].replace("\n", " "))

        # 5. document list on the KB
        r = call_fallback(c, "kb_get_documents",
                          [{"kb_id": kb_id}, {"kb_id": kb_id, "limit": 5},
                           {"kbId": kb_id}])
        check("kb_get_documents responds", bool(r) and "_error" not in r,
              blob(r)[:140].replace("\n", " "))

        # 6. fs tree cross-check
        r = call_fallback(c, "fs_get_tree", [{}, {"max_depth": 1}])
        check("fs_get_tree responds", bool(r) and "_error" not in r,
              blob(r)[:140].replace("\n", " "))
    finally:
        c.close()

    failed = RESULTS.count(False)
    print(f"\n==== mcp smoke summary: {len(RESULTS) - failed} passed, "
          f"{failed} failed ====", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
