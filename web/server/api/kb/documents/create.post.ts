import { defineEventHandler, readBody, createError } from 'h3'
import { extname, basename } from 'path'
import { getTreeFileSystemService } from '~/server/utils/tree-service'
import { coerceKbPayload } from '~/server/utils/kb-payload'
import { getDynamicBackendUrl, getDynamicAuthConfig } from '~/server/utils/dynamic-config'

/**
 * POST /api/kb/documents/create
 *
 * **Atomic operation**: ONLY creates a new markdown document inside a KB.
 * Writes file to disk + .tree-fs.json + .knowledge-base.yml (with file ID).
 *
 * Does NOT handle tags (use PATCH /api/kb/documents/tags separately).
 * Does NOT index (use POST /api/v1/search/index-document separately).
 */
export default defineEventHandler(async (event) => {
  const body = (await readBody(event)) || {}
  coerceKbPayload(body)

  if (!body.kbId?.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'kbId is required' })
  }
  if (!body.name?.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'name is required' })
  }
  if (body.content == null) {
    throw createError({ statusCode: 400, statusMessage: 'content is required' })
  }

  const treeService = await getTreeFileSystemService()
  await treeService.reloadMetadata()

  const kb = await treeService.getKnowledgeBaseById(body.kbId)
  if (!kb) {
    throw createError({ statusCode: 404, statusMessage: 'Knowledge base not found' })
  }

  // Ensure .md extension
  let fileName = body.name.trim()
  if (!extname(fileName)) {
    fileName += '.md'
  }

  const content = String(body.content)
  const description = body.description?.trim() || ''

  // ── 大文档入库规范化 (2026-09-11) ──────────────────────────────────
  // 超过预筛阈值时向后端申请拆分计划（策略由 config.yml ingestion.large_doc
  // 统一决定），再把每个 part 作为独立文档写盘 —— 之后每 part 独立向量分块/
  // BM25 索引/图谱节点，检索粒度与召回都受益。
  const SPLIT_PREFILTER_CHARS = 12000
  if (content.length > SPLIT_PREFILTER_CHARS && (body as any).autoSplit !== false) {
    try {
      const auth = getDynamicAuthConfig()
      const plan = await $fetch<any>(`${getDynamicBackendUrl()}/api/v1/documents/split`, {
        method: 'POST',
        headers: auth.token ? { Authorization: `Bearer ${auth.token}` } : {},
        body: { title: fileName, content },
        timeout: 60000,
      })
      if (plan?.success && plan.split && Array.isArray(plan.parts) && plan.parts.length > 1) {
        const base = basename(fileName, extname(fileName))
        const documents: any[] = []
        for (const part of plan.parts) {
          const partName = `${base} (part ${part.part_index} of ${part.part_count}).md`
          const partDesc = `${description}${description ? ' ' : ''}[part ${part.part_index}/${part.part_count} of ${fileName}]`
          const file = await treeService.uploadFile(
            kb.id, Buffer.from(String(part.content), 'utf-8'), partName, partDesc)
          documents.push(file)
        }
        return {
          success: true,
          split: true,
          part_count: documents.length,
          parent_name: fileName,
          documents,
          document: documents[0], // 向后兼容：旧调用方取 document 仍可用
        }
      }
    } catch (e: any) {
      // 拆分失败不阻塞入库：回落为单文档写入（并记录原因）
      console.warn(`[documents/create] large-doc split skipped: ${e?.message || e}`)
    }
  }

  // uploadFile() handles: disk write + .tree-fs.json + .knowledge-base.yml (with file ID)
  const buffer = Buffer.from(content, 'utf-8')
  const file = await treeService.uploadFile(kb.id, buffer, fileName, description)

  return { success: true, document: file }
})
