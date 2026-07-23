import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

export default defineEventHandler(async (event): Promise<unknown> => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/graph/build-kb`, {
    method: 'POST',
    body: { kb_id: body?.kb_id || '', force: body?.force ?? false },
  })
})
