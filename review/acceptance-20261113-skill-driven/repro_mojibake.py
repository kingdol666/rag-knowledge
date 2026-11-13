# -*- coding: utf-8 -*-
"""repro_mojibake.py — US-003 复现：中文路径 kb_doc_move 的原始字节证据链。

输出目录（全部字面量）：review/acceptance-20261113-skill-driven/repro/
每轮产物：
  round<N>_move_mcp.bin      — mcp_call kb_doc_move 原始 stdout 字节
  round<N>_move_http.bin     — 直连 web move 端点的原始响应字节（绕过 mcp_call）
  round<N>_chroma_docs.txt   — 目标库 Chroma chunk 文本 repr
  round<N>_summary.json      — 判定：响应/存储是否含 mojibake
判定标准：解码后文本含 U+FFFD 或出现 "楠屾敹" 类 GBK 误解码特征串。
出站防护：http+127.0.0.1 白名单 + 解析 IP 环回校验（同 start_experiment.py）。
"""
import ipaddress
import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(r"D:/codes/ClaudeGPT/rag_project/rag-knowledge")
OUT = REPO / "review" / "acceptance-20261113-skill-driven" / "repro"
OUT.mkdir(parents=True, exist_ok=True)
CHROMA_DIR = REPO / "chroma_db"
WEB_BASE = "http://127.0.0.1:6789"
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
STAMP = "20261113"
MOJI_MARKS = ("楠屾敹", "鏂囨.", "娴嬭瘯", "\ufffd")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _guard(url: str) -> str:
    u = urlparse(url)
    if u.scheme != "http" or u.hostname not in ALLOWED_HOSTS:
        raise ValueError("blocked non-loopback url")
    for info in socket.getaddrinfo(u.hostname, u.port or 80):
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_loopback:
            raise ValueError("blocked non-loopback resolve")
    return url


def mcp_raw(tool: str, args: str, timeout: float = 120) -> bytes:
    r = subprocess.run([sys.executable, "-X", "utf8", r"D:/codes/ClaudeGPT/rag_project/rag-knowledge/scripts/mcp_call.py",
                        tool, args], capture_output=True, timeout=timeout)
    return r.stdout


def token() -> str:
    cred = json.loads((REPO / "storage" / "loop-auth.json").read_text(encoding="utf-8"))
    tok = cred.get("token") or ""
    if not tok:
        tok = _login(cred)
        cred["token"] = tok
        (REPO / "storage" / "loop-auth.json").write_text(json.dumps(cred, indent=2), encoding="utf-8")
    return tok


