"""AgentWorkShop integration API tests — 按 rag-bridge / diag-bridge 插件的真实调用面测试。

真实消费契约（来自 .AgentWorkShop/plugins/rag-bridge/index.mjs 与 diag-bridge/index.mjs，
以及 docs/agentworkshop-integration.md 钉死的端口与端点）：

  rag-bridge 工具序列（铁律: HTTP 200 且 body.success===true 才算成功）:
    GET  {web}   /api/kb/catalog                       列库
    POST {web}   /api/kb/create                        ensureKB 幂等建库(aw-industrial)
    POST {base}  /api/v1/experience/{kb}/init          经验库初始化(幂等)
    POST {base}  /api/v1/search/two-stage              检索主入口
    POST {base}  /api/v1/experience/{kb}               写经验(category 枚举)
    POST {web}   /api/kb/documents/create              文档写盘 → doc_path
    POST {base}  /api/v1/search/index-document         向量索引(content 直传)
    GET  {base}  /api/v1/experience/{kb}?limit=        经验列表
    POST {base}  /api/v1/experience/global-search      跨库经验检索(零 LLM)
    POST {base}  /api/v1/graph/agent-relation          图谱关联
  diag-bridge: catalog + documents/create + index-document + experience 写入(同上)
  本平台新增对外能力: GET /api/v1/meditation/harnesses + POST /api/v1/meditation/run(harness 覆盖)

外部接入认证（中间件三通道）:
    Bearer <MCP_AUTH_TOKEN>  → mcp-service 身份（kb-mcp 通道, 全 access）
    Bearer <用户 API token>  → register/login → POST /auth/tokens 铸造（外部用户通道）
    无 token                 → 401（必须返回可读错误）

Usage: python scripts/e2e_agentworkshop_api.py
Exit 0 = 全绿。
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
BACKEND = os.environ.get("RAG_E2E_BACKEND", "http://127.0.0.1:8771").rstrip("/")
WEB = os.environ.get("RAG_E2E_WEB", "http://127.0.0.1:6789").rstrip("/")

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def assert_local_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Blocked scheme: {parsed.scheme}")
    if (parsed.hostname or "").lower() not in _LOCAL_HOSTS:
        raise ValueError(f"Blocked non-local host: {parsed.hostname}")
    return url


def mcp_token() -> str:
    tok = os.environ.get("RAG_E2E_TOKEN", "")
    if tok:
        return tok
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("MCP_AUTH_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"')
    return ""


_results: list[tuple[str, bool, str]] = []


def step(name: str, ok: bool, detail: str = "") -> None:
    _results.append((name, ok, detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f" — {detail[:150]}" if detail else ""))


def call(method: str, url: str, body: dict | None = None, token: str = "",
         timeout: int = 60) -> tuple[int, dict]:
    """模拟 rag-bridge callJson：返回 (status, parsed-body)。"""
    assert_local_url(url)
    req = urllib.request.Request(url, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode("utf-8")
    try:
        with urllib.request.urlopen(req, data=data, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"_raw": raw[:300]}


def rag(name: str, method: str, url: str, body: dict | None, token: str,
        timeout: int = 60) -> dict:
    """rag-bridge 铁律：HTTP 200 且 body.success===true。返回 body。"""
    code, parsed = call(method, url, body, token, timeout)
    ok = code == 200 and isinstance(parsed, dict) and parsed.get("success") is True
    detail = "" if ok else f"HTTP {code}: {json.dumps(parsed, ensure_ascii=False)[:110]}"
    step(name, ok, detail)
    return parsed if isinstance(parsed, dict) else {}


def main() -> int:
    svc = mcp_token()
    if not svc:
        print("❌ 未找到 MCP_AUTH_TOKEN（.env 或 RAG_E2E_TOKEN）")
        return 1
    stamp = time.strftime("%Y%m%d-%H%M%S")

    print(f"=== AgentWorkShop integration API tests ===\n  backend={BACKEND}\n  web={WEB}\n")

    # ══ A. 外部用户接入通道：register → login → 铸造长期 API token ══
    print("── A. external user token bootstrap ──")
    user, pwd = f"aw-e2e-{stamp}", "E2e!{0}".format(stamp.replace("-", ""))
    code, body = call("POST", f"{BACKEND}/api/v1/auth/register",
                      {"username": user, "password": pwd, "email": f"{user}@e2e.local"})
    reg_ok = code in (200, 400)  # 400=已存在（重复跑）也算通道可用
    step("auth register (or already exists)", reg_ok, f"HTTP {code}")
    code, body = call("POST", f"{BACKEND}/api/v1/auth/login",
                      {"username": user, "password": pwd})
    user_token = body.get("token", "") if isinstance(body, dict) else ""
    step("auth login → session token", bool(user_token))
    code, body = call("POST", f"{BACKEND}/api/v1/auth/tokens",
                      {"name": "aw-plugin", "ttl_days": 30,
                       "scopes": ["read", "write"]}, token=user_token)
    api_token = body.get("token", "") if isinstance(body, dict) else ""
    step("mint long-lived API token", bool(api_token),
         "scopes=[read,write] ttl=30d" if api_token else f"HTTP {code}")

    # 无 token 负路径：必须 401 且可读
    code, body = call("GET", f"{BACKEND}/api/v1/meditation/harnesses")
    hint = json.dumps(body, ensure_ascii=False)
    step("no-token → readable 401", code == 401 and ("token" in hint or "认证" in hint),
         f"HTTP {code} {hint[:90]}")

    # ══ B. rag-bridge 真实调用序列（MCP service token 通道 = kb-mcp 同款） ══
    print("── B. rag-bridge tool sequence (service token) ──")
    KB = f"aw-industrial-e2e-{stamp}"
    code, body = call("GET", f"{WEB}/api/kb/catalog", token=svc)
    step("kb_list: GET web /api/kb/catalog", code == 200, f"HTTP {code}")

    kb_id = ""
    parsed = rag("ensureKB: POST web /api/kb/create", "POST", f"{WEB}/api/kb/create",
                 {"name": KB, "description": "AgentWorkShop 工业知识库(诊断报告/经验教训/操作规范)"},
                 svc)
    kb_id = (parsed.get("knowledgeBase") or {}).get("id", "")

    parsed = rag("experience init: POST /api/v1/experience/{kb}/init", "POST",
                 f"{BACKEND}/api/v1/experience/{kb_id}/init", {}, svc)

    # 检索主入口（铁律 success===true）
    parsed = rag("kb_search: POST /api/v1/search/two-stage", "POST",
                 f"{BACKEND}/api/v1/search/two-stage",
                 {"query": "伺服轴回零失败怎么办", "kb_id": kb_id, "stage2_top_k": 3}, svc, timeout=90)

    # 写经验（category 枚举见 experience_models.py —— 用 troubleshooting）
    parsed = rag("kb_store experience: POST /api/v1/experience/{kb}", "POST",
                 f"{BACKEND}/api/v1/experience/{kb_id}",
                 {"title": "伺服轴回零失败处理",
                  "category": "troubleshooting",
                  "problem": "回零过程中出现硬件异常，轴无法完成回零。",
                  "solution": "检查原点开关信号线与电气间隙；确认伺服使能时序后再触发回零。",
                  "key_lessons": ["回零前先确认原点开关状态", "使能时序是常见根因"],
                  "tags": ["产线A", "诊断", "source:diag-bridge"]}, svc)

    # 文档写盘 → doc_path
    doc_path = ""
    parsed = rag("doc ingest step1: POST web /api/kb/documents/create", "POST",
                 f"{WEB}/api/kb/documents/create",
                 {"kbId": kb_id, "name": f"diag-{stamp}.md",
                  "content": "# 诊断报告\n\n现象：回零失败。\n根因：原点开关被遮挡。\n处理：清理遮挡并重试。",
                  "description": "AgentWorkShop diag-bridge 自动入库"}, svc)
    doc_path = parsed.get("document", {}).get("path", "") or parsed.get("path", "")

    # 向量索引（content 直传）
    if doc_path:
        parsed = rag("doc ingest step2: POST /api/v1/search/index-document", "POST",
                     f"{BACKEND}/api/v1/search/index-document",
                     {"kb_id": kb_id, "doc_path": doc_path,
                      "content": "# 诊断报告\n\n现象：回零失败。\n根因：原点开关被遮挡。\n处理：清理遮挡并重试。",
                      "tags": ["产线A", "诊断", "source:diag-bridge"]}, svc, timeout=180)
        time.sleep(1)
        parsed = rag("retrieval after ingest: POST /api/v1/search/two-stage", "POST",
                     f"{BACKEND}/api/v1/search/two-stage",
                     {"query": "回零失败 原点开关", "kb_id": kb_id, "stage2_top_k": 3},
                     svc, timeout=90)

    parsed = rag("experience list: GET /api/v1/experience/{kb}", "GET",
                 f"{BACKEND}/api/v1/experience/{kb_id}?limit=10", None, svc)

    parsed = rag("global experience search: POST /api/v1/experience/global-search", "POST",
                 f"{BACKEND}/api/v1/experience/global-search",
                 {"query": "伺服回零", "top_k": 5}, svc)

    if doc_path:
        parsed = rag("graph agent-relation: POST /api/v1/graph/agent-relation", "POST",
                     f"{BACKEND}/api/v1/graph/agent-relation",
                     {"doc_path": doc_path, "target_doc_path": doc_path,
                      "relation_type": "self_reference",
                      "reasoning": "e2e: diagnose report references its own resolution"},
                     svc)

    # ══ C. 外部用户 token 通道（同一调用面，证明外部接入可用） ══
    print("── C. same sequence with external user token ──")
    code, body = call("GET", f"{WEB}/api/kb/catalog", token=api_token)
    step("user token: GET web /api/kb/catalog", code == 200, f"HTTP {code}")
    parsed = rag("user token: POST /api/v1/search/two-stage", "POST",
                 f"{BACKEND}/api/v1/search/two-stage",
                 {"query": "诊断", "kb_id": kb_id, "stage2_top_k": 3}, api_token, timeout=90)
    code, body = call("GET", f"{BACKEND}/api/v1/meditation/harnesses", token=api_token,
                      timeout=180)  # 冷缓存需逐个探测 14 个 CLI 的 --version
    ids = [h.get("id") for h in body.get("harnesses", [])] if isinstance(body, dict) else []
    step("user token: GET /meditation/harnesses", code == 200 and "omp" in ids,
         f"default={body.get('default') if isinstance(body, dict) else code}")

    # ══ D. 本平台新增对外能力：指定 harness 作业 + 三态错误 ══
    print("── D. harness-aware job API ──")
    parsed = rag("meditation run with harness=mock", "POST",
                 f"{BACKEND}/api/v1/meditation/run",
                 {"kb_id": kb_id, "trigger": "manual", "harness": "mock"}, svc, timeout=180)
    code, body = call("POST", f"{BACKEND}/api/v1/meditation/run",
                      {"kb_id": kb_id, "harness": "no-such-engine"}, token=svc)
    det = body.get("detail") if isinstance(body, dict) else {}
    step("unknown harness → 400 HARNESS_UNKNOWN",
         code == 400 and isinstance(det, dict) and det.get("code") == "HARNESS_UNKNOWN",
         f"HTTP {code}")
    code, body = call("POST", f"{BACKEND}/api/v1/meditation/run",
                      {"kb_id": kb_id, "harness": "gemini"}, token=svc)
    det = body.get("detail") if isinstance(body, dict) else {}
    step("unconfigured harness → 409 HARNESS_NOT_CONFIGURED",
         code == 409 and isinstance(det, dict) and det.get("code") == "HARNESS_NOT_CONFIGURED",
         f"HTTP {code} issues={det.get('issues') if isinstance(det, dict) else '-'}")

    # ══ summary ══
    failed = [r for r in _results if not r[1]]
    print(f"\n=== {len(_results) - len(failed)}/{len(_results)} steps passed ===")
    if failed:
        print("failed steps:")
        for name, _, detail in failed:
            print(f"  ❌ {name}: {detail[:120]}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
