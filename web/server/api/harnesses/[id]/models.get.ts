/**
 * GET /api/harnesses/[id]/models
 *
 * Per-harness model catalog + reasoning-effort levels for the chat UI.
 *  - dsh / hermes : ACP probe (session/new configOptions — the agent's own
 *            model catalog and reasoning_effort levels, per-model validated;
 *            both are ACP engines, results cached in-process for 5 min)
 *  - others: proxy to backend GET /api/v1/meditation/models?harness=… which
 *            discovers via each harness's official CLI command
 *            (omp models --json / opencode models / crush models /
 *             pi --list-models / cursor-agent models) with a static fallback.
 *
 * Response: { success, harness, source, models: [{id, name, thinking?}],
 *             reasoning_levels: [{id, label, description?}] }
 */
import { defineEventHandler, createError, getRouterParam, getQuery } from 'h3'
// $fetch imported explicitly: the Nitro global's type embeds the typed route
// table, which contains this very handler — TS then fails the whole chain
// with TS7022/TS7024 circular-inference errors.
import { $fetch } from 'ofetch'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'
import { HARNESS_CHAT_CATALOG } from '~/server/utils/harness-catalog'
import { acpProbeConfigOptions, type AcpConfigOptionSummary } from '~/server/engines/acp-engine'

// ── ACP probe in-process cache（探针每次要 spawn 一个引擎进程，约 3-5 秒） ──
interface AcpProbeCacheEntry { at: number; summary: AcpConfigOptionSummary | null }
const ACP_PROBE_TTL_MS = 5 * 60_000

function acpProbeCache(): Map<string, AcpProbeCacheEntry> {
  const g = globalThis as typeof globalThis & { __acpProbeCache?: Map<string, AcpProbeCacheEntry> }
  if (!g.__acpProbeCache) g.__acpProbeCache = new Map()
  return g.__acpProbeCache
}

async function acpProbeCached(id: string, force: boolean): Promise<AcpConfigOptionSummary | null> {
  const cache = acpProbeCache()
  if (!force) {
    const hit = cache.get(id)
    if (hit && Date.now() - hit.at < ACP_PROBE_TTL_MS) return hit.summary
  }
  const summary = await acpProbeConfigOptions(id)
  cache.set(id, { at: Date.now(), summary })
  return summary
}

export default defineEventHandler(async (event) => {
  const id = (getRouterParam(event, 'id') || '').trim()
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'harness id 必填' })
  }
  if (!HARNESS_CHAT_CATALOG[id] && id !== 'heuristic') {
    throw createError({ statusCode: 400, statusMessage: `Unknown harness: ${id}` })
  }

  const query = getQuery(event)
  const force = query.force === 'true' || query.force === '1'

  // ── dsh / hermes: ACP 原生 configOptions（模型目录 + 按模型校验的思考档位） ──
  if (id === 'dsh' || id === 'hermes') {
    const summary = await acpProbeCached(id, force)
    if (!summary) {
      return { success: true, harness: id, source: 'unavailable', models: [], reasoning_levels: [] }
    }
    return {
      success: true,
      harness: id,
      source: 'acp-config',
      models: summary.modelOptions.map(m => ({ id: m.value, name: m.name, group: m.group })),
      reasoning_levels: summary.reasoningEfforts.map(e => ({
        id: e.value, label: e.name, ...(e.description ? { description: e.description } : {}),
      })),
      current: { model: summary.currentModel, effort: summary.currentEffort },
    }
  }

  // ── 其余引擎：后端官方命令发现 ──
  const backendUrl = getDynamicBackendUrl()
  try {
    const res = await $fetch<any>(`${backendUrl}/api/v1/meditation/models`, {
      params: { harness: id, ...(force ? { force: 'true' } : {}) },
      timeout: 60_000,
    })
    return {
      success: true,
      harness: id,
      source: res?.source || 'static',
      models: res?.models || [],
      reasoning_levels: res?.reasoning_levels || [],
    }
  } catch (e: any) {
    return {
      success: false,
      harness: id,
      source: 'unavailable',
      models: [],
      reasoning_levels: [],
      error: e instanceof Error ? e.message : String(e),
    }
  }
})
