import { defineEventHandler, readBody, createError } from 'h3'
import { extname } from 'path'
import { getTreeFileSystemService } from '~/server/utils/tree-service'

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

  // uploadFile() handles: disk write + .tree-fs.json + .knowledge-base.yml (with file ID)
  const buffer = Buffer.from(String(body.content), 'utf-8')
  const file = await treeService.uploadFile(kb.id, buffer, fileName, body.description?.trim() || '')

  return { success: true, document: file }
})
