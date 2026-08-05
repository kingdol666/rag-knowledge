import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/soul/ask — 人格问答(显式或自动路由);合成+PAS 可达 3 分钟
 * v2: 改用原生 fetch + text() + JSON.parse, 绕过全局 $fetch 代理,
 * 规避 dev 模式下全局 $fetch 的响应解码差异(UTF-8 中文保持原样)。
 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  const res = await fetch(`${backendUrl}/api/v1/soul/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(300_000),
  })
  const text = await res.text()
  return JSON.parse(text)
})
