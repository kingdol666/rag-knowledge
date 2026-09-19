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
import json
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
    "claude": ["sonnet", "opus", "haiku"],
    "codex": ["gpt-5-codex", "gpt-5", "o3"],
    "gemini": ["gemini-2.5-pro", "gemini-2.5-flash"],
    "qwen": ["qwen3-coder-plus", "qwen3-max"],
    "copilot": ["auto"],
    "cursor": ["composer-1", "claude-sonnet-4", "gpt-5"],
    "goose": [],
    "hermes": [],
    "dsh": [],
}

# ── 思考强度（reasoning effort）——各引擎官方旗标的真实取值面 ─────────
# 空 = 该引擎无每回合思考强度旗标（UI 隐藏该选择器）。
REASONING_LEVELS: dict[str, list[dict[str, str]]] = {
    "claude": [{"id": "low", "label": "Low"}, {"id": "medium", "label": "Medium"},
               {"id": "high", "label": "High"}, {"id": "xhigh", "label": "X-High"},
               {"id": "max", "label": "Max"}],
    # omp 的档位随模型变化（omp models --json 的 thinking 数组），运行时以模型目录为准
    "omp": [],
    "codex": [{"id": "minimal", "label": "Minimal"}, {"id": "low", "label": "Low"},
              {"id": "medium", "label": "Medium"}, {"id": "high", "label": "High"}],
    "copilot": [{"id": "none", "label": "None"}, {"id": "minimal", "label": "Minimal"},
                {"id": "low", "label": "Low"}, {"id": "medium", "label": "Medium"},
                {"id": "high", "label": "High"}, {"id": "xhigh", "label": "X-High"},
                {"id": "max", "label": "Max"}],
    "pi": [{"id": "off", "label": "Off"}, {"id": "minimal", "label": "Minimal"},
           {"id": "low", "label": "Low"}, {"id": "medium", "label": "Medium"},
           {"id": "high", "label": "High"}, {"id": "xhigh", "label": "X-High"}],
    "dsh": [{"id": "off", "label": "Off"}, {"id": "low", "label": "Low"},
            {"id": "high", "label": "High"}, {"id": "max", "label": "Max"}],
    "gemini": [], "goose": [], "crush": [], "opencode": [], "qwen": [], "cursor": [], "hermes": [],
}

# ── 动态模型目录发现（各 CLI 官方命令；探测拉起同源） ────────────────
# argv 的可执行名经 resolve_command 解析（覆盖链一致）；解析器把 stdout 归一为
# [{id, name, thinking?: [..]}]。
_MODEL_DISCOVERY: dict[str, dict[str, Any]] = {
    "omp": {"argv": ["models", "--json"], "parser": "omp-json", "timeout": 25},
    "opencode": {"argv": ["models"], "parser": "lines", "timeout": 30},
    "crush": {"argv": ["models"], "parser": "lines", "timeout": 30},
    "pi": {"argv": ["--list-models"], "parser": "pi-table", "timeout": 30},
    "cursor": {"argv": ["models"], "parser": "lines", "timeout": 30},
}

_MODEL_CACHE: dict[str, tuple[float, dict]] = {}
_MODEL_CACHE_TTL = 600.0  # 10 min：模型目录低频变化


def _parse_omp_models_json(stdout: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return []
    out = []
    for m in data.get("models", []):
        if not isinstance(m, dict):
            continue
        out.append({
            "id": m.get("selector") or m.get("id", ""),
            "name": m.get("name") or m.get("id", ""),
            "thinking": m.get("thinking") or [],
        })
    return [m for m in out if m["id"]]


def _parse_lines(stdout: str) -> list[dict[str, Any]]:
    out = []
    for line in stdout.splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "─", "==")):
            out.append({"id": line.split()[0] if " " in line else line, "name": line})
    return out[:400]


def _parse_pi_table(stdout: str) -> list[dict[str, Any]]:
    # pi 表格行：provider model context max-out thinking images
    out = []
    for line in stdout.splitlines():
        cols = line.split()
        if len(cols) >= 2 and cols[0] != "provider" and not cols[0].startswith("─"):
            out.append({"id": f"{cols[0]}/{cols[1]}", "name": f"{cols[0]}/{cols[1]}"})
    return out[:400]


_MODEL_PARSERS = {
    "omp-json": _parse_omp_models_json,
    "lines": _parse_lines,
    "pi-table": _parse_pi_table,
}


