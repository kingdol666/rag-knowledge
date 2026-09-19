/**
 * Harness Chat Catalog — chat capability matrix for ALL registry harnesses.
 *
 * The Python backend (`backend/app/services/harness_registry.py`) is the
 * single source of truth for WHAT harnesses exist and whether each is
 * installed/usable. This file is the web-layer source of truth for HOW each
 * harness chats: transport, per-harness REAL permission modes (the exact
 * CLI/SDK/env settings each harness natively accepts), and HITL support.
 *
 * Honesty rule (mirrors the backend registry): capability flags only claim
 * what this integration truly implements; degraded surfaces go in `notes`.
 */
import { existsSync } from 'fs'
import { resolve, delimiter } from 'path'
import type { PermissionModeInfo } from '~/server/engines/types'

export type ChatTransport = 'sdk' | 'rpc' | 'acp' | 'oneshot' | 'inprocess'

export interface HarnessChatMeta {
  id: string
  label: string
  transport: ChatTransport
  /** Real interactive Human-in-the-Loop support (permission requests surfaced to the user). */
  hitl: boolean
  /** Chat-capable in the web layer (factory has an adapter for it). */
  chat: boolean
  /** Harness-specific permission modes (real flags each harness accepts). */
  permissionModes: PermissionModeInfo[]
  defaultMode: string
  /** How multi-turn continuity works. */
  historyMode: 'native-resume' | 'server-replay'
  /** arg-delivery prompt guard (Windows cmd shim limit) — 0 = unlimited. */
  promptLimitChars: number
  /** CLI command name used for local fallback availability checks. */
  command: string
  notes: string
}

const ACP_MODES: PermissionModeInfo[] = [
  { id: 'default', label: 'HITL (ask per action)', desc: '每个工具调用都经 session/request_permission 问用户（原生 HITL）', mapping: 'ACP request_permission → 审批弹窗' },
  { id: 'bypassPermissions', label: 'Auto-approve all', desc: '自动选择 allow_always，不再询问', mapping: 'request_permission 自动回 allow_always' },
]

const ONE_SHOT_DEFAULT: PermissionModeInfo[] = [
  { id: 'default', label: 'Read-only (safe)', desc: '无头单回合的保守档：只读/不落地，权限请求按引擎语义自动拒绝', mapping: '引擎各自的 headless 默认旗标' },
]

