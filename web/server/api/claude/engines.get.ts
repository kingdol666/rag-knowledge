/**
 * GET /api/claude/engines  (legacy endpoint — kept for backward compat)
 *
 * Now derives from the unified harness catalog (see GET /api/harnesses for
 * the full merged registry+chat matrix). Shape is unchanged:
 *   { engines: { claude: { available }, omp: { available }, ... } }
 * so the older chat page code keeps working; the id set now covers every
 * chat-capable harness.
 */
import { defineEventHandler } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'
import { HARNESS_CHAT_CATALOG, resolveCommandLocal } from '~/server/utils/harness-catalog'

/** Claude runs in-process via the Agent SDK — resolvable package = available. */
function isClaudeSdkAvailable(): boolean {
  try {
    const { createRequire } = require('module')
    const r = createRequire(import.meta.url)
    r.resolve('@anthropic-ai/claude-agent-sdk')
    return true
  } catch {
    return false
  }
}

export default defineEventHandler(async () => {
  // Ask the backend registry first (authoritative probe incl. credentials).
  let backendAvailable: Record<string, boolean> | null = null
  try {
    const res = await $fetch<any>(`${getDynamicBackendUrl()}/api/v1/meditation/harnesses`, { timeout: 20000 })
    if (res?.harnesses) {
      backendAvailable = Object.fromEntries(
        res.harnesses.map((h: any) => [h.id, !!h.installed && !!h.available]),
      )
    }
  } catch { /* fall back to local checks */ }

  const engines: Record<string, { available: boolean }> = {}
  for (const meta of Object.values(HARNESS_CHAT_CATALOG)) {
    if (meta.id === 'claude') {
      engines.claude = { available: isClaudeSdkAvailable() }
      continue
    }
    if (meta.id === 'mock') {
      engines.mock = { available: true }
      continue
    }
    engines[meta.id] = {
      available: backendAvailable
        ? !!backendAvailable[meta.id]
        : !!resolveCommandLocal(meta.command),
    }
  }
  return { engines }
})
