/**
 * useChatQueue — Message Queue Persistence & Helpers
 * ──────────────────────────────────────────────────
 * Self-contained types, constants, and pure helpers for the Claude chat
 * message queue. Extracted from claude-chat.vue to keep the SFC lean.
 *
 * These helpers do NOT touch any component reactive state — callers pass
 * the queue (a QueueItem[]) in and receive parsed data out, so the Vue
 * reactivity graph stays intact inside the component.
 */

import type { PermissionMode } from '~/utils/claude'

/** A single FIFO message-queue entry with a full context snapshot. */
export interface QueueItem {
  id: string
  text: string
  status: 'pending' | 'editing' | 'sending' | 'sent' | 'failed'
  created_at: number
  /** Context snapshot at queue time (ensures consistency even if user changes settings later) */
  cwd: string
  permissionMode: PermissionMode
  model: string
  reasoningEffort: string
  /** Original attachments (snapshot of names — actual files already uploaded at queue time) */
  attachmentNames: string[]
  /** Error message if status === 'failed' */
  error?: string
  /** Sent count increments each retry attempt */
  retryCount: number
}

/** localStorage persistence key */
export const QUEUE_STORAGE_KEY = 'claude-chat-queue'

/** Maximum auto-retries before marking as failed */
export const MAX_QUEUE_RETRIES = 3

/** Result of deserializing the queue from localStorage. */
export interface LoadedQueue {
  queue: QueueItem[]
  /** Highest numeric id suffix found, used to restore the id counter. */
  maxId: number
}

/**
 * Serialize queue items to localStorage.
 * Only stable fields are persisted (no transient send state beyond status).
 */
export function saveQueueToStorage(items: QueueItem[]): void {
  try {
    const serializable = items.map((item) => ({
      id: item.id,
      text: item.text,
      status: item.status,
      created_at: item.created_at,
      cwd: item.cwd,
      permissionMode: item.permissionMode,
      model: item.model,
      reasoningEffort: item.reasoningEffort,
      attachmentNames: item.attachmentNames,
      error: item.error,
      retryCount: item.retryCount,
    }))
    localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(serializable))
  } catch {
    /* localStorage may be full or unavailable */
  }
}

/**
 * Coerce an arbitrary parsed value into a QueueItem, restoring it from
 * persisted storage. Any item left in the 'sending' state (a send crashed
 * mid-flight) is reset back to 'pending'.
 */
const VALID_QUEUE_STATUSES = ['pending', 'editing', 'sending', 'sent', 'failed'] as const

/** Narrow an arbitrary string to a known queue status. */
function isQueueStatus(s: string): s is QueueItem['status'] {
  return (VALID_QUEUE_STATUSES as readonly string[]).includes(s)
}

function parseStoredItem(raw: unknown): QueueItem | null {
  if (!raw || typeof raw !== 'object') return null
  const rec = raw as Record<string, unknown>

  const id = typeof rec.id === 'string' ? rec.id : ''
  const text = typeof rec.text === 'string' ? rec.text : ''
  const created_at = typeof rec.created_at === 'number' ? rec.created_at : Date.now()
  const cwd = typeof rec.cwd === 'string' ? rec.cwd : ''
  const model = typeof rec.model === 'string' ? rec.model : ''
  const reasoningEffort = typeof rec.reasoningEffort === 'string' ? rec.reasoningEffort : ''
  const permissionMode = typeof rec.permissionMode === 'string'
    ? (rec.permissionMode as PermissionMode)
    : ('bypassPermissions' as PermissionMode)
  const retryCount = typeof rec.retryCount === 'number' ? rec.retryCount : 0

  const rawNames = rec.attachmentNames
  const attachmentNames = Array.isArray(rawNames)
    ? rawNames.filter((n): n is string => typeof n === 'string')
    : []

  const rawStatus = typeof rec.status === 'string' ? rec.status : 'pending'
  const status: QueueItem['status'] = isQueueStatus(rawStatus) ? rawStatus : 'pending'
  const wasSending = status === 'sending'
  const rawError = rec.error

  return {
    id,
    text,
    status: wasSending ? 'pending' : status,
    created_at,
    cwd,
    permissionMode,
    model,
    reasoningEffort,
    attachmentNames,
    retryCount,
    error: wasSending
      ? '上次发送中断，重试中...'
      : typeof rawError === 'string' ? rawError : undefined,
  }
}

export function loadQueueFromStorage(): LoadedQueue | null {
  try {
    const raw = localStorage.getItem(QUEUE_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return null

    const queue = parsed
      .map(parseStoredItem)
      .filter((item): item is QueueItem => item !== null)

    // Recover the highest numeric id suffix so new ids never collide.
    const maxId = queue.reduce((max: number, item: QueueItem) => {
      const num = parseInt(item.id.replace('q_', ''), 10)
      return Number.isNaN(num) ? max : Math.max(max, num)
    }, 0)

    return { queue, maxId }
  } catch {
    /* Corrupt localStorage entry — ignore */
    return null
  }
}

/** Human-readable label for a queue status (used in tooltips). */
export function statusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '等待发送',
    sending: '发送中…',
    sent: '已发送 ✓',
    failed: '发送失败 ✗',
    editing: '编辑中',
  }
  return map[status] || status
}
