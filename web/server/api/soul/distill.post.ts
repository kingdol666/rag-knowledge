import { defineEventHandler, readBody, createError } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/**
 * POST /api/soul/distill — 补天蒸馏(文本/需求 → LLM 提取人格画像 → 建库+4文档+索引)
 *
 * body: {
 *   name: string              // soul-<名字>
 *   personality_req?: string  // 人格需求(人物/风格/思维框架)
 *   source_material?: string  // 源材料(聊天记录/文档片段/人物描述)
 *   kb_scope?: string[]       // 缺省 ["*"]
 *   domain_labels?: string[]  // 路由标签
 *   supported_task_types?: string[]
 *   harness?: string
 *   async_mode?: boolean      // 默认 true → 返回 task_id(训练控制台追踪)
 * }
 *
 * v2: 原生 fetch + text() + JSON.parse(与 ask 同源修复, 规避全局 $fetch 解码差异)。
 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const name = String(body?.name || '').trim()
  if (!name) throw createError({ statusCode: 400, statusMessage: 'name required' })
  const backendUrl = getDynamicBackendUrl()
  const res = await fetch(`${backendUrl}/api/v1/soul/distill`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name,
      personality_req: body?.personality_req || '',
      source_material: body?.source_material || '',
      kb_scope: Array.isArray(body?.kb_scope) ? body.kb_scope : ['*'],
      domain_labels: Array.isArray(body?.domain_labels) ? body.domain_labels : [],
      supported_task_types: Array.isArray(body?.supported_task_types) ? body.supported_task_types : [],
      harness: body?.harness || '',
      async_mode: body?.async_mode !== false,
    }),
    signal: AbortSignal.timeout(300_000),
  })
  const text = await res.text()
  return JSON.parse(text)
})
