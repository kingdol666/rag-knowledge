/**
 * GET /api/harnesses
 *
 * Unified harness catalog for the chat UI dropdown + harness hub page.
 * Merges two sources:
 *  - Python backend GET /api/v1/meditation/harnesses (authoritative: registry,
 *    probe, credentials, env checklist, version, resolved command)
 *  - Web-layer chat metadata (~/server/utils/harness-catalog.ts: transport,
 *    per-harness REAL permission modes, HITL support)
 *
 * When the backend is unreachable, availability falls back to a local
 * filesystem PATH scan so the dropdown still renders (degraded, flagged).
 *
 * Response: { success, backend_reachable, default, count, harnesses: [...] }
 * Each item: { id, label, description, homepage, installed, available,
 *              version, resolved_command, models, capabilities, requires_env,
 *              credentials, issues, hint, transport, hitl, chat,
 *              permissionModes, defaultMode, historyMode, promptLimitChars, notes }
 */
import { defineEventHandler } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'
import {
  HARNESS_CHAT_CATALOG,
  resolveCommandLocal,
} from '~/server/utils/harness-catalog'

interface BackendHarness {
  id: string
  label: string
  description: string
  homepage: string
  process_model: string
  capabilities: Record<string, boolean>
  requires_env: string[]
  notes: string
  models: string[]
  installed: boolean
  available?: boolean
  version?: string
  resolved_command?: string | null
  credentials?: Record<string, any>
  issues?: string[]
  hint?: string
}

export default defineEventHandler(async () => {
  const backendUrl = getDynamicBackendUrl()

  let backendPayload: { default?: string; harnesses?: BackendHarness[] } | null = null
  try {
    backendPayload = await $fetch<{ default?: string; harnesses?: BackendHarness[] }>(
      `${backendUrl}/api/v1/meditation/harnesses`,
      { timeout: 20000 },
    )
  } catch {
    backendPayload = null
  }

  const backendById = new Map<string, BackendHarness>()
  for (const h of backendPayload?.harnesses || []) backendById.set(h.id, h)

  const chatIds = new Set(Object.keys(HARNESS_CHAT_CATALOG))
  const ids: string[] = [...chatIds]
  // Registry entries without a web chat adapter still appear (hub shows them,
  // chat flag=false) — e.g. future registry additions.
  for (const h of backendPayload?.harnesses || []) {
    if (!ids.includes(h.id)) ids.push(h.id)
  }

  const harnesses = ids.map((id) => {
    const b = backendById.get(id)
    const meta = HARNESS_CHAT_CATALOG[id]
    const installed = b ? !!b.installed : !!resolveCommandLocal(meta?.command || '')
    const available = b
      ? (b.available !== undefined ? !!b.available : (!!b.installed && !(b.issues || []).length))
      : installed // degraded: can't see credentials/env when backend is down
    return {
      id,
      label: b?.label || meta?.label || id,
      description: b?.description || meta?.notes || '',
      homepage: b?.homepage || '',
      installed,
      available,
      version: b?.version || '',
      resolved_command: b?.resolved_command || null,
      models: b?.models || [''],
      capabilities: b?.capabilities || {},
      requires_env: b?.requires_env || [],
      credentials: b?.credentials || null,
      issues: b?.issues || [],
      hint: b?.hint || '',
      notes: meta?.notes || b?.notes || '',
      // Registry entries without a web chat adapter (e.g. heuristic) have no
      // chat transport — 'oneshot' would be misleading.
      transport: meta?.transport || 'none',
      hitl: !!meta?.hitl,
      chat: !!meta?.chat,
      permissionModes: meta?.permissionModes || [],
      defaultMode: meta?.defaultMode || 'default',
      historyMode: meta?.historyMode || 'server-replay',
      promptLimitChars: meta?.promptLimitChars || 0,
    }
  })

  return {
    success: true,
    backend_reachable: !!backendPayload,
    default: backendPayload?.default || 'omp',
    count: harnesses.length,
    harnesses,
  }
})
