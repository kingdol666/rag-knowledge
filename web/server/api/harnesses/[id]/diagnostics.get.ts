/**
 * GET /api/harnesses/[id]/diagnostics
 *
 * Proxies to the Python backend
 * GET /api/v1/meditation/harnesses/{id}/diagnostics (harness runtime
 * diagnostics: resolved command, env checklist, last probe results…).
 * Auth is injected by Nitro's backend-auth plugin.
 *
 * Backend unreachable → { success: false, error: 'Backend unreachable: …' }
 */
import { defineEventHandler, createError } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'
import { HARNESS_CHAT_CATALOG } from '~/server/utils/harness-catalog'

export default defineEventHandler(async (event) => {
  const id = (getRouterParam(event, 'id') || '').trim()
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'harness id 必填' })
  }
  const known = HARNESS_CHAT_CATALOG[id] || id === 'heuristic'
  if (!known) {
    throw createError({ statusCode: 400, statusMessage: `Unknown harness: ${id}` })
  }

  const backendUrl = getDynamicBackendUrl()
  try {
    return await $fetch(
      `${backendUrl}/api/v1/meditation/harnesses/${encodeURIComponent(id)}/diagnostics`,
      { timeout: 30_000 },
    )
  } catch (e: any) {
    return {
      success: false,
      error: `Backend unreachable: ${e instanceof Error ? e.message : String(e)}`,
    }
  }
})
