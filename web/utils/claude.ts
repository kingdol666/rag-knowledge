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
    label: 'Default',
    desc: 'Standard permission behavior. Dangerous operations require approval. In headless mode (no interaction), unapproved tools are denied.',
  },
  acceptEdits: {
    label: 'Auto Edit',
    desc: 'Auto-accept file edits (Read/Edit/Write allowed), others follow default.',
  },
  bypassPermissions: {
    label: 'Bypass',
    desc: 'Fully automatic — all tools allowed (use with caution, trusted tasks only).',
  },
  plan: {
    label: 'Plan Mode',
    desc: 'Read-only exploration — Claude can only read, not modify any files.',
  },
  dontAsk: {
    label: 'No Ask',
    desc: 'Strictest — tools not pre-approved in allowedTools are always denied, never ask.',
  },
}
