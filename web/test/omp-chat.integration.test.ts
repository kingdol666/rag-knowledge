// @ts-nocheck -- Bun supplies test globals; the web tsc configuration targets Nuxt.
import { afterAll, expect, mock, test } from 'bun:test'
import { EventEmitter } from 'events'

// Exercise both route handlers without starting a server, a child process, or
// any external service; the RPC adapter has a separate integration test.
let toolNames: string[] = []
let attempts = 0
let simulateRetryHealth = false
const originalFetch = globalThis.fetch
const requests: any[] = []
const stubEngine = {
  name: 'omp',
  async *query(req: any) {
    requests.push(req)
    attempts++
    yield { type: 'system', subtype: 'init', session_id: 'test-session' }
    for (const [index, name] of toolNames.entries()) {
      yield { type: 'assistant', message: { content: [{ type: 'tool_use', id: String(index), name }] } }
    }
    yield { type: 'result', subtype: 'success', is_error: false, result: 'answer', session_id: 'test-session' }
  },
}

mock.module('~/server/engines', () => ({
  getEngine: () => stubEngine,
  normalizeEngine: (name: string) => name || 'omp',
  getChatMeta: () => ({ permissionModes: [{ id: 'bypassPermissions' }] }),
  engineTurn: (engine: any, req: any) => engine.query(req),
}))
mock.module('~/server/utils/claude-config', () => ({ getProjectRoot: () => '.' }))
mock.module('~/server/utils/kb-instruction', () => ({
  buildKbInstruction: () => '',
  buildAgentChatPreamble: () => '',
}))
mock.module('~/server/utils/chat-db', () => ({
  upsertSession: () => {}, saveMessage: () => {}, getSessionMessages: () => [],
}))
mock.module('~/server/utils/claude-pending', () => ({
  addPending: () => {}, denyAllPending: () => {}, resolvePending: () => {},
}))

// Nuxt supplies these as server auto-imports for the chat endpoint.
Object.assign(globalThis, {
  defineEventHandler: (handler: any) => handler,
  readBody: async (event: any) => event.body,
  fetch: (url: any, ...args: any[]) => simulateRetryHealth
    ? Promise.resolve({ ok: true })
    : originalFetch(url, ...args),
  setResponseStatus: () => {},
  setResponseHeaders: () => {},
  createError: (details: any) => new Error(details.statusMessage),
})
const { default: chatHandler } = await import('../server/api/claude/chat.post')
const { default: agentHandler } = await import('../server/api/kb/agent/chat.post')
afterAll(() => { globalThis.fetch = originalFetch })

function event(body: any): any {
  return { body, node: { req: new EventEmitter(), res: { write() {}, end() {} } } }
}
function reset(names: string[]) {
  toolNames = names
  attempts = 0
  requests.length = 0
}

test('chat endpoint accepts Claude, direct OMP, and plugin OMP KB spellings', async () => {
  for (const name of [
    'mcp__kb-mcp__kb_list',
    'mcp__kb_mcp_kb_list',
    'mcp__kb_mcp_kb_mcp_kb_list',
  ]) {
    reset([name, 'mcp__other__kb_list'])
    const result = await chatHandler(event({ prompt: 'test', engine: 'omp', allowedTools: [name] }))
    expect(result.success).toBe(true)
    expect(result.toolCalls).toEqual(['mcp__kb-mcp__kb_list'])
    expect(result.toolCallCount).toBe(1)
    expect(requests[0].requireKbMcp).toBe(true)
    expect(requests[0].fullPromptText).toContain('mcp__kb_mcp_*')
    expect(attempts).toBe(1)
  }
})

test('non-KB MCP is neither counted nor mistaken for a KB mount request', async () => {
  reset(['mcp__other__kb_list', 'mcp__kb_mcp_other_kb_list'])
  const noKbRequest = await chatHandler(event({ prompt: 'test', engine: 'omp', allowedTools: ['mcp__other__kb_list'] }))
  expect(noKbRequest.success).toBe(true)
  expect(noKbRequest.toolCalls).toEqual([])
  expect(requests[0].requireKbMcp).toBe(false)
  expect(attempts).toBe(1)
})

test('KB-required chat rejects unrelated MCP calls after its retries', async () => {
  reset(['mcp__other__kb_list', 'mcp__kb_mcp_other_kb_list'])
  simulateRetryHealth = true
  try {
    const result = await chatHandler(event({ prompt: 'test', engine: 'omp', allowedTools: ['mcp__kb_mcp_kb_list'] }))
    expect(attempts).toBe(3)
    expect(result.success).toBe(false)
    expect(result.code).toBe('KB_NO_RETRIEVAL')
    expect(result.toolCalls).toEqual([])
    expect(result.toolCallCount).toBe(0)
  } finally {
    simulateRetryHealth = false
  }
})

test('agent endpoint preserves non-KB tools and normalizes direct and plugin OMP formats', async () => {
  reset(['mcp__kb_mcp_kb_mcp_kb_list', 'mcp__kb_mcp_kb_doc_read', 'mcp__kb-mcp__kb_doc_read', 'mcp__other__kb_list'])
  // h3's real readBody reads the JSON body from the simulated request.
  const agentEvent = event({})
  agentEvent.method = 'POST'
  agentEvent.node.req.method = 'POST'
  agentEvent.node.req.headers = { 'content-type': 'application/json' }
  agentEvent.node.req.body = JSON.stringify({ prompt: 'test', harness: 'omp' })
  const result = await agentHandler(agentEvent)
  expect(result.success).toBe(true)
  expect(result.tools_used).toEqual(['mcp__kb-mcp__kb_list', 'mcp__kb-mcp__kb_doc_read', 'mcp__kb-mcp__kb_doc_read', 'mcp__other__kb_list'])
  expect(requests[0].requireKbMcp).toBe(true)
})