def _login(cred: dict) -> str:
    req = urllib.request.Request(_guard(WEB_BASE + "/api/auth/login"),
                                 data=json.dumps({"username": cred["username"], "password": cred["password"]}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    d = json.loads(_OPENER.open(req, timeout=15).read())
    return d.get("token") or d.get("data", {}).get("token")


def http_post_json(url: str, payload: dict, tok: str, timeout: float = 90) -> bytes:
    req = urllib.request.Request(_guard(url), data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json; charset=utf-8",
                                          "Authorization": "Bearer " + tok}, method="POST")
    with _OPENER.open(req, timeout=timeout) as resp:
        return resp.read()


def moji(s: str) -> bool:
    return any(m in s for m in MOJI_MARKS)


def chroma_docs(collection: str) -> list:
    import chromadb
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    col = client.get_collection(collection)
    got = col.get(limit=20, include=["documents", "metadatas"])
    return [{"doc": d, "meta_path": (m or {}).get("doc_path", "")} for d, m in zip(got["documents"], got["metadatas"])]


def main() -> None:
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    kb_name = f"验收mojibake-{STAMP}-C"
    kb2_name = f"验收mojibake-{STAMP}-D"
    tok = token()
    for attempt in range(rounds):
        tag = f"round{attempt + 1}"
        # ── setup：两个全新 KB，各接收一次 move ──
        d = json.loads(mcp_raw("kb_create", json.dumps({"name": kb_name, "description": "mojibake repro"}, ensure_ascii=False)))
        kb1 = d["knowledgeBase"]["kb_id"]
        d = json.loads(mcp_raw("kb_create", json.dumps({"name": kb2_name, "description": "mojibake repro target"}, ensure_ascii=False)))
        kb2 = d["knowledgeBase"]["kb_id"]
        doc_name = f"验收文档-{STAMP}-{attempt + 1}.md"
        d = json.loads(mcp_raw("kb_doc_create", json.dumps({
            "kb_id": kb1, "name": doc_name, "description": "中文描述验收移动",
            "content": "# 验收文档\n\n中文内容断言：ZQ-MOJI-REP绝地。第二行确保多字节。\n"}, ensure_ascii=False), timeout=180))
        task_id = (d.get("_auto_index") or {}).get("task_id")
        if task_id:
            for _ in range(30):
                if json.loads(mcp_raw("kb_task_status", json.dumps({"task_id": task_id}))).get("status") == "done":
                    break
                time.sleep(2)

        # ── 轮次 A：经 MCP 移动（复现首轮观测形态）──
        src_path = f"{kb_name}/{doc_name}"
        raw = mcp_raw("kb_doc_move", json.dumps({"doc_path": src_path, "target_kb_id": kb2}, ensure_ascii=False), timeout=180)
        (OUT / f"{tag}_move_mcp.bin").write_bytes(raw)
        target_path = f"{kb2_name}/{doc_name}"
        try:
            docs2 = chroma_docs(f"kb_{kb2}")
        except Exception as e:
            docs2 = [{"doc": "", "meta_path": "", "error": str(e)}]
        (OUT / f"{tag}_chroma_docs.txt").write_text(
            "\n\n".join((x.get("doc") or "")[:400] + "\n  meta_path=" + (x.get("meta_path") or "") for x in docs2),
            encoding="utf-8")
        raw_search = mcp_raw("kb_search_vector", json.dumps(
            {"query": "ZQ-MOJI-REP 绝地 中文内容断言", "kb_id": kb2, "top_k": 3}, ensure_ascii=False), timeout=180)
        (OUT / f"{tag}_search_mcp.bin").write_bytes(raw_search)

        # ── 轮次 B：再建一篇，绕过 mcp_call 直连 web 端点移动（传输层对照）──
        doc_name2 = f"验收文档直连-{STAMP}-{attempt + 1}.md"
        payload = json.dumps({"kb_id": kb1, "name": doc_name2, "description": "直连通道",
                              "content": "# 直连验收\n\n第二篇中文断言：ZQ-MOJI-HTTP-直连。\n"}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(_guard(WEB_BASE + "/api/kb/documents/create"),
                                     data=payload, headers={"Content-Type": "application/json; charset=utf-8",
                                                            "Authorization": "Bearer " + tok}, method="POST")
        urllib.request.urlopen(req, timeout=90).read()
        time.sleep(6)
        raw_http = http_post_json(WEB_BASE + "/api/kb/documents/move",
                                  {"docPath": f"{kb_name}/{doc_name2}", "targetKbId": kb2}, tok, timeout=180)
        (OUT / f"{tag}_move_http.bin").write_bytes(raw_http)

        # ── 判定 ──
        def probe(b: bytes) -> dict:
            s = b.decode("utf-8", "replace")
            return {"moji": moji(s), "head": s[:160]}

        summary = {
            "tag": tag, "kb1": kb1, "kb2": kb2,
            "move_mcp": probe(raw), "search_mcp": probe(raw_search),
            "move_http": probe(raw_http),
            "chroma_doc_heads": [(x.get("doc") or "")[:120] for x in docs2[:3]],
            "chroma_moji": any(moji(x.get("doc") or "") or moji(x.get("meta_path") or "") for x in docs2),
        }
        (OUT / f"{tag}_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({k: summary[k] for k in ("tag", "chroma_moji")}, ensure_ascii=False),
              "| move_mcp.moji=", summary["move_mcp"]["moji"],
              "| move_http.moji=", summary["move_http"]["moji"],
              "| search_mcp.moji=", summary["search_mcp"]["moji"])

        # ── cleanup：删光两库文档后删库 ──
        docs_now = json.loads(mcp_raw("kb_get_documents", json.dumps({"kb_id": kb2}, ensure_ascii=False), timeout=120))
        for path in [x.get("path") or x.get("doc_path") for x in (docs_now.get("documents") or docs_now.get("docs") or [])]:
            if path:
                mcp_raw("kb_doc_delete", json.dumps({"kb_id": kb2, "doc_path": path}, ensure_ascii=False), timeout=120)
        mcp_raw("kb_delete", json.dumps({"kb_id": kb1}, ensure_ascii=False), timeout=120)
        mcp_raw("kb_delete", json.dumps({"kb_id": kb2}, ensure_ascii=False), timeout=120)


if __name__ == "__main__":
    main()
