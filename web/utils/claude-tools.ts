/**
 * Claude Code built-in tool catalog (static descriptions) + attachment utility functions.
 *
 * Tool names sourced from @anthropic-ai/claude-agent-sdk/sdk-tools.d.ts ToolInputSchemas.
 * Descriptions synthesized from Claude Code official docs, used by the frontend tool panel.
 * MCP tools (mcp__server__tool) and Skills (/skill-name) come from SDK init messages, merged dynamically.
 */

export interface ToolCatalogEntry {
  name: string
  category: '文件' | '执行' | '搜索' | '网络' | '任务' | '交互' | 'MCP' | '其他'
  description: string
  icon?: string
}

/** Full set of Claude Code SDK built-in tools (from sdk-tools.d.ts) */
export const BUILT_IN_TOOLS: ToolCatalogEntry[] = [
  // Files
  { name: 'Read', category: '文件', description: '读取文件内容（支持图片/PDF/Office 自动识别）', icon: '📖' },
  { name: 'Write', category: '文件', description: '创建或覆写文件', icon: '✏️' },
  { name: 'Edit', category: '文件', description: '字符串精确替换编辑（首选，非整文件覆写）', icon: '🔧' },
  { name: 'NotebookEdit', category: '文件', description: '编辑 Jupyter Notebook 单元格', icon: '📓' },

  // Execution
  { name: 'Bash', category: '执行', description: '执行 shell 命令（受权限模式管控）', icon: '⚡' },
  { name: 'REPL', category: '执行', description: 'Python 交互式代码执行环境', icon: '🐍' },

  // Search
  { name: 'Glob', category: '搜索', description: '按文件名模式匹配查找文件', icon: '🔍' },
  { name: 'Grep', category: '搜索', description: '按内容正则搜索文件', icon: '🔎' },

  // Network
  { name: 'WebSearch', category: '网络', description: '实时网络搜索', icon: '🌐' },
  { name: 'WebFetch', category: '网络', description: '抓取指定 URL 内容', icon: '🔗' },

  // Tasks
  { name: 'Agent', category: '任务', description: '启动子 Agent（并行/专项任务）', icon: '🤖' },
  { name: 'Task', category: '任务', description: '后台任务管理', icon: '📋' },
  { name: 'TaskCreate', category: '任务', description: '创建后台任务', icon: '➕' },
  { name: 'TaskUpdate', category: '任务', description: '更新后台任务状态', icon: '🔄' },
  { name: 'TaskGet', category: '任务', description: '查询任务详情', icon: '👀' },
  { name: 'TaskList', category: '任务', description: '列出所有任务', icon: '📊' },
  { name: 'TaskOutput', category: '任务', description: '读取任务输出', icon: '📤' },
  { name: 'TaskStop', category: '任务', description: '停止任务', icon: '⏹️' },
  { name: 'TodoWrite', category: '任务', description: '写入任务清单（计划跟踪）', icon: '✅' },
  { name: 'Workflow', category: '任务', description: '动态工作流编排', icon: '⚙️' },
  { name: 'Monitor', category: '任务', description: '实时监控任务', icon: '📡' },
  { name: 'ExitPlanMode', category: '任务', description: '退出计划模式（提交方案）', icon: '🎯' },
  { name: 'EnterPlanMode', category: '任务', description: '进入计划模式（只读探索）', icon: '📝' },
  { name: 'EnterWorktree', category: '任务', description: '创建 git worktree 隔离环境', icon: '🌳' },
  { name: 'ExitWorktree', category: '任务', description: '退出 worktree', icon: '🚪' },
  { name: 'ReportFindings', category: '任务', description: '汇报探索发现', icon: '📈' },
  { name: 'Projects', category: '任务', description: '项目列表与切换', icon: '📁' },

  // Interaction
  { name: 'AskUserQuestion', category: '交互', description: '向用户提问（选项式）', icon: '❓' },
  { name: 'PushNotification', category: '交互', description: '推送系统通知', icon: '🔔' },

  // Other
  { name: 'CronCreate', category: '其他', description: '创建定时任务', icon: '⏰' },
  { name: 'CronList', category: '其他', description: '列出定时任务', icon: '📅' },
  { name: 'CronDelete', category: '其他', description: '删除定时任务', icon: '🗑️' },
  { name: 'ScheduleWakeup', category: '其他', description: '调度唤醒', icon: '⏲️' },
  { name: 'Artifact', category: '其他', description: '创建/管理 Artifact', icon: '🎨' },
  { name: 'ClaudeDesign', category: '其他', description: 'Pencil 设计文件操作', icon: '✨' },
  { name: 'ReadMcpResource', category: 'MCP', description: '读取 MCP 资源', icon: '🔌' },
  { name: 'ReadMcpResourceDir', category: 'MCP', description: '列出 MCP 资源目录', icon: '🔌' },
  { name: 'ListMcpResources', category: 'MCP', description: '列出所有 MCP 资源', icon: '🔌' },
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
export const TOOL_CATEGORY_ORDER = ['文件', '执行', '搜索', '网络', '任务', '交互', 'MCP', '其他']

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
  if (att.isImage) return '图片'
  if (att.isPdf) return 'PDF'
  if (att.isText) return '文本'
  return '文件'
}
