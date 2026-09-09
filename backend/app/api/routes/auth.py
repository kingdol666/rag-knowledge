"""Authentication & API-token management routes.

Public (no auth):  POST /register  POST /login  POST /verify
Authenticated:     GET  /me  GET/POST /tokens  DELETE /tokens/{id}
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from app.services import auth_service
from app.services.auth_service import AuthError

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


def _err(exc: AuthError):
    raise HTTPException(status_code=exc.status_code, detail={"error": "auth_error",
                                                             "message": str(exc)})


@router.post("/register", summary="注册用户（首个用户自动成为 admin）")
async def register(req: dict[str, Any]):
    try:
        # First registered user becomes admin — standard bootstrap convention.
        role = "admin" if auth_service.count_users() == 0 else "user"
        user = auth_service.create_user(
            username=req.get("username", ""), password=req.get("password", ""),
            email=req.get("email", ""), role=role)
        return {"success": True, "user": user,
                "note": "首个注册用户自动获得 admin 角色" if role == "admin" else None}
    except AuthError as e:
        _err(e)


@router.post("/login", summary="登录（返回用户信息；请另行创建 API token 用于调用）")
async def login(req: dict[str, Any]):
    user = auth_service.authenticate_user(req.get("username", ""), req.get("password", ""))
    if user is None:
        raise HTTPException(status_code=401, detail={
            "error": "invalid_credentials", "message": "用户名或密码错误"})
    # convenience: also mint a short-lived session token in one round-trip
    session = auth_service.issue_token(user["id"], name="login-session", ttl_days=1,
                                       scopes=["read", "write"])
    return {"success": True, "user": user, "token": session["token"],
            "token_expires_at": session["expires_at"],
            "hint": "token 为 1 天有效期的会话凭证；长期调用请在 /auth/tokens 创建专属 token"}


@router.post("/verify", summary="校验 token 有效性（供 web 层与网关转发校验）")
async def verify(req: dict[str, Any]):
    token = req.get("token", "")
    # MCP service token: accepted by the backend middleware, so web-layer
    # verification must recognize it too — otherwise kb-mcp would pass the
    # backend but get 401 from the web proxy.
    if auth_service.is_mcp_token(token):
        return {"valid": True,
                "user": {"id": "svc-mcp", "username": "mcp-service", "role": "service"},
                "token": {"id": "svc-mcp", "name": "mcp-service", "scopes": ["read", "write", "admin"],
                          "expires_at": None}}
    result = auth_service.verify_access_token(token)
    if result is None:
        return {"valid": False}
    u, t = result["user"], result["token"]
    return {"valid": True,
            "user": {"id": u["id"], "username": u["username"], "role": u["role"]},
            "token": {"id": t["id"], "name": t["name"], "scopes": t["scopes"],
                      "expires_at": t["expires_at"]}}


@router.get("/me", summary="当前身份（需 token）")
async def me(request: Request):
    user = getattr(request.state, "auth_user", None)
    if user is None:
        raise HTTPException(status_code=401, detail={"error": "unauthorized",
                                                     "message": "缺少或无效的 token"})
    return {"success": True, "user": user}


@router.post("/tokens", summary="创建 API token（明文仅返回一次）")
async def create_token(request: Request, req: dict[str, Any]):
    user = getattr(request.state, "auth_user", None)
    if user is None:
        raise HTTPException(status_code=401, detail={"error": "unauthorized",
                                                     "message": "缺少或无效的 token"})
    try:
        tok = auth_service.issue_token(
            user["id"], name=req.get("name", ""),
            ttl_days=req.get("ttl_days", 30), scopes=req.get("scopes"))
        return {"success": True, "token": tok["token"], "record": {
            k: v for k, v in tok.items() if k != "token"},
            "warning": "请立即保存，该明文不会再次显示"}
    except AuthError as e:
        _err(e)


@router.get("/tokens", summary="列出我的 token（仅摘要，无明文）")
async def list_tokens(request: Request):
    user = getattr(request.state, "auth_user", None)
    if user is None:
        raise HTTPException(status_code=401, detail={"error": "unauthorized",
                                                     "message": "缺少或无效的 token"})
    return {"success": True, "tokens": auth_service.list_tokens(user["id"])}


@router.delete("/tokens/{token_id}", summary="撤销 token")
async def revoke_token(request: Request, token_id: str):
    user = getattr(request.state, "auth_user", None)
    if user is None:
        raise HTTPException(status_code=401, detail={"error": "unauthorized",
                                                     "message": "缺少或无效的 token"})
    ok = auth_service.revoke_token(user["id"], token_id)
    if not ok:
        raise HTTPException(status_code=404, detail={"error": "not_found",
                                                     "message": "token 不存在或已撤销"})
    return {"success": True, "revoked": token_id}
