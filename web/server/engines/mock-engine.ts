/**
 * Mock ChatEngine — in-process scripted engine (no LLM, no subprocess).
 *
 * Purpose: exercise the full chat + HITL pipeline (SSE streaming, permission
 * approval round-trip, session persistence) on machines with zero harnesses
 * installed, plus CI. Honesty: it never fabricates model intelligence — the
 * replies are clearly labeled scripted output.
 *
 * HITL demo: when the prompt contains "[hitl-demo]" (and permission mode is
 * not bypassPermissions), the adapter emits one scripted permission request
 * ("mock:write_file") with ACP-shaped options and waits for the user's
 * decision via onPermissionRequest before finishing the turn.
 */
import { randomUUID } from 'crypto'
import type { ChatEngine, PermissionRequestOption, QueryRequest, StandardMessage } from './types'

const MOCK_OPTIONS: PermissionRequestOption[] = [
  { optionId: 'allow_once', name: 'Allow once', kind: 'allow_once' },
  { optionId: 'allow_always', name: 'Always allow', kind: 'allow_always' },
  { optionId: 'reject_once', name: 'Reject once', kind: 'reject_once' },
]

export class MockEngine implements ChatEngine {
  constructor(readonly name: string) {}

  async *query(req: QueryRequest): AsyncIterable<StandardMessage> {
    const sessionId = req.resume || `mock-${randomUUID()}`
    const startTime = Date.now()

    yield {
      type: 'system', subtype: 'init',
      session_id: sessionId, model: req.model || 'mock-1',
      cwd: req.cwd, permissionMode: req.permissionMode,
      tools: ['mock:write_file'], mcp_servers: [], slash_commands: [],
    }

    const wantsHitl = req.fullPromptText.includes('[hitl-demo]')
      && req.permissionMode !== 'bypassPermissions'

    let hitlNote = ''
    if (wantsHitl && req.onPermissionRequest) {
      yield {
        type: 'assistant',
        message: {
          role: 'assistant',
          content: [{ type: 'tool_use', id: 'tu_mock_1', name: 'mock:write_file', input: { path: 'demo.txt', content: 'scripted' } }],
        },
      }
      const decision = await req.onPermissionRequest(
        'mock:write_file',
        { path: 'demo.txt', content: 'scripted' },
        'tu_mock_1',
        sessionId,
        MOCK_OPTIONS,
      )
      if (decision.behavior === 'allow') {
        hitlNote = `HITL demo: you ALLOWED mock:write_file (${decision.optionId || 'allow_once'}).`
      } else {
        hitlNote = `HITL demo: you DENIED mock:write_file. ${decision.message || ''}`.trim()
      }
    }

    const turnCount = (req.history || []).filter(m => m.role === 'user').length + 1
    const text = [
      `[mock harness · scripted reply · turn ${turnCount}]`,
      '',
      `Received: ${req.prompt.slice(0, 200)}${req.prompt.length > 200 ? '…' : ''}`,
      hitlNote ? `\n${hitlNote}` : '',
      '',
      'This is the in-process mock engine — it validates the chat/HITL pipeline end-to-end without any CLI or credentials. Pick a real harness from the dropdown to talk to an actual agent.',
    ].filter(s => s !== '').join('\n')

    yield { type: 'stream_event', event: { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text } } }
    // Complete assistant message (parity with real engines) so the persisted
    // history carries the assistant side for server-replay continuity.
    yield {
      type: 'assistant',
      message: { role: 'assistant', content: [{ type: 'text', text }] },
    }
    yield {
      type: 'result', result: text, is_error: false, total_cost_usd: 0,
      duration_ms: Date.now() - startTime, num_turns: 1,
      usage: { input_tokens: 0, output_tokens: 0 },
      stop_reason: 'stop', terminal_reason: 'stop',
      session_id: sessionId,
    }
  }
}
