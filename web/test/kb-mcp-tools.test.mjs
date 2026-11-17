import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { stripTypeScriptTypes } from 'node:module'
import test from 'node:test'

const source = readFileSync(new URL('../server/utils/kb-mcp-tools.ts', import.meta.url), 'utf8')
const runtime = await import(`data:text/javascript;base64,${Buffer.from(stripTypeScriptTypes(source)).toString('base64')}`)

const { evaluateKbRetrieval, filterKbMcpTools, isKbMcpTool, normalizeKbMcpToolName, requestsKbMcp } = runtime

test('accepts Claude and both OMP kb-mcp tool name formats', () => {
  assert.equal(isKbMcpTool('mcp__kb-mcp__kb_list'), true)
  assert.equal(isKbMcpTool('mcp__kb_mcp_kb_list'), true)
  assert.equal(isKbMcpTool('mcp__kb_mcp_kb_mcp_kb_list'), true)
  assert.equal(normalizeKbMcpToolName('mcp__kb-mcp__kb_list'), 'mcp__kb-mcp__kb_list')
  assert.equal(normalizeKbMcpToolName('mcp__kb_mcp_kb_list'), 'mcp__kb-mcp__kb_list')
  assert.equal(normalizeKbMcpToolName('mcp__kb_mcp_kb_mcp_kb_list'), 'mcp__kb-mcp__kb_list')
  assert.equal(normalizeKbMcpToolName('mcp__kb_mcp_kb_mcp_kb_search_two_stage'), 'mcp__kb-mcp__kb_search_two_stage')
})

test('OMP plugin namespace strips only the plugin and server identity', () => {
  const pluginToolNames = [
    'mcp__kb_mcp_kb_mcp_kb_list',
    'mcp__kb_mcp_kb_mcp_kb_doc_read',
    'mcp__kb_mcp_kb_mcp_experience_search_smart',
    'mcp__kb_mcp_kb_mcp_soul_qdcvr_ask',
    'mcp__kb_mcp_kb_mcp_backend_status',
    'mcp__kb_mcp_kb_mcp_fs_get_tree',
    'mcp__kb_mcp_kb_mcp_parse_doc',
    'mcp__kb_mcp_kb_mcp_kb_doc_mcp_read',
  ]
  assert.deepEqual(filterKbMcpTools(pluginToolNames), [
    'mcp__kb-mcp__kb_list',
    'mcp__kb-mcp__kb_doc_read',
    'mcp__kb-mcp__experience_search_smart',
    'mcp__kb-mcp__soul_qdcvr_ask',
    'mcp__kb-mcp__backend_status',
    'mcp__kb-mcp__fs_get_tree',
    'mcp__kb-mcp__parse_doc',
    'mcp__kb-mcp__kb_doc_mcp_read',
  ])
})

test('does not count unrelated MCP tools or incomplete names', () => {
  const names = [
    'mcp__other__kb_list',
    'mcp__other_kb_list',
    'mcp__kb_mcp_other_kb_list',
    'mcp__other_kb_mcp_kb_list',
    'mcp__kb_mcp_other_kb_mcp_kb_list',
    'mcp__kb_mcp_kb_mcp_other_kb_list',
    'mcp__kb_mcp_kb_mcp_',
    'mcp__kb-mcp__',
    'Read',
    '',
  ]
  for (const name of names) assert.equal(isKbMcpTool(name), false, name)
  assert.deepEqual(filterKbMcpTools([
    'mcp__other__kb_list',
    'mcp__kb_mcp_kb_search',
    'mcp__kb_mcp_kb_mcp_kb_doc_read',
    'Grep',
    'mcp__kb-mcp__kb_doc_read',
  ]), [
    'mcp__kb-mcp__kb_search',
    'mcp__kb-mcp__kb_doc_read',
    'mcp__kb-mcp__kb_doc_read',
  ])
})

test('chat mount selection and retrieval guard use normalized KB tools only', () => {
  assert.equal(requestsKbMcp(['mcp__kb_mcp_kb_list']), true)
  assert.equal(requestsKbMcp(['mcp__kb-mcp__kb_list']), true)
  assert.equal(requestsKbMcp(['mcp__other__kb_list', 'Read']), false)

  assert.deepEqual(evaluateKbRetrieval(
    ['mcp__kb_mcp_kb_list'], 'retrieved', true, true,
  ), {
    success: true,
    toolCalls: ['mcp__kb-mcp__kb_list'],
    toolCallCount: 1,
  })
  assert.deepEqual(evaluateKbRetrieval(
    ['mcp__kb-mcp__kb_list'], 'retrieved', true, true,
  ), {
    success: true,
    toolCalls: ['mcp__kb-mcp__kb_list'],
    toolCallCount: 1,
  })
  assert.deepEqual(evaluateKbRetrieval(
    ['mcp__other__kb_list'], 'an answer', true, true,
  ), {
    success: false,
    code: 'KB_NO_RETRIEVAL',
    toolCalls: [],
    toolCallCount: 0,
  })
  assert.deepEqual(evaluateKbRetrieval(
    ['Read'], 'KB_TOOLS_NOT_READY', true, true,
  ), {
    success: false,
    code: 'KB_TOOLS_NOT_READY',
    toolCalls: [],
    toolCallCount: 0,
  })
})
