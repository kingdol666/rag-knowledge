/**
 * POST /api/claude/workspaces/validate
 *
 * Validate whether a directory path is valid (no save, just probe).
 * Request body: { path }
 *
 * Used by the frontend directory picker for instant feedback.
 */
import { validatePath } from '~/server/utils/claude-workspace'

interface ValidateBody { path?: string }

export default defineEventHandler(async (event) => {
  const body = await readBody<ValidateBody>(event)
  const p = body?.path?.trim()
  if (!p) {
    throw createError({ statusCode: 400, statusMessage: 'path 必填' })
  }
  return { success: true, ...validatePath(p), path: p }
})
