/**
 * Engine abstraction layer — shared types.
 *
 * Every chat-capable harness (14-engine registry in the Python backend) is
 * adapted to the same ChatEngine interface. All engines emit the same
 * StandardMessage format (Anthropic/Claude SDK shape), so the frontend
 * MessageProcessor renders identically regardless of engine.
 *
 * Transports:
 *  - sdk      — in-process @anthropic-ai/claude-agent-sdk (claude)
 *  - rpc      — `omp --mode rpc` JSONL child process (omp)
 *  - acp      — Agent Client Protocol v1 over stdio (dsh/hermes); the only
 *               transport besides sdk with REAL interactive HITL: the agent's
 *               `session/request_permission` calls are surfaced to the user.
 *  - oneshot  — headless one-shot CLI per turn with server-side history
 *               replay (codex/gemini/copilot/cursor/opencode/crush/goose/
 *               qwen/pi). Headless one-shot mode cannot answer permission
 *               prompts, so each harness gets its documented conservative
 *               flag set instead (see harness-catalog.ts) — hitl=false.
 *  - inprocess — scripted mock engine (chat pipeline e2e / HITL demo).
 */

/** Engine identifiers — all registry harness ids are addressable. */
export type EngineName = string

/**
 * Permission mode as sent by the caller. Meaning is per-harness (each harness
 * exposes its REAL modes via harness-catalog.ts permissionModes); unknown
 * values fall back to that harness's safest default inside the adapters.
 */
export type PermissionMode = string

/** Permission mode descriptor — mirrors the harness's REAL CLI/SDK settings. */
export interface PermissionModeInfo {
  id: string
  label: string
  desc: string
  /** Real flag/env the mode maps to (informational, shown in UI tooltips). */
  mapping?: string
}

/** Query request — engine-agnostic. */
export interface QueryRequest {
  prompt: string
  cwd: string
  permissionMode: string
  model?: string
  allowedTools: string[]
  resume?: string
  maxTurns: number
  reasoningEffort?: string
  /** Full prompt text after KB instruction + path hints (pre-built by caller). */
  fullPromptText: string
  /**
   * Server-side conversation history (oldest first). Required for transports
   * without native cross-request sessions (oneshot/acp): the adapter replays
   * it into the prompt so multi-turn chat still works.
   */
  history?: Array<{ role: 'user' | 'assistant'; text: string }>
  /**
   * Permission callback — resolves to { behavior: 'allow'|'deny', optionId? }.
   * For ACP engines `options` carries the harness-provided choices and the
   * user's `optionId` selection is sent back verbatim (native HITL).
   */
  onPermissionRequest?: (
    toolName: string,
    input: Record<string, unknown>,
    toolUseId: string,
    sessionId: string,
    options?: PermissionRequestOption[],
  ) => Promise<{ behavior: string; message?: string; updatedInput?: any; optionId?: string }>
  /** Abort signal (client disconnect). */
  signal?: AbortSignal
}

/** One selectable option offered by a harness permission request (ACP). */
export interface PermissionRequestOption {
  optionId: string
  name: string
  kind: 'allow_once' | 'allow_always' | 'reject_once' | 'reject_always' | string
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
 * All adapters yield StandardMessage objects as an async iterable.
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

/** Standardized message format — identical to Claude Agent SDK message shape. */
export interface StandardMessage {
  type: 'system' | 'assistant' | 'user' | 'result' | 'stream_event'
  [key: string]: any
}
