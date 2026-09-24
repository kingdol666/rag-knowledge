import { getDynamicBackendUrl, getDynamicAuthConfig, getRawConfig } from './dynamic-config'

/**
 * Large-doc split helper (2026-09-18) — shared by both ingestion entry points:
 * - POST /api/kb/documents/create        (manual / API document creation)
 * - POST /api/parse/save-parsed-files    (MinerU parse → save into KB)
 *
 * The split threshold comes from config.yml `ingestion.large_doc` (editable on
 * the Settings page, hot-reloaded by the backend). The web layer only decides
 * *whether* to ask for a plan (cheap local prefilter via cached config.yml);
 * the backend POST /api/v1/documents/split re-reads the authoritative config
 * and returns the actual parts. Each part carries a `description` excerpted
 * from that part's real body text, so stored descriptions always match the
 * stored content (ingest skill gate A3c).
 */

export const DEFAULT_LARGE_DOC_MAX_CHARS = 10_000

export interface SplitPlanPart {
  title: string
  content: string
  part_index: number
  part_count: number
  source_title: string
  start_char: number
  end_char: number
  source_start?: number
  source_end?: number
  chars: number
  source_chars?: number
  description: string
  description_seed?: string
  agent_description?: string
  section_range?: string
  source_sha256?: string
  boundary_kind?: string
  warnings?: string[]
  strategy?: string
  planner?: string
  description_provenance?: string
}

export interface SplitPlan {
  success: boolean
  split: boolean
  reason: string
  part_count: number
  source_chars: number
  max_chars: number
  strategy?: string
  planner?: string
  source_sha256?: string
  warnings?: string[]
  parts: SplitPlanPart[]
}

/** Read `ingestion.large_doc` from shared config.yml (cached, TTL). */
export function getLargeDocConfig(): { autoSplit: boolean; maxChars: number } {
  const raw = getRawConfig() || {}
  const cfg = raw.ingestion?.large_doc || {}
  const maxChars = Number(cfg.max_chars)
  return {
    autoSplit: cfg.auto_split !== false,
    maxChars: Number.isFinite(maxChars) && maxChars > 0 ? maxChars : DEFAULT_LARGE_DOC_MAX_CHARS,
  }
}

/** Request a split plan from the backend — the authoritative config lives
 * backend-side (hot-reloaded). Returns null when the backend is unreachable
 * (callers fall back to single-doc save). */
export async function requestSplitPlan(
  title: string,
  content: string,
  autoSplit = true,
  agentPlan?: Record<string, unknown>,
): Promise<SplitPlan | null> {
  try {
    const auth = getDynamicAuthConfig()
    return await $fetch<SplitPlan>(`${getDynamicBackendUrl()}/api/v1/documents/split`, {
      method: 'POST',
      headers: auth.token ? { Authorization: `Bearer ${auth.token}` } : {},
      body: { title, content, auto_split: autoSplit, agent_plan: agentPlan },
      timeout: 60000,
    })
  } catch (e: any) {
    console.warn(`[large-doc-split] split plan request failed: ${e?.message || e}`)
    return null
  }
}

/** Compose the stored description for one part: real-content excerpt first
 * (ingest skill A3c — descriptions must describe the actual stored text),
 * keeping the caller's own description and the part marker as provenance. */
export function buildPartDescription(
  userDescription: string | undefined,
  part: SplitPlanPart,
): string {
  const generated = (part.agent_description || part.description || '').trim()
  const fallback = (part.description_seed || part.description || '').trim()
  const base = generated || fallback
  const section = part.section_range ? ` · ${part.section_range}` : ''
  const marker = `[part ${part.part_index}/${part.part_count}${section}]`
  // The source-derived description is authoritative. A user label is kept only
  // as a short suffix so it cannot displace the method/problem/evidence text.
  const suffix = userDescription?.trim() ? ` · ${userDescription.trim()}` : ''
  const budget = Math.max(40, 220 - marker.length - suffix.length - 1)
  return `${base.slice(0, budget).trim()} ${marker}${suffix}`.slice(0, 220)
}
