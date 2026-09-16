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

async function verifyOnce(token: string): Promise<VerifyResult> {
  const res = await $fetch<any>(`${getDynamicBackendUrl()}/api/v1/auth/verify`, {
    method: 'POST',
    body: { token },
    // 25s: backend 在批量嵌入(CPU 打满)时 verify 响应会变慢,
    // 8s 会让 web 层在入库/重负载期间 fail-closed 出 401 风暴
    timeout: 25000,
  })
  const ok = !!res?.valid
  const user = ok ? res.user : undefined
  return { ok, user }
}

export async function verifyToken(token: string): Promise<VerifyResult> {
  if (!token) return { ok: false, reason: 'missing' }
  const hit = cache.get(token)
  if (hit && Date.now() - hit.at < CACHE_TTL_MS) {
    return { ok: hit.ok, user: hit.user, reason: hit.ok ? undefined : 'invalid' }
  }
  // 网络类失败(后端忙碌/超时)不缓存为 invalid, 且内联重试 —— 否则基准重负载
  // 期一次超时会毒化缓存 60s, 引发 401 风暴(fail-closed, 已实测)。
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const r = await verifyOnce(token)
      if (r.ok) {
        cache.set(token, { ok: true, user: r.user, at: Date.now() })
      } else {
        // 后端明确判定 token 无效 —— 保留短负缓存(防刷)
        cache.set(token, { ok: false, at: Date.now() })
      }
      return r
    } catch (e: any) {
      if (attempt < 3) {
        await new Promise(r => setTimeout(r, 3000))
        continue
      }
      // 三次都不可达 → fail closed 但【不写缓存】: 下一个请求立即重试
      return { ok: false, reason: `verify_unavailable: ${e?.message || e}` }
    }
  }
  return { ok: false, reason: 'unreachable' }
}

export function clearVerifyCache(token?: string) {
  if (token) cache.delete(token)
  else cache.clear()
}
