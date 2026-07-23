/**
 * Claude Code SDK ChatEngine adapter.
 *
 * Wraps `@anthropic-ai/claude-agent-sdk`'s `query()` behind the unified
 * ChatEngine interface. The Claude SDK already emits StandardMessage-compatible
 * messages (system/assistant/user/result/stream_event), so this adapter is a
 * thin pass-through that normalizes the query parameters and wires the
 * permission callback + abort signal.
 */
import { query as claudeQuery } from '@anthropic-ai/claude-agent-sdk'
import type {
  ChatEngine,
  QueryRequest,
  StandardMessage,
} from './types'

/** Multimodal content block (image/document). */
export interface AttachmentBlock {
  type: 'image' | 'document' | 'text'
  source?: { type: 'base64'; media_type: string; data: string }
  text?: string
}

export class ClaudeEngine implements ChatEngine {
  readonly name = 'claude' as const

  async *query(req: QueryRequest): AsyncIterable<StandardMessage> {
    // Build the Claude SDK prompt. The SDK accepts either a string or an
    // AsyncIterable<SDKUserMessage> for multimodal content. The caller passes
    // attachment blocks via the `attachmentBlocks` field when present.
    const blocks = (req as QueryRequest & { attachmentBlocks?: AttachmentBlock[] }).attachmentBlocks
    const hasMultimodal = blocks && blocks.length > 0

    let promptArg: string | AsyncIterable<any> = req.fullPromptText
    if (hasMultimodal) {
      async function* msgStream() {
        yield {
          type: 'user' as const,
          message: {
            role: 'user' as const,
            content: [
              { type: 'text', text: req.fullPromptText },
              ...blocks!,
            ],
          },
          parent_tool_use_id: null,
        }
      }
      promptArg = msgStream()
    }

    const q = claudeQuery({
      prompt: promptArg,
      options: {
        cwd: req.cwd,
        permissionMode: req.permissionMode,
        model: req.model || undefined,
        allowedTools: req.allowedTools,
        resume: req.resume || undefined,
        maxTurns: req.maxTurns || 50,
        settingSources: ['user', 'project'],
        env: { ...process.env },
        // Pass reasoning_effort if set
        ...(req.reasoningEffort && req.reasoningEffort !== 'auto'
          ? {
              reasoning_effort: req.reasoningEffort as
                | 'low'
                | 'medium'
                | 'high'
                | 'xhigh'
                | 'max',
            }
          : {}),
        // Enable token-level streaming for typewriter rendering
        includePartialMessages: true,
        // Wire permission callback if provided (for approval modes)
        ...(req.onPermissionRequest
          ? {
              canUseTool: async (
                toolName: string,
                input: Record<string, unknown>,
                opts: any,
              ) => {
                const toolUseId: string =
                  opts?.tool_use_id ||
                  `tu_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
                // The permission UI resolves { behavior: 'allow'|'deny', ... }.
                // Narrow to the SDK's PermissionResult discriminated union.
                const res = await req.onPermissionRequest!(toolName, input, toolUseId, '')
                if (res.behavior === 'deny') {
                  return { behavior: 'deny' as const, message: res.message ?? 'Denied' }
                }
                return { behavior: 'allow' as const }
              },
            }
          : {}),
      },
    })

    // Forward abort signal to close the query
    if (req.signal) {
      req.signal.addEventListener(
        'abort',
        () => {
          try {
            ;(q as any).close?.()
          } catch {
            /* Already ended */
          }
        },
        { once: true },
      )
    }

    for await (const message of q) {
      yield message as StandardMessage
    }
  }
}
