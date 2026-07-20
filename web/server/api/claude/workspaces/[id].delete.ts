/**
 * DELETE /api/claude/workspaces/[id]
 *
 * Delete a specific workspace.
 */
import { deleteWorkspace } from '~/server/utils/claude-workspace'

export default defineEventHandler((event) => {
  const id = parseInt(getRouterParam(event, 'id') || '')
  if (isNaN(id)) {
    throw createError({ statusCode: 400, statusMessage: 'id 必须为数字' })
  }
  const ok = deleteWorkspace(id)
  if (!ok) {
    throw createError({ statusCode: 404, statusMessage: '工作区不存在' })
  }
  return { success: true, deleted: id }
})