async def discover_models(harness_id: str, force: bool = False) -> dict[str, Any]:
    """引擎模型目录发现（动态 CLI 优先，静态表兜底）。

    返回 {source: 'cli'|'static', models: [{id, name, thinking?}], reasoning_levels}。
    reasoning_levels 来自 REASONING_LEVELS（各引擎官方旗标的取值面）；
    omp 的档位随模型走（models[].thinking），此处返回 [] 表示按模型约束。
    """
    if harness_id == "heuristic":
        return {"source": "static", "models": [], "reasoning_levels": []}
    if not is_known_harness(harness_id):
        raise UnknownHarnessError(f"Unknown harness: {harness_id}")

    cached = _MODEL_CACHE.get(harness_id)
    if cached and not force and time.time() - cached[0] < _MODEL_CACHE_TTL:
        return cached[1]

    reasoning = REASONING_LEVELS.get(harness_id, [])
    disc = _MODEL_DISCOVERY.get(harness_id)
    result: dict[str, Any] | None = None
    if disc:
        resolved = resolve_command(harness_id)
        if resolved:
            parser = _MODEL_PARSERS[disc["parser"]]
            try:
                run_args = wrap_windows_cmd([resolved] + list(disc["argv"]))
                completed = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: subprocess.run(
                        run_args, capture_output=True, timeout=disc["timeout"],
                        **_run_silent_kwargs(),
                    ),
                )
                stdout = (completed.stdout or b"").decode("utf-8", errors="replace")
                # 部分引擎把目录表打到 stderr（实测 pi --list-models）——合并解析
                stderr = (completed.stderr or b"").decode("utf-8", errors="replace")
                combined = stdout if stdout.strip() else stderr
                # 认证失败/配置错误输出以 Error 开头 —— 不当模型名，回落静态
                if combined.strip().startswith(("Error:", "error:", "fatal:")):
                    models = []
                else:
                    models = parser(combined) if combined.strip() else []
                if models:
                    result = {"source": "cli", "models": models, "reasoning_levels": reasoning}
            except Exception as e:  # noqa: BLE001 — 目录发现失败回落静态
                logger.debug("model discovery %s failed: %s", harness_id, e)
    if result is None:
        result = {
            "source": "static",
            "models": [{"id": mid, "name": mid} for mid in _STATIC_MODELS.get(harness_id, [])],
            "reasoning_levels": reasoning,
        }
    _MODEL_CACHE[harness_id] = (time.time(), result)
    return result


