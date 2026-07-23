import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

export default defineEventHandler(async (event): Promise<unknown> => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/graph/build-all`, {
    method: 'POST',
    body: {
      force: body?.force ?? false,
      enable_vector_similarity: body?.enable_vector_similarity ?? true,
    },
  })
})
