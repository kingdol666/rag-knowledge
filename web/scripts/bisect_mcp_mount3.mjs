// Bisect round 3: toggle one SDK option at a time to find the mount breaker.
// Usage: node scripts/bisect_mcp_mount3.mjs <variant>
//   full      = engine replica (env + settingSources + strict + disallowed)
//   noenv     = no env override (inherit process env)
//   nosetting = no settingSources
//   nostrict  = no strictMcpConfig
//   nodisallow= no disallowedTools
import { query } from '@anthropic-ai/claude-agent-sdk'

const variant = process.argv[2] || 'full'
const KB_MCP_SERVERS = { 'kb-mcp': { type: 'sse', url: 'http://127.0.0.1:8000/sse' } }
const TOOLS = ['mcp__kb-mcp__kb_project_status']
const DISALLOWED = ['ToolSearch', 'Task', 'Agent', 'Skill', 'PowerShell', 'Bash', 'Read', 'Glob', 'Grep']

const opts = {
  cwd: 'D:\\codes\\ClaudeGPT\\rag_project\\rag-knowledge',
  permissionMode: 'default',
  maxTurns: 4,
  allowedTools: TOOLS,
  mcpServers: KB_MCP_SERVERS,
}
if (variant !== 'nosetting') opts.settingSources = ['user', 'project']
if (variant !== 'nostrict') opts.strictMcpConfig = true
if (variant !== 'nodisallow') opts.disallowedTools = DISALLOWED
if (variant !== 'noenv') {
  const env = { ...process.env }
  env.ENABLE_TOOL_SEARCH = 'false'
  env.NO_PROXY = '127.0.0.1,localhost'
  env.no_proxy = '127.0.0.1,localhost'
  env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = '0'
  opts.env = env
}

let sawTool = false
let statuses = new Set()
for await (const message of query({
  prompt: 'Call the tool mcp__kb-mcp__kb_project_status now, then reply with its summary field verbatim.',
  options: opts,
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
console.log(`${variant}: kbToolCalled=${sawTool} mcpStatus={[${[...statuses].join(' | ')}]}`)
