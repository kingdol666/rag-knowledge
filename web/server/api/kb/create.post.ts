import { defineEventHandler, readBody, createError } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'

/**
 * POST /api/kb/create
 *
 * **Atomic operation**: ONLY creates a new knowledge base folder.
 * Writes folder to disk + .tree-fs.json + .knowledge-base.yml (with KB ID).
 *
 * Does NOT initialize experience folder (use POST /api/v1/experience/{kbId}/init separately).
 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)

  if (!body.name?.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'name is required' })
  }

  const treeService = await getTreeFileSystemService()
  await treeService.reloadMetadata()

  // createFolder handles: disk create + .tree-fs.json + .knowledge-base.yml (with KB ID)
  const folder = await treeService.createFolder({
    name: body.name.trim(),
    description: body.description?.trim() || '',
    parentId: body.parentId || null,
    isKnowledgeBase: true,
  })

  return { success: true, knowledgeBase: folder }
})
