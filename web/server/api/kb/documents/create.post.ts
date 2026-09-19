import { defineEventHandler, readBody, createError } from 'h3'
import { extname, basename } from 'path'
import { getTreeFileSystemService } from '~/server/utils/tree-service'
import { coerceKbPayload } from '~/server/utils/kb-payload'
import { getLargeDocConfig, buildPartDescription, requestSplitPlan } from '~/server/utils/large-doc-split'
/**
 * POST /api/kb/documents/create
 *
 * **Atomic operation**: ONLY creates a new markdown document inside a KB.
 * Writes file to disk + .tree-fs.json + .knowledge-base.yml (with file ID).
 *
 * Does NOT handle tags (use PATCH /api/kb/documents/tags separately).
 * Does NOT index (use POST /api/v1/search/index-document separately).
 *
 * Large-doc normalization (2026-09-18): when the content character count
 * exceeds `ingestion.large_doc.max_chars` (Settings page, hot-effective), the
 * backend split plan splits it into parts and each part is stored as its own
 * document whose description is excerpted from that part's real body.
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
  const sourceChars = content.length

  // ── 大文档入库规范化 (2026-09-18) ──────────────────────────────────
  // 字符数超过 ingestion.large_doc.max_chars（设置页可配，热生效）时向后端
  // 申请拆分计划，再把每个 part 作为独立文档写盘 —— 之后每 part 独立向量分块/
  // BM25 索引/图谱节点，检索粒度与召回都受益；描述按 part 真实正文摘录。
  const largeDoc = getLargeDocConfig()
  const autoSplit = (body as any).autoSplit !== false && largeDoc.autoSplit
  if (autoSplit && sourceChars > largeDoc.maxChars) {
    try {
      const plan = await requestSplitPlan(fileName, content, true)
      if (plan?.success && plan.split && Array.isArray(plan.parts) && plan.parts.length > 1) {
        const base = basename(fileName, extname(fileName))
        const documents: any[] = []
        for (const part of plan.parts) {
          const partName = `${base} (part ${part.part_index} of ${part.part_count}).md`
          const partDesc = buildPartDescription(description, part)
          const file = await treeService.uploadFile(
            kb.id, Buffer.from(String(part.content), 'utf-8'), partName, partDesc)
          documents.push(file)
        }
        return {
          success: true,
          split: true,
          part_count: documents.length,
          source_chars: plan.source_chars ?? sourceChars,
          max_chars: plan.max_chars ?? largeDoc.maxChars,
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

  return { success: true, source_chars: sourceChars, document: file }
})
