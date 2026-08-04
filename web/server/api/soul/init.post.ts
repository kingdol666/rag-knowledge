import { defineEventHandler, readBody, createError } from 'h3'
import { readFileSync, existsSync } from 'fs'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'
import { getTreeFileSystemService, } from '~/server/utils/tree-service'
import { joinTreeStoragePath } from '~/server/utils/runtime-paths'

/**
 * POST /api/soul/init — 创建 SOUL 人格(全流程编排)
 *
 * 与 MCP `soul_init` / `ragctl soul distill` 同语义, 模板法初始化:
 *   1. 读取 4 个人格模板文档(soul-template/)
 *   2. 建库(treeService.createFolder — disk + .tree-fs.json + .knowledge-base.yml)
 *   3. 写 4 个人格文档(treeService.uploadFile)
 *   4. 后端 bootstrap(soul-config.yml + profile-summary + meditation config + 子目录)
 *   5. 索引 4 文档(向量 + 图谱, 60s 内可检索)
 *
 * 任何一步失败均带回显式 error 字段; 索引失败仅告警不阻塞(与 MCP soul_init 一致)。
 */
const TEMPLATE_DOCS = ['soul-definition.md', 'values.md', 'thinking-style.md', 'memory-conventions.md']

export default defineEventHandler(async (event) => {
  const body = (await readBody(event)) || {}

  // ── 名称规范化(soul- 前缀) ──
  let name = (body.name || body.soul_name || '').toString().trim()
  if (!name) {
    throw createError({ statusCode: 400, statusMessage: 'name is required' })
  }
  if (!name.startsWith('soul-')) name = `soul-${name}`

  const description = (body.description || `SOUL 人格 ${name}`).toString().slice(0, 300)
  const kbScope = Array.isArray(body.kb_scope) && body.kb_scope.length
    ? body.kb_scope
    : ['*']
  const domainLabels = Array.isArray(body.domain_labels) ? body.domain_labels : []
  const supportedTaskTypes = Array.isArray(body.supported_task_types) ? body.supported_task_types : []
  const harness = (body.harness || '').toString().trim()
  const model = (body.model || '').toString().trim()

  // ── 1. 读取 4 个人格模板 ──
  const templates: Record<string, string> = {}
  for (const doc of TEMPLATE_DOCS) {
    const src = joinTreeStoragePath('soul-template', doc)
    if (!existsSync(src)) {
      throw createError({ statusCode: 500, statusMessage: `persona template missing: soul-template/${doc}` })
    }
    templates[doc] = readFileSync(src, 'utf-8')
  }

  // ── 2. 建库 ──
  const treeService = await getTreeFileSystemService()
  await treeService.reloadMetadata()
  const folder = await treeService.createFolder({
    name,
    description,
    parentId: null,
    isKnowledgeBase: true,
  })
  const kbId = folder.id
  if (!kbId) {
    throw createError({ statusCode: 500, statusMessage: 'kb create returned no id' })
  }

  // ── 3. 写 4 个人格文档 ──
  const docsCreated: { name: string; ok: boolean }[] = []
  for (const doc of TEMPLATE_DOCS) {
    const buf = Buffer.from(templates[doc], 'utf-8')
    try {
      await treeService.uploadFile(kbId, buf, doc, '')
      docsCreated.push({ name: doc, ok: true })
    } catch (e: any) {
      docsCreated.push({ name: doc, ok: false })
    }
  }

  // ── 4. 后端 bootstrap(soul-config + profile-summary + meditation config) ──
  const backendUrl = getDynamicBackendUrl()
  const boot: any = await $fetch(`${backendUrl}/api/v1/soul/bootstrap`, {
    method: 'POST',
    body: {
      soul_kb_id: kbId,
      kb_scope: kbScope,
      domain_labels: domainLabels,
      supported_task_types: supportedTaskTypes,
      harness,
      model,
    },
  }).catch((e: any) => ({ _error: e?.message || String(e) }))

  // ── 5. 索引 4 文档(失败告警不阻塞) ──
  const docsIndexed: { name: string; ok: boolean }[] = []
  for (const doc of TEMPLATE_DOCS) {
    try {
      const r: any = await $fetch(`${backendUrl}/api/v1/search/index-document`, {
        method: 'POST',
        body: { kb_id: kbId, doc_path: doc },
      })
      docsIndexed.push({ name: doc, ok: !!(r?.success ?? true) })
    } catch {
      docsIndexed.push({ name: doc, ok: false })
    }
  }

  return {
    success: true,
    knowledgeBase: folder,
    kb_id: kbId,
    name,
    docs_created: docsCreated,
    docs_indexed: docsIndexed,
    profile_summary_generated: !!boot?.profile_summary_generated,
    meditation_config_created: !!boot?.meditation_config_created,
    bootstrap_error: boot?._error || null,
  }
})
