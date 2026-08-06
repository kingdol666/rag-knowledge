/**
 * SOUL 训练 WebSocket composable — 实时接收训练事件并渲染。
 *
 * 用法:
 *   const ws = useSoulTraining()
 *   ws.connect('soul-马斯克', token)
 *   ws.events        // ref<TrainingEvent[]> — 响应式事件流
 *   ws.progress      // ref<TrainingProgress | null> — 最新进度
 *   ws.status        // ref<TrainingStatus>
 *   ws.disconnect()
 *
 * 连接: ws://backend:8765/api/v1/soul/ws/training/{soul_kb_id}?token=<token>
 */

import { ref, type Ref } from 'vue'

/** 训练进度数据(从后端 progress_cb 传来) */
export interface TrainingProgress {
  phase?: string
  type?: string
  round?: number
  rounds?: number
  msg?: string
  questions?: number
  memories?: number
  docs_processed?: number
  gaps?: number
  reward?: number
  converged?: boolean
  auto_applied?: number
  identity?: number
  values?: number
  thinking?: number
  language?: number
  knowledge?: number
  coherence?: number
  overall?: number
  optimized_docs?: string[]
  cognitions_absorbed?: number
  elapsed_sec?: number
  [key: string]: unknown
}

/** 详细训练事件(actor/critic/updater/optimize 阶段输出) */
export interface TrainingDetailEvent {
  ts?: string
  phase?: string
  type?: string
  round?: number
  data?: Record<string, unknown>
  [key: string]: unknown
}

/** WebSocket 消息类型 */
export interface TrainingMessage {
  type: 'progress' | 'event' | 'done' | 'error' | 'status'
  ts: string
  soul_kb_id: string
  task_id?: string
  progress?: TrainingProgress
  event?: TrainingDetailEvent
  status?: string
  result?: Record<string, unknown> | null
  error?: string
}

export type TrainingStatus = 'idle' | 'connecting' | 'connected' | 'training' | 'done' | 'error'

/** 六维评分 */
export interface DimensionScores {
  identity: number
  values: number
  thinking: number
  language: number
  knowledge: number
  coherence: number
  overall: number
}

let _socket: WebSocket | null = null
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null
let _currentSoul = ''
let _currentToken = ''

