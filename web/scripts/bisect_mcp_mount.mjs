// Bisect the a2-arm MCP mount failure (2026-09-30).
// Reproduces the exact engine.query options in 4 variants and prints the
// SDK init message's mcp_servers status + tool count for each.
import { query } from '@anthropic-ai/claude-agent-sdk'

const KB_MCP_SERVERS = { 'kb-mcp': { type: 'sse', url: 'http://127.0.0.1:8000/sse' } }
const KB_RETRIEVAL_TOOLS = [
  'mcp__kb-mcp__kb_list', 'mcp__kb-mcp__kb_search', 'mcp__kb-mcp__kb_search_vector',
  'mcp__kb-mcp__kb_search_two_stage', 'mcp__kb-mcp__kb_doc_read',
  'mcp__kb-mcp__kb_get_documents', 'mcp__kb-mcp__kb_laya_judge']
const PLUGIN_NAMES = KB_RETRIEVAL_TOOLS.map(t => t.replace('mcp__kb-mcp__', 'mcp__plugin_rag-knowledge_kb-mcp__'))
const DISALLOWED = ['ToolSearch', 'Task', 'Agent', 'Skill', 'PowerShell', 'Bash', 'Read', 'Glob', 'Grep']

const baseEnv = {
  ...process.env,
  ENABLE_TOOL_SEARCH: 'false',
  NO_PROXY: '127.0.0.1,localhost',
  no_proxy: '127.0.0.1,localhost',
  CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: '0',
}

const VARIANTS = {
  'V1_full_a2_replica': { allowedTools: [...KB_RETRIEVAL_TOOLS, ...PLUGIN_NAMES], disallowedTools: DISALLOWED },
  'V2_no_plugin_names': { allowedTools: [...KB_RETRIEVAL_TOOLS], disallowedTools: DISALLOWED },
  'V3_no_disallowed': { allowedTools: [...KB_RETRIEVAL_TOOLS, ...PLUGIN_NAMES], disallowedTools: undefined },
}

const prompt = 'Reply with the single word OK and nothing else.'
for (const [name, v] of Object.entries(VARIANTS)) {
  const opts = {
    prompt,
    options: {
      cwd: 'D:\\codes\\ClaudeGPT\\rag_project\\rag-knowledge',
      permissionMode: 'default',
      maxTurns: 2,
      settingSources: ['user', 'project'],
      allowedTools: v.allowedTools,
      ...(v.disallowedTools ? { disallowedTools: v.disallowedTools } : {}),
      mcpServers: KB_MCP_SERVERS,
      strictMcpConfig: true,
      env: baseEnv,
    },
  }
  let out = ''
  try {
    for await (const message of query(opts)) {
      if (message.type === 'system' && message.subtype === 'init') {
        const ms = (message.mcp_servers || []).map(s => `${s.name}:${s.status}`).join(',')
        out = `mcp=[${ms}] tools=${(message.tools || []).length} kbTools=${(message.tools || []).filter(t => t.includes('kb_')).length}`
        break
      }
    }
  } catch (e) {
    out = `ERROR ${e.message?.slice(0, 120)}`
  }
  console.log(`${name}: ${out}`)
}
