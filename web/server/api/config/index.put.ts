import { defineEventHandler, readBody } from 'h3'
import {
  getDynamicBackendUrl,
  getDynamicTreeStoragePath,
  invalidateConfigCache,
} from '~/server/utils/dynamic-config'

/** PUT /api/config — proxy to backend PUT /api/v1/config, then invalidate frontend cache */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  const result = await $fetch(`${backendUrl}/api/v1/config`, {
    method: 'PUT',
    body,
  })

  // Invalidate the frontend config cache so all subsequent requests
  // pick up the new config.yml / .env values immediately.
  invalidateConfigCache()

  // Also update runtimeConfig so useRuntimeConfig() callers get fresh values
  try {
    const rc = useRuntimeConfig()
    rc.pdfParserApiUrl = getDynamicBackendUrl()
    const freshStorage = getDynamicTreeStoragePath()
    rc.treeStoragePath = freshStorage
    if (rc.public) {
      rc.public.treeStoragePath = freshStorage
    }
  } catch { /* runtimeConfig may not be available in all contexts */ }

  return result
})
