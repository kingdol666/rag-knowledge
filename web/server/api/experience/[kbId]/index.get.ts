import { defineEventHandler, getRouterParam, readBody, getQuery } from 'h3'
import { getServerConfig } from '~/utils/paths.mjs'

export default defineEventHandler(async (event) => {
  const kbId = getRouterParam(event, 'kbId')
  const expId = getRouterParam(event, 'expId')
  if (!kbId) {
    return { success: false, error: 'kbId is required' }
  }
  const config = getServerConfig()
  const backendUrl = process.env.BACKEND_URL || getPdfParserApiUrl() || 'http://localhost:8765'
  try {
    const base = `${backendUrl}/api/v1/experience/${encodeURIComponent(kbId)}`
    const url = false ? `${base}/${encodeURIComponent(expId || '')}` : base

    const query = getQuery(event)
    const qs = new URLSearchParams(query as Record<string, string>).toString()
    const fullUrl = qs ? url + '?' + qs : url
    const response = await fetch(fullUrl)
    return await response.json()
  } catch (e) {
    return { success: false, error: `Backend unreachable: ${e instanceof Error ? e.message : String(e)}` }
  }
})
