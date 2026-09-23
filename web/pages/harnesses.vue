<template>
  <div class="harness-hub-page">
    <!-- ═══ Header ═══ -->
    <header class="page-header">
      <div class="header-content">
        <div class="header-left">
          <div class="header-icon"><AppstoreOutlined /></div>
          <div class="header-text">
            <h1 class="header-title">Harness Hub</h1>
            <p class="header-subtitle">全部 Agent 执行引擎 · 可用性 · 诊断 · 聊天入口</p>
          </div>
        </div>
        <div class="header-actions">
          <a-statistic title="" :value="availableCount" class="hub-stat">
            <template #suffix><span class="hub-stat-suffix">/ {{ harnesses.length }} 可用</span></template>
          </a-statistic>
          <a-button class="action-btn" @click="loadCatalog" :loading="loading">
            <template #icon><ReloadOutlined /></template> 刷新
          </a-button>
          <a-button type="primary" ghost class="action-btn" @click="goChat()">
            <template #icon><MessageOutlined /></template> 打开聊天
          </a-button>
        </div>
      </div>
    </header>

    <!-- ═══ Summary bar ═══ -->
    <div class="hub-meta">
      <a-tag v-if="backendReachable" color="green">后端注册表已连接（探测为准）</a-tag>
      <a-tag v-else color="red">后端不可达 — 可用性为本地降级探测（仅命令存在性）</a-tag>
      <a-tag v-for="id in availableIds" :key="id" color="blue" class="avail-chip">{{ id }}</a-tag>
    </div>

    <!-- ═══ Harness cards ═══ -->
    <div class="hub-grid">
      <div
        v-for="h in harnesses"
        :key="h.id"
        class="harness-card"
        :class="{ unavailable: !h.available, selectable: h.available }"
        @click="h.available && goChat(h.id)"
      >
        <div class="card-head">
          <span class="card-icon">{{ engineIcon(h.id) }}</span>
          <div class="card-title-wrap">
            <div class="card-title">
              {{ h.label }}
              <a-tag v-if="h.hitl" color="purple" class="mini-tag">HITL</a-tag>
              <a-tag v-if="h.transport && h.transport !== 'none'" color="geekblue" class="mini-tag">{{ h.transport }}</a-tag>
            </div>
            <div class="card-sub">{{ h.id }}<span v-if="h.version"> · {{ h.version.slice(0, 60) }}</span></div>
          </div>
          <a-tag :color="statusColor(h)" class="status-tag">{{ statusText(h) }}</a-tag>
        </div>

        <div class="card-body">
          <p class="card-desc">{{ h.description }}</p>

          <div v-if="h.resolved_command" class="kv"><span class="k">命令</span><code class="v">{{ h.resolved_command }}</code></div>
          <div v-if="h.requires_env.length" class="kv">
            <span class="k">凭据 Env</span>
            <span class="v env-list">
              <a-tag v-for="e in h.requires_env" :key="e"
                     :color="credentialOk(h, e) ? 'green' : 'red'" class="env-tag">{{ e }}</a-tag>
            </span>
          </div>
          <div v-if="h.credentials" class="kv">
            <span class="k">凭据面</span>
            <span class="v">
              <a-tag :color="h.credentials.ready ? 'green' : 'red'" class="env-tag">
                {{ h.credentials.ready ? (h.credentials.store_ready ? '自有登录态/配置就绪' : 'env 就绪') : '未配置' }}
              </a-tag>
            </span>
          </div>
          <div class="kv">
            <span class="k">会话/权限</span>
            <span class="v">{{ h.historyMode === 'native-resume' ? '原生会话续接' : '平台历史回放' }}
              · {{ h.permissionModes.length }} 档权限模式</span>
          </div>

          <a-alert
            v-if="!h.available && h.hint"
            type="warning"
            show-icon
            class="card-hint"
            :message="h.hint"
          />
          <a-alert
            v-else-if="h.available && h.notes"
            type="info"
            show-icon
            class="card-hint"
            :message="h.notes"
          />
        </div>

        <div class="card-foot" @click.stop>
          <a-button size="small" @click="runDiagnose(h, false)" :loading="diagLoading[h.id]">
            诊断
          </a-button>
          <a-tooltip :title="h.available ? '真实引擎往返自测（发一条最小 prompt 验证全链路）' : '引擎不可用，无法自测'">
            <a-button size="small" type="primary" ghost :disabled="!h.available"
                      @click="runDiagnose(h, true)" :loading="diagLoading[h.id]">
              自测
            </a-button>
          </a-tooltip>
          <a-button size="small" type="primary" :disabled="!h.available" @click="goChat(h.id)">
            去聊天
          </a-button>
        </div>
      </div>
    </div>

    <!-- ═══ Diagnosis result modal ═══ -->
    <a-modal
      v-model:open="diagOpen"
      :title="`诊断报告 — ${diagTarget?.label || diagTarget?.id || ''}`"
      width="680px"
      :footer="null"
    >
      <div v-if="diagReport" class="diag-report">
        <div class="diag-summary">
          <a-tag :color="diagReport.diagnosis?.available ? 'green' : 'red'">
            {{ diagReport.diagnosis?.available ? '可用' : '不可用' }}
          </a-tag>
          <a-tag v-if="diagReport.diagnosis?.probe?.version">{{ diagReport.diagnosis.probe.version.slice(0, 60) }}</a-tag>
          <a-tag v-if="diagReport.diagnosis?.self_test?.ran"
                 :color="diagReport.diagnosis.self_test.success ? 'green' : 'red'">
            自测{{ diagReport.diagnosis.self_test.success ? '通过' : '失败' }}
            <template v-if="diagReport.diagnosis.self_test.elapsed"> · {{ diagReport.diagnosis.self_test.elapsed }}s</template>
          </a-tag>
          <a-tag v-else-if="diagReport.diagnosis?.self_test?.skipped" color="default">未自测</a-tag>
        </div>

        <div v-if="diagReport.diagnosis?.self_test?.reply" class="diag-reply">
          <div class="muted">自测回复：</div>
          <pre class="diag-reply-pre">{{ diagReport.diagnosis.self_test.reply }}</pre>
        </div>
        <div v-if="diagReport.diagnosis?.self_test?.error" class="diag-reply">
          <div class="muted">自测错误（{{ diagReport.diagnosis.self_test.error_code || 'unknown' }}）：</div>
          <pre class="diag-reply-pre err">{{ diagReport.diagnosis.self_test.error }}
{{ diagReport.diagnosis.self_test.hint || '' }}
{{ (diagReport.diagnosis.self_test.detail || '').slice(0, 400) }}</pre>
        </div>
        <a-alert v-if="diagReport.diagnosis?.issues?.length"
                 type="warning" show-icon class="diag-issue"
                 :message="diagReport.diagnosis.issues.join('；')" />
        <a-alert v-if="diagReport.diagnosis?.circuit_breaker?.tripped"
                 type="error" show-icon class="diag-issue"
                 message="熔断器已跳闸（连续失败 3 次，24h 后自动复位；重启后端可清）" />

        <details class="diag-raw">
          <summary class="muted">原始报告 (JSON)</summary>
          <pre class="diag-json">{{ JSON.stringify(diagReport.diagnosis, null, 2) }}</pre>
        </details>
      </div>
      <a-spin v-else />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  AppstoreOutlined, ReloadOutlined, MessageOutlined,
} from '@ant-design/icons-vue'
import { message as antMessage } from 'ant-design-vue'
import { ENGINE_MAP } from '~/utils/chat-engine'

