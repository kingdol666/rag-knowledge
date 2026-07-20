/**
 * Backend-auth Nitro plugin (Phase 0).
 *
 * Intercepts the global `$fetch` used by Nuxt server routes to proxy requests
 * to the FastAPI backend. When shared-token auth is enabled, automatically
 * attaches `Authorization: Bearer <token>` to all outgoing backend calls so
 * the backend's verify_token dependency accepts the Nuxt proxy.
 *
 * This keeps the browser flow zero-config: the browser talks same-origin to
 * Nuxt (no token needed from the browser), and Nuxt authenticates to the
 * backend transparently using the server-side token.
 *
 * Runs at server startup; reads config dynamically on each call so runtime
 * config changes (hot-reload of config.yml) are picked up immediately.
 */
import { getDynamicBackendUrl, getDynamicAuthConfig } from '~/server/utils/dynamic-config'

// defineNitroPlugin is auto-imported by Nitro — do not import from nitropack/server.
export default defineNitroPlugin(() => {
  const originalFetch = globalThis.$fetch as unknown as (
    ...args: any[]
  ) => any

  if (!originalFetch || typeof originalFetch !== 'function') return

  const proxied = new Proxy(originalFetch, {
    apply(target: any, thisArg: any, args: any[]) {
      try {
        const auth = getDynamicAuthConfig()
        if (auth.enabled && auth.token) {
          const backendUrl = getDynamicBackendUrl()
          const input = args[0]
          const url: string =
            typeof input === 'string'
              ? input
              : input?.url || ''
          // Only inject for requests targeting the backend.
          if (url && backendUrl && url.startsWith(backendUrl)) {
            const opts: any = args[1] || {}
            const existingHeaders: Record<string, string> =
              (opts.headers && !(opts.headers instanceof Headers))
                ? { ...opts.headers }
                : {}
            opts.headers = {
              ...existingHeaders,
              Authorization: `Bearer ${auth.token}`,
            }
            args[1] = opts
          }
        }
      } catch {
        // If config reading fails, fall through to original (non-fatal).
      }
      return Reflect.apply(target, thisArg, args)
    },
  })

  globalThis.$fetch = proxied as any
})
