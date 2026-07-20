/**
 * Centralized backend proxy utility for Nuxt server routes.
 *
 * Wraps $fetch calls to the FastAPI backend with:
 * - Consistent timeout (default 30s)
 * - Structured error handling with statusCode propagation
 * - Graceful degradation (returns null on failure instead of throwing)
 * - Automatic backend URL resolution via dynamic-config
 */
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

const DEFAULT_TIMEOUT = 30000

export interface ProxyOptions {
  timeout?: number
  /** Return null on error instead of throwing (default: true for GET, false for mutations) */
  graceful?: boolean
}

/**
 * Proxy a request to the backend with standardized error handling.
 *
 * Usage:
 *   const data = await backendProxy('/api/v1/search/two-stage', 'POST', { body })
 *   const data = await backendProxy('/api/v1/search/stats', 'GET')
 */
export async function backendProxy<T = any>(
  path: string,
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' = 'GET',
  options: { body?: any; query?: Record<string, any> } & ProxyOptions = {},
): Promise<T | null> {
  const backendUrl = getDynamicBackendUrl()
  const url = `${backendUrl}${path}`
  const { body, query, timeout, graceful = method === 'GET' } = options

  try {
    const fetchOpts: any = {
      method,
      timeout: timeout ?? DEFAULT_TIMEOUT,
    }
    if (body !== undefined) fetchOpts.body = body
    if (query) fetchOpts.query = query

    return await $fetch<T>(url, fetchOpts)
  } catch (err: any) {
    const status = err?.statusCode || err?.status || 'unknown'
    const message = err?.message || err?.statusMessage || String(err)

    console.error(`[backendProxy] ${method} ${path} failed (${status}): ${message}`)

    if (graceful) {
      return null
    }

    throw createError({
      statusCode: typeof status === 'number' ? status : 502,
      statusMessage: `Backend error: ${message}`,
    })
  }
}
