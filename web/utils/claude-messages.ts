/**
 * Claude Agent SDK message -> UI message processor.
 *
 * References sugyan/claude-code-webui's UnifiedMessageProcessor architecture:
 *  - toolUseCache pairs the assistant's tool_use (with id+name+input) with the subsequent user's
 *    tool_result (which only has tool_use_id), recovering the tool name + input.
 *  - Special tools: TodoWrite renders a todo list directly from input.todos (skips result);
 *    ExitPlanMode renders a plan card from input.plan.
 *  - MCP tool names like mcp__server__tool are rendered as "server › tool".
 *  - thinking content is rendered independently (collapsible).
 *  - result messages expand cost / duration / turns / tokens / modelUsage / terminal_reason.
 *
 * Pure TS, no Vue dependency, shared frontend/backend.
 */

export interface TodoItem {
  content: string
  status: 'pending' | 'in_progress' | 'completed'
  activeForm: string
}

export type UIMessage =
  | { kind: 'user'; text: string; id: number }
  | { kind: 'assistant'; html: string; id: number }
  | { kind: 'thinking'; text: string; id: number }
  | {
      kind: 'tool_use'
      toolName: string
      display: string
      isMcp: boolean
      server?: string
      input: any
      toolUseId: string
      id: number
    }
  | {
      kind: 'tool_result'
      toolName: string
      display: string
      result: string
      isError: boolean
      toolUseId: string
      id: number
    }
  | { kind: 'plan'; plan: string; id: number }
  | { kind: 'todo'; todos: TodoItem[]; id: number }
  | {
      kind: 'ask_user'
      header: string
      question: string
      options: { label: string; description?: string }[]
      toolUseId: string
      answered: boolean
      answer?: string
      id: number
    }
  | { kind: 'system'; subtype: string; text: string; id: number }
  | {
      kind: 'result'
      html: string
      cost: number
      duration: number
      turns: number
      isError: boolean
      id: number
    }
  | { kind: 'error'; text: string; id: number }

interface ToolUseCache {
  name: string
  input: Record<string, unknown>
}

export class MessageProcessor {
  private toolCache = new Map<string, ToolUseCache>()
  private seq = 0

  reset() {
    this.toolCache.clear()
    this.seq = 0
  }

  private nextId() {
    return ++this.seq
  }

  /** mcp__kb-mcp__kb_list -> "kb-mcp / kb_list"; Edit -> "Edit" */
  static parseToolName(name: string): {
    display: string
    isMcp: boolean
    server?: string
  } {
    if (name.startsWith('mcp__')) {
      const rest = name.slice(4)
      const idx = rest.indexOf('__')
      if (idx > 0) {
        const server = rest.slice(0, idx)
        const tool = rest.slice(idx + 2)
        return { display: `${server} › ${tool}`, isMcp: true, server }
      }
    }
    return { display: name, isMcp: false }
  }

  /** Format tool input as readable preview (picks key fields by tool type). */
  static formatInputPreview(name: string, input: any): string {
    if (!input || typeof input !== 'object') return ''
    const mcpMatch = name.match(/^mcp__(.+?)__(.+)$/)
    const baseName = mcpMatch ? mcpMatch[2] : name
    const parts: string[] = []
    if (baseName === 'Bash' && input.command) {
      parts.push(`$ ${input.command}`)
    } else if (['Read', 'Write', 'Edit'].includes(baseName) && input.file_path) {
      parts.push(String(input.file_path))
      if (baseName === 'Edit' && input.old_string) {
        parts.push(`— 替换 ${(input.old_string as string).length} 字符`)
      }
    } else if (baseName === 'Glob' && input.pattern) {
      parts.push(String(input.pattern))
    } else if (baseName === 'Grep' && input.pattern) {
      parts.push(`/${input.pattern}/${input.path ? ' in ' + input.path : ''}`)
    } else if (baseName === 'WebFetch' && input.url) {
      parts.push(String(input.url))
    } else if (baseName === 'WebSearch' && input.query) {
      parts.push(`"${input.query}"`)
    } else if (baseName === 'Task' && input.description) {
      parts.push(String(input.description))
    } else if (input.prompt) {
      parts.push(String(input.prompt).slice(0, 120))
    } else if (input.query) {
      parts.push(String(input.query).slice(0, 120))
    }
    return parts.join(' ')
  }

