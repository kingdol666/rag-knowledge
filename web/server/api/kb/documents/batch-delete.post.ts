﻿import { defineEventHandler, readBody, createError } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'

/**
 * POST /api/kb/documents/batch-delete
 *
 * Deletes multiple documents from the file system and cleans up indexes.
 * Removes files from disk + .tree-fs.json + .knowledge-base.yml.
 * Automatically cleans up vector chunks and graph nodes (fire-and-forget).
 */
export default defineEventHandler(async (event) => {
  const body = (await readBody(event)) || {}

  if (!body.kbId?.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'kbId is required' })
  }
  if (!Array.isArray(body.docPaths) || body.docPaths.length === 0) {
    throw createError({ statusCode: 400, statusMessage: 'docPaths must be a non-empty array' })
  }

  const treeService = await getTreeFileSystemService()
  await treeService.reloadMetadata()

  const results: Array<{ path: string; success: boolean; error?: string }> = []

  for (const docPath of body.docPaths) {
    try {
      // Resolve bare filename or relative path to full storage-relative path
      const resolvedPath = await treeService.resolveDocPath(body.kbId, docPath)
      if (!resolvedPath) {
        results.push({ path: docPath, success: false, error: 'Not found' })
        continue
      }
      const file = await treeService.getFileByPath(resolvedPath)
      if (!file) {
        results.push({ path: docPath, success: false, error: 'Not found' })
        continue
      }
      // deleteFile handles: disk delete + .tree-fs.json + .knowledge-base.yml
      await treeService.deleteFile(file.id)
      results.push({ path: docPath, success: true })
    } catch (err: any) {
      results.push({ path: docPath, success: false, error: err.message })
    }
  }

  const successful = results.filter(r => r.success).length
  const failed = results.length - successful

  return { success: true, total: results.length, successful, failed, results }
})
