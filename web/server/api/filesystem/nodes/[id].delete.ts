import { defineEventHandler } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'

export default defineEventHandler(async (event) => {
  const method = event.method
  const id = event.context.params?.id
  const treeService = await getTreeFileSystemService()

  // Reload metadata before each request
  await treeService.reloadMetadata()

  if (!id) {
    return { error: 'ID is required' }
  }

  if (method === 'DELETE') {
    const node = await treeService.getNodeById(id)
    
    if (!node) {
      return { error: 'Node not found' }
    }

    if (node.type === 'folder') {
      return await treeService.deleteFolder(id)
    } else {
      return await treeService.deleteFile(id)
    }
  }

  return { error: 'Invalid method' }
})