export function useSoulTraining() {
  const events: Ref<TrainingMessage[]> = ref([])
  const progress: Ref<TrainingProgress | null> = ref(null)
  const status: Ref<TrainingStatus> = ref('idle')
  const connected: Ref<boolean> = ref(false)
  const latestScores: Ref<DimensionScores | null> = ref(null)
  const rewardHistory: Ref<number[]> = ref([])

  /** 从 /api/config/frontend 获取 backend URL */
  async function getBackendUrl(): Promise<string> {
    try {
      const cfg = await $fetch<{ config?: { backend_url?: string } }>('/api/config/frontend')
      const url = cfg?.config?.backend_url || ''
      if (url) return url
    } catch { /* noop */ }
    // fallback: 同源(开发模式 Nuxt 代理)
    return ''
  }

  /** 构造 WebSocket URL */
  async function buildWsUrl(soulKbId: string, token: string): Promise<string> {
    const backendUrl = await getBackendUrl()
    // 转换 http(s):// → ws(s)://
    const wsBase = backendUrl
      ? backendUrl.replace(/^http/, 'ws')
      : `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}`
    const tokenParam = token ? `?token=${encodeURIComponent(token)}` : ''
    return `${wsBase}/api/v1/soul/ws/training/${encodeURIComponent(soulKbId)}${tokenParam}`
  }

  /** 从 progress 或 event 中提取六维评分 */
  function extractScores(data: TrainingProgress | TrainingDetailEvent): DimensionScores | null {
    const id = data.identity
    const val = data.values
    const thk = data.thinking
    const lang = data.language
    if (id !== undefined || val !== undefined || thk !== undefined) {
      return {
        identity: Number(id ?? 0),
        values: Number(val ?? 0),
        thinking: Number(thk ?? 0),
        language: Number(lang ?? 0),
        knowledge: Number(data.knowledge ?? 0),
        coherence: Number(data.coherence ?? 0),
        overall: Number(data.overall ?? data.reward ?? 0),
      }
    }
    return null
  }

  /** 连接 WebSocket */
  async function connect(soulKbId: string, token: string = '') {
    // 如果已连接到同一个 SOUL, 不重复连接
    if (_socket && _currentSoul === soulKbId && _socket.readyState === WebSocket.OPEN) {
      return
    }
    // 断开旧连接
    disconnect()

    _currentSoul = soulKbId
    _currentToken = token
    status.value = 'connecting'

    const url = await buildWsUrl(soulKbId, token)

    try {
      _socket = new WebSocket(url)
    } catch {
      status.value = 'error'
      return
    }

    _socket.onopen = () => {
      connected.value = true
      status.value = 'connected'
    }

    _socket.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data) as TrainingMessage
        handleMessage(data)
      } catch {
        // 非 JSON 消息, 忽略
      }
    }

    _socket.onclose = (ev) => {
      connected.value = false
      if (status.value !== 'done' && status.value !== 'error') {
        status.value = 'idle'
      }
      // 非正常关闭时自动重连(间隔 3s)
      if (ev.code !== 1000 && ev.code !== 4001 && ev.code !== 4004 && _currentSoul) {
        scheduleReconnect()
      }
    }

    _socket.onerror = () => {
      // onclose 会处理状态
    }
  }

  /** 处理收到的 WebSocket 消息 */
  function handleMessage(data: TrainingMessage) {
    events.value.push(data)
    // 限制事件缓冲(最多 500 条)
    if (events.value.length > 500) {
      events.value = events.value.slice(-400)
    }

    switch (data.type) {
      case 'status':
        if (data.status === 'connected') {
          status.value = 'connected'
        }
        break
      case 'progress':
        if (data.progress) {
          progress.value = data.progress
        }
        if (data.status === 'running') {
          status.value = 'training'
        }
        // 提取六维评分
        if (data.progress) {
          const scores = extractScores(data.progress)
          if (scores) latestScores.value = scores
          // reward 历史
          const reward = data.progress.reward
          if (reward !== undefined && data.progress.type === 'critic_score') {
            rewardHistory.value.push(Number(reward))
          }
        }
        break
      case 'event':
        // 详细事件已加入 events, 更新评分
        if (data.event?.phase === 'critic' && data.event?.type === 'critic_score') {
          const scores = extractScores(data.event)
          if (scores) latestScores.value = scores
          const reward = data.event.reward
          if (reward !== undefined) rewardHistory.value.push(Number(reward))
        }
        if (data.event?.phase === 'reward') {
          status.value = 'training'
        }
        break
      case 'done':
        status.value = 'done'
        if (data.result) progress.value = { result: data.result } as TrainingProgress
        break
      case 'error':
        status.value = 'error'
        break
    }
  }

  /** 自动重连 */
  function scheduleReconnect() {
    if (_reconnectTimer) return
    _reconnectTimer = setTimeout(() => {
      _reconnectTimer = null
      if (_currentSoul) {
        connect(_currentSoul, _currentToken)
      }
    }, 3000)
  }

  /** 断开连接 */
  function disconnect() {
    if (_reconnectTimer) {
      clearTimeout(_reconnectTimer)
      _reconnectTimer = null
    }
    _currentSoul = ''
    if (_socket) {
      try {
        _socket.onclose = null // 阻止重连
        _socket.close(1000)
      } catch { /* noop */ }
      _socket = null
    }
    connected.value = false
  }

  /** 清空事件 */
  function clearEvents() {
    events.value = []
    progress.value = null
    latestScores.value = null
    rewardHistory.value = []
    status.value = 'idle'
  }

  return {
    events,
    progress,
    status,
    connected,
    latestScores,
    rewardHistory,
    connect,
    disconnect,
    clearEvents,
  }
}
