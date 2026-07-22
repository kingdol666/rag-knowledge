import { defineEventHandler, getQuery, readBody } from 'h3'
import { getTagManagementService } from '~/server/services/tag-management-service'

/** DELETE /api/kb/tags — remove tag(s) from the registry.
 *  Body/query:
 *    tag=xxx                — remove a single tag
 *    cleanup_orphans=true   — remove ALL orphan (unreferenced) + garbage tags */
export default defineEventHandler(async (event) => {
  const service = getTagManagementService()
  const query = getQuery(event)

  // K3 fix: bulk orphan + garbage cleanup
  if (query.cleanup_orphans === 'true' || query.cleanup_orphans === '1') {
    const result = await service.removeOrphanTags()
    return {
      success: true,
      removed: result.removed,
      removed_count: result.removed.length,
      kept: result.kept,
      kept_count: result.kept.length,
    }
  }

  // Single tag removal (from body or query)
  let tag = (query.tag as string) || ''
  if (!tag) {
    try {
      const body = await readBody(event)
      tag = body?.tag || ''
    } catch { /* no body */ }
  }

  if (!tag) {
    return { success: false, error: 'tag is required (query ?tag= or body {tag})', status: 400 }
  }

  await service.removeTag(tag)
  return { success: true, removed: tag }
})