export const HARNESS_CHAT_CATALOG: Record<string, HarnessChatMeta> = {
  claude: {
    id: 'claude',
    label: 'Claude Code',
    transport: 'sdk',
    hitl: true,
    chat: true,
    permissionModes: [
      { id: 'default', label: 'Default (HITL)', desc: '每次使用工具前询问用户（canUseTool → 审批弹窗）', mapping: 'permissionMode=default' },
      { id: 'acceptEdits', label: 'Accept Edits', desc: '自动允许文件编辑，其余工具仍需审批', mapping: 'permissionMode=acceptEdits' },
      { id: 'plan', label: 'Plan Mode', desc: '只读规划模式', mapping: 'permissionMode=plan' },
      { id: 'dontAsk', label: 'Dont Ask', desc: '不弹审批，不允许的工具直接拒绝', mapping: 'permissionMode=dontAsk' },
      { id: 'bypassPermissions', label: 'Bypass All', desc: '跳过所有权限检查', mapping: '--dangerously-skip-permissions' },
    ],
    defaultMode: 'default',
    historyMode: 'native-resume',
    promptLimitChars: 0,
    command: 'claude',
    notes: 'Claude Agent SDK in-process；canUseTool 回调 = 真实 HITL。',
  },
  omp: {
    id: 'omp',
    label: 'OMP',
    transport: 'rpc',
    hitl: false,
    chat: true,
    permissionModes: [
      { id: 'default', label: 'Agent (auto tools)', desc: 'omp RPC 常驻会话，工具自动执行（--mode rpc 语义）', mapping: 'omp --mode rpc' },
    ],
    defaultMode: 'default',
    historyMode: 'native-resume',
    promptLimitChars: 0,
    command: 'omp',
    notes: 'omp RPC JSONL 协议常驻进程；无程序化审批面（extension_ui 请求按协议自动取消）。',
  },
  dsh: {
    id: 'dsh',
    label: 'DeepSeek Harness',
    transport: 'acp',
    hitl: true,
    chat: true,
    permissionModes: [
      { id: 'default', label: 'HITL (read-only + ask)', desc: '只读沙箱，每步工具调用经 session/request_permission 问用户（原生 HITL）', mapping: 'DSH_PERMISSION_MODE=read-only (approval=ask)' },
      { id: 'acceptEdits', label: 'Workspace write (ask)', desc: '允许工作区写，工作区外/危险操作仍询问', mapping: 'DSH_PERMISSION_MODE=workspace-write' },
      { id: 'plan', label: 'Read-only (ask)', desc: '只读沙箱，工具仍需确认', mapping: 'DSH_PERMISSION_MODE=read-only' },
      { id: 'bypassPermissions', label: 'Auto-approve all', desc: '全自动，不再询问', mapping: 'DSH_PERMISSION_MODE=danger-full-access (approval=never)' },
    ],
    defaultMode: 'default',
    historyMode: 'server-replay',
    promptLimitChars: 0,
    command: 'dsh',
    notes: '标准 ACP v1（dsh --profile acp）。审批策略由 DSH_PERMISSION_MODE 环境变量驱动（适配器按会话注入）；kb 工具经 HTTP MCP sidecar（kb-mcp --http）注入，因为 dsh 只支持 HTTP 传输的 MCP；request_permission 原生转发给用户 = 真实 HITL。',
  },
  hermes: {
    id: 'hermes',
    label: 'Hermes Agent',
    transport: 'acp',
    hitl: true,
    chat: true,
    permissionModes: ACP_MODES,
    defaultMode: 'default',
    historyMode: 'server-replay',
    promptLimitChars: 0,
    command: 'hermes',
    notes: '标准 ACP v1（hermes acp）；审批请求原生转发给用户 = 真实 HITL。需 uv pip install -e ".[acp]"。',
  },
  codex: {
    id: 'codex',
    label: 'OpenAI Codex CLI',
    transport: 'oneshot',
    hitl: false,
    chat: true,
    permissionModes: [
      { id: 'default', label: 'Auto-review (workspace write)', desc: '工作区写沙箱 + --approve-for-me 自动审批（exec 无头无人可批，MCP/kb 工具在此档可用）', mapping: '--sandbox workspace-write --approve-for-me' },
      { id: 'plan', label: 'Read-only', desc: '只读沙箱；MCP 工具调用会被无头审批策略拒绝', mapping: '--sandbox read-only' },
      { id: 'acceptEdits', label: 'Workspace write', desc: '允许工作区写（MCP 调用同样受无头审批限制）', mapping: '--sandbox workspace-write' },
      { id: 'bypassPermissions', label: 'Full access', desc: '无沙箱无审批（检索/MCP 全可用）', mapping: '--dangerously-bypass-approvals-and-sandbox' },
    ],
    defaultMode: 'default',
    historyMode: 'server-replay',
    promptLimitChars: 0,
    command: 'codex',
    notes: 'codex exec --json NDJSON；prompt 走 stdin。kb-mcp 经 ~/.codex/config.toml 注册。无头 exec 无交互审批面（hitl=false）——权限边界=沙箱档位；MCP 调用在 read-only 下被审批策略拒绝，default 档用 --approve-for-me 自动审批放行。',
  },
  gemini: {
    id: 'gemini',
    label: 'Gemini CLI',
    transport: 'oneshot',
    hitl: false,
    chat: true,
    permissionModes: [
      { id: 'default', label: 'Default', desc: 'gemini 默认审批模式（非交互下写操作被拒）', mapping: '--approval-mode default' },
      { id: 'acceptEdits', label: 'Auto edits', desc: '自动接受编辑', mapping: '--approval-mode auto_edit' },
      { id: 'bypassPermissions', label: 'YOLO', desc: '全自动', mapping: '--approval-mode yolo' },
    ],
    defaultMode: 'default',
    historyMode: 'server-replay',
    promptLimitChars: 7500,
    command: 'gemini',
    notes: '-p 必带 prompt 值（实测 stdin 不被接受）；npm shim 7.5K 护栏。',
  },
  copilot: {
    id: 'copilot',
    label: 'GitHub Copilot CLI',
    transport: 'oneshot',
    hitl: false,
    chat: true,
    permissionModes: [
      { id: 'default', label: 'No tools', desc: '不授权工具面（保守档）', mapping: '（默认，无 --allow-all-tools）' },
      { id: 'bypassPermissions', label: 'Allow all tools', desc: '授权全部工具', mapping: '--allow-all-tools' },
    ],
    defaultMode: 'default',
    historyMode: 'server-replay',
    promptLimitChars: 7500,
    command: 'copilot',
    notes: '--output-format json 为 JSONL；无头下工具调用需显式授权旗标（无交互审批面）。',
  },
  cursor: {
    id: 'cursor',
    label: 'Cursor CLI',
    transport: 'oneshot',
    hitl: false,
    chat: true,
    permissionModes: [
      { id: 'default', label: 'Proposal-only', desc: '文件变更只提案不落地', mapping: '（默认，无 --force）' },
      { id: 'bypassPermissions', label: 'Force apply', desc: '变更直接落地', mapping: '--force' },
    ],
    defaultMode: 'default',
    historyMode: 'server-replay',
    promptLimitChars: 30000,
    command: 'cursor-agent',
    notes: 'CLI 名是 cursor-agent（cursor 的 legacy 别名）；帧与 Claude Code 同构。',
  },
  opencode: {
    id: 'opencode',
    label: 'OpenCode',
    transport: 'oneshot',
    hitl: false,
    chat: true,
    permissionModes: ONE_SHOT_DEFAULT,
    defaultMode: 'default',
    historyMode: 'server-replay',
    promptLimitChars: 7500,
    command: 'opencode',
    notes: 'opencode run 纯文本 stdout；npm shim 8K 护栏。',
  },
  crush: {
    id: 'crush',
    label: 'Charm Crush',
    transport: 'oneshot',
    hitl: false,
    chat: true,
    permissionModes: ONE_SHOT_DEFAULT,
    defaultMode: 'default',
    historyMode: 'server-replay',
    promptLimitChars: 30000,
    command: 'crush',
    notes: 'crush run 纯文本 stdout（v0.92+ 无 JSON 输出）；无程序化审批。',
  },
  goose: {
    id: 'goose',
    label: 'Block Goose',
    transport: 'oneshot',
    hitl: false,
    chat: true,
    permissionModes: [
      { id: 'default', label: 'Auto (headless)', desc: 'GOOSE_MODE=auto（无头唯一可行档）', mapping: 'GOOSE_MODE=auto' },
    ],
    defaultMode: 'default',
    historyMode: 'server-replay',
    promptLimitChars: 30000,
    command: 'goose',
    notes: 'goose run --output-format stream-json；-t 投递 prompt。',
  },
  qwen: {
    id: 'qwen',
    label: 'Qwen Code',
    transport: 'oneshot',
    hitl: false,
    chat: true,
    permissionModes: ONE_SHOT_DEFAULT,
    defaultMode: 'default',
    historyMode: 'server-replay',
    promptLimitChars: 0,
    command: 'qwen',
    notes: 'stdin 一级输入通道；纯文本输出（容忍 json 数组/stream-json 形状）。',
  },
  pi: {
    id: 'pi',
    label: 'pi coding agent',
    transport: 'oneshot',
    hitl: false,
    chat: true,
    permissionModes: ONE_SHOT_DEFAULT,
    defaultMode: 'default',
    historyMode: 'server-replay',
    promptLimitChars: 0,
    command: 'pi',
    notes: '-p --mode json JSONL 事件流；prompt 写临时文件 @投递。',
  },
  mock: {
    id: 'mock',
    label: 'Mock (scripted)',
    transport: 'inprocess',
    hitl: true,
    chat: true,
    permissionModes: [
      { id: 'default', label: 'HITL demo', desc: '含一次脚本化审批请求，验证 HITL 全链路', mapping: 'inprocess' },
      { id: 'bypassPermissions', label: 'No prompts', desc: '不发起审批请求', mapping: 'inprocess' },
    ],
    defaultMode: 'default',
    historyMode: 'server-replay',
    promptLimitChars: 0,
    command: '',
    notes: '进程内剧本引擎：零依赖验证聊天/HITL 全链路（含一次脚本化审批请求）。',
  },
}

