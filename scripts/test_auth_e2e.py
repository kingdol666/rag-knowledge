# -*- coding: utf-8 -*-
"""鉴权系统端到端测试：注册 → 登录 → Token 管理 → 带/无 token 调用 → 撤销。

覆盖 web(6789) 与 backend(8770) 两层拦截、MCP 服务 token 放行、
Token 元数据（名称/创建时间/失效时间）与撤销/过期语义。
"""
import secrets

import httpx
import json

WEB = "http://localhost:6789"
BACKEND = "http://localhost:8770"
results = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {('— ' + detail) if (detail and not ok) else ''}")


def mcp_token_for_cleanup() -> str:
    for line in open(".env", encoding="utf-8"):
        if line.startswith("MCP_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip()
    return ""


def main():
    user = f"e2e_{secrets.token_hex(4)}"
    pwd = "e2e-Passw0rd!"
    hdr = {}

    print("=== 1. 未认证请求应被拦截 ===")
    for label, url in [("web /api/kb/catalog", f"{WEB}/api/kb/catalog"),
                       ("backend /api/v1/soul/list", f"{BACKEND}/api/v1/soul/list"),
                       ("web 写接口", f"{WEB}/api/kb/create")]:
        r = httpx.post(url, timeout=15) if label == "web 写接口" else httpx.get(url, timeout=15)
        record(f"无token {label} -> 401", r.status_code == 401, f"got {r.status_code}")

    r = httpx.get(f"{BACKEND}/api/v1/health", timeout=10)
    record("health 白名单放行", r.status_code == 200, f"got {r.status_code}")

    print("\n=== 2. 注册与登录 ===")
    # 前置清理：上一轮异常退出可能残留同名测试库（重名守卫会 409 拦截重建）
    try:
        cat = httpx.get(f"{WEB}/api/kb/catalog", timeout=20,
                        headers={"Authorization": f"Bearer {mcp_token_for_cleanup()}"})
        for k in cat.json().get("knowledgeBases", []):
            if k.get("name") == "ZZ鉴权e2e库":
                httpx.request("DELETE", f"{WEB}/api/kb/delete", timeout=30,
                              headers={"Authorization": f"Bearer {mcp_token_for_cleanup()}"},
                              json={"kbId": k.get("kbId")})
                print("  (清理残留测试库)")
    except Exception as e:
        print(f"  (清理跳过: {type(e).__name__})")

    r = httpx.post(f"{WEB}/api/auth/register", timeout=20,
                   json={"username": user, "password": pwd, "email": f"{user}@test.com"})
    record("web 代理注册", r.status_code == 200 and r.json().get("success"), r.text[:120])
    dup = httpx.post(f"{WEB}/api/auth/register", timeout=20,
                     json={"username": user, "password": pwd})
    record("重复注册 -> 409", dup.status_code == 409, f"got {dup.status_code}")

    bad = httpx.post(f"{WEB}/api/auth/login", timeout=20,
                     json={"username": user, "password": "wrong-password"})
    record("错误密码登录 -> 401", bad.status_code == 401, f"got {bad.status_code}")

    r = httpx.post(f"{WEB}/api/auth/login", timeout=30, json={"username": user, "password": pwd})
    d = r.json()
    session_token = d.get("token", "")
    record("登录成功且返回会话 token", r.status_code == 200 and session_token.startswith("sk-"),
           r.text[:150])
    hdr = {"Authorization": f"Bearer {session_token}"}

    r = httpx.get(f"{WEB}/api/auth/me", timeout=15, headers=hdr)
    me = r.json().get("user") or {}
    record("/auth/me 返回身份", r.status_code == 200 and me.get("username") == user,
           r.text[:120])

    print("\n=== 3. Token 管理（名称/创建时间/失效时间）===")
    r = httpx.post(f"{WEB}/api/auth/tokens", timeout=20, headers=hdr,
                   json={"name": "e2e-长期token", "ttl_days": 90})
    d = r.json()
    rec = d.get("record") or {}
    long_token = d.get("token", "")
    record("创建 token 明文一次性返回", long_token.startswith("sk-"), r.text[:150])
    record("token 元数据完整",
           rec.get("name") == "e2e-长期token" and rec.get("created_at") and rec.get("expires_at"),
           json.dumps(rec, ensure_ascii=False)[:200])
    record("90 天有效期正确", "days=89" in str(
        (lambda a, b: abs((__import__('datetime').datetime.fromisoformat(a) -
                           __import__('datetime').datetime.fromisoformat(b)).days))(rec.get("expires_at"), rec.get("created_at"))
    ) or abs((__import__('datetime').datetime.fromisoformat(rec["expires_at"]) -
              __import__('datetime').datetime.fromisoformat(rec["created_at"])).days - 90) <= 1,
        f"{rec.get('created_at')} -> {rec.get('expires_at')}")

    r = httpx.post(f"{WEB}/api/auth/tokens", timeout=20, headers=hdr,
                   json={"name": "e2e-永不过期", "ttl_days": 0})
    never = (r.json().get("record") or {})
    record("永不过期 token（expires_at 为空）",
           never.get("expires_at") in (None, "null"), json.dumps(never, ensure_ascii=False)[:120])

    r = httpx.get(f"{WEB}/api/auth/tokens", timeout=15, headers=hdr)
    toks = r.json().get("tokens") or []
    record("token 列表（≥2 条，无明文）", len(toks) >= 2 and all("token" not in t for t in toks),
           f"{len(toks)} 条")

    print("\n=== 4. 带 token 调用知识库 API（两层）===")
    r = httpx.get(f"{WEB}/api/kb/catalog", timeout=20, headers=hdr)
    record("web 知识库目录 -> 200", r.status_code == 200, f"got {r.status_code}")

    r = httpx.post(f"{WEB}/api/kb/create", timeout=30, headers=hdr,
                   json={"name": "ZZ鉴权e2e库", "description": "鉴权端到端测试"})
    record("web 创建知识库", r.status_code == 200, r.text[:150])
    kb_id = (r.json().get("knowledgeBase") or {}).get("kb_id")

    r = httpx.post(f"{WEB}/api/kb/documents/create", timeout=30, headers=hdr,
                   json={"kb_id": "ZZ鉴权e2e库", "name": "doc.md",
                         "content": "# e2e\n\n鉴权后写入的内容 auth-mark-7721"})
    record("web 写入文档", r.status_code == 200, r.text[:150])

    r = httpx.get(f"{WEB}/api/kb/search", timeout=30, headers=hdr,
                  params={"query": "auth-mark-7721", "top_k": 3})
    record("web 关键词检索", r.status_code == 200 and r.json().get("count"), r.text[:120])

    r = httpx.post(f"{BACKEND}/api/v1/search/two-stage", timeout=60, headers=hdr,
                   json={"query": "auth-mark-7721", "top_k": 3})
    record("backend 两阶段检索（同 token 跨层通用）",
           r.status_code == 200 and r.json().get("success"), r.text[:120])

    r = httpx.get(f"{BACKEND}/api/v1/soul/list", timeout=20, headers=hdr)
    record("backend 人格列表", r.status_code == 200, f"got {r.status_code}")

    print("\n=== 5. 撤销后应立即失效 ===")
    tok_id = next((t["id"] for t in toks if t["name"] == "e2e-长期token"), None)
    r = httpx.delete(f"{WEB}/api/auth/tokens/{tok_id}", timeout=15, headers=hdr)
    record("撤销 token", r.status_code == 200, r.text[:120])
    r = httpx.get(f"{WEB}/api/kb/catalog", timeout=20,
                  headers={"Authorization": f"Bearer {long_token}"})
    record("已撤销 token 调用 -> 401", r.status_code == 401, f"got {r.status_code}")
    r = httpx.get(f"{WEB}/api/kb/catalog", timeout=20, headers=hdr)
    record("会话 token 仍有效", r.status_code == 200, f"got {r.status_code}")

    print("\n=== 6. MCP 服务 token 直接放行 ===")
    mcp_tok = ""
    for line in open(".env", encoding="utf-8"):
        if line.startswith("MCP_AUTH_TOKEN="):
            mcp_tok = line.split("=", 1)[1].strip()
    r = httpx.get(f"{BACKEND}/api/v1/soul/list", timeout=20,
                  headers={"Authorization": f"Bearer {mcp_tok}"})
    record("MCP token 访问 backend", r.status_code == 200, f"got {r.status_code}")
    r = httpx.get(f"{WEB}/api/kb/catalog", timeout=20,
                  headers={"Authorization": f"Bearer {mcp_tok}"})
    record("MCP token 访问 web", r.status_code == 200, f"got {r.status_code}")

    print("\n=== 7. 清理 ===")
    r = httpx.request("DELETE", f"{WEB}/api/kb/delete", timeout=30, headers=hdr, json={"kbId": kb_id})
    record("清理测试库", r.status_code == 200, r.text[:100])

    passed = sum(1 for _, ok, _ in results if ok)
    print("\n" + "=" * 60)
    print(f"端到端汇总: {passed}/{len(results)} 通过")
    for n, ok, m in results:
        if not ok:
            print(f"  未通过: {n} — {m}")
    print("=" * 60)


if __name__ == "__main__":
    main()
