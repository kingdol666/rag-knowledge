"""Harness Engine Specs — 一次性回合作业引擎的命令构建 / prompt 投递 / 输出解析。

对应架构文档中的 OneShotEngineSpec 基座：引擎差异全部收敛为一份 spec 映射表
（resolveCommand / buildArgs / promptDelivery / engineEnv / mapLine），
由 manager 的统一 _run_engine 通道驱动。新增引擎 = 注册表加一项 + 这里加一个 spec。

promptDelivery 四种形态：
- stdin   : prompt 写入子进程 stdin（claude/codex/gemini/qwen/copilot）
- argfile : prompt 写临时文件后以 @<path> 位置参数投递（omp/pi，规避 Windows 8K 上限）
- arg     : prompt 直接作为 argv 位置参数（opencode/cursor/crush/goose；
            受 CreateProcess/cmd 长度上限约束 → prompt_limit_chars 显式护栏）
- embedded: prompt 内嵌在协议参数里经 stdio 传输（dsh/hermes 的 ACP 会话）

错误即事件：所有失败路径（spawn 失败/非 0 退出/超时/解析失败）都结构化返回，
绝不静默吞掉；schema 漂移防护：未知事件忽略并计数。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

from app.services.harness_registry import (
    DEFAULT_HARNESS,
    UnknownHarnessError,
    resolve_command,
    validate_spawn_arg,
    wrap_windows_cmd,
)


# ── Spec 数据结构 ─────────────────────────────────────────────────────

@dataclass
class OneShotEngineSpec:
    """一个引擎的一次性回合作业规格。"""
    id: str
    delivery: str                      # stdin | argfile | arg | embedded | inprocess
    build_args: Callable[[dict], list[str]]   # cfg → 附加 argv（不含可执行名与 prompt）
    parse_output: Callable[[str], tuple[str, Optional[dict]]]  # stdout 文本 → (text, usage)
    engine_env: Optional[Callable[[dict], dict]] = None       # cfg → 额外进程环境
    prompt_limit_chars: Optional[int] = None  # arg 投递的长度护栏（None = 不限）
    timeout_default: int = 600


# ── 输出解析器（每引擎 mapLine；未知事件忽略并计数） ─────────────────

def _iter_json_lines(content: str):
    """逐行尝试 JSON 解析；坏行跳过（schema 漂移防护）。"""
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith("{") and not line.startswith("["):
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def _blocks_text(blocks: Any) -> str:
    """Anthropic 风格 content blocks → 纯文本。"""
    if isinstance(blocks, str):
        return blocks
    if isinstance(blocks, dict):
        blocks = [blocks]
    if not isinstance(blocks, list):
        return ""
    parts = []
    for b in blocks:
        if isinstance(b, dict) and b.get("type") == "text":
            parts.append(str(b.get("text", "")))
    return "\n".join(p for p in parts if p)


def _parse_omp(content: str) -> tuple[str, Optional[dict]]:
    """omp --mode=json：JSONL 事件流，最终回复在 agent_end/turn_end/message_end。

    兜底：agent_end 缺失（超时收割/版本漂移）时聚合 message_update 的
    text_delta 增量（thinking_delta 是推理不算回复）。
    """
    usage = None
    text = ""
    deltas: list[str] = []
    for ev in _iter_json_lines(content):
        if not isinstance(ev, dict):
            continue
        if ev.get("type") in ("agent_end", "turn_end", "message_end"):
            msg = ev.get("message") or ev.get("messages") or []
            msgs = [msg] if isinstance(msg, dict) else msg
            assistant = [m for m in msgs if isinstance(m, dict) and m.get("role") == "assistant"]
            if assistant:
                t = _blocks_text(assistant[-1].get("content"))
                if t.strip():
                    text = t
        elif ev.get("type") == "message_update":
            sub = ev.get("assistantMessageEvent") or {}
            if sub.get("type") == "text_delta" and isinstance(sub.get("delta"), str):
                deltas.append(sub["delta"])
        if ev.get("type") == "usage" or "usage" in ev:
            u = ev.get("usage") or {}
            if isinstance(u, dict) and u:
                usage = usage or u
    if text.strip():
        return text.strip(), usage
    return "".join(deltas).strip(), usage


def _parse_claude(content: str) -> tuple[str, Optional[dict]]:
    """claude -p --output-format json：单个 JSON 对象，result 字段为最终消息。"""
    objs = [o for o in _iter_json_lines(content) if isinstance(o, dict)]
    # 兼容多行拼接的单个 JSON：整体尝试一次
    if not objs:
        try:
            o = json.loads(content)
            objs = [o] if isinstance(o, dict) else []
        except json.JSONDecodeError:
            objs = []
    for obj in reversed(objs):
        if obj.get("type") == "error":
            continue
        result = obj.get("result")
        usage = obj.get("usage") or None
        if isinstance(result, str) and result.strip():
            return result.strip(), usage
        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False), usage
        text = obj.get("text") or ""
        if isinstance(text, str) and text.strip():
            return text.strip(), usage
    return "", None


def _parse_codex(content: str) -> tuple[str, Optional[dict]]:
    """codex exec --json：NDJSON 事件流；最终回复 = 最后一条 item.completed 的 agent_message。"""
    text = ""
    usage = None
    for ev in _iter_json_lines(content):
        if not isinstance(ev, dict):
            continue
        etype = ev.get("type", "")
        if etype == "item.completed":
            item = ev.get("item") or {}
            itype = item.get("type") or item.get("item_type")
            if itype == "agent_message":
                t = item.get("text") or ""
                if isinstance(t, str) and t.strip():
                    text = t
        elif etype == "turn.completed":
            u = ev.get("usage")
            if isinstance(u, dict):
                usage = u
    return text.strip(), usage


def _parse_gemini_json(content: str) -> tuple[str, Optional[dict]]:
    """gemini/qwen --output-format json：单对象 {response, stats}；兼容 stream-json 帧。"""
    try:
        obj = json.loads(content)
        if isinstance(obj, dict):
            resp = obj.get("response")
            if isinstance(resp, str) and resp.strip():
                return resp.strip(), obj.get("stats")
            if isinstance(resp, (dict, list)):
                return json.dumps(resp, ensure_ascii=False), obj.get("stats")
    except json.JSONDecodeError:
        pass
    # stream-json 帧（init/message/result）
    text = ""
    for ev in _iter_json_lines(content):
        if not isinstance(ev, dict):
            continue
        if ev.get("type") == "result" and isinstance(ev.get("response"), str):
            text = ev["response"]
        elif ev.get("type") == "message":
            c = ev.get("content")
            if isinstance(c, str) and c.strip():
                text = c
    return text.strip(), None


def _parse_copilot(content: str) -> tuple[str, Optional[dict]]:
    """copilot -p --output-format json：尽力结构化（response/text/result 字段），纯文本兜底。"""
    for obj in reversed([o for o in _iter_json_lines(content) if isinstance(o, dict)]):
        for key in ("response", "text", "result", "message"):
            v = obj.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip(), None
            t = _blocks_text(v)
            if t.strip():
                return t.strip(), None
    return _plain_text(content), None


def _parse_cursor(content: str) -> tuple[str, Optional[dict]]:
    """cursor-agent --output-format json：与 Claude Code 同构（result 字段）；stream-json 兜底。"""
    text, usage = _parse_claude(content)
    if text:
        return text, usage
    for ev in reversed([o for o in _iter_json_lines(content) if isinstance(o, dict)]):
        if ev.get("type") == "result":
            r = ev.get("result")
            if isinstance(r, str) and r.strip():
                return r.strip(), ev.get("usage")
    return "", None


def _parse_goose(content: str) -> tuple[str, Optional[dict]]:
    """goose --output-format stream-json：JSONL 事件，assistant message 聚合；纯文本兜底。"""
    text = ""
    usage = None
    for ev in _iter_json_lines(content):
        if not isinstance(ev, dict):
            continue
        etype = str(ev.get("type") or ev.get("event") or "")
        msg = ev.get("message") if isinstance(ev.get("message"), dict) else None
        role = (msg or {}).get("role") or ev.get("role")
        if role == "assistant":
            blocks = msg.get("content") if msg else ev.get("content")
            t = _blocks_text(blocks)
            if t.strip():
                text = t
        if etype in ("turn.completed", "usage") and isinstance(ev.get("usage"), dict):
            usage = ev["usage"]
    if not text:
        # goose 某些版本 stream-json 里最终回复是 {"type":"text","text":...} 形态
        for ev in _iter_json_lines(content):
            if isinstance(ev, dict) and ev.get("type") == "text" and isinstance(ev.get("text"), str):
                if ev["text"].strip():
                    text = ev["text"]
    return text.strip(), usage


def _parse_pi(content: str) -> tuple[str, Optional[dict]]:
    """pi --mode json：JSONL（message_end 携带完整 assistant 消息；message_update 增量）。"""
    text = ""
    chunks: list[str] = []
    for ev in _iter_json_lines(content):
        if not isinstance(ev, dict):
            continue
        etype = ev.get("type", "")
        if etype == "message_end":
            msg = ev.get("message") or {}
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                t = _blocks_text(msg.get("content"))
                if t.strip():
                    text = t
        elif etype == "message_update":
            delta = ev.get("delta") or ev.get("text") or ""
            if isinstance(delta, str):
                chunks.append(delta)
    if text:
        return text.strip(), None
    joined = "".join(chunks).strip()
    return joined, None


def _plain_text(content: str) -> str:
    """纯文本 stdout 引擎（opencode/crush）：整段 stdout 即回复。"""
    return content.strip()


_SPECS: dict[str, OneShotEngineSpec] = {}

def _spec(hid: str, **kw) -> None:
    _SPECS[hid] = OneShotEngineSpec(id=hid, **kw)


# omp: prompt 经 @临时文件（规避 Windows 8K 命令行上限），JSONL 事件流
# 工具面按调用方开关：meditation 合成需要 kb 工具；单次补全传 no_tools 压纯文本
def _omp_args(cfg: dict) -> list[str]:
    args = ["-p", "--auto-approve", "--no-session", "--mode=json",
            "--max-time", str(cfg.get("timeout_sec", 600))]
    if cfg.get("model"):
        args += ["--model", cfg["model"]]
    if cfg.get("thinking"):
        args += ["--thinking", cfg["thinking"]]
    if cfg.get("no_tools"):
        args += ["--no-tools"]
    if cfg.get("system_prompt_text"):
        args += ["--system-prompt", str(cfg["system_prompt_text"])]
    return args
_spec("omp", delivery="argfile", build_args=_omp_args, parse_output=_parse_omp)


# claude: stdin 投递 + --output-format json（既有行为全量保留）
def _claude_args(cfg: dict) -> list[str]:
    from app.utils.paths import PROJECT_ROOT
    args = ["-p", "--output-format", "json",
            "--model", cfg.get("model") or "claude-sonnet-4-20250514",
            "--max-budget-usd", str(cfg.get("max_budget_usd", 0.05)),
            "--dangerously-skip-permissions",
            "--no-session-persistence",
            "--bare"]
    if cfg.get("with_workspace_tools"):
        args += ["--mcp-config", str(Path(PROJECT_ROOT.parent) / ".mcp.json"),
                 "--add-dir", str(PROJECT_ROOT.parent)]
    if cfg.get("system_prompt_path"):
        args += ["--system-prompt-file", str(cfg["system_prompt_path"])]
    if cfg.get("result_schema"):
        args += ["--json-schema", json.dumps(cfg["result_schema"])]
    return args
_spec("claude", delivery="stdin", build_args=_claude_args, parse_output=_parse_claude)


# codex: codex exec --json -，prompt 走 stdin；read-only 沙箱保守档
def _codex_args(cfg: dict) -> list[str]:
    args = ["exec", "--json", "--sandbox", "read-only", "--skip-git-repo-check", "-"]
    if cfg.get("model"):
        args = ["exec", "--json", "--sandbox", "read-only",
                "--skip-git-repo-check", "-m", str(cfg["model"]), "-"]
    return args
_spec("codex", delivery="stdin", build_args=_codex_args, parse_output=_parse_codex)


# dsh / hermes: ACP v1 单回合会话（embedded，驱动器见 run_acp_oneshot）
_spec("dsh", delivery="embedded",
      build_args=lambda cfg: ["--profile", "acp"],
      parse_output=lambda content: ("", None))
_spec("hermes", delivery="embedded",
      build_args=lambda cfg: ["acp"],
      parse_output=lambda content: ("", None))


# opencode: opencode run <prompt>（npm shim → 8K 护栏），纯文本 stdout
def _opencode_args(cfg: dict) -> list[str]:
    args = ["run"]
    if cfg.get("model"):
        args += ["-m", str(cfg["model"])]
    return args
_spec("opencode", delivery="arg", build_args=_opencode_args,
      parse_output=lambda c: (_plain_text(c), None), prompt_limit_chars=7500)


# gemini: -p <prompt> arg 投递（本机 gemini 实测 -p 必带参数，stdin 管道不被
# 该版本接受 —— 勿信文档，探针为准）；npm shim → 7.5K 护栏，超长显式报错
def _gemini_args(cfg: dict) -> list[str]:
    args = ["--output-format", "json"]
    if cfg.get("model"):
        args = ["-m", str(cfg["model"])] + args
    args += ["-p"]
    return args
_spec("gemini", delivery="arg", build_args=_gemini_args, parse_output=_parse_gemini_json,
      prompt_limit_chars=7500)


# qwen: 老版 gemini fork —— 无 --output-format；stdin 是一级输入通道
# （-p 语义为"追加到 stdin 输入"，管道 stdin + 无 -p 即非交互）→ 纯文本 stdout
def _qwen_args(cfg: dict) -> list[str]:
    if cfg.get("model"):
        return ["-m", str(cfg["model"])]
    return []
_spec("qwen", delivery="stdin", build_args=_qwen_args,
      parse_output=lambda c: (_plain_text(c), None))


# copilot: -p <text> 必须紧跟 prompt 值（本机实测 -p 空置时吞掉后续旗标报
# "prompt not quoted"）；--output-format json 可用；npm shim → 7.5K 护栏
def _copilot_args(cfg: dict) -> list[str]:
    args = ["--output-format", "json", "--no-ask-user"]
    if cfg.get("model"):
        args += ["--model", str(cfg["model"])]
    args += ["-p"]
    return args
_spec("copilot", delivery="arg", build_args=_copilot_args, parse_output=_parse_copilot,
      prompt_limit_chars=7500)


# cursor: cursor-agent -p --output-format json（native exe，32K 上限内 arg 投递）
def _cursor_args(cfg: dict) -> list[str]:
    args = ["-p", "--output-format", "json"]
    if cfg.get("model"):
        args += ["-m", str(cfg["model"])]
    return args
_spec("cursor", delivery="arg", build_args=_cursor_args, parse_output=_parse_cursor,
      prompt_limit_chars=30000)


# crush: crush run（v0.92+ 纯文本 stdout）；stdin 必须关闭（EOF 挂起坑）
def _crush_args(cfg: dict) -> list[str]:
    return ["run"]
_spec("crush", delivery="arg", build_args=_crush_args,
      parse_output=lambda c: (_plain_text(c), None), prompt_limit_chars=30000)


# goose: prompt 必须 -t 投递（位置参数被拒 exit 2 的教训）+ stream-json
def _goose_args(cfg: dict) -> list[str]:
    args = ["run", "--output-format", "stream-json"]
    if cfg.get("goose_name"):
        args += ["--name", str(cfg["goose_name"])]
    # build_engine_argv 会把 prompt 追加在 argv 末尾 → -t 放最后使其成为 prompt 旗标
    args += ["-t"]
    return args
def _goose_env(cfg: dict) -> dict:
    env = {"GOOSE_MODE": "auto", "GOOSE_DISABLE_SESSION_NAMING": "true"}
    if cfg.get("model"):
        env["GOOSE_MODEL"] = str(cfg["model"])
    return env
_spec("goose", delivery="arg", build_args=_goose_args, parse_output=_parse_goose,
      engine_env=_goose_env, prompt_limit_chars=30000)


# pi: prompt 写临时文件后 @<path> 投递；--mode json JSONL 事件
def _pi_args(cfg: dict) -> list[str]:
    args = ["-p", "--mode", "json"]
    if cfg.get("model"):
        args += ["--model", str(cfg["model"])]
    return args
_spec("pi", delivery="argfile", build_args=_pi_args, parse_output=_parse_pi)


# mock: 进程内剧本引擎
_spec("mock", delivery="inprocess",
      build_args=lambda cfg: [],
      parse_output=lambda c: (_plain_text(c), None))


def get_spec(harness_id: str) -> OneShotEngineSpec:
    if harness_id not in _SPECS:
        raise UnknownHarnessError(f"Unknown harness: {harness_id}")
    return _SPECS[harness_id]


# ── 命令装配（探测与拉起同源：经 resolve_command + Windows 包装） ─────

def build_engine_argv(harness_id: str, cfg: dict, prompt: str,
                      prompt_file: Optional[Path] = None) -> list[str]:
    """装配完整 argv（含可执行名）。arg 投递时 enforce 长度护栏（显式报错不截断）。"""
    spec = get_spec(harness_id)
    resolved = resolve_command(harness_id)
    if not resolved:
        raise RuntimeError(f"Harness '{harness_id}' executable not found")

    args = [str(a) for a in spec.build_args(cfg)]

    if spec.delivery == "argfile":
        if not prompt_file:
            raise RuntimeError(f"Harness '{harness_id}' argfile delivery requires prompt_file")
        validate_spawn_arg(str(prompt_file))
        argv = [resolved] + args + [f"@{prompt_file}"]
    elif spec.delivery == "arg":
        if spec.prompt_limit_chars and len(prompt) > spec.prompt_limit_chars:
            raise ValueError(
                f"Prompt too long for '{harness_id}' arg delivery: {len(prompt)} chars "
                f"(limit {spec.prompt_limit_chars}). Use a stdin/@file harness "
                f"(claude/codex/gemini/omp/pi/...) or shorten the job input.")
        argv = [resolved] + args + [prompt]
    else:  # stdin / embedded / inprocess
        argv = [resolved] + args

    return wrap_windows_cmd(argv)


def engine_env_for(harness_id: str, cfg: dict) -> dict:
    spec = get_spec(harness_id)
    extra = spec.engine_env(cfg) if spec.engine_env else {}
    return {**os.environ, **extra}


# ── ACP 驱动器（dsh / hermes：标准 ACP v1 单回合会话） ────────────────

async def run_acp_oneshot(harness_id: str, cfg: dict, prompt: str,
                          stderr_fp=None) -> dict:
    """spawn ACP 引擎并驱动一个完整单回合：initialize → session/new → session/prompt。

    - 审批请求（session/request_permission 等）一律 fail-closed 回 cancelled（单回合保守档）
    - session/update 的 agent_message_text 增量聚合为最终回复
    - 超时/spawn 失败/无文本 结构化报错
    """
    from app.utils.paths import PROJECT_ROOT
    resolved = resolve_command(harness_id)
    if not resolved:
        raise RuntimeError(f"Harness '{harness_id}' executable not found")
    spec = get_spec(harness_id)
    argv = wrap_windows_cmd([resolved] + [str(a) for a in spec.build_args(cfg)])
    env = engine_env_for(harness_id, cfg)

    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=stderr_fp or asyncio.subprocess.DEVNULL,
        cwd=str(PROJECT_ROOT.parent),
        env=env,
    )

    state = {"text": "", "stop_reason": "", "unknown_events": 0}
    pending_requests: dict[Any, asyncio.Future] = {}
    prompt_req_holder: dict[str, Any] = {"id": None}
    prompt_done: asyncio.Future = asyncio.get_event_loop().create_future()

    def _send(obj: dict) -> None:
        proc.stdin.write((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))

    async def _read_loop() -> None:
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                state["unknown_events"] += 1
                continue
            if not isinstance(msg, dict):
                continue
            # 服务端请求 → fail-closed 应答（超时/取消一律拒绝语义）
            if "id" in msg and "method" in msg:
                _send({"jsonrpc": "2.0", "id": msg["id"],
                       "result": {"outcome": {"outcome": "cancelled"}}})
                continue
            # 响应
            if "id" in msg and ("result" in msg or "error" in msg):
                fut = pending_requests.pop(msg.get("id"), None)
                if fut and not fut.done():
                    if "error" in msg:
                        fut.set_exception(RuntimeError(str(msg["error"])[:300]))
                    else:
                        fut.set_result(msg.get("result"))
                # session/prompt 的响应 = 回合终点
                if msg.get("id") == prompt_req_holder["id"] and not prompt_done.done():
                    prompt_done.set_result(msg.get("result"))
                continue
            # 通知
            method = msg.get("method", "")
            params = msg.get("params") or {}
            if method == "session/update":
                upd = params.get("update") or {}
                if upd.get("sessionUpdate") == "agent_message_text":
                    c = upd.get("content") or {}
                    t = c.get("text") if isinstance(c, dict) else ""
                    if isinstance(t, str):
                        state["text"] += t
            else:
                state["unknown_events"] += 1

    async def _request(method: str, params: dict, req_id: int, timeout: float) -> Any:
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        pending_requests[req_id] = fut
        _send({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        return await asyncio.wait_for(fut, timeout=timeout)

    reader_task = asyncio.ensure_future(_read_loop())
    timeout = int(cfg.get("timeout_sec", 600))
    next_id = 1
    try:
        await asyncio.wait_for(_request("initialize", {
            "protocolVersion": 1,
            "clientCapabilities": {},
        }, next_id, 30), timeout=30)
        next_id += 1

        sess = await asyncio.wait_for(_request("session/new", {
            "cwd": str(PROJECT_ROOT.parent),
            "mcpServers": [],
        }, next_id, 30), timeout=30)
        next_id += 1
        session_id = (sess or {}).get("sessionId") or (sess or {}).get("session_id") or ""

        prompt_req_holder["id"] = next_id
        next_id += 1
        _send({"jsonrpc": "2.0", "id": prompt_req_holder["id"], "method": "session/prompt",
               "params": {
                   "sessionId": session_id,
                   "prompt": [{"type": "text", "text": prompt}],
               }})

        result = await asyncio.wait_for(prompt_done, timeout=timeout)
        if isinstance(result, dict):
            state["stop_reason"] = str(result.get("stopReason", ""))
    except asyncio.TimeoutError:
        state["error"] = f"acp_timeout after {timeout}s"
    except Exception as e:
        state["error"] = f"acp_error: {e}"
    finally:
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass
        await asyncio.sleep(0.1)
        if proc.returncode is None:
            _terminate_acp(proc)
        try:
            await asyncio.wait_for(proc.wait(), timeout=10)
        except asyncio.TimeoutError:
            pass
        reader_task.cancel()

    return state


def _terminate_acp(proc: asyncio.subprocess.Process) -> None:
    """杀进程树（win32 taskkill /T /F；POSIX 进程组）。"""
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           capture_output=True, timeout=10,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        else:
            import signal
            import os as _os
            try:
                pgid = _os.getpgid(proc.pid)
                _os.killpg(pgid, signal.SIGTERM)
            except ProcessLookupError:
                proc.kill()
    except Exception as e:
        logger.warning("ACP terminate failed: %s", e)
        try:
            proc.kill()
        except Exception:
            pass


# ── Mock 进程内剧本引擎 ────────────────────────────────────────────────

def mock_respond(prompt: str, schema: Optional[dict] = None) -> str:
    """Mock 引擎的剧本化回复：
    - meditation 作业（prompt 含 meditation_result 模板）→ 返回合法 meditation_result JSON
    - 其他 → 通用 mock 回执 JSON
    让联调/CI 在无任何外部 CLI 与凭据的机器上全链路跑通。
    """
    if "meditation_result" in prompt:
        # 真实冥想 prompt 模板内嵌 `"kb_id": "..."` JSON 样例；兼容 id= 形态兜底
        m = re.search(r'"kb_id"\s*:\s*"([^"]+)"', prompt) or re.search(r"id=([\w\-/.]+)", prompt)
        kb_id = m.group(1) if m else ""
        s = re.search(r"待处理信号:\s*(\d+)", prompt)
        signals = int(s.group(1)) if s else 0
        return json.dumps({"meditation_result": {
            "kb_id": kb_id,
            "experiences_created": [],
            "drafts_created": [{
                "title": "Mock draft (mock harness)",
                "draft_id": "mock-draft-1",
                "quality_score": 5.0,
            }],
            "skipped": [],
            "total_signals_processed": signals,
            "summary": "mock harness scripted meditation result",
        }}, ensure_ascii=False)
    return json.dumps({
        "mock": True,
        "prompt_chars": len(prompt),
        "summary": "mock harness scripted completion",
    }, ensure_ascii=False)
