import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/**
 * POST /api/meditation/run
 * Proxy to backend POST /api/v1/experience/meditation/run
 * Body: { kb_id?, trigger? }
 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()

  try {
    // Backend meditation/run currently runs globally; kb_id filtering is done
    // by the scheduler reading per-KB config. Pass body through for future use.
    const url = `${backendUrl}/api/v1/meditation/run`
    return await $fetch(url, {
      method: 'POST',
      body: body || {},
    })
  } catch (e) {
    return { success: false, error: `Backend unreachable: ${e instanceof Error ? e.message : String(e)}` }
  }
})