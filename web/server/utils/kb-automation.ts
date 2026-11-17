import { getDynamicBackendUrl, getDynamicAuthConfig } from './dynamic-config'

/**
 * KB automation helper (2026-10-07) — 自动经验总结机制的 web 层封装。
 *
 * 职责边界：
 * - 代理端点（GET/POST /api/kb/automation/*）：前端 → 本封装 → 后端
 *   /api/v1/automation/*，注入 Bearer（前端不接触后端地址与令牌）
 * - 入库钩子 notifyKbIngest：由 POST /api/kb/documents/create 在落盘成功后
 *   fire-and-forget 调用；**fail-open**——自动化机制任何故障只打日志，
 *   绝不阻断文档入库主流程
 */

export interface KbAutomationStatus {
  success: boolean
  kb_id: string
  enabled: boolean
  doc_counter: number
  interval: number
  next_trigger_at: number
  trigger_count: number
  summary_exp_id: string
  docs_since_summary: Array<{ path: string; title: string; at: string; count: number }>
  history: Array<Record<string, unknown>>
  last_trigger_at?: string
  total_docs?: number
  error?: string
}

function backendAuthHeaders(): Record<string, string> {
  const auth = getDynamicAuthConfig()
  return auth.token ? { Authorization: `Bearer ${auth.token}` } : {}
}

async function backendAutomationFetch<T>(
  path: string,
  init?: { method?: string; body?: unknown },
): Promise<T> {
  return await $fetch<T>(`${getDynamicBackendUrl()}${path}`, {
    method: init?.method || 'GET',
    headers: backendAuthHeaders(),
    body: init?.body,
    timeout: 30000,
  })
}

/** 查询 KB 自动化状态（代理 GET /api/v1/automation/{kb_id}）。 */
export function fetchKbAutomationStatus(kbId: string): Promise<KbAutomationStatus> {
  return backendAutomationFetch(`/api/v1/automation/${encodeURIComponent(kbId)}`)
}

/** 开关自动经验总结（代理 POST /api/v1/automation/{kb_id}/toggle）。 */
export function toggleKbAutomation(kbId: string, enabled: boolean) {
  return backendAutomationFetch(`/api/v1/automation/${encodeURIComponent(kbId)}/toggle`, {
    method: 'POST',
    body: { enabled },
  })
}

/** 手动触发一次经验总结（代理 POST /api/v1/automation/{kb_id}/summarize）。 */
export function summarizeKbAutomation(kbId: string) {
  return backendAutomationFetch(`/api/v1/automation/${encodeURIComponent(kbId)}/summarize`, {
    method: 'POST',
  })
}

/**
 * 入库通知（fail-open，fire-and-forget）。调用方不 await、不 catch 也安全：
 * 内部已吞掉所有异常，只留 console.warn 审计痕迹。
 */
export function notifyKbIngest(
  kbId: string,
  payload: { doc_path?: string; title?: string; doc_count?: number },
): Promise<unknown> {
  return backendAutomationFetch(`/api/v1/automation/${encodeURIComponent(kbId)}/ingest`, {
    method: 'POST',
    body: { doc_path: payload.doc_path || '', title: payload.title || '', doc_count: payload.doc_count || 1 },
  }).catch((e: any) => {
    console.warn(`[kb-automation] ingest notify failed (fail-open): ${e?.message || e}`)
    return null
  })
}
