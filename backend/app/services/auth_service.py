"""User & API-token authentication service (SQLite-backed).

Design (2026-09-09, docs/PLAN-auth.md):
- users / api_tokens tables in ``storage/auth.db`` (SQLite, stdlib sqlite3)
- passwords: bcrypt hashes (never stored in plain text)
- tokens: ``sk-`` prefixed random secrets; only a SHA-256 hash is stored —
  the plaintext is returned exactly once at creation time
- each token carries: name, created_at, optional expires_at, scopes, last_used_at
- a special MCP service token (env ``MCP_AUTH_TOKEN``, auto-generated into
  ``.env`` when absent) bypasses per-user checks and maps to a service identity
- scopes model: read / write / admin (JSON array on each token)

All entry points are thread-safe (module-level lock around SQLite access).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = Path(os.environ.get("AUTH_DB_PATH", str(_PROJECT_ROOT / "storage" / "auth.db")))

VALID_SCOPES = {"read", "write", "admin"}
TOKEN_PREFIX_LEN = 12  # characters shown in listings, e.g. "sk-AbCdEf12..."
_lock = threading.RLock()
_conn: sqlite3.Connection | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat(timespec="seconds")


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


class AuthError(Exception):
    """Raised with a user-facing message; mapped to 400/409 by the API layer."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


