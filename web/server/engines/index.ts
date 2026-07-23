/**
 * Engine factory — selects the right ChatEngine by name.
 *
 * Both Claude and OMP engines are singletons (no per-request state in the
 * constructor; all state lives inside query()).
 */
import { ClaudeEngine } from './claude-engine'
import { OmpEngine } from './omp-engine'
import type { ChatEngine, EngineName } from './types'

const _claudeEngine = new ClaudeEngine()
const _ompEngine = new OmpEngine()

const ENGINES: Record<EngineName, ChatEngine> = {
  claude: _claudeEngine,
  omp: _ompEngine,
}

/** Resolve a string to a valid engine name (defaults to 'claude'). */
export function normalizeEngine(name?: string): EngineName {
  if (name === 'omp') return 'omp'
  return 'claude'
}

/** Get the ChatEngine instance for a given engine name. */
export function getEngine(name?: string): ChatEngine {
  return ENGINES[normalizeEngine(name)]
}
