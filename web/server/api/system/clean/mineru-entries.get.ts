import { defineEventHandler } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** GET /api/system/clean/mineru-entries — proxy to backend GET /api/v1/system/clean/mineru-entries */
export default defineEventHandler(async () => {
  const backend = getDynamicBackendUrl()
  try {
    const res = await $fetch(`${backend}/api/v1/system/clean/mineru-entries`, {
      timeout: 15000,
    })
    return res
  } catch (e: any) {
    console.error('[api/system/clean/mineru-entries] Backend request failed:', e.message)
    return { success: false, entries: [], note: `Backend unavailable: ${e.message}` }
  }
})
