/**
 * Web-layer token auth middleware (2026-09-09, replaces the Phase-0 shared token).
 *
 * Runs on every server request:
 *  - auth disabled (config.yml server.auth.enabled=false, maintenance) → pass
 *  - non-/api paths (pages, static) → pass (route guards handle the UI side)
 *  - /api/auth/* bootstrap proxy and /api/health → pass
 *  - everything else under /api/* → Bearer token must validate against the
 *    backend user/token service (same policy as backend AuthMiddleware);
 *    verified identity is attached to event.context.authUser
 */
import { defineEventHandler, createError, getRequestHeader } from 'h3'
import { verifyToken } from '../utils/auth-verify'
import { getDynamicAuthConfig } from '../utils/dynamic-config'

const WHITELIST = (path: string) => {
  if (path.startsWith('/api/auth/')) return true           // register/login/verify proxy
  if (path === '/api/health' || path.startsWith('/api/health/')) return true
  return false
}

export default defineEventHandler(async (event) => {
  const { enabled } = getDynamicAuthConfig()
  if (!enabled) return // maintenance mode — matches backend auth_enabled=false

  const path = event.path || event.node?.req?.url || ''
  const clean = path.split('?')[0].replace(/\/+$/, '')
  if (!clean.startsWith('/api/') || WHITELIST(clean)) return

  const auth = getRequestHeader(event, 'authorization') || ''
  const token = auth.toLowerCase().startsWith('bearer ')
    ? auth.slice(7).trim()
    : (getRequestHeader(event, 'x-kb-token') || '').trim()

  if (!token) {
    throw createError({
      statusCode: 401,
      statusMessage: 'Unauthorized',
      data: { error: 'unauthorized', message: '认证失败: 缺少 token',
              hint: '登录后在 /tokens 页面创建 API Token，请求头携带 Authorization: Bearer <token>' },
    })
  }

  const result = await verifyToken(token)
  if (!result.ok) {
    throw createError({
      statusCode: 401,
      statusMessage: 'Unauthorized',
      data: { error: 'unauthorized', message: '认证失败: token 无效、已撤销或已过期' },
    })
  }
  event.context.authUser = result.user
})
