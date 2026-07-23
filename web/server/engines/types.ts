/**
 * Engine abstraction layer — shared types.
 *
 * Both Claude Code SDK and OMP SDK implement the same ChatEngine interface.
 * All engines emit the same StandardMessage format (Anthropic/Claude SDK shape),
 * so the frontend MessageProcessor renders identically regardless of engine.
 *
 * Design: Adapter Pattern — standardize divergent SDK APIs behind one interface.
 */

/** Supported engine identifiers. */
export type EngineName = 'claude' | 'omp'

/** Permission modes (shared between engines). */
export const PERMISSION_MODES = [
  'default',
  'acceptEdits',
  'bypassPermissions',
  'plan',
  'dontAsk',
] as const
export type PermissionMode = (typeof PERMISSION_MODES)[number]

/**
 * Standardized message format — identical to Claude Agent SDK message shape.
 * The frontend MessageProcessor parses these directly; the OMP adapter translates
 * OMP events into this format so rendering is 100% shared.
 */
export interface StandardMessage {
  type: 'system' | 'assistant' | 'user' | 'result' | 'stream_event'
  [key: string]: any
}

/** Content block types (Anthropic format). */
export type ContentBlock =
  | { type: 'text'; text: string }
  | { type: 'thinking'; thinking: string }
  | { type: 'tool_use'; id: string; name: string; input: any }
  | { type: 'tool_result'; tool_use_id: string; content: any; is_error?: boolean }

/** Query request — engine-agnostic. */
export interface QueryRequest {
  prompt: string
  cwd: string
  permissionMode: PermissionMode
  model?: string
  allowedTools: string[]
  resume?: string
  maxTurns: number
  reasoningEffort?: string
  /** Full prompt text after KB instruction + path hints (pre-built by caller). */
  fullPromptText: string
  /** Multimodal attachment blocks (Claude only; OMP uses path hints in text). */
  attachmentBlocks?: Array<{
    type: 'image' | 'document' | 'text'
    source?: { type: 'base64'; media_type: string; data: string }
    text?: string
  }>
  /** Permission callback — resolves to { behavior: 'allow'|'deny' }. */
  onPermissionRequest?: (
    toolName: string,
    input: Record<string, unknown>,
    toolUseId: string,
    sessionId: string,
  ) => Promise<{ behavior: string; message?: string; updatedInput?: any }>
  /** Abort signal (client disconnect). */
  signal?: AbortSignal
}
/** Session metadata for history listing. */
export interface SessionInfo {
  session_id: string
  title: string | null
  cwd: string | null
  model: string | null
  updated_at: string
  engine: EngineName
}

/**
 * ChatEngine — the unified interface every engine implements.
 *
 * Both adapters yield StandardMessage objects as an async iterable.
 * The caller (chat.post.ts) writes each message to the SSE stream.
 */
export interface ChatEngine {
  readonly name: EngineName

  /**
   * Execute a query, yielding standardized messages as they arrive.
   * The async generator ends when the turn completes or an error occurs.
   */
  query(req: QueryRequest): AsyncIterable<StandardMessage>
}