/** Ids the chat factory can actually drive. */
export const CHAT_CAPABLE_IDS = Object.values(HARNESS_CHAT_CATALOG)
  .filter(m => m.chat)
  .map(m => m.id)

export function getChatMeta(id: string): HarnessChatMeta | undefined {
  return HARNESS_CHAT_CATALOG[id]
}

// ── Node-side availability fallback ─────────────────────────────────
// The Python backend probe (probe_harness) is authoritative — this is only
// used when the backend is unreachable so the dropdown still renders.
// Pure filesystem existence checks (no process spawning): scan PATH plus the
// usual per-user install dirs for the harness executable/shim.

const FALLBACK_DIRS = [
  resolve(process.env.APPDATA || '', 'npm'),
  resolve(process.env.USERPROFILE || process.env.HOME || '', '.local', 'bin'),
  resolve(process.env.USERPROFILE || process.env.HOME || '', '.bun', 'bin'),
]

const WIN_EXTS = ['.cmd', '.exe', '.bat', '']
const UNIX_EXTS = ['']

/** Scan PATH + fallback dirs for the harness executable. Absolute path or ''. */
export function resolveCommandLocal(command: string): string {
  if (!command) return ''
  // Literal allowlist guard: only catalog command names are ever probed.
  const known = new Set(Object.values(HARNESS_CHAT_CATALOG).map(m => m.command))
  if (!known.has(command)) return ''

  const exts = process.platform === 'win32' ? WIN_EXTS : UNIX_EXTS
  const dirs = [...(process.env.PATH || '').split(delimiter).filter(Boolean), ...FALLBACK_DIRS]
  for (const dir of dirs) {
    for (const ext of exts) {
      try {
        const cand = resolve(dir, command + ext)
        if (existsSync(cand)) return cand
      } catch { /* malformed path segment — skip */ }
    }
  }
  return ''
}
