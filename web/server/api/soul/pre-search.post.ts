import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/**
 * POST /api/soul/pre-search — QDCVR 前置检索
 *
 * 先用两阶段检索定位知识库证据, 返回格式化片段供 context_override 注入,
 * 让人格在真实检索证据之上做增强回答(检索→验证→人格合成)。
 * Body: { query, kb_id?, top_k }
 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  const res = await $fetch<any>(`${backendUrl}/api/v1/search/two-stage`, {
    method: 'POST',
    body: {
      query: body.query,
      kb_id: body.kb_id || null,
      stage1_top_k: 20,
      stage2_top_k: Number(body.top_k) || 5,
      enable_graph_expansion: true,
    },
    timeout: 60000,
  })

  const results = res?.stage2?.results || res?.results || []
  // 展开为片段级 [{path, chunk_text, score}]
  const chunks: any[] = []
  for (const r of results) {
    const docPath = r.doc_path || r.path || ''
    const sub = r.chunks || []
    if (sub.length) {
      for (const c of sub) {
        chunks.push({
          path: docPath,
          chunk_text: c.chunk_text || c.text || c.content || '',
          score: Number(c.score || 0),
        })
      }
    } else {
      chunks.push({
        path: docPath,
        chunk_text: r.content || r.chunk_text || '',
        score: Number(r.score || 0),
      })
    }
  }
  chunks.sort((a, b) => b.score - a.score)
  const top = chunks.slice(0, 6)

  // 注入文本(带来源标注)
  const override = top.map((c, i) =>
    `[${i + 1}] 来源: ${c.path} (score=${c.score.toFixed(3)})\n${(c.chunk_text || '').slice(0, 600)}`
  ).join('\n\n---\n\n')

  return { success: true, chunks: top, context_override: override }
})
