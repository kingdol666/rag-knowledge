// Bisect round 4: find which disallowedTools entry kills MCP mounting.
// Usage: node scripts/bisect_mcp_mount4.mjs <listName>
import { query } from '@anthropic-ai/claude-agent-sdk'

const KB_MCP_SERVERS = { 'kb-mcp': { type: 'sse', url: 'http://127.0.0.1:8000/sse' } }
const TOOLS = ['mcp__kb-mcp__kb_project_status']
const LISTS = {
  toolsearch_only: ['ToolSearch'],
  full_engine: ['ToolSearch', 'Task', 'Agent', 'Skill', 'PowerShell',
    'SendMessage', 'SendMessageToAgent', 'AgentMessage',
    'TaskOutput', 'TaskUpdate', 'TaskGet', 'TaskList', 'TaskStop',
    'TaskCreate', 'Workflow', 'EndConversation',
    'ReadMcpResourceTool', 'ReadMcpResourceDirTool', 'ListMcpResourcesTool',
    'EnterWorktree', 'Bash', 'Edit', 'Write', 'NotebookEdit',
    'Read', 'Glob', 'Grep',
    'WebSearch', 'WebFetch', 'WebFetchDomain',
    'AskUserQuestion', 'EnterPlanMode', 'ExitPlanMode',
    'TodoWrite', 'TodoRead', 'CronCreate', 'CronDelete',
    'CronList', 'CronUpdate', 'DesignSync'],
  ts_task_mcpres: ['ToolSearch', 'Task', 'ReadMcpResourceTool', 'ReadMcpResourceDirTool', 'ListMcpResourcesTool'],
  ts_task_endconv: ['ToolSearch', 'Task', 'EndConversation'],
  ts_task: ['ToolSearch', 'Task'],
  ts_agent: ['ToolSearch', 'Agent'],
  task_only: ['Task'],
  agent_only: ['Agent'],
  core5: ['ToolSearch', 'Task', 'Agent', 'Skill', 'PowerShell'],
  filetools: ['Bash', 'Edit', 'Write', 'NotebookEdit', 'Read', 'Glob', 'Grep'],
  webtools: ['WebSearch', 'WebFetch', 'WebFetchDomain'],
  misctools: ['AskUserQuestion', 'EnterPlanMode', 'ExitPlanMode', 'TodoWrite', 'TodoRead'],
  taskfam: ['SendMessage', 'SendMessageToAgent', 'AgentMessage', 'TaskOutput', 'TaskUpdate',
            'TaskGet', 'TaskList', 'TaskStop', 'TaskCreate', 'Workflow', 'EndConversation'],
}
const listName = process.argv[2] || 'toolsearch_only'

const env = { ...process.env }
env.ENABLE_TOOL_SEARCH = 'false'
env.NO_PROXY = '127.0.0.1,localhost'
env.no_proxy = '127.0.0.1,localhost'
env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = '0'

let sawTool = false
const statuses = new Set()
for await (const message of query({
  prompt: 'Call the tool mcp__kb-mcp__kb_project_status now, then reply with its summary field verbatim.',
  options: {
    cwd: 'D:\\codes\\ClaudeGPT\\rag_project\\rag-knowledge',
    permissionMode: 'default',
    maxTurns: 4,
    settingSources: ['user', 'project'],
    allowedTools: TOOLS,
    disallowedTools: LISTS[listName],
    mcpServers: KB_MCP_SERVERS,
    strictMcpConfig: true,
    env,
  },
})) {
  if (message.type === 'system' && (message.mcp_servers || []).length) {
    statuses.add(message.mcp_servers.map(s => `${s.name}:${s.status}`).join(','))
  }
  if (message.type === 'assistant') {
    for (const b of (message.message?.content || [])) {
      if (b.type === 'tool_use' && String(b.name).startsWith('mcp__')) sawTool = true
    }
  }
  if (message.type === 'result') break
}
console.log(`${listName}: kbToolCalled=${sawTool} mcpStatus={[${[...statuses].join(' | ')}]}`)
