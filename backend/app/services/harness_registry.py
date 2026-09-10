"""Harness Registry — 14 个 Agent 执行引擎的单一事实源（Single Source of Truth）。

架构对齐 docs/multi-harness-architecture.md（AgentWorkShop 多 Harness 适配指南），
按本平台「一次性回合作业」模型（meditation 合成 / soul 补全）移植其七条核心原则：

1. 单一契约: 所有引擎经 harness_specs.OneShotEngineSpec 驱动同一个 _run_engine 作业通道。
2. 单一事实源: 本文件的 HARNESS_REGISTRY 是引擎清单的唯一出处 —— 探测、拉起、API 列表、
   模型目录、前端下拉全部由此派生，禁止在别处再写引擎白名单。
3. 两种进程模型: inprocess（mock）/ oneshot CLI（其余 13 个）。本平台的作业天然是
   一次性回合，常驻会话型引擎（codex/dsh/opencode/qwen/hermes）走其官方无头单回合入口。
4. 能力如实声明: capabilities 六元组（steer/supervise/hitl/terminal/context_stats/compact）
   只声明本集成真实实现的能力；不支持的面在 notes 里写明降级语义，不虚报、不静默缺失。
5. 探测与拉起同源: resolve_command 同时服务 probe 与真实 spawn；
   配置覆盖链（config.yml harness.commands.<id>）是命令解析的最后一环。
6. 错误即事件: 未知引擎 400 / 未安装 409（assert_harness_usable），执行期失败结构化返回。
7. Windows 纪律: npm 全局 CLI 是 .cmd shim → 字面量 `cmd.exe /d /s /c` 包装 + 逐参数校验。
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_HARNESS = "omp"

# 引擎命令名 → 探测/拉起同源使用的可执行名。
# cursor 的 CLI 名是 cursor-agent（非 cursor），其余与注册 id 一致。
_CLI_COMMANDS: dict[str, str] = {
    "omp": "omp",
    "opencode": "opencode",
    "codex": "codex",
    "dsh": "dsh",
    "claude": "claude",
    "gemini": "gemini",
    "copilot": "copilot",
    "cursor": "cursor-agent",
    "crush": "crush",
    "goose": "goose",
    "qwen": "qwen",
    "pi": "pi",
    "hermes": "hermes",
}

# 各引擎静态模型目录（"" = 引擎默认模型）。omp 走 `omp models --json` 动态发现。
_STATIC_MODELS: dict[str, list[str]] = {
    "claude": ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-haiku-4-20250514"],
    "codex": ["gpt-5-codex", "gpt-5", "o4-mini"],
    "gemini": ["gemini-2.5-pro", "gemini-2.5-flash"],
    "qwen": ["qwen3-coder-plus", "qwen3-max"],
    "copilot": ["claude-sonnet-4", "gpt-5"],
    "cursor": ["composer-1", "claude-sonnet-4", "gpt-5"],
}


def _caps(*, steer=False, supervise=True, hitl=False, terminal=False,
          context_stats=False, compact=False) -> dict[str, bool]:
    """能力六元组（如实声明，本平台一次性作业集成口径）。"""
    return {
        "steer": steer,
        "supervise": supervise,
        "hitl": hitl,
        "terminal": terminal,
        "context_stats": context_stats,
        "compact": compact,
    }


# ── HARNESS_REGISTRY：单一事实源 ─────────────────────────────────────
# 字段: id / label / description / homepage / process_model(inprocess|oneshot)
#       / capabilities / requires_env(探测信息面) / notes(降级语义)
HARNESS_REGISTRY: dict[str, dict[str, Any]] = {
    "mock": {
        "label": "Mock",
        "description": "进程内剧本引擎（无 LLM、恒可用）。联调/CI/无凭据机器全链路验证。",
        "homepage": "",
        "process_model": "inprocess",
        "capabilities": _caps(steer=True, supervise=True),
        "requires_env": [],
        "notes": "进程内直调，不 spawn 子进程；输出为剧本化结果。",
    },
    "omp": {
        "label": "oh-my-pi (OMP)",
        "description": "默认推荐引擎。`omp -p --mode=json @file` 单回合无头调用。",
        "homepage": "https://github.com/acidsugarx/oh-my-pi",
        "process_model": "oneshot",
        "capabilities": _caps(context_stats=True),
        "requires_env": [],
        "notes": "prompt 经 @临时文件 投递（规避 Windows 8K 命令行上限）；JSONL 事件流解析。",
    },
    "opencode": {
        "label": "OpenCode",
        "description": "`opencode run` 非交互单回合；纯文本 stdout。",
        "homepage": "https://opencode.ai",
        "process_model": "oneshot",
        "capabilities": _caps(),
        "requires_env": [],
        "notes": "npm shim 安装时命令行长度上限 ~8K；超长 prompt 将显式报错而非截断。",
    },
    "codex": {
        "label": "OpenAI Codex CLI",
        "description": "`codex exec --json` 无头单回合；NDJSON 事件流；prompt 走 stdin。",
        "homepage": "https://github.com/openai/codex",
        "process_model": "oneshot",
        "capabilities": _caps(context_stats=True),
        "requires_env": [],
        "notes": "sandbox=read-only 保守档；usage 从 turn.completed 事件透出。",
    },
    "dsh": {
        "label": "DeepSeek Harness",
        "description": "`dsh --profile acp` 标准 ACP v1 单回合会话（session/new + session/prompt）。",
        "homepage": "https://github.com/deepseek-ai/DeepSeek-Harness",
        "process_model": "oneshot",
        "capabilities": _caps(),
        "requires_env": ["DEEPSEEK_API_KEY"],
        "notes": "ACP 驱动器内嵌审批请求 fail-closed 拒绝（单回合保守档）；steer 恒 deferred。",
    },
    "claude": {
        "label": "Claude Code",
        "description": "`claude -p --output-format json` 无头单回合；prompt 走 stdin。",
        "homepage": "https://code.claude.com/docs/en/claude-code",
        "process_model": "oneshot",
        "capabilities": _caps(context_stats=True),
        "requires_env": ["ANTHROPIC_API_KEY"],
        "notes": "--dangerously-skip-permissions 仅限本平台合成作业；探测要求 API key 就绪。",
    },
    "gemini": {
        "label": "Gemini CLI",
        "description": "`gemini -p <prompt> --output-format json` 无头单回合。",
        "homepage": "https://github.com/google-gemini/gemini-cli",
        "process_model": "oneshot",
        "capabilities": _caps(context_stats=True),
        "requires_env": ["GEMINI_API_KEY"],
        "notes": "本机实测 -p 必带 prompt 参数（stdin 管道不被接受）；npm shim 安装时 prompt 上限 ~7.5K，超长显式报错。鉴权锁定 Google 面（API key/OAuth）。",
    },
    "copilot": {
        "label": "GitHub Copilot CLI",
        "description": "`copilot -p <prompt> --output-format json` 单回合（-p 必带 prompt 值）。",
        "homepage": "https://docs.github.com/en/copilot/how-tos/copilot-cli",
        "process_model": "oneshot",
        "capabilities": _caps(),
        "requires_env": ["COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"],
        "notes": "token 链 COPILOT_GITHUB_TOKEN > GH_TOKEN > GITHUB_TOKEN；npm shim 安装时 prompt 上限 ~7.5K。",
    },
    "cursor": {
        "label": "Cursor CLI",
        "description": "`cursor-agent -p --output-format json` 单回合；帧与 Claude Code 同构。",
        "homepage": "https://cursor.com/docs/cli/headless",
        "process_model": "oneshot",
        "capabilities": _caps(context_stats=True),
        "requires_env": ["CURSOR_API_KEY"],
        "notes": "默认不带 --force（文件变更只提案不落地，保守档）。",
    },
    "crush": {
        "label": "Charm Crush",
        "description": "`crush run` 单回合；v0.92+ 无 JSON 格式 → 纯文本 stdout。",
        "homepage": "https://github.com/charmbracelet/crush",
        "process_model": "oneshot",
        "capabilities": _caps(),
        "requires_env": [],
        "notes": "npm shim 可能损坏，可用命令覆盖链指向包内真实 bin；无程序化审批。",
    },
    "goose": {
        "label": "Block Goose",
        "description": "`goose run --output-format stream-json -t <prompt>` 单回合。",
        "homepage": "https://blockgoose.io",
        "process_model": "oneshot",
        "capabilities": _caps(context_stats=True),
        "requires_env": ["OPENAI_API_KEY"],
        "notes": "GOOSE_MODE=auto 无头姿势；provider/model 经 GOOSE_PROVIDER/GOOSE_MODEL env。",
    },
    "qwen": {
        "label": "Qwen Code",
        "description": "`qwen` 管道 stdin 非交互单回合（gemini 同源老 fork，无 --output-format）。",
        "homepage": "https://github.com/QwenLM/qwen-code",
        "process_model": "oneshot",
        "capabilities": _caps(),
        "requires_env": ["OPENAI_API_KEY", "OPENAI_BASE_URL"],
        "notes": "同族≠同协议教训：qwen 独立探针；prompt 走 stdin（长度不限）；纯文本输出。",
    },
    "pi": {
        "label": "pi coding agent",
        "description": "`pi -p --mode json @file` 单回合；prompt 经 @临时文件 投递。",
        "homepage": "https://github.com/badlogic/pi-mono",
        "process_model": "oneshot",
        "capabilities": _caps(context_stats=True),
        "requires_env": [],
        "notes": "provider/model 经 --provider/--model + ~/.pi/agent/models.json 自定义网关。",
    },
    "hermes": {
        "label": "Hermes Agent",
        "description": "`hermes acp` 标准 ACP v1 单回合会话（与 dsh 同型驱动器）。",
        "homepage": "https://github.com/NousResearch/hermes-agent",
        "process_model": "oneshot",
        "capabilities": _caps(),
        "requires_env": ["GLM_API_KEY"],
        "notes": "模型面来自 hermes 自身 config.yaml；审批请求 fail-closed。",
    },
}

# 注册表顺序即前端下拉顺序（mock 恒可用排最前便于联调）
HARNESS_IDS: list[str] = list(HARNESS_REGISTRY.keys())

# 引擎要求的 CLI 命令名（mock 为进程内，无命令）
def harness_command_name(harness_id: str) -> Optional[str]:
    return _CLI_COMMANDS.get(harness_id)


class HarnessNotConfiguredError(RuntimeError):
    """引擎已安装但凭据/配置缺失 —— 上层应映射 HTTP 409（与未安装区分）。"""

    def __init__(self, harness_id: str, issues: list[str]):
        super().__init__(f"Harness '{harness_id}' is not configured: {'; '.join(issues)}")
        self.harness_id = harness_id
        self.issues = issues


class UnknownHarnessError(ValueError):
    """未知引擎 id —— 上层应映射 HTTP 400。"""


class HarnessUnavailableError(RuntimeError):
    """引擎未安装/不可用 —— 上层应映射 HTTP 409。"""

    def __init__(self, harness_id: str, message: str, probe: dict | None = None):
        super().__init__(message)
        self.harness_id = harness_id
        self.probe = probe or {}


def is_known_harness(harness_id: str) -> bool:
    return harness_id in HARNESS_REGISTRY


# ── 命令覆盖链（config.yml harness.commands.<id> 是最后一环） ────────

def _configured_override(harness_id: str) -> str:
    try:
        from app.config import config
        return config.harness_command(harness_id)
    except Exception:
        return ""


_FALLBACK_DIRS = [
    Path.home() / ".local" / "bin",
    Path.home() / ".bun" / "bin",
    Path(os.environ.get("APPDATA", "")) / "npm" if os.environ.get("APPDATA") else None,
    Path("C:/Program Files/nodejs"),
]


def resolve_command(harness_id: str) -> Optional[str]:
    """解析引擎可执行文件绝对路径。探测与真实 spawn 走同一函数（探测拉起同源）。

    覆盖链: config.yml harness.commands.<id> → PATH(shutil.which, 含 PATHEXT)
            → 常见安装目录兜底（~/.local/bin、~/.bun/bin、npm 全局）。
    未找到返回 None。
    """
    if harness_id == "mock":
        return "inprocess:mock"
    cmd_name = harness_command_name(harness_id)
    if not cmd_name:
        return None

    override = _configured_override(harness_id)
    if override:
        # 覆盖项允许带引号/参数？不允许 —— 只接受单一路径或命令名（参数在 build_args 里）
        override = override.strip().strip('"')
        p = Path(override)
        if p.is_file():
            return str(p)
        found = shutil.which(override)
        if found:
            return found
        logger.warning("harness.commands.%s=%r 无法解析，回退 PATH 探测", harness_id, override)

    found = shutil.which(cmd_name)
    if found:
        return found

    exe_name = cmd_name if sys.platform != "win32" else f"{cmd_name}.exe"
    cmd_name_ext = cmd_name if sys.platform != "win32" else f"{cmd_name}.cmd"
    for d in _FALLBACK_DIRS:
        if not d:
            continue
        for name in (exe_name, cmd_name_ext):
            cand = d / name
            if cand.is_file():
                return str(cand)
    return None


_ARG_BAD_CHARS = re.compile(r'["\r\n\x00]')


def validate_spawn_arg(arg: str) -> str:
    """逐参数校验（Windows cmd.exe 包装纪律）：拒绝引号/换行/NUL 控制字符。"""
    if _ARG_BAD_CHARS.search(arg):
        raise ValueError(f"spawn arg contains forbidden characters: {arg[:80]!r}")
    return arg


def wrap_windows_cmd(argv: list[str]) -> list[str]:
    """Windows: .cmd/.bat shim 不能被 CreateProcess 直启 → 字面量 cmd.exe /d /s /c 包装。

    包装器必须是字面量（绝不由环境变量决定）；包装链会重新解析参数 →
    每个参数先过 validate_spawn_arg（拒绝引号/换行/NUL）。
    .exe 直启走 list-form Popen（无 shell 重解析），参数面不做限制。
    非 Windows 原样返回。
    """
    if not argv:
        return argv
    target = argv[0]
    if sys.platform == "win32" and target.lower().endswith((".cmd", ".bat")):
        return ["cmd.exe", "/d", "/s", "/c"] + [validate_spawn_arg(a) for a in argv]
    return list(argv)


# ── 可用性探测（与拉起同源；结果缓存 30s） ────────────────────────────

_PROBE_CACHE: dict[str, dict] = {}
_PROBE_CACHE_TTL = 30.0
# 按 event loop 分键的探测锁（跨 loop 安全：测试/多 worker 各自持锁）
_PROBE_LOCKS: dict[int, asyncio.Lock] = {}


def _probe_lock() -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    lock = _PROBE_LOCKS.get(id(loop))
    if lock is None:
        lock = asyncio.Lock()
        _PROBE_LOCKS[id(loop)] = lock
    return lock


def reset_probe_cache() -> None:
    """测试/命令覆盖变更后清空探测缓存与锁表。"""
    _PROBE_CACHE.clear()
    _PROBE_LOCKS.clear()


def _env_status(harness_id: str) -> list[dict[str, Any]]:
    """requires_env 的信息面：逐个 env 名给出是否就绪（OR 语义表示任一即可）。"""
    out = []
    for name in HARNESS_REGISTRY[harness_id]["requires_env"]:
        present = bool(os.environ.get(name, ""))
        out.append({"name": name, "present": present})
    return out


async def probe_harness(harness_id: str, force: bool = False) -> dict:
    """探测引擎可用性。返回 {installed, version, resolved_command, env, inprocess}。

    - mock: 恒 installed（inprocess）
    - CLI: resolve_command 命中 → `<cmd> --version` 实测（10s 超时，静默窗口启动）
    - claude 特例: bare 模式必须 ANTHROPIC_API_KEY 就绪才算 installed（沿用既有语义）
    """
    if harness_id == "heuristic":
        return {"installed": True, "version": "", "resolved_command": "inprocess:heuristic",
                "inprocess": True, "env": []}
    if not is_known_harness(harness_id):
        raise UnknownHarnessError(f"Unknown harness: {harness_id}")

    cached = _PROBE_CACHE.get(harness_id)
    now = time.time()
    if cached and not force and now - cached.get("_probed_at", 0) < _PROBE_CACHE_TTL:
        return {k: v for k, v in cached.items() if not k.startswith("_")}

    async with _probe_lock():
        cached = _PROBE_CACHE.get(harness_id)
        if cached and not force and time.time() - cached.get("_probed_at", 0) < _PROBE_CACHE_TTL:
            return {k: v for k, v in cached.items() if not k.startswith("_")}

        info = await _probe_impl(harness_id)
        info["_probed_at"] = time.time()
        _PROBE_CACHE[harness_id] = info
        return {k: v for k, v in info.items() if not k.startswith("_")}


async def _probe_impl(harness_id: str) -> dict:
    env_status = _env_status(harness_id)
    base = {
        "resolved_command": None,
        "version": "",
        "inprocess": False,
        "env": env_status,
    }

    if harness_id == "mock":
        return {**base, "installed": True, "resolved_command": "inprocess:mock", "inprocess": True}

    resolved = resolve_command(harness_id)
    if not resolved:
        return {**base, "installed": False,
                "error": f"executable '{harness_command_name(harness_id)}' not found on PATH"}

    version = ""
    installed = False
    try:
        argv = wrap_windows_cmd([resolved, "--version"])
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                argv, capture_output=True, timeout=10,
                **_run_silent_kwargs(),
            ),
        )
        installed = result.returncode == 0
        version = (result.stdout or b"").decode("utf-8", errors="replace").strip().splitlines()
        version = version[0][:120] if version else ""
    except Exception as e:
        logger.debug("Harness probe %s failed: %s", harness_id, e)
        installed = False

    # claude bare 模式需要 API key（沿用既有探测语义）
    if harness_id == "claude" and not any(e["present"] for e in env_status):
        installed = False

    return {**base, "installed": installed, "version": version, "resolved_command": resolved}


def _run_silent_kwargs() -> dict:
    """探测子进程不闪控制台窗口（Windows）。"""
    if sys.platform != "win32":
        return {}
    flags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        flags |= subprocess.CREATE_NO_WINDOW
    si = subprocess.STARTUPINFO()
    si.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
    si.wShowWindow = 0
    return {"creationflags": flags, "startupinfo": si}


def configuration_issues(harness_id: str, probe: dict | None = None) -> list[str]:
    """'没有配置' 检查：引擎 requires_env 声明的凭据环境变量是否就绪。

    返回可读问题列表（空列表 = 配置就绪）。规则：
    - requires_env 为空的引擎（omp/codex 等自带存储凭据）视为就绪；
    - requires_env 列出"或"语义的（如 copilot 三 token 任一即可）任一命中即就绪；
    - 其余引擎要求全部 env 就绪。
    """
    entry = HARNESS_REGISTRY[harness_id]
    env_status = _env_status(harness_id)
    if not env_status:
        return []
    issues: list[str] = []
    if harness_id == "claude":
        # claude bare 模式必须 API key（沿用既有探测硬规则）
        if not any(e["present"] for e in env_status):
            issues.append("ANTHROPIC_API_KEY not set (required by claude bare mode)")
        return issues
    # 多 token 链（任一即可）：COPILOT_GITHUB_TOKEN/GH_TOKEN/GITHUB_TOKEN
    chains: list[list[str]] = [
        [n for n in ("COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN") if n in entry["requires_env"]],
    ]
    handled: set[str] = set()
    for chain in chains:
        if chain and any(e["present"] for e in env_status if e["name"] in chain):
            handled.update(chain)
    for e in env_status:
        if e["name"] in handled or e["present"]:
            continue
        issues.append(f"{e['name']} not set")
    return issues


async def assert_harness_usable(harness_id: str) -> dict:
    """执行前强校验（三态）：
    - 未知引擎 → UnknownHarnessError（路由映射 400）
    - 未安装   → HarnessUnavailableError（路由映射 409）
    - 可用     → 返回 probe 信息
    """
    if not is_known_harness(harness_id):
        raise UnknownHarnessError(
            f"Unknown harness '{harness_id}'. Supported: {', '.join(HARNESS_IDS)}")
    probe = await probe_harness(harness_id)
    if not probe.get("installed", False):
        missing = [probe.get("error") or "probe failed"]
        if harness_id == "claude" and not any(e["present"] for e in probe.get("env", [])):
            missing.append("ANTHROPIC_API_KEY not set")
        raise HarnessUnavailableError(
            harness_id,
            f"Harness '{harness_id}' is not available: {'; '.join(missing)}",
            probe=probe,
        )
    return probe


# ── API 派生面 ────────────────────────────────────────────────────────

def harness_models(harness_id: str) -> list[str]:
    """模型目录：静态表（omp 由 /models 端点动态发现）。未知引擎 400。"""
    if not is_known_harness(harness_id):
        raise UnknownHarnessError(f"Unknown harness: {harness_id}")
    return [""] + _STATIC_MODELS.get(harness_id, [])


async def resolve_default_harness(force: bool = False) -> str:
    """默认引擎解析（配置驱动 + 可用性感知）：

    1. 配置值（config.yml soul.default_harness）已安装 → 用之；
    2. 否则按注册表顺序取第一个已安装的真实引擎（mock 仅作最终兜底，
       避免无任何真实引擎的机器上默认值失效）；
    3. 全部未装 → 回落 mock（剧本引擎恒可用，保证作业链路可跑）。
    """
    try:
        from app.config import config
        configured = config.soul_default_harness
    except Exception:
        configured = DEFAULT_HARNESS

    try:
        if (await probe_harness(configured, force=force)).get("installed"):
            return configured
    except Exception:
        pass

    for hid in HARNESS_IDS:
        if hid == "mock":
            continue
        try:
            if (await probe_harness(hid)).get("installed"):
                return hid
        except Exception:
            continue
    return "mock"


def resolve_default_harness_cached() -> str:
    """同步版：仅消费已暖的探测缓存（不现场 spawn），冷启动时回落配置值。"""
    try:
        from app.config import config
        configured = config.soul_default_harness
    except Exception:
        return DEFAULT_HARNESS
    cached = _PROBE_CACHE.get(configured)
    if cached and cached.get("installed"):
        return configured
    for hid in HARNESS_IDS:
        if hid == "mock":
            continue
        cached = _PROBE_CACHE.get(hid)
        if cached and cached.get("installed"):
            return hid
    return configured


async def list_harnesses() -> list[dict[str, Any]]:
    """注册表全景（含实时可用性）—— API /harnesses 端点与前端下拉的数据源。"""
    out = []
    for hid in HARNESS_IDS:
        entry = HARNESS_REGISTRY[hid]
        try:
            probe = await probe_harness(hid)
        except Exception as e:
            logger.warning("probe %s failed: %s", hid, e)
            probe = {"installed": False, "error": str(e)}
        out.append({
            "id": hid,
            "label": entry["label"],
            "description": entry["description"],
            "homepage": entry["homepage"],
            "process_model": entry["process_model"],
            "capabilities": dict(entry["capabilities"]),
            "requires_env": entry["requires_env"],
            "notes": entry["notes"],
            "models": harness_models(hid),
            "installed": bool(probe.get("installed")),
            "version": probe.get("version", ""),
            "resolved_command": probe.get("resolved_command"),
        })
    return out
