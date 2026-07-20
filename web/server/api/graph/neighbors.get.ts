import { defineEventHandler, getQuery } from 'h3'

export default defineEventHandler(async (event): Promise<any> => {
  const q = getQuery(event)
  const backendUrl = useRuntimeConfig().pdfParserApiUrl as string
  return await $fetch(`${backendUrl}/api/v1/graph/neighbors`, { query: q })
})
