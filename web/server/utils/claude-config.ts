/**
 * Claude Agent SDK configuration utilities — API key + project root + permission mode.
 *
 * The SDK bundles a native claude binary (npm optional dependency); no pre-installed claude CLI required.
 * Authentication uses the ANTHROPIC_API_KEY environment variable (third-party setups cannot use claude.ai login).
 */
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
// web/server/utils/ -> web/server/ -> web/ -> rag-knowledge/
const MONOREPO_ROOT = resolve(__dirname, '../../..')

/** Default working directory = project root (rag-knowledge/). Override with CLAUDE_PROJECT_ROOT. */
export function getProjectRoot(): string {
  const override = process.env.CLAUDE_PROJECT_ROOT?.trim()
  return override || MONOREPO_ROOT
}

/** Read Anthropic API key from environment variable. */
export function getApiKey(): string | undefined {
  const k = process.env.ANTHROPIC_API_KEY?.trim()
  return k || undefined
}

/** SDK-supported permission modes (subset, excluding auto — leaving the 5 with clear semantics). */
export const PERMISSION_MODES = [
  'default',           // Standard permission behavior (dangerous ops need canUseTool approval)
  'acceptEdits',       // Auto-accept file edits
  'bypassPermissions', // Bypass all permissions (fully automatic, use with caution)
  'plan',              // Plan mode (read-only exploration, no modifications)
  'dontAsk',           // No prompting; deny tools not pre-approved
] as const
export type PermissionMode = (typeof PERMISSION_MODES)[number]

export const PERMISSION_MODE_INFO: Record<PermissionMode, { label: string; desc: string }> = {
  default: { label: '默认', desc: '标准行为，危险操作需审批（本场景不交互 → 走 canUseTool 默认拒绝）' },
  acceptEdits: { label: '自动编辑', desc: '自动接受文件编辑（Read/Edit/Write 放行）' },
  bypassPermissions: { label: '绕过权限', desc: '全自动，所有工具放行（慎用，适合可信任务）' },
  plan: { label: '规划模式', desc: '只读探索，不修改任何文件' },
  dontAsk: { label: '不询问', desc: '未预批准的工具直接拒绝（最严格）' },
}
