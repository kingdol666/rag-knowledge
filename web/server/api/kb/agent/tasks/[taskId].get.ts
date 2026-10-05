/**
 * GET /api/kb/agent/tasks/:taskId
 *
 * The async callback surface of POST /api/kb/agent/chat (mode:"async"):
 * returns the task-scoped response — status while running, the full chat
 * envelope once the background turn settles (completed / failed).
 *
 * Auth: global web token middleware (Bearer), same as every /api/* route.
 */
import { defineEventHandler, createError, getRouterParam } from 'h3'
import { getTask } from '~/server/utils/agent-task-registry'

export default defineEventHandler(async (event) => {
  const taskId = String(getRouterParam(event, 'taskId') || '').trim()
  if (!taskId) {
    throw createError({ statusCode: 400, statusMessage: 'taskId 必填' })
  }

  const rec = getTask(taskId)
  if (!rec) {
    throw createError({
      statusCode: 404,
      statusMessage: `task not found: ${taskId}（不存在、已过期(2h) 或服务已重启）`,
    })
  }

  return {
    success: true as const,
    task_id: rec.task_id,
    status: rec.status,
    mode: rec.mode,
    prompt: rec.prompt,
    engine: rec.engine,
    permission: rec.permission,
    created_at: rec.created_at,
    finished_at: rec.finished_at ?? null,
    // null while running; the chat envelope (reply / partial_text / tools_used
    // / duration_ms / ...) once completed or failed.
    result: rec.result ?? null,
  }
})