def reset_model_cache() -> None:
    _MODEL_CACHE.clear()


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
        "homepage": "https://github.com/can1357/oh-my-pi",
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
        # 2026-09-13 修正：官方 dsh-acp README 明确 authenticate 为
        # "Immediate success; the server requires no authentication." ——
        # 凭据属于**模型 provider 路由**（ACP profile 里的 provider/model），
        # 不是 DEEPSEEK_API_KEY 环境变量。原先把它列为 requires_env 会让
        # 未设该变量的机器在 POST /meditation/run 时被 409 拦下，
        # 尽管 dsh 实际可用（本机实测能正常返回结果）。
        "requires_env": [],
        "notes": "ACP 驱动器内嵌审批请求 fail-closed 拒绝（单回合保守档）；steer 恒 deferred。"
                 "模型/provider 由 ACP profile 配置（非环境变量）。"
                 "另有更简单的官方一次性入口 `dsh --profile headless \"<task>\"` 可供后续评估。",
    },
    "claude": {
        "label": "Claude Code",
        "description": "`claude -p --output-format json` 无头单回合；prompt 走 stdin。",
        "homepage": "https://code.claude.com/docs/en/claude-code",
        "process_model": "oneshot",
        "capabilities": _caps(context_stats=True),
        "requires_env": ["ANTHROPIC_API_KEY"],
        "notes": "--dangerously-skip-permissions 仅限本平台合成作业。"
                 "凭据面：ANTHROPIC_API_KEY **或** 本地 `claude` 登录态（OAuth 订阅）任一即可 —— "
                 "`--bare` 只在提供了 key 时才传，否则保留订阅登录。"
                 "未指定模型时用引擎自身默认（硬编码模型名会随官方下线过期）。",
    },
    "gemini": {
        "label": "Gemini CLI",
        "description": "`gemini -p <prompt> --output-format json` 无头单回合。",
        "homepage": "https://github.com/google-gemini/gemini-cli",
        "process_model": "oneshot",
        "capabilities": _caps(context_stats=True),
        "requires_env": ["GEMINI_API_KEY"],
        "notes": "实测 -p **必须自带取值**（`echo x | gemini -p` 报 not enough arguments）；"
                 "stdin 管道是官方另一条 headless 入口，但不能填充 -p。"
                 "7.5K 是**本集成**对 .cmd 投递的 cmd.exe 护栏（非官方限制），超长显式报错。"
                 "鉴权锁 Google 面（API key / OAuth / Vertex）。"
                 "⚠️ 官方公告：2026-06-18 起免费层与 Google One 用户的 Gemini CLI 已由 "
                 "Antigravity CLI（`agy -p … --output-format json`，字段同为 response）接替。",
    },
    "copilot": {
        "label": "GitHub Copilot CLI",
        "description": "`copilot -p <prompt> --output-format json` 单回合（-p 必带 prompt 值）。",
        "homepage": "https://docs.github.com/en/copilot/how-tos/copilot-cli",
        "process_model": "oneshot",
        "capabilities": _caps(),
        "requires_env": ["COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"],
        "notes": "token 链 COPILOT_GITHUB_TOKEN > GH_TOKEN > GITHUB_TOKEN（官方文档明示此优先级）；"
                 "也支持 `copilot login` OAuth，但 classic ghp_ PAT 不可用（需 fine-grained v2 + Copilot Requests 权限）。"
                 "`--output-format json` 输出是 **JSONL 逐行对象**，终稿在 `assistant.message.data.content`，"
                 "usage 在 `result.usage`。",
    },
    "cursor": {
        "label": "Cursor CLI",
        "description": "`cursor-agent -p --output-format json` 单回合；帧与 Claude Code 同构。",
        "homepage": "https://cursor.com/docs/cli/headless",
        "process_model": "oneshot",
        "capabilities": _caps(context_stats=True),
        "requires_env": ["CURSOR_API_KEY"],
        "notes": "官方文档以 `agent` 为主名，`cursor-agent` 是安装脚本同时创建的 **legacy 别名**"
                 "（Windows 上 `agent` 易冲突，故保留别名）；另有隐藏的 `agent acp`（ACP server）。"
                 "模型只用长名 `--model`（官方参数表无 `-m`）。"
                 "默认不带 --force（文件变更只提案不落地，保守档）。"
                 "凭据：CURSOR_API_KEY / --api-key / `agent login` OAuth 任一。",
    },
    "crush": {
        "label": "Charm Crush",
        "description": "`crush run` 单回合；v0.92+ 无 JSON 格式 → 纯文本 stdout。",
        "homepage": "https://github.com/charmbracelet/crush",
        "process_model": "oneshot",
        "capabilities": _caps(),
        "requires_env": [],
        "notes": "官方 flag 集（quiet/verbose/model/small-model/reasoning-effort/session/continue）"
                 "确认无 JSON 输出 → 纯文本 stdout，日志/spinner 走 stderr。"
                 "prompt 可走 argv 或管道 stdin；无程序化审批。"
                 "（历史备注「npm shim 可能损坏」的真实成因多为 `ignore-scripts=true` "
                 "阻断了 postinstall 二进制下载，可用命令覆盖链指向包内真实 bin。）",
    },
    "goose": {
        "label": "Block Goose",
        "description": "`goose run --output-format stream-json -t <prompt>` 单回合。",
        # 2026-09-13：goose 已迁至 Agentic AI Foundation，站点改为 goose-docs.ai。
        "homepage": "https://github.com/aaif-goose/goose",
        "process_model": "oneshot",
        "capabilities": _caps(context_stats=True),
        "requires_env": ["OPENAI_API_KEY"],
        "notes": "`-t <prompt>` 投递（裸位置参数会被拒，exit 2）；"
                 "GOOSE_MODE 默认已是 auto；provider/model 经 GOOSE_PROVIDER/GOOSE_MODEL 或 --provider/--model。"
                 "stream-json 事件 schema 官方未公开，解析器按 message/notification/error/complete 保守兼容。"
                 "未配置 provider 时 exit 1 + 一行 error（已按引擎级错误处理，不再假成功）。",
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
        # 官方 ACP 文档明确：provider 解析走 Hermes 自己的运行时解析器，
        # ACP 继承当前已配置的 provider 与凭据。GLM_API_KEY 只是 ~40 个可选
        # provider key 之一 —— 把它列为 requires_env 会让所有用其它 provider
        # 的用户的 hermes 被永久判定为「未配置」。
        "requires_env": [],
        "notes": "模型面来自 hermes 自身 config.yaml（`hermes model` 配置）；"
                 "需先装 ACP extra：`uv pip install -e '.[acp]'`；"
                 "stdout 专用于 JSON-RPC，日志走 stderr；审批请求 fail-closed。",
    },
}

