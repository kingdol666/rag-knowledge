// Bisect round 5: canUseTool x allowedTools-list content matrix.
// Usage: node scripts/bisect_mcp_mount5.mjs <m1|m2|m3|m4>
import { query } from '@anthropic-ai/claude-agent-sdk'

const KB_MCP_SERVERS = { 'kb-mcp': { type: 'sse', url: 'http://127.0.0.1:8000/sse' } }
const KB_LIST = ['mcp__kb-mcp__kb_list', 'mcp__kb-mcp__kb_search', 'mcp__kb-mcp__kb_search_vector',
  'mcp__kb-mcp__kb_search_two_stage', 'mcp__kb-mcp__kb_search_stats', 'mcp__kb-mcp__kb_doc_read',
  'mcp__kb-mcp__kb_get_documents', 'mcp__kb-mcp__kb_doc_get_by_tag', 'mcp__kb-mcp__kb_graph_stats',
  'mcp__kb-mcp__kb_graph_search', 'mcp__kb-mcp__kb_project_status', 'mcp__kb-mcp__backend_status']
const A2_LIST = [...KB_LIST, ...KB_LIST.map(t => t.replace('mcp__kb-mcp__', 'mcp__plugin_rag-knowledge_kb-mcp__'))]
const FULL_ENGINE = ['ToolSearch', 'Task', 'Agent', 'Skill', 'PowerShell',
  'SendMessage', 'SendMessageToAgent', 'AgentMessage', 'TaskOutput', 'TaskUpdate',
  'TaskGet', 'TaskList', 'TaskStop', 'TaskCreate', 'Workflow', 'EndConversation',
  'ReadMcpResourceTool', 'ReadMcpResourceDirTool', 'ListMcpResourcesTool',
  'EnterWorktree', 'Bash', 'Edit', 'Write', 'NotebookEdit', 'Read', 'Glob', 'Grep',
  'WebSearch', 'WebFetch', 'WebFetchDomain', 'AskUserQuestion', 'EnterPlanMode',
  'ExitPlanMode', 'TodoWrite', 'TodoRead', 'CronCreate', 'CronDelete', 'CronList',
  'CronUpdate', 'DesignSync']
const TS_TASK = ['ToolSearch', 'Task']

const VARIANT = {
  m1: { canUse: true, dis: FULL_ENGINE, tools: A2_LIST },
  m2: { canUse: true, dis: FULL_ENGINE, tools: KB_LIST },
  m3: { canUse: false, dis: FULL_ENGINE, tools: KB_LIST },
  m4: { canUse: true, dis: TS_TASK, tools: KB_LIST },
}[process.argv[2] || 'm1']

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
    allowedTools: VARIANT.tools,
    disallowedTools: VARIANT.dis,
    mcpServers: KB_MCP_SERVERS,
    strictMcpConfig: true,
    env,
    ...(VARIANT.canUse ? {
      canUseTool: async (toolName) => ({ behavior: 'allow' }),
    } : {}),
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
console.log(`${process.argv[2]}: kbToolCalled=${sawTool} mcpStatus={[${[...statuses].join(' | ')}]}`)