interface PermissionModeInfo {
  id: string
  label: string
  desc: string
  mapping?: string
}
interface HarnessItem {
  id: string
  label: string
  description: string
  homepage: string
  installed: boolean
  available: boolean
  version: string
  resolved_command: string | null
  models: string[]
  capabilities: Record<string, boolean>
  requires_env: string[]
  credentials: { env_ready: boolean; store_ready: boolean; ready: boolean; env: Array<{ name: string; present: boolean }> } | null
  issues: string[]
  hint: string
  notes: string
  transport: string
  hitl: boolean
  chat: boolean
  permissionModes: PermissionModeInfo[]
  defaultMode: string
  historyMode: 'native-resume' | 'server-replay'
  promptLimitChars: number
}

const router = useRouter()
const harnesses = ref<HarnessItem[]>([])
const backendReachable = ref(true)
const loading = ref(false)
const diagLoading = reactive<Record<string, boolean>>({})
const diagOpen = ref(false)
const diagTarget = ref<HarnessItem | null>(null)
const diagReport = ref<any>(null)

const availableIds = computed(() => harnesses.value.filter(h => h.available).map(h => h.id))
const availableCount = computed(() => availableIds.value.length)

function engineIcon(id: string): string {
  return ENGINE_MAP[id]?.icon || '🔗'
}
function statusColor(h: HarnessItem): string {
  if (h.available) return 'green'
  return h.installed ? 'orange' : 'red'
}
function statusText(h: HarnessItem): string {
  if (h.available) return '可用'
  return h.installed ? '未配置' : '未安装'
}
function credentialOk(h: HarnessItem, envName: string): boolean {
  return !!h.credentials?.env?.find(e => e.name === envName)?.present
}

async function loadCatalog() {
  loading.value = true
  try {
    const res = await $fetch<{ harnesses: HarnessItem[]; backend_reachable: boolean }>('/api/harnesses')
    harnesses.value = res.harnesses || []
    backendReachable.value = res.backend_reachable !== false
    // D3 fix: first mount raced the backend probe cache and rendered 0/0
    // with no error. One quiet retry turns the transient empty state into data.
    if (harnesses.value.length === 0 && backendReachable.value) {
      await new Promise(r => setTimeout(r, 1200))
      const retry = await $fetch<{ harnesses: HarnessItem[]; backend_reachable: boolean }>('/api/harnesses')
      harnesses.value = retry.harnesses || []
      backendReachable.value = retry.backend_reachable !== false
    }
  } catch (e: any) {
    antMessage.error('加载 Harness 目录失败: ' + (e?.message || e))
  } finally {
    loading.value = false
  }
}

