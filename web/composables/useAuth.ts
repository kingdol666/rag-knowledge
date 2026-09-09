/**
 * Client-side auth state: token persistence + auth API calls.
 * Token lives in localStorage('kb_auth_token'); identity in 'kb_auth_user'.
 */
export interface AuthUser {
  id: string
  username: string
  role: string
  email?: string
}

const TOKEN_KEY = 'kb_auth_token'
const USER_KEY = 'kb_auth_user'

export function useAuth() {
  const token = (): string => (typeof localStorage !== 'undefined' ? localStorage.getItem(TOKEN_KEY) || '' : '')
  const user = (): AuthUser | null => {
    if (typeof localStorage === 'undefined') return null
    try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null') } catch { return null }
  }

  const saveSession = (tok: string, u: AuthUser | null) => {
    localStorage.setItem(TOKEN_KEY, tok)
    if (u) localStorage.setItem(USER_KEY, JSON.stringify(u))
  }

  const clearSession = () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  const isLoggedIn = (): boolean => !!token()

  /** Register a new user; on success immediately logs in. */
  async function register(username: string, password: string, email = '') {
    const res: any = await $fetch('/api/auth/register', { method: 'POST', body: { username, password, email } })
    const loginRes: any = await $fetch('/api/auth/login', { method: 'POST', body: { username, password } })
    saveSession(loginRes.token, loginRes.user)
    return res
  }

  async function login(username: string, password: string) {
    const res: any = await $fetch('/api/auth/login', { method: 'POST', body: { username, password } })
    saveSession(res.token, res.user)
    return res
  }

  function logout() { clearSession() }

  async function listTokens(): Promise<any[]> {
    const res: any = await $fetch('/api/auth/tokens', {
      headers: { Authorization: `Bearer ${token()}` },
    })
    return res.tokens || []
  }

  /** Create an API token; the plaintext is returned exactly once by the backend. */
  async function createToken(name: string, ttlDays = 30): Promise<any> {
    return await $fetch('/api/auth/tokens', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token()}` },
      body: { name, ttl_days: ttlDays },
    })
  }

  async function revokeToken(id: string) {
    return await $fetch(`/api/auth/tokens/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token()}` },
    })
  }

  return { token, user, isLoggedIn, saveSession, clearSession, register, login, logout, listTokens, createToken, revokeToken }
}
