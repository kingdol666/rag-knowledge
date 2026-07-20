import { defineEventHandler } from 'h3'
import { getTagManagementService } from '~/server/services/tag-management-service'

/** GET /api/kb/tags — list all registered tags. */
export default defineEventHandler(async (event) => {
  const service = getTagManagementService()
  const tags = await service.listTags()
  return { success: true, tags, count: tags.length }
})