async function runDiagnose(h: HarnessItem, selfTest: boolean) {
  diagLoading[h.id] = true
  try {
    const res = await $fetch<any>('/api/harnesses/diagnose', {
      method: 'POST',
      body: { harness: h.id, selfTest },
    })
    diagTarget.value = h
    diagReport.value = res
    diagOpen.value = true
  } catch (e: any) {
    antMessage.error(`诊断失败: ${e?.data?.statusMessage || e?.statusMessage || e?.message || e}`)
  } finally {
    diagLoading[h.id] = false
  }
}

function goChat(engineId?: string) {
  if (engineId) {
    router.push({ path: '/claude-chat', query: { engine: engineId } })
  } else {
    router.push('/claude-chat')
  }
}

onMounted(loadCatalog)
</script>

<style scoped>
.harness-hub-page {
  min-height: 100vh;
  padding: 0 0 48px;
  color: var(--kb-fg);
}

/* header — matches the shared .page-header pattern */
.page-header { border-bottom: 1px solid var(--kb-border); }
.header-content {
  display: flex; align-items: center; justify-content: space-between;
  gap: 16px; padding: 18px 28px; flex-wrap: wrap;
}
.header-left { display: flex; align-items: center; gap: 14px; }
.header-icon {
  width: 44px; height: 44px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; color: #fff;
  background: linear-gradient(135deg, var(--kb-primary), var(--kb-gold));
  box-shadow: var(--kb-shadow-primary);
}
.header-title { margin: 0; font-size: 22px; font-weight: 700; letter-spacing: 0.2px; }
.header-subtitle { margin: 2px 0 0; font-size: 13px; color: var(--kb-fg-muted); }
.header-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.hub-stat :deep(.ant-statistic-content) { font-size: 20px; font-weight: 700; color: var(--kb-primary); }
.hub-stat-suffix { font-size: 12px; font-weight: 500; color: var(--kb-fg-muted); }

.hub-meta {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  padding: 12px 28px 0;
}
.avail-chip { font-family: var(--kb-mono, monospace); }

.hub-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
  padding: 18px 28px;
}
.harness-card {
  display: flex; flex-direction: column;
  background: var(--kb-card-bg, var(--kb-bg-soft, rgba(255, 255, 255, 0.03)));
  border: 1px solid var(--kb-border);
  border-radius: 14px;
  padding: 16px;
  transition: box-shadow 0.2s ease, transform 0.2s ease, border-color 0.2s ease;
}
.harness-card.selectable { cursor: pointer; }
.harness-card.selectable:hover {
  border-color: var(--kb-primary);
  box-shadow: var(--kb-shadow-primary);
  transform: translateY(-2px);
}
.harness-card.unavailable { opacity: 0.72; }

.card-head { display: flex; align-items: flex-start; gap: 10px; }
.card-icon { font-size: 26px; line-height: 1.2; }
.card-title-wrap { flex: 1; min-width: 0; }
.card-title { font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.mini-tag { font-size: 10px; line-height: 16px; margin: 0; }
.card-sub { font-size: 12px; color: var(--kb-fg-muted); margin-top: 2px; word-break: break-all; }
.status-tag { flex-shrink: 0; margin: 0; }

.card-body { flex: 1; margin-top: 10px; }
.card-desc { font-size: 12.5px; color: var(--kb-fg-muted); line-height: 1.6; margin: 0 0 8px; }
.kv { display: flex; align-items: baseline; gap: 8px; margin: 4px 0; font-size: 12px; }
.kv .k { color: var(--kb-fg-muted); flex-shrink: 0; width: 62px; text-align: right; }
.kv .v { word-break: break-all; }
.env-list { display: inline-flex; gap: 4px; flex-wrap: wrap; }
.env-tag { font-size: 10px; line-height: 16px; margin: 0; font-family: var(--kb-mono, monospace); }
.card-hint { margin-top: 10px; font-size: 12px; }
.card-hint :deep(.ant-alert-message) { font-size: 12px; }

.card-foot {
  display: flex; gap: 8px; justify-content: flex-end;
  margin-top: 12px; padding-top: 10px;
  border-top: 1px dashed var(--kb-border);
}

.diag-report { display: flex; flex-direction: column; gap: 10px; }
.diag-summary { display: flex; gap: 6px; flex-wrap: wrap; }
.diag-reply-pre {
  margin: 6px 0 0; padding: 10px; border-radius: 8px;
  background: var(--kb-bg-soft, rgba(127, 127, 127, 0.08));
  border: 1px solid var(--kb-border);
  font-size: 12px; white-space: pre-wrap; word-break: break-all;
  max-height: 200px; overflow: auto;
}
.diag-reply-pre.err { border-color: rgba(239, 68, 68, 0.4); }
.diag-issue { font-size: 12px; }
.diag-raw summary { cursor: pointer; font-size: 12px; }
.diag-json {
  margin-top: 8px; padding: 10px; border-radius: 8px;
  background: var(--kb-bg-soft, rgba(127, 127, 127, 0.08));
  border: 1px solid var(--kb-border);
  font-size: 11px; max-height: 320px; overflow: auto;
}
.muted { color: var(--kb-fg-muted); font-size: 12px; }
</style>
