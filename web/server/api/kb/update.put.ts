import { defineEventHandler, readBody, createError } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'

/**
 * PUT /api/kb/update
 * Update knowledge-base name and/or description.
 *
 * Body: { kbId, name?, description? }
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

  const updated = await treeService.updateFolder(kb.id, {
    name: body.name?.trim() || undefined,
    description: body.description?.trim() || undefined,
  })

  return { success: true, knowledgeBase: updated }
})
