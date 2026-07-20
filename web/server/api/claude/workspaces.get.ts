/**
 * GET /api/claude/workspaces
 *
 * List all saved workspaces.
 */
import { listWorkspaces } from '~/server/utils/claude-workspace'

export default defineEventHandler(() => {
  const workspaces = listWorkspaces()
  return { success: true, count: workspaces.length, workspaces }
})