# 注册表顺序即前端下拉顺序（mock 恒可用排最前便于联调）
HARNESS_IDS: list[str] = list(HARNESS_REGISTRY.keys())

# ── 自有凭据库（OAuth / 本地登录）探测面 ─────────────────────────────
# 多数引擎并不经环境变量取凭据，而是把 OAuth/登录态存在自己的配置目录里。
# 只查 env 会把「已安装且已登录」的引擎误判为不可用（claude 订阅号、
# codex ChatGPT 登录、gemini/omp/pi 等都是这种）。这里的路径只做「存在性」
# 判断，表示引擎自带凭据，不读取任何 secret 内容。
# 路径支持 ~ 展开；目录存在即视为已登录。
_CREDENTIAL_PATHS: dict[str, list[str]] = {
    "claude": ["~/.claude/.credentials.json", "~/.claude.json"],
    "codex": ["~/.codex/auth.json"],
    # gemini: settings.json 只是配置文件，存在≠已认证（实测存在 settings.json
    # 但未配 auth 的机器上 -p 运行 exit 41 "Please set an Auth method"）——
    # 只认 OAuth 凭据文件；API key / Vertex / GCA 走 requires_env 的 env 面。
    "gemini": ["~/.gemini/oauth_creds.json"],
    "qwen": ["~/.qwen/oauth_creds.json", "~/.qwen/settings.json"],
    "omp": ["~/.omp"],
    "pi": ["~/.pi"],
    "opencode": ["~/.local/share/opencode/auth.json"],
    "goose": ["~/.config/goose/config.yaml", "~/.config/goose/secrets.yaml"],
    "crush": ["~/.config/crush/crush.json", "~/.crush"],
    "copilot": ["~/.config/github-copilot/hosts.json"],
    "cursor": ["~/.cursor/cli-config.json"],
    "dsh": ["~/.dsh/config.yml", "~/.dsh/config.yaml"],
    "hermes": ["~/.hermes/config.yaml"],
}


def _credential_store_present(harness_id: str) -> bool:
    """引擎自有凭据库是否就绪（OAuth / 本地登录态）。"""
    for raw in _CREDENTIAL_PATHS.get(harness_id, []):
        try:
            p = Path(os.path.expanduser(raw))
            if p.exists():
                return True
        except Exception:  # noqa: BLE001 — 探测不得因路径异常而失败
            continue
    return False


