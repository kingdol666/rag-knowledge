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
    const client = new OmpRpcClient(req.cwd, req.model, req.resume)
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
            // Best-effort enrichment from get_state
            client.send({ type: 'get_state' }, 5000)
              .then((resp: any) => {
                const data = resp?.data || {}
                if (data.sessionId && !state.sessionId) {
                  state.sessionId = data.sessionId
                }
                if (data.model?.id) {
                  state.fullModel = data.model.id
                }
              })
              .catch(() => {})
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
          } else if (evt.type === 'toolcall_start') {
            const toolUseId = evt.toolCallId || `tu_${Date.now()}`
            enqueue({
              type: 'assistant',
              message: {
                role: 'assistant',
                content: [{
                  type: 'tool_use',
                  id: toolUseId,
                  name: evt.toolName || 'Tool',
                  input: evt.arguments || {},
                }],
              },
            })
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
              if (b.type === 'tool_use') content.push(b)
            }
            if (content.length > 0) {
              enqueue({
                type: 'assistant',
                message: { role: 'assistant', content },
              })
            }
            state.streamingText = ''
            state.streamingThinking = ''
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

          enqueue({
            type: 'result',
            result: resultText,
            is_error: stopReason === 'error',
            total_cost_usd: cost,
            duration_ms: Date.now() - state.startTime,
            num_turns: 1,
            usage: { input_tokens: inputTokens, output_tokens: outputTokens },
            stop_reason: stopReason,
            terminal_reason: stopReason,
            session_id: state.sessionId,
            modelUsage: lastAssistant?.model
              ? { [lastAssistant.model]: { inputTokens, outputTokens, costUSD: cost } }
              : undefined,
          })
          finish()
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