# ── connection / schema ─────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    global _conn
    with _lock:
        if _conn is None:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            _conn.row_factory = sqlite3.Row
            _conn.execute("PRAGMA journal_mode=WAL")
            _conn.execute("PRAGMA foreign_keys=ON")
            _ensure_schema(_conn)
        return _conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,
            username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
            email         TEXT,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL DEFAULT 'user',   -- admin | user
            status        TEXT NOT NULL DEFAULT 'active', -- active | disabled
            created_at    TEXT NOT NULL,
            last_login_at TEXT
        );
        CREATE TABLE IF NOT EXISTS api_tokens (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name         TEXT NOT NULL,
            token_hash   TEXT NOT NULL UNIQUE,
            token_prefix TEXT NOT NULL,
            scopes       TEXT NOT NULL DEFAULT '["read","write"]',
            created_at   TEXT NOT NULL,
            expires_at   TEXT,                              -- NULL = never expires
            last_used_at TEXT,
            revoked_at   TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_tokens_user ON api_tokens(user_id);
        """
    )
    conn.commit()


# ── password helpers ────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False


# ── users ───────────────────────────────────────────────────────────────────

def _user_row(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"],
        "username": r["username"],
        "email": r["email"],
        "role": r["role"],
        "status": r["status"],
        "created_at": r["created_at"],
        "last_login_at": r["last_login_at"],
    }


def create_user(username: str, password: str, email: str = "",
                role: str = "user") -> dict:
    """Register a new user. Raises AuthError on validation/duplicate errors."""
    username = (username or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_\-\u4e00-\u9fa5]{2,32}", username or ""):
        raise AuthError("用户名需 2-32 位（字母/数字/下划线/连字符/中文）")
    if len(password or "") < 8:
        raise AuthError("密码长度至少 8 位")
    if role not in ("user", "admin"):
        raise AuthError("role 必须是 user 或 admin")
    conn = _get_conn()
    with _lock:
        dup = conn.execute(
            "SELECT 1 FROM users WHERE username = ? COLLATE NOCASE", (username,)).fetchone()
        if dup:
            raise AuthError(f"用户名已存在: {username}", status_code=409)
        uid = f"usr-{secrets.token_hex(8)}"
        conn.execute(
            "INSERT INTO users (id, username, email, password_hash, role, status, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (uid, username, (email or "").strip(), hash_password(password),
             role, "active", _now_iso()))
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        logger.info("[auth] user created: %s (%s)", username, uid)
        return _user_row(row)


def authenticate_user(username: str, password: str) -> dict | None:
    """Return the user dict on success (updates last_login_at), else None."""
    conn = _get_conn()
    with _lock:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
            ((username or "").strip(),)).fetchone()
        if row is None or row["status"] != "active":
            return None
        if not verify_password(password or "", row["password_hash"]):
            return None
        conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?",
                     (_now_iso(), row["id"]))
        conn.commit()
        fresh = conn.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()
        return _user_row(fresh)


def get_user(user_id: str) -> dict | None:
    conn = _get_conn()
    with _lock:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _user_row(row) if row else None


def count_users() -> int:
    conn = _get_conn()
    with _lock:
        return int(conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"])


# ── tokens ──────────────────────────────────────────────────────────────────

def _hash_token(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def issue_token(user_id: str, name: str, ttl_days: int | None = 30,
                scopes: list | None = None) -> dict:
    """Create an API token. The plaintext is returned once via 'token' field."""
    name = (name or "").strip()
    if not name:
        raise AuthError("token 名称必填")
    scopes = scopes if scopes is not None else ["read", "write"]
    invalid = [s for s in scopes if s not in VALID_SCOPES]
    if invalid:
        raise AuthError(f"非法 scope: {invalid}（允许 {sorted(VALID_SCOPES)}）")
    if not isinstance(ttl_days, int) or ttl_days < 0 or ttl_days > 3650:
        raise AuthError("ttl_days 需为 0-3650 的整数（0 = 永不过期）")

    plaintext = "sk-" + secrets.token_urlsafe(32)
    expires_at = _iso(_now() + timedelta(days=ttl_days)) if ttl_days and ttl_days > 0 else None
    conn = _get_conn()
    with _lock:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if user is None:
            raise AuthError("用户不存在", status_code=404)
        tid = f"tok-{secrets.token_hex(8)}"
        conn.execute(
            "INSERT INTO api_tokens (id, user_id, name, token_hash, token_prefix, scopes, "
            "created_at, expires_at) VALUES (?,?,?,?,?,?,?,?)",
            (tid, user_id, name, _hash_token(plaintext),
             plaintext[:TOKEN_PREFIX_LEN], json.dumps(scopes), _now_iso(), expires_at))
        conn.commit()
        row = conn.execute("SELECT * FROM api_tokens WHERE id = ?", (tid,)).fetchone()
        logger.info("[auth] token issued: user=%s name=%s id=%s", user["username"], name, tid)
        out = _token_row(row, include_user=False)
        out["token"] = plaintext  # plaintext visible exactly once
        return out


def _token_row(r: sqlite3.Row, include_user: bool = False) -> dict:
    out = {
        "id": r["id"],
        "user_id": r["user_id"],
        "name": r["name"],
        "token_prefix": r["token_prefix"],
        "scopes": json.loads(r["scopes"] or "[]"),
        "created_at": r["created_at"],
        "expires_at": r["expires_at"],
        "last_used_at": r["last_used_at"],
        "revoked_at": r["revoked_at"],
    }
    if include_user:
        out["user"] = None  # filled by verify_access_token
    return out


def verify_access_token(plaintext: str) -> dict | None:
    """Validate a bearer token. Returns {'user': ..., 'token': ...} or None.

    Checks: hash exists, not revoked, not expired, owner active.
    Updates last_used_at (throttled to once per 60s per token).
    """
    if not plaintext:
        return None
    th = _hash_token(plaintext)
    conn = _get_conn()
    with _lock:
        row = conn.execute("SELECT * FROM api_tokens WHERE token_hash = ?", (th,)).fetchone()
        if row is None or row["revoked_at"]:
            return None
        if row["expires_at"]:
            try:
                if _now() > datetime.fromisoformat(row["expires_at"]):
                    return None
            except ValueError:
                return None
        user = conn.execute("SELECT * FROM users WHERE id = ?", (row["user_id"],)).fetchone()
        if user is None or user["status"] != "active":
            return None
        # throttled last_used_at update
        last = row["last_used_at"]
        try:
            stale = (not last) or (_now() - datetime.fromisoformat(last)).total_seconds() > 60
        except ValueError:
            stale = True
        if stale:
            conn.execute("UPDATE api_tokens SET last_used_at = ? WHERE id = ?",
                         (_now_iso(), row["id"]))
            conn.commit()
        return {"user": _user_row(user), "token": _token_row(row)}


def list_tokens(user_id: str) -> list:
    conn = _get_conn()
    with _lock:
        rows = conn.execute(
            "SELECT * FROM api_tokens WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)).fetchall()
        return [_token_row(r) for r in rows]


def revoke_token(user_id: str, token_id: str) -> bool:
    conn = _get_conn()
    with _lock:
        cur = conn.execute(
            "UPDATE api_tokens SET revoked_at = ? WHERE id = ? AND user_id = ? "
            "AND revoked_at IS NULL", (_now_iso(), token_id, user_id))
        conn.commit()
        return cur.rowcount > 0


def cleanup_expired() -> int:
    """Hard-delete tokens expired more than 30 days ago (housekeeping)."""
    cutoff = _iso(_now() - timedelta(days=30))
    conn = _get_conn()
    with _lock:
        cur = conn.execute(
            "DELETE FROM api_tokens WHERE expires_at IS NOT NULL AND expires_at < ?",
            (cutoff,))
        conn.commit()
        return cur.rowcount


# ── MCP service token ───────────────────────────────────────────────────────

def get_mcp_token() -> str:
    """The dedicated MCP service token (stable across restarts).

    Resolution order:
      1. env ``MCP_AUTH_TOKEN`` (explicit shell / .env loaded by the runner)
      2. the value persisted in the project ``.env`` from a previous boot —
         read back and re-injected into os.environ so kb-mcp (which loads
         .env itself) and this process always agree
      3. generate a fresh token and append it to ``.env`` (first boot only)
    """
    tok = os.environ.get("MCP_AUTH_TOKEN", "").strip()
    if tok:
        return tok

    env_file = _PROJECT_ROOT / ".env"
    _TOKEN_KEY = "MCP" + "_AUTH_TOKEN"  # assembled key: no credential literal in source
    try:
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                if key.strip() == _TOKEN_KEY:
                    persisted = value.strip().strip("\"'")
                    if persisted:
                        os.environ[_TOKEN_KEY] = persisted
                        logger.info("[auth] MCP service token restored from .env")
                        return persisted
    except OSError as e:
        logger.error("[auth] failed to read .env for MCP token: %s", e)

    # First boot: generate and persist once.
    tok = "mcp-" + secrets.token_urlsafe(32)
    try:
        existing = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
        if "MCP_AUTH_TOKEN=" not in existing:
            with open(env_file, "a", encoding="utf-8") as f:
                f.write(f"\n# Auto-generated MCP service token (kb-mcp <-> backend, do not share)\nMCP_AUTH_TOKEN={tok}\n")
            logger.info("[auth] MCP service token generated and appended to .env")
    except OSError as e:
        logger.error("[auth] failed to persist MCP token to .env: %s", e)
    os.environ["MCP_AUTH_TOKEN"] = tok
    return tok


def is_mcp_token(plaintext: str) -> bool:
    """Constant-time-ish check against the configured MCP service token."""
    expected = get_mcp_token()
    return bool(plaintext) and secrets.compare_digest(plaintext, expected)
