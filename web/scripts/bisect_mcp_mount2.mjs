// Bisect round 2: force a real tool call and stream ALL system messages.
// V-A: env as inherited (proxy vars + NO_PROXY)  V-B: proxy vars stripped.
import { query } from '@anthropic-ai/claude-agent-sdk'

const KB_MCP_SERVERS = { 'kb-mcp': { type: 'sse', url: 'http://127.0.0.1:8000/sse' } }
const TOOLS = [
  'mcp__kb-mcp__kb_list', 'mcp__kb-mcp__kb_search', 'mcp__kb-mcp__kb_search_vector',
  'mcp__kb-mcp__kb_search_two_stage', 'mcp__kb-mcp__kb_doc_read',
  'mcp__kb-mcp__kb_get_documents', 'mcp__kb-mcp__kb_laya_judge',
  'mcp__kb-mcp__kb_project_status', 'mcp__kb-mcp__backend_status']
const DISALLOWED = ['ToolSearch', 'Task', 'Agent', 'Skill', 'PowerShell', 'Bash', 'Read', 'Glob', 'Grep']

function mkEnv(stripProxy) {
  const env = { ...process.env }
  if (stripProxy) {
    for (const k of Object.keys(env)) {
      if (/proxy/i.test(k)) delete env[k]
    }
  } else {
    env.NO_PROXY = '127.0.0.1,localhost'
    env.no_proxy = '127.0.0.1,localhost'
  }
  env.ENABLE_TOOL_SEARCH = 'false'
  env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = '0'
  return env
}

async function run(name, stripProxy) {
  const t0 = Date.now()
  let sawTool = false
  const mcpStatus = new Set()
  try {
    for await (const message of query({
      prompt: 'Call the tool mcp__kb-mcp__kb_project_status now (no arguments needed), then reply with its summary field verbatim.',
      options: {
        cwd: 'D:\\codes\\ClaudeGPT\\rag_project\\rag-knowledge',
        permissionMode: 'default',
        maxTurns: 6,
        settingSources: ['user', 'project'],
        allowedTools: TOOLS,
        disallowedTools: DISALLOWED,
        mcpServers: KB_MCP_SERVERS,
        strictMcpConfig: true,
        env: mkEnv(stripProxy),
      },
    })) {
      if (message.type === 'system') {
        const ms = message.mcp_servers || []
        if (ms.length) mcpStatus.add(ms.map(s => `${s.name}:${s.status}`).join(','))
      }
      if (message.type === 'assistant') {
        const blocks = message.message?.content || []
        for (const b of blocks) {
          if (b.type === 'tool_use' && String(b.name).startsWith('mcp__kb-mcp__')) sawTool = true
        }
      }
      if (message.type === 'result') break
    }
  } catch (e) {
    console.log(`${name}: ERROR ${String(e.message).slice(0, 120)}`)
    return
  }
  console.log(`${name}: kbToolCalled=${sawTool} mcpStatus={[${[...mcpStatus].join(' | ')}]} wall=${((Date.now() - t0) / 1000).toFixed(1)}s`)
}

await run('V-A env+NO_PROXY    ', false)
await run('V-B env-stripped    ', true)
