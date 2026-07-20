import { defineEventHandler, readBody } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'
import type { CreateFolderRequest, CreateFileRequest } from '~/types/tree-file-system'

export default defineEventHandler(async (event) => {
  const method = event.method
  const treeService = await getTreeFileSystemService()

  // Reload metadata before each request
  await treeService.reloadMetadata()

  const body = await readBody(event)

  if (method === 'POST') {
    const { type, ...data } = body

    if (type === 'folder') {
      const request: CreateFolderRequest = {
        name: data.name,
        parentId: data.parentId,
        description: data.description,
        isKnowledgeBase: data.isKnowledgeBase
      }
      return await treeService.createFolder(request)
    }

    if (type === 'file') {
      const request: CreateFileRequest = {
        name: data.name,
        parentId: data.parentId,
        fileType: data.fileType,
        mimeType: data.mimeType,
        fileSize: data.fileSize,
        metadata: data.metadata
      }
      return await treeService.createFile(request)
    }

    return { error: 'Invalid type. Use "folder" or "file"' }
  }

  return { error: 'Invalid method' }
})
