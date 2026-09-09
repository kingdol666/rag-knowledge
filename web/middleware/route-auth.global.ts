/**
 * Global client route guard: unauthenticated visitors land on /login.
 * /login itself stays reachable; everything else requires a session token.
 */
export default defineNuxtRouteMiddleware((to) => {
  if (import.meta.server) return
  const token = localStorage.getItem('kb_auth_token')
  if (to.path === '/login') {
    if (token) return navigateTo('/')
    return
  }
  if (!token) {
    return navigateTo(`/login?redirect=${encodeURIComponent(to.fullPath)}`)
  }
})
