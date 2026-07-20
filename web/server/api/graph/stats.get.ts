import { defineEventHandler } from 'h3'

export default defineEventHandler(async () => {
  const backendUrl = useRuntimeConfig().pdfParserApiUrl as string
  const res = await $fetch<{ success?: boolean; stats?: any }>(`${backendUrl}/api/v1/graph/stats`)
  // Backend returns { success, stats: {...} } — return as-is so frontend can extract .stats
  return res
})
