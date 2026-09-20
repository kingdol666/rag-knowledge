/**
 * Engine factory — selects the right ChatEngine by harness id.
 *
 * Claude and OMP are singletons with heavy SDK imports; the remaining
 * harnesses share stateless adapters (ACP / one-shot CLI / mock), cached
 * per id. All adapters implement the same ChatEngine interface and emit
 * StandardMessage frames, so chat.post.ts and the frontend stay
 * engine-agnostic.
 */
import { ClaudeEngine } from './claude-engine'
import { OmpEngine } from './omp-engine'
import { AcpEngine } from './acp-engine'
import { CliOneShotEngine } from './cli-oneshot-engine'
import { MockEngine } from './mock-engine'
import { CHAT_CAPABLE_IDS, getChatMeta } from '~/server/utils/harness-catalog'
import type { ChatEngine, EngineName, QueryRequest, StandardMessage } from './types'
export type { PermissionMode } from './types'

const _claudeEngine = new ClaudeEngine()
const _ompEngine = new OmpEngine()

const _shared: Record<string, ChatEngine> = {
  dsh: new AcpEngine('dsh'),
  hermes: new AcpEngine('hermes'),
  mock: new MockEngine('mock'),
}
for (const id of ['codex', 'gemini', 'copilot', 'cursor', 'opencode', 'crush', 'goose', 'qwen', 'pi']) {
  _shared[id] = new CliOneShotEngine(id)
}

/** Resolve a string to a chat-capable engine id, or null if unsupported. */
export function normalizeEngine(name?: string): EngineName | null {
  const id = (name || '').trim()
  return CHAT_CAPABLE_IDS.includes(id) ? id : null
}

/** Get the ChatEngine instance for a given engine name. Throws when unknown. */
export function getEngine(name?: string): ChatEngine {
  const id = normalizeEngine(name)
  if (!id) {
    throw new Error(
      `Unknown or chat-unsupported harness '${name}'. `
      + `Chat-capable harnesses: ${CHAT_CAPABLE_IDS.join(', ')}`)
  }
  if (id === 'claude') return _claudeEngine
  if (id === 'omp') return _ompEngine
  return _shared[id]
}

/**
 * Execute one engine turn - the async-iterable frame stream, as a free
 * function. Non-SSE callers (POST /api/kb/native-search) run a turn through
 * this instead of touching the adapter method directly, keeping the
 * engine-facing surface in the factory module.
 */
export function engineTurn(engine: ChatEngine, req: QueryRequest): AsyncIterable<StandardMessage> {
  return engine.query(req)
}

export { CHAT_CAPABLE_IDS, getChatMeta }
