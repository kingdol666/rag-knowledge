/**
 * Claude chat-related constants (shared frontend/backend).
 * Pure data, no server dependency, safely importable by frontend components.
 */

export const PERMISSION_MODES = [
  'default',
  'acceptEdits',
  'bypassPermissions',
  'plan',
  'dontAsk',
] as const

export type PermissionMode = (typeof PERMISSION_MODES)[number]

export const PERMISSION_MODE_INFO: Record<
  PermissionMode,
  { label: string; desc: string }
> = {
  default: {
    label: '默认',
    desc: '标准权限行为。危险操作需审批，本场景（无交互）下未预批准的工具会被拒绝',
  },
  acceptEdits: {
    label: '自动编辑',
    desc: '自动接受文件编辑（Read/Edit/Write 放行），其他仍按 default',
  },
  bypassPermissions: {
    label: '绕过权限',
    desc: '全自动 — 所有工具放行（慎用，仅可信任务）',
  },
  plan: {
    label: '规划模式',
    desc: '只读探索 — Claude 只能读不能改任何文件',
  },
  dontAsk: {
    label: '不询问',
    desc: '最严格 — 未在 allowedTools 预批准的工具一律拒绝，从不询问',
  },
}
