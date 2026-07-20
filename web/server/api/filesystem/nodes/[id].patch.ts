import { defineEventHandler, readBody } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'
import type { UpdateFolderRequest, UpdateFileRequest } from '~/types/tree-file-system'

export default defineEventHandler(async (event) => {
  const method = event.method
  const id = event.context.params?.id
  const body = await readBody(event)
  const treeService = await getTreeFileSystemService()

  // Reload metadata before each request
  await treeService.reloadMetadata()

  if (!id) {
    return { error: 'ID is required' }
  }

  if (method === 'PATCH') {
    const node = await treeService.getNodeById(id)

    if (!node) {
      return { error: 'Node not found' }
    }

    if (node.type === 'folder') {
      const request: UpdateFolderRequest = {
        name: body.name,
        description: body.description
      }
      return await treeService.updateFolder(id, request)
   } else {
     const request: UpdateFileRequest = {
       name: body.name,
       description: body.description,
       metadata: body.metadata
     }
     return await treeService.updateFile(id, request)
    }
  }

  return { error: 'Invalid method' }
})
