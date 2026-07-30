/**
 * Claude Code built-in tool catalog (static descriptions) + attachment utility functions.
 *
 * Tool names sourced from @anthropic-ai/claude-agent-sdk/sdk-tools.d.ts ToolInputSchemas.
 * Descriptions synthesized from Claude Code official docs, used by the frontend tool panel.
 * MCP tools (mcp__server__tool) and Skills (/skill-name) come from SDK init messages, merged dynamically.
 */

export interface ToolCatalogEntry {
  name: string
  category: 'File' | 'Execute' | 'Search' | 'Network' | 'Task' | 'Interaction' | 'MCP' | 'Other'
  description: string
  icon?: string
}

/** Full set of Claude Code SDK built-in tools (from sdk-tools.d.ts) */
export const BUILT_IN_TOOLS: ToolCatalogEntry[] = [
  // Files
  { name: 'Read', category: 'File', description: 'Read file content (auto-detect images/PDF/Office)', icon: '📖' },
  { name: 'Write', category: 'File', description: 'Create or overwrite files', icon: '✏️' },
  { name: 'Edit', category: 'File', description: 'String-precise replace editing (preferred, not full-file overwrite)', icon: '🔧' },
  { name: 'NotebookEdit', category: 'File', description: 'Edit Jupyter Notebook cells', icon: '📓' },

  // Execution
  { name: 'Bash', category: 'Execute', description: 'Execute shell commands (governed by permission mode)', icon: '⚡' },
  { name: 'REPL', category: 'Execute', description: 'Python interactive code execution environment', icon: '🐍' },

  // Search
  { name: 'Glob', category: 'Search', description: 'Pattern-match files by name', icon: '🔍' },
  { name: 'Grep', category: 'Search', description: 'Regex search file content', icon: '🔎' },

  // Network
  { name: 'WebSearch', category: 'Network', description: 'Real-time web search', icon: '🌐' },
  { name: 'WebFetch', category: 'Network', description: 'Fetch content from URL', icon: '🔗' },

  // Tasks
  { name: 'Agent', category: 'Task', description: 'Launch sub Agent (parallel/specialized tasks)', icon: '🤖' },
  { name: 'Task', category: 'Task', description: 'Background task management', icon: '📋' },
  { name: 'TaskCreate', category: 'Task', description: 'Create background task', icon: '➕' },
  { name: 'TaskUpdate', category: 'Task', description: 'Update background task status', icon: '🔄' },
  { name: 'TaskGet', category: 'Task', description: 'Query task details', icon: '👀' },
  { name: 'TaskList', category: 'Task', description: 'List all tasks', icon: '📊' },
  { name: 'TaskOutput', category: 'Task', description: 'Read task output', icon: '📤' },
  { name: 'TaskStop', category: 'Task', description: 'Stop task', icon: '⏹️' },
  { name: 'TodoWrite', category: 'Task', description: 'Write task list (plan tracking)', icon: '✅' },
  { name: 'Workflow', category: 'Task', description: 'Dynamic workflow orchestration', icon: '⚙️' },
  { name: 'Monitor', category: 'Task', description: 'Real-time task monitoring', icon: '📡' },
  { name: 'ExitPlanMode', category: 'Task', description: 'Exit plan mode (submit proposal)', icon: '🎯' },
  { name: 'EnterPlanMode', category: 'Task', description: 'Enter plan mode (read-only exploration)', icon: '📝' },
  { name: 'EnterWorktree', category: 'Task', description: 'Create git worktree isolated environment', icon: '🌳' },
  { name: 'ExitWorktree', category: 'Task', description: 'Exit worktree', icon: '🚪' },
  { name: 'ReportFindings', category: 'Task', description: 'Report exploration findings', icon: '📈' },
  { name: 'Projects', category: 'Task', description: 'Project list and switching', icon: '📁' },

  // Interaction
  { name: 'AskUserQuestion', category: 'Interaction', description: 'Ask user a question (multiple choice)', icon: '❓' },
  { name: 'PushNotification', category: 'Interaction', description: 'Push system notification', icon: '🔔' },

  // Other
  { name: 'CronCreate', category: 'Other', description: 'Create scheduled task', icon: '⏰' },
  { name: 'CronList', category: 'Other', description: 'List scheduled tasks', icon: '📅' },
  { name: 'CronDelete', category: 'Other', description: 'Delete scheduled task', icon: '🗑️' },
  { name: 'ScheduleWakeup', category: 'Other', description: 'Schedule wakeup', icon: '⏲️' },
  { name: 'Artifact', category: 'Other', description: 'Create/manage artifacts', icon: '🎨' },
  { name: 'ClaudeDesign', category: 'Other', description: 'Pencil design file operations', icon: '✨' },
  { name: 'ReadMcpResource', category: 'MCP', description: 'Read MCP resource', icon: '🔌' },
  { name: 'ReadMcpResourceDir', category: 'MCP', description: 'List MCP resource directory', icon: '🔌' },
  { name: 'ListMcpResources', category: 'MCP', description: 'List all MCP resources', icon: '🔌' },
]

/** Grouped by category */
export const TOOLS_BY_CATEGORY: Record<string, ToolCatalogEntry[]> = BUILT_IN_TOOLS.reduce(
  (acc, tool) => {
    if (!acc[tool.category]) acc[tool.category] = []
    acc[tool.category].push(tool)
    return acc
  },
  {} as Record<string, ToolCatalogEntry[]>,
)

/** Tool category display order */
export const TOOL_CATEGORY_ORDER = ['File', 'Execute', 'Search', 'Network', 'Task', 'Interaction', 'MCP', 'Other']

// ══════ Attachment utility functions ══════

export interface Attachment {
  id: string
  name: string
  path: string
  size: number
  mime: string
  isImage: boolean
  isText: boolean
  isPdf: boolean
}

/** Format file size */
export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** Attachment type icon */
export function attachmentIcon(att: Attachment): string {
  if (att.isImage) return '🖼️'
  if (att.isPdf) return '📄'
  if (att.isText) return '📝'
  return '📎'
}

/** Attachment type label */
export function attachmentTypeLabel(att: Attachment): string {
  if (att.isImage) return 'Image'
  if (att.isPdf) return 'PDF'
  if (att.isText) return 'Text'
  return 'File'
}
