/**
 * Engine constants and theme definitions (shared frontend).
 *
 * Each engine has:
 *  - A stable identifier (sent to the backend as `engine` param)
 *  - Display metadata (label, icon emoji, description)
 *  - A theme override object that replaces CSS variables when active
 *
 * The theme switching works by toggling a data-engine attribute on the
 * chat page root; CSS scoped under [data-engine="omp"] overrides the
 * default --kb-* tokens with OMP's blue-purple palette.
 */
import type { CSSProperties } from 'vue'

export type EngineName = 'claude' | 'omp'

export interface EngineMeta {
  name: EngineName
  label: string
  icon: string
  description: string
}

export const ENGINES: EngineMeta[] = [
  {
    name: 'claude',
    label: 'Claude Code',
    icon: '🤖',
    description: 'Anthropic Claude Agent SDK',
  },
  {
    name: 'omp',
    label: 'OMP',
    icon: '⚡',
    description: 'Oh My Pi Coding Agent',
  },
]

export const ENGINE_MAP: Record<EngineName, EngineMeta> = Object.fromEntries(
  ENGINES.map((e) => [e.name, e]),
) as Record<EngineName, EngineMeta>

export function isEngineName(v: string | undefined | null): v is EngineName {
  return v === 'claude' || v === 'omp'
}

export function normalizeEngine(v: string | undefined | null): EngineName {
  return v === 'omp' ? 'omp' : 'claude'
}

/**
 * Theme tokens injected as inline CSS custom properties on the chat page root.
 *
 * Claude theme: copper/amber (the existing palette — unchanged).
 * OMP theme: blue-purple (indigo primary, violet accents).
 *
 * Only the action/accent tokens are overridden; structural tokens (bg, fg,
 * border, radius, shadow) stay shared so layout is identical.
 */
export const ENGINE_THEME: Record<EngineName, Record<string, string>> = {
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
