import { defineEventHandler, getQuery } from 'h3'
import { getTagManagementService } from '~/server/services/tag-management-service'

/** GET /api/kb/tags — list all registered tags.
 *  Query params:
 *    live=true            — rebuild from documents before listing (orphan removal + garbage filter)
 *    include_garbage=true — include test-residue/heading tags (admin/debug only) */
export default defineEventHandler(async (event) => {
  const service = getTagManagementService()
  const query = getQuery(event)

  // K3 fix: live rebuild purges orphan/test-residue tags from the registry
  if (query.live === 'true' || query.live === '1') {
    await service.rebuildTags()
  }

  const tags = await service.listTags({
    includeGarbage: query.include_garbage === 'true' || query.include_garbage === '1',
  })
  return { success: true, tags, count: tags.length }
})
