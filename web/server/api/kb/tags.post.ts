import { defineEventHandler, readBody, createError } from 'h3'
import { getTagManagementService } from '~/server/services/tag-management-service'

/** POST /api/kb/tags — register a new tag. */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const tag = (body?.tag as string || '').trim()
  if (!tag || tag.length > 50) {
    throw createError({ statusCode: 400, statusMessage: 'tag is required (max 50 chars)' })
  }
  const service = getTagManagementService()
  await service.addTag(tag)
  return { success: true, tag }
})