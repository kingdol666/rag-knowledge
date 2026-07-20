import { defineEventHandler, getQuery } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'

export default defineEventHandler(async (event) => {
  const method = event.method
  const treeService = await getTreeFileSystemService()

  // Reload metadata before each request
  await treeService.reloadMetadata()

  if (method === 'GET') {
    const query = getQuery(event)

    if (query.action === 'children') {
      const parentId = query.parentId as string | null
      return await treeService.getChildren(parentId || null)
    }

    if (query.action === 'node' && query.id) {
      return await treeService.getNodeById(query.id as string)
    }

    if (query.action === 'count') {
      return {
        folders: await treeService.getFolderCount(),
        files: await treeService.getFileCount(),
        total: await treeService.getTotalCount()
      }
    }

    return await treeService.getTree()
  }

  return { error: 'Invalid action' }
})
