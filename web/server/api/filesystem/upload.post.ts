import { defineEventHandler, readMultipartFormData, createError } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'

/**
 * POST /api/filesystem/upload
 *
 * **Atomic operation**: ONLY uploads a file to the file system tree and
 * writes metadata (.tree-fs.json + .knowledge-base.yml with file ID).
 *
 * Does NOT index (vector/graph). Callers should chain:
 * upload → index (POST /api/v1/search/index-document) if needed.
 *
 * Error contract (P2 fix 2026-10-04): failures now return real 4xx/5xx
 * status codes instead of HTTP 200 + {"error"} bodies — callers and gateways
 * judge outcome by status code, not by parsing success flags.
 */
export default defineEventHandler(async (event) => {
  const method = event.method

  if (method !== 'POST') {
    throw createError({ statusCode: 405, statusMessage: 'Invalid method. Use POST for upload.' })
  }

  const treeService = await getTreeFileSystemService()
  await treeService.reloadMetadata()

  let formData
  try {
    formData = await readMultipartFormData(event)
  } catch (err: any) {
    console.error('[Upload] Failed to parse multipart form:', err)
    throw createError({ statusCode: 400, statusMessage: 'Failed to parse uploaded file: ' + err.message })
  }

  if (!formData || formData.length === 0) {
    throw createError({ statusCode: 400, statusMessage: 'No file uploaded' })
  }

  let parentId: string | null = null
  let fileBuffer: Buffer | null = null
  let originalFilename = ''
  let description = ''

  for (const item of formData) {
    if (item.name === 'parentId') {
      parentId = item.data?.toString() || null
    } else if (item.name === 'description') {
      description = item.data?.toString() || ''
    } else if (item.name === 'file') {
      if (item.filename) {
        originalFilename = item.filename
      }
      if (item.data) {
        fileBuffer = item.data
      }
    }
  }

  if (!fileBuffer || !originalFilename) {
    throw createError({ statusCode: 400, statusMessage: 'File is required' })
  }

  try {
    // uploadFile() handles:
    // 1. Write file to disk
    // 2. Update .tree-fs.json (metadata with file ID)
    // 3. Update .knowledge-base.yml (with file ID via updateYamlForFile)
    const result = await treeService.uploadFile(parentId, fileBuffer, originalFilename, description)
    return {
      success: true,
      file: result
    }
  } catch (error: any) {
    console.error('Upload error:', error)
    throw createError({ statusCode: 500, statusMessage: error.message || 'Upload failed' })
  }
})
