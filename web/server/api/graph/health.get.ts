import { defineEventHandler } from 'h3'

export default defineEventHandler(async (): Promise<any> => {
  const backendUrl = useRuntimeConfig().pdfParserApiUrl as string
  return await $fetch(`${backendUrl}/api/v1/graph/health`)
})
