import { defineEventHandler, readBody } from 'h3'

export default defineEventHandler(async (event): Promise<any> => {
  const body = await readBody(event)
  const backendUrl = useRuntimeConfig().pdfParserApiUrl as string
  return await $fetch(`${backendUrl}/api/v1/graph/build-all`, {
    method: 'POST',
    body: {
      force: body?.force ?? false,
      enable_vector_similarity: body?.enable_vector_similarity ?? true,
    },
  })
})
