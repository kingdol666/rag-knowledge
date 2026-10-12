/**
 * OMP ChatEngine adapter — translates `bun omp --mode rpc` events into
 * the standardized StandardMessage format (Claude SDK shape).
 *
 * Uses a mutable state object + const arrow functions instead of closure
 * variables + hoisted function declarations. This avoids transpiler scope
 * issues with async generators in esbuild/Vite.
 */
import { OmpRpcClient } from './omp-rpc-client'
import { AsyncQueue } from './async-queue'
import type {
  ChatEngine,
  QueryRequest,
  StandardMessage,
} from './types'

export class OmpEngine implements ChatEngine {
  readonly name = 'omp' as const

  async *query(req: QueryRequest): AsyncIterable<StandardMessage> {
    const client = new OmpRpcClient(req.cwd, req.model, req.resume, req.reasoningEffort)
    const queue = new AsyncQueue<StandardMessage>()

    // All mutable state in one object — safe to capture in closures
    const state = {
      sessionId: req.resume || '',
      initSent: false,
      fullModel: req.model || 'default',
      resultEmitted: false,
      startTime: Date.now(),
      streamingText: '',
      streamingThinking: '',
      // Track tool_use ids already streamed via toolcall_start so the
      // subsequent message_end frame doesn't emit them a second time
      // (would render duplicate tool cards in the UI).
      emittedToolUseIds: new Set<string>(),
      // toolResult message_end frames are the canonical result carrier; some
      // OMP builds also mirror them on message_start — dedupe by toolCallId.
      emittedToolResultIds: new Set<string>(),
    }

    /**
     * Fetch the REAL OMP session id via get_state. The previous code sent
     * this at turn_start — while the agent turn was streaming, the RPC loop
     * was busy, the 5s timeout elapsed and the .catch swallowed the failure,
     * so every session persisted as session_id='' (all OMP chats collapsed
     * into ONE overwritten history row and frames were never saved because
     * chat.post.ts guards saveMessage with `if (sessionId)`). OMP answers
     * get_state instantly when the process is IDLE — hence: call it right
     * after waitReady (before prompting) and again at agent_end (before the
     * result frame), never mid-turn.
     */
    const fetchSessionId = async (timeoutMs = 8000): Promise<string> => {
      try {
        const resp = await client.send({ type: 'get_state' }, timeoutMs)
        const data = resp?.data || {}
        if (data.sessionId && !state.sessionId) {
          state.sessionId = String(data.sessionId)
        }
        if (data.model?.id) {
          state.fullModel = String(data.model.id)
        }
      } catch { /* best-effort — fallback id below keeps rows distinct */ }
      return state.sessionId
    }

    const enqueue = (msg: StandardMessage): void => {
      queue.push(msg)
    }

    const finish = (err?: Error): void => {
      if (err) {
        enqueue({
          type: 'result',
          result: '',
          is_error: true,
          total_cost_usd: 0,
          duration_ms: Date.now() - state.startTime,
          num_turns: 0,
          usage: { input_tokens: 0, output_tokens: 0 },
          stop_reason: 'error',
          terminal_reason: err.message,
          session_id: state.sessionId,
        })
      }
      queue.close()
    }

    // Event handler — const arrow function for correct closure scoping
    const handleEvent = (frame: any): void => {
      switch (frame.type) {
        case 'turn_start': {
          if (!state.initSent) {
            state.initSent = true
            enqueue({
              type: 'system',
              subtype: 'init',
              session_id: state.sessionId,
              model: state.fullModel,
              cwd: req.cwd,
              permissionMode: req.permissionMode,
              tools: [],
              mcp_servers: [],
              slash_commands: [],
            })
            // sessionId is fetched BEFORE the prompt (see query() below) while
            // the RPC loop is idle; mid-turn get_state calls time out because
            // OMP is busy streaming, so none is attempted here.
          }
          break
        }

        case 'message_update': {
          const evt = frame.assistantMessageEvent
          if (!evt) break

          if (evt.type === 'text_delta' && evt.delta) {
            state.streamingText += evt.delta
            enqueue({
              type: 'stream_event',
              event: {
                type: 'content_block_delta',
                index: 0,
                delta: { type: 'text_delta', text: evt.delta },
              },
            })
          } else if (evt.type === 'thinking_delta' && evt.delta) {
            state.streamingThinking += evt.delta
            enqueue({
              type: 'stream_event',
              event: {
                type: 'content_block_delta',
                index: 1,
                delta: { type: 'thinking_delta', thinking: evt.delta },
              },
            })
          } else if (evt.type === 'toolcall_end') {
            // ⭐ Real OMP frames carry the complete tool call HERE —
            // toolCallStart has NO toolCallId/toolName/arguments fields
            // (emitting there produced "Tool" cards with empty Input).
            const tc = evt.toolCall || {}
            const toolUseId = String(tc.id || `tu_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`)
            if (!state.emittedToolUseIds.has(toolUseId)) {
              state.emittedToolUseIds.add(toolUseId)
              enqueue({
                type: 'assistant',
                message: {
                  role: 'assistant',
                  content: [{
                    type: 'tool_use',
                    id: toolUseId,
                    name: String(tc.name || 'Tool'),
                    input: (tc.arguments && typeof tc.arguments === 'object') ? tc.arguments : {},
                  }],
                },
              })
            }
          }
          break
        }

        case 'message_end': {
          const msg = frame.message
          if (msg?.role === 'assistant') {
            const content: any[] = []
            if (state.streamingText) {
              content.push({ type: 'text', text: state.streamingText })
            }
            if (state.streamingThinking) {
              content.push({ type: 'thinking', thinking: state.streamingThinking })
            }
            for (const b of msg.content || []) {
              // OMP names tool blocks `toolCall` (id/name/arguments); map them
              // to the SDK's tool_use shape so the UI renders real cards.
              // Skip ones already streamed via toolcall_end — without this
              // guard the same call renders two cards (delta + end).
              if (b.type === 'tool_use' || b.type === 'toolCall') {
                const bid = String(b.id || '')
                if (bid && state.emittedToolUseIds.has(bid)) continue
                if (bid) state.emittedToolUseIds.add(bid)
                content.push({
                  type: 'tool_use',
                  id: bid,
                  name: String(b.name || 'Tool'),
                  input: (b.arguments && typeof b.arguments === 'object') ? b.arguments : (b.input || {}),
                })
              }
            }
            if (content.length > 0) {
              enqueue({
                type: 'assistant',
                message: { role: 'assistant', content },
                // ⭐ Subagent passthrough — OMP frames may carry these fields
                // when a delegated child agent (Task/Agent tool) produces the
                // message. Forward them so the web UI can group nested
                // transcripts in the subagent sidebar.
                parent_tool_use_id: frame.parent_tool_use_id || msg.parent_tool_use_id || null,
                subagent_type: frame.subagent_type || frame.agent_type || msg.subagent_type || undefined,
                task_description: frame.task_description || msg.task_description || msg.description || undefined,
              })
            }
            state.streamingText = ''
            state.streamingThinking = ''
          } else if (msg?.role === 'toolResult') {
            // ⭐ Real OMP tool results arrive as role:"toolResult" messages
            // (toolCallId/toolName/content/isError) — the old code only
            // forwarded role:"user" + type:"tool_result" blocks, which OMP
            // never sends, so tool results were silently dropped and the UI
            // never showed a result card. Repack into the SDK user shape.
            const rid = String(msg.toolCallId || '')
            if (!rid || !state.emittedToolResultIds.has(rid)) {
              if (rid) state.emittedToolResultIds.add(rid)
              let text = ''
              if (typeof msg.content === 'string') {
                text = msg.content
              } else if (Array.isArray(msg.content)) {
                text = msg.content
                  .map((c: any) => (typeof c === 'string' ? c : (c?.type === 'text' ? c.text : '')))
                  .filter(Boolean)
                  .join('\n')
              }
              if (!text && msg.content != null) {
                text = JSON.stringify(msg.content)
              }
              enqueue({
                type: 'user',
                message: {
                  role: 'user',
                  content: [{
                    type: 'tool_result',
                    tool_use_id: rid,
                    content: text,
                    is_error: !!msg.isError,
                  }],
                },
              })
            }
          } else if (msg?.role === 'user') {
            for (const b of msg.content || []) {
              if (b.type === 'tool_result') {
                enqueue({
                  type: 'user',
                  message: { role: 'user', content: [b] },
                })
              }
            }
          }
          break
        }

        case 'agent_end': {
          if (state.resultEmitted) {
            finish()
            return
          }
          state.resultEmitted = true
          const messages = frame.messages || []
          const lastAssistant = [...messages].reverse().find(
            (m: any) => m.role === 'assistant',
          )
          const usage = lastAssistant?.usage || {}
          const cost = Number(usage?.cost?.total || 0)
          const inputTokens = Number(usage?.input || usage?.inputTokens || 0)
          const outputTokens = Number(usage?.output || usage?.outputTokens || 0)
          const stopReason = lastAssistant?.stopReason || 'stop'
          const resultText = lastAssistant?.content
            ?.filter((b: any) => b.type === 'text')
            .map((b: any) => b.text)
            .join('\n') || ''

          // The turn has settled — the RPC loop is idle NOW, so this is the
          // reliable moment to fetch the real session id (mid-turn attempts
          // time out). Emit the result frame once the fetch settles (or 8s
          // elapses); a generated fallback keeps history rows distinct even
          // if OMP never answers.
          const emitResult = (sid: string) => {
            enqueue({
              type: 'result',
              result: resultText,
              is_error: stopReason === 'error',
              total_cost_usd: cost,
              duration_ms: Date.now() - state.startTime,
              num_turns: messages.filter((m: any) => m.role === 'assistant').length || 1,
              usage: { input_tokens: inputTokens, output_tokens: outputTokens },
              stop_reason: stopReason,
              terminal_reason: stopReason,
              session_id: sid,
              modelUsage: lastAssistant?.model
                ? { [lastAssistant.model]: { inputTokens, outputTokens, costUSD: cost } }
                : undefined,
            })
            finish()
          }
          if (state.sessionId) {
            emitResult(state.sessionId)
          } else {
            fetchSessionId(8000)
              .catch(() => '')
              .then((sid) => emitResult(sid || `omp-${Date.now()}`))
          }
          break
        }

        default:
          break
      }
    }

    client.onEvent((frame: any) => {
      try {
        handleEvent(frame)
      } catch (e) {
        finish(e as Error)
      }
    })

    // Wire up abort signal
    if (req.signal) {
      req.signal.addEventListener('abort', () => {
        client.abort()
        finish()
      }, { once: true })
    }

    try {
      await client.waitReady()

      // ⭐ Session id MUST be captured BEFORE prompting: this is the one
      // moment the RPC loop is guaranteed idle, so get_state answers fast
      // and the init frame (emitted at turn_start) carries a REAL
      // session_id — chat.post.ts upserts the history row and saves every
      // frame under it. Mid-turn fetches time out (OMP busy streaming) and
      // previously collapsed every OMP chat into one overwritten '' row.
      // Retry once: the session file may still be materializing on a cold
      // start.
      if (!state.sessionId) {
        await fetchSessionId(8000)
        if (!state.sessionId) {
          await new Promise((r) => setTimeout(r, 800))
          await fetchSessionId(8000)
        }
      }

      const promptResp = await client.send({
        type: 'prompt',
        message: req.fullPromptText,
      })

      if (!promptResp?.success) {
        throw new Error(promptResp?.error || 'OMP prompt command failed')
      }

      for await (const msg of queue) {
        yield msg
      }
    } finally {
      client.kill()
    }
  }
}
