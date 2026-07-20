import { defineEventHandler, getRouterParam, readBody } from 'h3'
import { getServerConfig } from '~/utils/paths.mjs'

export default defineEventHandler(async (event) => {
  const kbId = getRouterParam(event, 'kbId')
  if (!kbId) {
    return { success: false, error: 'kbId is required' }
  }
  const config = getServerConfig()
  const backendUrl = process.env.BACKEND_URL || getPdfParserApiUrl() || 'http://localhost:8765'
  try {
    const body = await readBody(event)
    const url = `${backendUrl}/api/v1/experience/${encodeURIComponent(kbId)}/vector-search`
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    })
    return await response.json()
  } catch (e) {
    return { success: false, error: `Backend unreachable: ${e instanceof Error ? e.message : String(e)}` }
  }
})
