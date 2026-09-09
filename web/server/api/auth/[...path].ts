/**
 * Auth bootstrap proxy: forwards register / login / verify / token-management
 * calls to the backend auth service so the browser only ever talks to this
 * origin (no CORS, no backend URL leakage).
 *
 * POST /api/auth/register  { username, password, email? }
 * POST /api/auth/login     { username, password }
 * POST /api/auth/verify    { token }
 * GET  /api/auth/tokens                  (Authorization: Bearer <token>)
 * POST /api/auth/tokens                  { name, ttl_days?, scopes? }
 * DELETE /api/auth/tokens/:id
 */
import { defineEventHandler, getMethod, getRequestURL, readBody, getRequestHeader, createError } from 'h3'
import { getDynamicBackendUrl } from '../../utils/dynamic-config'

export default defineEventHandler(async (event) => {
  const method = getMethod(event).toUpperCase()
  const path = getRequestURL(event).pathname
    .replace(/^\/api\/auth/, '')
    .replace(/\/+$/, '') || '/'

  const backend = getDynamicBackendUrl()
  const headers: Record<string, string> = { 'content-type': 'application/json' }
  const auth = getRequestHeader(event, 'authorization')
  if (auth) headers['authorization'] = auth

  try {
    return await $fetch(`${backend}/api/v1/auth${path}`, {
      method: method as any,
      headers,
      body: ['POST', 'PUT', 'PATCH'].includes(method) ? await readBody(event) : undefined,
    })
  } catch (e: any) {
    const status = e?.statusCode || e?.response?.status || 502
    const data = e?.data || e?.response?._data || { error: 'auth_proxy_error', message: String(e?.message || e) }
    throw createError({ statusCode: status, statusMessage: typeof data === 'string' ? data : undefined, data })
  }
})
