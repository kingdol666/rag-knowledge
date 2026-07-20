import { defineEventHandler, readBody } from 'h3'

export default defineEventHandler(async (event): Promise<any> => {
  const body = await readBody(event)
  const backendUrl = useRuntimeConfig().pdfParserApiUrl as string
  return await $fetch(`${backendUrl}/api/v1/graph/build-kb`, {
    method: 'POST',
    body: { kb_id: body?.kb_id || '', force: body?.force ?? false },
  })
})