  /** Process one SDK message, returns 0..N UI messages. */
  process(msg: any): UIMessage[] {
    if (!msg || typeof msg.type !== 'string') return []
    const out: UIMessage[] = []

    // Stream partial messages: stream_event (content_block_delta etc.)
    // Frontend uses a dedicated onStreamDelta handler; return empty here to avoid new UI messages
    if (msg.type === 'stream_event') {
      return out
    }

    if (msg.type === 'system') {
      if (msg.subtype === 'init') {
        const tools: string[] = msg.tools || []
        const mcps: any[] = msg.mcp_servers || []
        const mcpLine =
          mcps.length > 0
            ? mcps
                .map((m) => `${m.name}(${m.status})`)
                .join(', ')
            : '无'
        const text =
          `**会话初始化** · session \`${(msg.session_id || '').slice(0, 12)}…\`\n` +
          `- model: \`${msg.model || 'default'}\`\n` +
          `- cwd: \`${msg.cwd || ''}\`\n` +
          `- permission: \`${msg.permissionMode || 'default'}\`\n` +
          `- tools: ${tools.length} 个${
            tools.length ? '（' + tools.slice(0, 10).join(', ') + (tools.length > 10 ? '…' : '') + '）' : ''
          }\n` +
          `- MCP servers: ${mcpLine}`
        out.push({ kind: 'system', subtype: 'init', text, id: this.nextId() })
      }
      // thinking_tokens / other system subtypes — don't flood the UI
      return out
    }

    if (msg.type === 'assistant') {
      const blocks: any[] = msg.message?.content || []
      const textParts: string[] = []
      for (const b of blocks) {
        if (b.type === 'text' && b.text) {
          textParts.push(b.text)
        } else if (b.type === 'thinking' && b.thinking) {
          out.push({ kind: 'thinking', text: b.thinking, id: this.nextId() })
        } else if (b.type === 'tool_reference') {
          // tool_reference is a reference marker within assistant content blocks (not an actual invocation); skip it
          continue
        } else if (b.type === 'tool_use') {          const id: string = b.id || ''
          const name: string = b.name || 'Tool'
          const input = b.input || {}
          this.toolCache.set(id, { name, input })
          const parsed = MessageProcessor.parseToolName(name)
          if (name === 'TodoWrite' && Array.isArray(input.todos)) {
            out.push({
              kind: 'todo',
              todos: input.todos as TodoItem[],
              id: this.nextId(),
            })
          } else if (name === 'ExitPlanMode' && input.plan) {
            out.push({ kind: 'plan', plan: String(input.plan), id: this.nextId() })
          } else if (name === 'AskUserQuestion') {
            // Claude Code built-in interactive question tool
            const header = String(input.header || 'Claude 想向你确认')
            const questions = Array.isArray(input.questions)
              ? input.questions
              : []
            const q0: any = questions[0] || {}
            const opts: any[] = Array.isArray(q0.options) ? q0.options : []
            out.push({
              kind: 'ask_user',
              header,
              question: String(q0.question || ''),
              options: opts.map((o: any) => ({
                label: String(o.label || ''),
                description: o.description ? String(o.description) : undefined,
              })),
              toolUseId: id,
              answered: false,
              id: this.nextId(),
            })
          } else {
            out.push({
              kind: 'tool_use',
              toolName: name,
              display: parsed.display,
              isMcp: parsed.isMcp,
              server: parsed.server,
              input,
              toolUseId: id,
              id: this.nextId(),
            })
          }
        }
      }
      if (textParts.length) {
        out.push({
          kind: 'assistant',
          html: textParts.join('\n\n'),
          id: this.nextId(),
        })
      }
      return out
    }

    if (msg.type === 'user') {
      const blocks: any[] = msg.message?.content || []
      for (const b of blocks) {
        if (b.type === 'tool_result') {
          const id: string = b.tool_use_id || ''
          const cached = this.toolCache.get(id)
          const toolName = cached?.name || 'Tool'
          if (toolName === 'TodoWrite') continue // already rendered from tool_use
          if (toolName === 'AskUserQuestion') continue // interactive card already rendered; skip SDK auto-result
          const content =
            typeof b.content === 'string'
              ? b.content
              : JSON.stringify(b.content)
          const parsed = MessageProcessor.parseToolName(toolName)
          out.push({
            kind: 'tool_result',
            toolName,
            display: parsed.display,
            result: content,
            isError: !!b.is_error,
            toolUseId: id,
            id: this.nextId(),
          })
        } else if (b.type === 'text' && b.text) {
          // Plain text from user (rare, user message inside tool loop)
          out.push({ kind: 'user', text: b.text, id: this.nextId() })
        }
      }
      return out
    }

    if (msg.type === 'result') {
      const usage = msg.usage || {}
      const cost = Number(msg.total_cost_usd || 0)
      const lines: string[] = [
        `**${msg.is_error ? '❌ 执行出错' : '✅ 完成'}** — **${msg.num_turns || 0} 轮** · **$${cost.toFixed(4)}** · **${((msg.duration_ms || 0) / 1000).toFixed(1)}s**`,
        ``,
        `| 指标 | 值 |`,
        `| --- | --- |`,
        `| 输入 tokens | ${usage.input_tokens || 0} |`,
        `| 输出 tokens | ${usage.output_tokens || 0} |`,
        `| 缓存命中 | ${usage.cache_read_input_tokens || 0} |`,
        `| 终止原因 | \`${msg.terminal_reason || msg.stop_reason || '—'}\` |`,
      ]
      if (msg.modelUsage && typeof msg.modelUsage === 'object') {
        const models = Object.keys(msg.modelUsage)
        if (models.length) {
          lines.push('')
          lines.push('**模型用量明细**')
          for (const m of models) {
            const u = msg.modelUsage[m]
            lines.push(
              `- \`${m}\`: $${Number(u.costUSD || 0).toFixed(4)} · ${u.outputTokens || 0} out · ${u.inputTokens || 0} in`,
            )
          }
        }
      }
      if (msg.result) {
        // Result text is already stream-rendered by assistant messages; result only shows metrics, no duplicate output
      }
      out.push({
        kind: 'result',
        html: lines.join('\n'),
        cost,
        duration: msg.duration_ms || 0,
        turns: msg.num_turns || 0,
        isError: !!msg.is_error,
        id: this.nextId(),
      })
      return out
    }

    return out
  }
}
