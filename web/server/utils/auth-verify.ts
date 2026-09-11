/**
 * Token verification against the backend auth service (with a short TTL cache).
 * Web layer never sees password hashes — it only forwards tokens for validation.
 */
import { getDynamicBackendUrl } from './dynamic-config'

const CACHE_TTL_MS = 60_000
const cache = new Map<string, { ok: boolean; user?: any; at: number }>()

export interface VerifyResult {
  ok: boolean
  user?: { id: string; username: string; role: string }
  reason?: string
}

export async function verifyToken(token: string): Promise<VerifyResult> {
  if (!token) return { ok: false, reason: 'missing' }
  const hit = cache.get(token)
  if (hit && Date.now() - hit.at < CACHE_TTL_MS) {
    return { ok: hit.ok, user: hit.user, reason: hit.ok ? undefined : 'invalid' }
  }
  try {
    const res = await $fetch<any>(`${getDynamicBackendUrl()}/api/v1/auth/verify`, {
      method: 'POST',
      body: { token },
      // 25s: backend 在批量嵌入(CPU 打满)时 verify 响应会变慢,
      // 8s 会让 web 层在入库/重负载期间 fail-closed 出 401 风暴
      timeout: 25000,
    })
    const ok = !!res?.valid
    const user = ok ? res.user : undefined
    cache.set(token, { ok, user, at: Date.now() })
    return { ok, user }
  } catch (e: any) {
    // backend unreachable → fail closed (do not leak data when auth is on)
    cache.set(token, { ok: false, at: Date.now() })
    return { ok: false, reason: `verify_unavailable: ${e?.message || e}` }
  }
}

export function clearVerifyCache(token?: string) {
  if (token) cache.delete(token)
  else cache.clear()
}
