/**
 * POST /api/claude/workspaces
 *
 * Add/update a workspace.
 * Request body: { name, path, description?, pin_order? }
 */
import { upsertWorkspace, validatePath } from '~/server/utils/claude-workspace'

interface WorkspaceBody {
  name?: string
  path?: string
  description?: string
  pin_order?: number | null
}

export default defineEventHandler(async (event) => {
  const body = await readBody<WorkspaceBody>(event)
  const { name, path, description, pin_order } = body || {}

  if (!name || !name.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'name 必填' })
  }
  if (!path || !path.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'path 必填' })
  }

  // Validate path validity
  const validation = validatePath(path.trim())
  if (!validation.valid) {
    throw createError({ statusCode: 400, statusMessage: `路径无效: ${validation.error}` })
  }
  if (!validation.isDirectory) {
    throw createError({ statusCode: 400, statusMessage: '路径必须是一个目录' })
  }

  const ws = upsertWorkspace({
    name: name.trim(),
    path: path.trim(),
    description: description?.trim(),
    pin_order: pin_order ?? undefined,
  })

  return { success: true, workspace: ws }
})