def harness_credentials(harness_id: str) -> dict[str, Any]:
    """凭据面全景（供 probe / UI / 诊断使用）。

    env_ready: requires_env 任一就绪（无声明 → True）
    store_ready: 引擎自有凭据库存在（OAuth / 登录态）
    ready: env_ready or store_ready —— 「这个引擎现在真的能用吗」
    """
    env_status = _env_status(harness_id)
    env_ready = (not env_status) or any(e["present"] for e in env_status)
    store_ready = _credential_store_present(harness_id)
    return {
        "env_ready": env_ready,
        "store_ready": store_ready,
        "ready": bool(env_ready or store_ready),
        "env": env_status,
    }


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
    Path(os.environ.get("LOCALAPPDATA", "")) / "cursor-agent" if os.environ.get("LOCALAPPDATA") else None,
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
        return {**base, "installed": True, "resolved_command": "inprocess:mock",
                "inprocess": True, "credentials": harness_credentials(harness_id)}

    resolved = resolve_command(harness_id)
    if not resolved:
        return {**base, "installed": False,
                "error": f"executable '{harness_command_name(harness_id)}' not found on PATH"}

    version = ""
    installed = False
    version_stream = ""
    try:
        argv = wrap_windows_cmd([resolved, "--version"])
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                argv, capture_output=True, timeout=10,
                **_run_silent_kwargs(),
            ),
        )
        # 多数引擎走 stdout，但有的（实测 pi 0.73.1）把版本写到 stderr。
        # 只读 stdout 会把可用引擎误判为「未安装 / 版本未知」。
        out_txt = (result.stdout or b"").decode("utf-8", errors="replace").strip()
        err_txt = (result.stderr or b"").decode("utf-8", errors="replace").strip()
        version_stream = "stdout" if out_txt else ("stderr" if err_txt else "")
        first = (out_txt or err_txt).splitlines()
        version = first[0][:120] if first else ""
        # 退出码 0 即已安装；非 0 但只要 --version 有可读输出，同样说明
        # 可执行文件真实存在且能跑（部分 CLI 用非 0 退出码报告版本）。
        installed = result.returncode == 0 or bool(version)
    except Exception as e:
        logger.debug("Harness probe %s failed: %s", harness_id, e)
        installed = False

    # claude：`--bare` 需要 API key，但没有 key 也可以用本地 OAuth 登录态
    # （adapter 仅在 key 存在时才传 --bare）。因此只有「env 与自有凭据库
    # 双双缺失」才算不可用 —— 否则会把已登录的 Claude Code 误判为未安装。
    if harness_id == "claude" and not harness_credentials("claude")["ready"]:
        installed = False

    return {**base, "installed": installed, "version": version,
            "resolved_command": resolved, "version_stream": version_stream,
            "credentials": harness_credentials(harness_id)}


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
    - 引擎自有凭据库存在（OAuth / 本地登录态）时同样视为就绪 —— 不能因为
      用户用的是订阅登录而不是 API key 就判定引擎不可用（claude 订阅号、
      codex ChatGPT 登录、gemini/qwen OAuth 都是这种）；
    - 其余引擎要求全部 env 就绪。
    """
    entry = HARNESS_REGISTRY[harness_id]
    creds = harness_credentials(harness_id)
    env_status = creds["env"]
    if not env_status:
        return []
    # 自有凭据库命中 → 无问题（引擎会用自己的登录态）
    if creds["store_ready"]:
        return []
    issues: list[str] = []
    if harness_id == "claude":
        # 既无 API key 也无本地登录态 → 明确不可用
        issues.append(
            "ANTHROPIC_API_KEY not set and no local Claude Code login found "
            "(run `claude` once to authenticate, or export the key)")
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


def availability_hint(harness_id: str, probe: dict, issues: list[str]) -> str:
    """不可用原因的人类可读修复指引（前端灰显项的 tooltip / 诊断报告用）。"""
    if harness_id == "mock":
        return ""
    if not probe.get("installed"):
        cmd = harness_command_name(harness_id)
        home = HARNESS_REGISTRY[harness_id].get("homepage", "")
        hint = f"CLI '{cmd}' not found. Install it"
        if home:
            hint += f" ({home})"
        hint += ", or point config.yml harness.commands."
        hint += f"{harness_id} at the real binary path."
        return hint
    if issues:
        return ("Installed but not configured: " + "; ".join(issues)
                + ". Set the env vars or complete the engine's own login "
                  "(its stored credentials are also accepted).")
    return ""


async def list_harnesses() -> list[dict[str, Any]]:
    """注册表全景（含实时可用性）—— API /harnesses 端点与前端下拉的数据源。

    available = installed && 无配置问题（前端据此灰显不可选项）。
    """
    out = []
    for hid in HARNESS_IDS:
        entry = HARNESS_REGISTRY[hid]
        try:
            probe = await probe_harness(hid)
        except Exception as e:
            logger.warning("probe %s failed: %s", hid, e)
            probe = {"installed": False, "error": str(e)}
        installed = bool(probe.get("installed"))
        issues = configuration_issues(hid, probe) if installed else []
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
            "installed": installed,
            "available": installed and not issues,
            "version": probe.get("version", ""),
            "resolved_command": probe.get("resolved_command"),
            "credentials": probe.get("credentials") or harness_credentials(hid),
            "issues": issues,
            "hint": availability_hint(hid, probe, issues),
            "probe_error": probe.get("error", ""),
        })
    return out


async def startup_probe_all() -> dict[str, Any]:
    """启动时全量可用性检查：预热探测缓存 + 汇总（供 lifespan 与 /health 用）。

    非 fatal：探测失败只记 warn，绝不阻塞服务启动。逐引擎串行 spawn
    `--version`（各 10s 上限），全部完成通常 <30s。
    """
    results: dict[str, dict] = {}
    for hid in HARNESS_IDS:
        try:
            results[hid] = await probe_harness(hid)
        except Exception as e:  # noqa: BLE001 — 启动探测不得失败
            results[hid] = {"installed": False, "error": str(e)}
    available = [hid for hid in HARNESS_IDS
                 if results[hid].get("installed")
                 and not configuration_issues(hid, results[hid])]
    summary = {
        "total": len(HARNESS_IDS),
        "available_count": len(available),
        "available": available,
        "unavailable": [hid for hid in HARNESS_IDS if hid not in available],
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    logger.info("Harness availability check: %d/%d available — %s | unavailable: %s",
                summary["available_count"], summary["total"],
                ", ".join(available) or "(none)",
                ", ".join(summary["unavailable"]) or "(none)")
    return summary
