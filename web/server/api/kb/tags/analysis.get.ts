import { defineEventHandler } from 'h3'
import { getTagManagementService } from '~/server/services/tag-management-service'

/** GET /api/kb/tags/analysis — one-pass orphan analysis (dry-run).
 *
 * Scans all .knowledge-base.yml ONCE via getTagReferenceCounts, then
 * classifies every registry tag into referenced / orphan.
 * Replaces the MCP layer's O(N×M) pattern of N concurrent HTTP probes
 * to /api/kb/documents/by-tag (one per tag), which reliably exceeded
 * the 30s MCP tool timeout at ~150 tags × 31 KBs. */
export default defineEventHandler(async () => {
  const service = getTagManagementService()
  const analysis = await service.analyzeTags()
  return {
    success: true,
    total_tags: analysis.total,
    referenced: analysis.referenced,
    orphan_tags: analysis.orphan,
    orphan: analysis.orphan.length,
    referenced_count: analysis.referenced.length,
  }
})
