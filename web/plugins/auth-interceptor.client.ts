/**
 * Global $fetch interceptor (client only).
 *
 * 1. attaches `Authorization: Bearer <token>` to every same-origin /api/*
 *    request and to direct backend (pdf parser) requests when a token exists;
 * 2. on any 401 response, clears the session and redirects to /login.
 *
 * Implemented by replacing the global ofetch instance — every composable that
 * calls bare `$fetch(...)` automatically goes through this wrapper.
 */
export default defineNuxtPlugin((nuxtApp) => {
  if (typeof window === 'undefined') return

  const raw = globalThis.$fetch
  const authed = raw.create({
    onRequest({ request, options }) {
      const url = typeof request === 'string' ? request : (request as Request).url || ''
      const token = localStorage.getItem('kb_auth_token') || ''
      if (token && (url.startsWith('/api/') || url.includes('localhost:8770') || url.includes(':8770/'))) {
        ;(options.headers as any) = new Headers(options.headers || {})
        ;(options.headers as Headers).set('Authorization', `Bearer ${token}`)
      }
    },
    onResponseError({ request, response }) {
      const url = typeof request === 'string' ? request : ''
      if (response.status === 401 && !url.startsWith('/api/auth/login')
          && !url.startsWith('/api/auth/register') && !url.startsWith('/api/auth/verify')) {
        localStorage.removeItem('kb_auth_token')
        localStorage.removeItem('kb_auth_user')
        if (!window.location.pathname.startsWith('/login')) {
          window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`
        }
      }
    },
  })

  // Replace the global instance so all existing $fetch call-sites are covered.
  ;(globalThis as any).$fetch = authed
  if (typeof nuxtApp !== 'undefined' && (nuxtApp as any)) {
    ;(nuxtApp as any).$fetch = authed
  }
})
