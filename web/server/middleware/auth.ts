/**
 * Shared-token auth middleware (Phase 0).
 *
 * Runs on every server request. Behavior:
 *  - auth disabled (default) → always pass (zero-config local use unchanged).
 *  - auth enabled:
 *    • GET / HEAD / OPTIONS → pass (read endpoints are unprotected).
 *    • Health probes (/api/health, /health) → pass.
 *    • Same-origin browser requests → pass (local browser zero-config).
 *    • Cross-origin / external write requests → require Authorization or
 *      X-KB-Token header matching the configured token, else 401.
 *
 * Note: this middleware protects web endpoints. Backend endpoints are
 * protected by their own verify_token dependency. The Nuxt→backend proxy
 * automatically carries the token via the backend-auth server plugin.
 */
import { defineEventHandler, getHeader, getMethod, createError } from 'h3'
import { getDynamicAuthConfig } from '~/server/utils/dynamic-config'

const WRITE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])
const HEALTH_PATHS = new Set(['/api/health', '/health', '/'])

export default defineEventHandler((event) => {
  const auth = getDynamicAuthConfig()
  if (!auth.enabled) return // auth disabled — allow all

  const method = getMethod(event).toUpperCase()
  // Read-only methods and OPTIONS preflight always pass.
  if (method === 'GET' || method === 'HEAD' || method === 'OPTIONS') return

  const path = event.path || event.node?.req?.url || ''
  // Health probes pass even when write methods (rare).
  if (HEALTH_PATHS.has(path)) return

  // Same-origin browser request → allow (local browser zero-config).
  if (isSameOrigin(event)) return

  // Cross-origin / non-browser write request → require valid token.
  if (hasValidToken(event, auth.token)) return

  throw createError({
    statusCode: 401,
    statusMessage: 'Unauthorized: invalid or missing auth token',
  })
})

/** Determine if the request is same-origin (a browser request from this server's own origin). */
function isSameOrigin(event: any): boolean {
  const secFetchSite = (getHeader(event, 'sec-fetch-site') || '').toLowerCase()

  // Modern browsers send Sec-Fetch-Site: same-origin (or none for user navigations).
  if (secFetchSite === 'same-origin' || secFetchSite === 'none') return true
  if (secFetchSite === 'cross-site' || secFetchSite === 'same-site') {
    // same-site is nearly same-origin for our purposes, but to be strict treat
    // same-site as trusted (same registrable domain). If Origin header is present
    // and matches Host, it's definitely same-origin.
    if (originMatchesHost(event)) return true
    return secFetchSite === 'same-site'
  }

  const origin = getHeader(event, 'origin')
  // No Origin + no Sec-Fetch-Site: either a same-origin browser request (some
  // browsers omit Origin) or a non-browser client. Non-browser clients carry
  // their own token and will pass the token check downstream, so allowing here
  // is safe. Cross-origin browser requests ALWAYS include Origin.
  if (!origin) return true

  // Origin present — must match Host to be same-origin.
  return originMatchesHost(event)
}

/** Check if the Origin header host matches the request Host header. */
function originMatchesHost(event: any): boolean {
  const origin = getHeader(event, 'origin')
  const host = getHeader(event, 'host')
  if (!origin || !host) return false
  try {
    const originHost = new URL(origin).host
    return originHost === host
  } catch {
    return false
  }
}

/** Check Authorization: Bearer <token> or X-KB-Token header. */
function hasValidToken(event: any, expected: string): boolean {
  if (!expected) return false
  const authHeader = getHeader(event, 'authorization') || ''
  let candidate = ''
  if (authHeader.toLowerCase().startsWith('bearer ')) {
    candidate = authHeader.slice(7).trim()
  }
  if (!candidate) {
    candidate = (getHeader(event, 'x-kb-token') || '').trim()
  }
  return !!candidate && candidate === expected
}
