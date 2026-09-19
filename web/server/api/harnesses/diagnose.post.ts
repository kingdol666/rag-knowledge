/**
 * POST /api/harnesses/diagnose
 *
 * Harness diagnosis job — proxies to the Python backend
 * POST /api/v1/meditation/harnesses/{id}/diagnose, which runs the registry
 * probe (executable + version + credential/env checklist) and optionally a
 * real engine round-trip self-test ({ selfTest: true } → body {self_test:true}).
 *
 * Body: { harness: string, selfTest?: boolean, timeoutSec?: number }
 */
import { defineEventHandler, readBody, createError } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'
import { HARNESS_CHAT_CATALOG } from '~/server/utils/harness-catalog'

interface DiagnoseBody {
  harness?: string
  selfTest?: boolean
  timeoutSec?: number
}

export default defineEventHandler(async (event) => {
  const body = await readBody<DiagnoseBody>(event) || {}
  const harness = (body.harness || '').trim()
  if (!harness) {
    throw createError({ statusCode: 400, statusMessage: 'harness (string) 必填' })
  }
  const known = HARNESS_CHAT_CATALOG[harness] || harness === 'heuristic'
  if (!known) {
    throw createError({ statusCode: 400, statusMessage: `Unknown harness: ${harness}` })
  }

  const backendUrl = getDynamicBackendUrl()
  try {
    return await $fetch(
      `${backendUrl}/api/v1/meditation/harnesses/${encodeURIComponent(harness)}/diagnose`,
      {
        method: 'POST',
        body: {
          self_test: body.selfTest === true,
          ...(body.timeoutSec ? { timeout_sec: body.timeoutSec } : {}),
        },
        // Real round-trips against slow CLIs need headroom.
        timeout: 330_000,
      },
    )
  } catch (e: any) {
    const status = e?.statusCode || e?.response?.status
    if (status === 400 || status === 409) {
      throw createError({
        statusCode: status,
        statusMessage: e?.data?.detail?.message || e?.message || 'diagnose failed',
      })
    }
    return {
      success: false,
      error: `Backend unreachable: ${e instanceof Error ? e.message : String(e)}`,
    }
  }
})
