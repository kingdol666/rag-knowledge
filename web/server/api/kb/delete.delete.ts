import { defineEventHandler, readBody, createError } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/**
 * DELETE /api/kb/delete
 *
 * Deletes an entire knowledge base from the file system AND cascades cleanup
 * to ChromaDB vector collections and Neo4j graph data.
 * Vector/graph cleanup is fire-and-forget: failures don't block the delete.
 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)

  if (!body.kbId?.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'kbId is required' })
  }

  const treeService = await getTreeFileSystemService()
  await treeService.reloadMetadata()

  const kb = await treeService.getKnowledgeBaseById(body.kbId)
  if (!kb) {
    throw createError({ statusCode: 404, statusMessage: 'Knowledge base not found' })
  }

  // deleteFolder handles: disk delete + .tree-fs.json + .knowledge-base.yml
  const result = await treeService.deleteFolder(kb.id)

  // Cascade cleanup: delete vector collections + graph data (fire-and-forget).
  // Without this, deleted KBs leave orphaned ChromaDB collections and Neo4j nodes.
  const kbIdForCleanup = kb.id
  const kbPathForCleanup = kb.path
  const backendUrl = getDynamicBackendUrl()
  Promise.allSettled([
    $fetch(`${backendUrl}/api/v1/search/kb/${encodeURIComponent(kbIdForCleanup)}?kb_path=${encodeURIComponent(kbPathForCleanup)}`, { method: 'DELETE', timeout: 10000 }).catch(() => {}),
    $fetch(`${backendUrl}/api/v1/graph/kb/${encodeURIComponent(kbIdForCleanup)}`, { method: 'DELETE', timeout: 10000 }).catch(() => {}),
  ]).then((results) => {
    const [vecRes, graphRes] = results
    if (vecRes.status === 'fulfilled') console.log(`[KB delete] cleaned vector collection for ${kbIdForCleanup}`)
    if (graphRes.status === 'fulfilled') console.log(`[KB delete] cleaned graph data for ${kbIdForCleanup}`)
  })

  return { ...result }
})
