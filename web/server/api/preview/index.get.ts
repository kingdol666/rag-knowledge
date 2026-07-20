import { defineEventHandler, getQuery, createError } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'
import { readFile } from 'fs/promises'
import { resolveSafePath } from '~/server/utils/safe-paths'

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const fileId = query.id as string
  const filePathParam = query.path as string

  let filePath: string
  let mimeType = 'application/octet-stream'

  // If path parameter is provided, read file directly by path (for images and other resources)
  if (filePathParam) {
    // Decode path and convert to local path
    const decodedPath = decodeURIComponent(filePathParam)
    filePath = resolveSafePath(decodedPath)

    // Infer MIME type from file extension
    // Images
    if (decodedPath.match(/\.(jpg|jpeg)$/i)) mimeType = 'image/jpeg'
    else if (decodedPath.match(/\.png$/i)) mimeType = 'image/png'
    else if (decodedPath.match(/\.gif$/i)) mimeType = 'image/gif'
    else if (decodedPath.match(/\.webp$/i)) mimeType = 'image/webp'
    else if (decodedPath.match(/\.svg$/i)) mimeType = 'image/svg+xml'
    else if (decodedPath.match(/\.bmp$/i)) mimeType = 'image/bmp'
    else if (decodedPath.match(/\.ico$/i)) mimeType = 'image/x-icon'
    // Video
    else if (decodedPath.match(/\.mp4$/i)) mimeType = 'video/mp4'
    else if (decodedPath.match(/\.webm$/i)) mimeType = 'video/webm'
    else if (decodedPath.match(/\.ogv$/i)) mimeType = 'video/ogg'
    else if (decodedPath.match(/\.mov$/i)) mimeType = 'video/quicktime'
    else if (decodedPath.match(/\.mkv$/i)) mimeType = 'video/x-matroska'
    else if (decodedPath.match(/\.avi$/i)) mimeType = 'video/x-msvideo'
    // Audio
    else if (decodedPath.match(/\.mp3$/i)) mimeType = 'audio/mpeg'
    else if (decodedPath.match(/\.wav$/i)) mimeType = 'audio/wav'
    else if (decodedPath.match(/\.ogg$/i)) mimeType = 'audio/ogg'
    else if (decodedPath.match(/\.aac$/i)) mimeType = 'audio/aac'
    else if (decodedPath.match(/\.flac$/i)) mimeType = 'audio/flac'
    else if (decodedPath.match(/\.m4a$/i)) mimeType = 'audio/mp4'
    else if (decodedPath.match(/\.wma$/i)) mimeType = 'audio/x-ms-wma'
  } else if (fileId) {
    // Get file info by file ID
    const treeService = await getTreeFileSystemService()
    await treeService.reloadMetadata()

    const file = await treeService.getFileById(fileId)

    if (!file) {
      throw createError({ statusCode: 404, statusMessage: 'File not found' })
    }

    filePath = resolveSafePath(file.path)
    mimeType = file.mimeType || 'application/octet-stream'
  } else {
    throw createError({ statusCode: 400, statusMessage: 'File ID or path is required' })
  }

  try {
    const content = await readFile(filePath)

    // Set Content-Type based on file type
    event.node.res.setHeader('Content-Type', mimeType)

    // Set inline display for previewable file types
    const previewableTypes = [
      'application/pdf',
      'text/plain',
      'text/html',
      'text/css',
      'text/javascript',
      'application/json',
      'text/markdown',
      // Images
      'image/png',
      'image/jpeg',
      'image/gif',
      'image/webp',
      'image/svg+xml',
      'image/bmp',
      'image/x-icon',
      // Video
      'video/mp4',
      'video/webm',
      'video/ogg',
      'video/quicktime',
      'video/x-matroska',
      'video/x-msvideo',
      // Audio
      'audio/mpeg',
      'audio/wav',
      'audio/ogg',
      'audio/aac',
      'audio/flac',
      'audio/mp4',
      'audio/x-ms-wma'
    ]

    if (previewableTypes.includes(mimeType)) {
      event.node.res.setHeader('Content-Disposition', 'inline')
    } else if (fileId) {
      // Only has filename when accessed by ID
      const treeService = await getTreeFileSystemService()
      await treeService.reloadMetadata()
      const file = await treeService.getFileById(fileId)
      if (file) {
        event.node.res.setHeader('Content-Disposition', `attachment; filename="${encodeURIComponent(file.name)}"`)
      }
    }

    return content
  } catch (error) {
    console.error('Error reading file:', error)
    throw createError({ statusCode: 500, statusMessage: 'Failed to read file' })
  }
})
