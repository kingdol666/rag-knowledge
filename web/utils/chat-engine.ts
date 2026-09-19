/**
 * Engine constants and theme definitions (shared frontend).
 *
 * The id set mirrors the backend 14-harness registry plus `mock`. The
 * authoritative availability/chat metadata comes from GET /api/harnesses at
 * runtime (see pages/claude-chat.vue + pages/harnesses.vue); the static
 * metadata below covers icons/labels/themes and SSR-safe first render.
 *
 * Theme switching works by toggling a data-engine attribute on the chat page
 * root; CSS scoped under [data-engine="omp"] etc. overrides the default
 * --kb-* tokens. Engines without a dedicated palette share the default.
 */
import type { CSSProperties } from 'vue'

export type EngineName = string

export interface EngineMeta {
  name: EngineName
  label: string
  icon: string
  description: string
  /** Chat adapter kind (informational badge in the UI). */
  transport?: 'sdk' | 'rpc' | 'acp' | 'oneshot' | 'inprocess'
}

export const ENGINES: EngineMeta[] = [
  { name: 'claude', label: 'Claude Code', icon: '🤖', description: 'Anthropic Claude Agent SDK', transport: 'sdk' },
  { name: 'omp', label: 'OMP', icon: '⚡', description: 'Oh My Pi Coding Agent', transport: 'rpc' },
  { name: 'codex', label: 'Codex CLI', icon: '🔧', description: 'OpenAI Codex CLI', transport: 'oneshot' },
  { name: 'gemini', label: 'Gemini CLI', icon: '✨', description: 'Google Gemini CLI', transport: 'oneshot' },
  { name: 'copilot', label: 'Copilot CLI', icon: '🐙', description: 'GitHub Copilot CLI', transport: 'oneshot' },
  { name: 'cursor', label: 'Cursor CLI', icon: '🖱️', description: 'Cursor Agent CLI', transport: 'oneshot' },
  { name: 'dsh', label: 'DeepSeek', icon: '🐋', description: 'DeepSeek Harness (ACP)', transport: 'acp' },
  { name: 'hermes', label: 'Hermes', icon: '📜', description: 'Hermes Agent (ACP)', transport: 'acp' },
  { name: 'opencode', label: 'OpenCode', icon: '📂', description: 'OpenCode run', transport: 'oneshot' },
  { name: 'crush', label: 'Crush', icon: '💫', description: 'Charm Crush', transport: 'oneshot' },
  { name: 'goose', label: 'Goose', icon: '🪿', description: 'Block Goose', transport: 'oneshot' },
  { name: 'qwen', label: 'Qwen Code', icon: '🧭', description: 'Qwen Code CLI', transport: 'oneshot' },
  { name: 'pi', label: 'pi agent', icon: '🥧', description: 'pi coding agent', transport: 'oneshot' },
  { name: 'mock', label: 'Mock', icon: '🧪', description: 'Scripted in-process engine (HITL demo/CI)', transport: 'inprocess' },
]

export const ENGINE_MAP: Record<string, EngineMeta> = Object.fromEntries(
  ENGINES.map(e => [e.name, e]),
)

export function isEngineName(v: string | undefined | null): boolean {
  return !!v && v in ENGINE_MAP
}

export function normalizeEngine(v: string | undefined | null): EngineName {
  return v && v in ENGINE_MAP ? v : 'claude'
}

/**
 * Theme tokens injected as inline CSS custom properties on the chat page root.
 * Claude = default copper/amber palette; OMP = blue-purple. All other
 * harnesses share the default palette (ENGINE_THEME lookup falls back to {}).
 */
export const ENGINE_THEME: Record<string, Record<string, string>> = {
  claude: {},
  omp: {
    '--kb-primary': '#6366f1',
    '--kb-primary-hover': '#4f46e5',
    '--kb-primary-soft': '#e0e7ff',
    '--kb-primary-tint': '#eef2ff',
    '--kb-primary-glow': 'rgba(99, 102, 241, 0.28)',
    '--kb-gold': '#7c5cff',
    '--kb-gold-bright': '#a78bfa',
    '--kb-gold-deep': '#5b21b6',
    '--kb-gold-soft': '#ede9fe',
    '--kb-gold-glow': 'rgba(167, 139, 250, 0.35)',
    '--kb-shadow-primary': '0 10px 26px rgba(99, 102, 241, 0.30)',
    '--kb-shadow-primary-lg': '0 18px 42px rgba(99, 102, 241, 0.38)',
    '--kb-shadow-gold': '0 8px 24px rgba(167, 139, 250, 0.28)',
    '--hl-keyword': '#6366f1',
    '--hl-tag': '#6366f1',
  },
}

/** localStorage key for the user's engine choice (persisted across sessions). */
export const ENGINE_STORAGE_KEY = 'chat-engine'
