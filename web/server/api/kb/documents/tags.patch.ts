import { defineEventHandler, readBody, createError } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'
import { getKnowledgeBaseYamlService } from '~/server/services/knowledge-base-yaml-service'
import { getTreeStorageAbsolutePath } from '~/server/utils/runtime-paths'
import { getTagManagementService, TagManagementService } from '~/server/services/tag-management-service'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** PATCH /api/kb/documents/tags — update a document's tags. */
export default defineEventHandler(async (event) => {
  const body = (await readBody(event)) || {}

  if (!body.kbId?.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'kbId is required' })
  }
  if (!body.docPath?.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'docPath is required' })
  }

  // Validate + filter tags: drop garbage-tag entries instead of rejecting the
  // entire array (fixes round-trip bug where docs carrying legacy garbage tags
  // are bricked for any tag edit). validateTags still rejects non-array input.
  let tags = TagManagementService.validateTags(body.tags)
  if (tags === null) {
    throw createError({ statusCode: 400, statusMessage: 'tags must be a string[] with non-empty entries (max 50 chars each)' })
  }
  // If validateTags filtered some out, we still proceed with the clean subset.
  // (validateTags already drops garbage internally via isGarbageTag per-tag)

  const treeService = await getTreeFileSystemService()
  await treeService.reloadMetadata()

  // Resolve kbId (UUID) to kb_path
  const kb = await treeService.getKnowledgeBaseById(body.kbId)
  if (!kb) {
    throw createError({ statusCode: 404, statusMessage: 'Knowledge base not found' })
  }

  // Resolve docPath (supports bare filename)
  const resolvedPath = await treeService.resolveDocPath(body.kbId, body.docPath)
  if (!resolvedPath) {
    throw createError({ statusCode: 404, statusMessage: 'Document not found' })
  }

  const yamlService = getKnowledgeBaseYamlService(getTreeStorageAbsolutePath())
  const updated = await yamlService.updateDocumentTags(kb.path, resolvedPath, tags)
  if (!updated) {
    throw createError({ statusCode: 404, statusMessage: 'Document not found in KB YAML' })
  }

  // Sync tags to global registry
  const tagService = getTagManagementService()
  await tagService.ensureTags(tags)

  // FIX: Trigger graph reindex so the Document node's tags field stays in sync.
  // Without this, kb_graph_document shows stale tags after kb_doc_update_tags.
  const backendUrl = getDynamicBackendUrl()
  fetch(`${backendUrl}/api/v1/search/index-document`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      kb_id: kb.id,
      doc_path: resolvedPath,
      doc_name: '',
      description: '',
    }),
  }).then(() => {
    console.log(`[tags.patch] graph reindex triggered for ${resolvedPath}`)
  }).catch((e) => {
    console.warn(`[tags.patch] graph reindex failed (non-fatal): ${e}`)
  })

  return {
    success: true,
    kb_id: kb.id,
    kb_path: kb.path,
    docPath: resolvedPath,
    tags,
    _note: 'Tags updated. Graph reindex triggered in background.'
  }
})