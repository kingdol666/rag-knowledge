import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/system/clean — proxy to backend POST /api/v1/system/clean */
export default defineEventHandler(async (event) => {
  const backend = getDynamicBackendUrl()
  const body = await readBody(event)

  try {
    const res = await $fetch(`${backend}/api/v1/system/clean`, {
      method: 'POST',
      body,
      timeout: 30000,
    })
    return res
  } catch (e: any) {
    console.error('[api/system/clean] Backend request failed:', e.message)
    return {
      success: false,
      dry_run: false,
      items: [],
      note: `Backend unavailable: ${e.message}`,
    }
  }
})