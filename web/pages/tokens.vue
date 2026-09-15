<template>
  <div class="tokens-page">
    <header class="page-header">
      <div class="header-content">
        <div class="header-left">
          <div class="header-icon"><KeyOutlined /></div>
          <div class="header-text">
            <h1 class="header-title">API Token 管理</h1>
            <p class="header-subtitle">
              为脚本与 CI 签发独立凭据，明文仅在创建时显示一次。
            </p>
          </div>
        </div>
      </div>
    </header>

    <div class="hint-card">
      <ApiOutlined class="hint-icon" />
      <p class="hint-text">
        调用任意 API 时在请求头携带
        <code>Authorization: Bearer &lt;token&gt;</code>
      </p>
    </div>

    <!-- Create -->
    <section class="panel create-card">
      <div class="panel-head">
        <PlusCircleOutlined class="panel-icon" />
        <h2 class="panel-title">创建新 Token</h2>
      </div>

      <form class="create-row" @submit.prevent="create">
        <a-input
          v-model:value="newName"
          class="name-input"
          placeholder="Token 名称，如：ci-robot / my-script"
          :maxlength="64"
          allow-clear
        />
        <a-select v-model:value="newTtl" class="ttl-select" :options="ttlOptions" />
        <a-button
          type="primary"
          class="create-btn"
          html-type="submit"
          :loading="busy"
          :disabled="!newName.trim() || busy"
        >
          <template #icon><KeyOutlined /></template>
          创建
        </a-button>
      </form>

      <Transition name="fresh-pop">
        <div v-if="freshToken" class="fresh">
          <div class="fresh-head">
            <CheckCircleFilled class="fresh-icon" />
            <strong>请立即复制（仅显示这一次）</strong>
            <a-button size="small" class="copy-btn" @click="copyToken">
              <template #icon><CopyOutlined /></template>
              {{ copied ? '已复制' : '复制' }}
            </a-button>
          </div>
          <code class="fresh-value">{{ freshToken }}</code>
        </div>
      </Transition>
    </section>

    <Transition name="fade">
      <div v-if="error" class="error">
        <ExclamationCircleOutlined />
        <span>{{ error }}</span>
      </div>
    </Transition>

    <!-- List -->
    <section class="panel list-card">
      <div class="panel-head">
        <SafetyCertificateOutlined class="panel-icon" />
        <h2 class="panel-title">已签发的 Token</h2>
        <span class="count-pill">{{ tokens.length }}</span>
      </div>

      <div v-if="loading" class="loading-state">
        <a-spin />
      </div>

      <EmptyState
        v-else-if="!tokens.length"
        :icon="KeyOutlined"
        title="还没有 Token"
        hint="创建一个开始调用 API。"
      />

      <template v-else>
        <!-- Desktop: table -->
        <div class="table-wrap">
          <table class="token-table">
            <thead>
              <tr>
                <th>名称</th>
                <th>前缀</th>
                <th>创建时间</th>
                <th>过期时间</th>
                <th>最近使用</th>
                <th>状态</th>
                <th class="th-action"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in tokens" :key="t.id">
                <td class="td-name">{{ t.name }}</td>
                <td><code>{{ t.token_prefix }}…</code></td>
                <td class="td-mono">{{ fmt(t.created_at) }}</td>
                <td class="td-mono">{{ t.expires_at ? fmt(t.expires_at) : '永不过期' }}</td>
                <td class="td-mono">{{ t.last_used_at ? fmt(t.last_used_at) : '从未使用' }}</td>
                <td><span class="status-pill" :class="status(t).cls">{{ status(t).label }}</span></td>
                <td class="td-action">
                  <a-popconfirm
                    v-if="!t.revoked_at"
                    title="确定撤销该 Token？"
                    ok-text="撤销"
                    cancel-text="取消"
                    @confirm="revoke(t.id)"
                  >
                    <a-button size="small" danger type="text" class="revoke-btn">撤销</a-button>
                  </a-popconfirm>
                  <span v-else class="dash">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Mobile: cards (a 7-column table can't be read on a phone) -->
        <ul class="token-cards">
          <li v-for="t in tokens" :key="t.id" class="token-card">
            <div class="tc-top">
              <span class="tc-name">{{ t.name }}</span>
              <span class="status-pill" :class="status(t).cls">{{ status(t).label }}</span>
            </div>
            <code class="tc-prefix">{{ t.token_prefix }}…</code>
            <dl class="tc-meta">
              <div><dt>创建</dt><dd>{{ fmt(t.created_at) }}</dd></div>
              <div><dt>过期</dt><dd>{{ t.expires_at ? fmt(t.expires_at) : '永不过期' }}</dd></div>
              <div><dt>最近使用</dt><dd>{{ t.last_used_at ? fmt(t.last_used_at) : '从未使用' }}</dd></div>
            </dl>
            <a-popconfirm
              v-if="!t.revoked_at"
              title="确定撤销该 Token？"
              ok-text="撤销"
              cancel-text="取消"
              @confirm="revoke(t.id)"
            >
              <a-button size="small" danger block class="revoke-btn">撤销</a-button>
            </a-popconfirm>
          </li>
        </ul>
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import {
  KeyOutlined, PlusCircleOutlined, CopyOutlined, CheckCircleFilled,
  ExclamationCircleOutlined, SafetyCertificateOutlined, ApiOutlined,
} from '@ant-design/icons-vue'
import EmptyState from '~/components/EmptyState.vue'

const { listTokens, createToken, revokeToken } = useAuth()

const tokens = ref<any[]>([])
const newName = ref('')
const newTtl = ref(30)
const freshToken = ref('')
const copied = ref(false)
const busy = ref(false)
const loading = ref(true)
const error = ref('')

const ttlOptions = [
  { value: 1, label: '1 天' },
  { value: 7, label: '7 天' },
  { value: 30, label: '30 天' },
  { value: 90, label: '90 天' },
  { value: 365, label: '1 年' },
  { value: 0, label: '永不过期' },
]

function fmt(iso: string) {
  try { return new Date(iso).toLocaleString() } catch { return iso }
}
function status(t: any) {
  if (t.revoked_at) return { label: '已撤销', cls: 'revoked' }
  if (t.expires_at && new Date(t.expires_at) < new Date()) return { label: '已过期', cls: 'expired' }
  return { label: '有效', cls: 'active' }
}

async function copyToken() {
  try {
    await navigator.clipboard.writeText(freshToken.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch { /* clipboard may be blocked — the value is selectable anyway */ }
}

async function load() {
  loading.value = true
  try { tokens.value = await listTokens() }
  catch (e: any) { error.value = e?.data?.message || e?.message || '加载失败' }
  finally { loading.value = false }
}

async function create() {
  busy.value = true; error.value = ''; freshToken.value = ''
  try {
    const res: any = await createToken(newName.value.trim(), newTtl.value)
    freshToken.value = res.token
    newName.value = ''
    await load()
  } catch (e: any) {
    error.value = e?.data?.message || e?.message || '创建失败'
  } finally { busy.value = false }
}

async function revoke(id: string) {
  try { await revokeToken(id); await load() }
  catch (e: any) { error.value = e?.data?.message || e?.message || '撤销失败' }
}

onMounted(load)
</script>

<style scoped>
.tokens-page {
  max-width: 1020px;
  margin: 0 auto;
  padding: clamp(4px, 1.4cqi, 12px) 0 24px;
  animation: kb-fade-in 0.4s var(--kb-ease-out);
}

/* ── Header ─────────────────────────────────────────────── */
.page-header { margin-bottom: 18px; animation: kb-fade-up 0.5s var(--kb-ease-out) both; }
.header-content { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.header-left { display: flex; align-items: center; gap: 16px; min-width: 0; }
.header-icon {
  width: 54px; height: 54px; border-radius: 15px;
  display: grid; place-items: center; font-size: 25px; color: #fff;
  background: linear-gradient(135deg, var(--kb-gold-deep), var(--kb-gold));
  box-shadow: var(--kb-shadow-gold);
  flex-shrink: 0;
}
.header-text { min-width: 0; }
.header-title {
  font-size: var(--kb-fs-h1, 26px); font-weight: 700;
  color: var(--kb-fg); margin: 0 0 3px;
  letter-spacing: -0.5px; font-family: var(--kb-font-serif);
}
.header-subtitle { font-size: var(--kb-fs-sm, 14px); color: var(--kb-fg-3); margin: 0; }

.hint-card {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 16px; margin-bottom: 18px;
  background: var(--kb-gold-soft);
  border: 1px solid rgba(184, 148, 90, 0.32);
  border-radius: var(--kb-radius);
  animation: kb-fade-up 0.5s 0.04s var(--kb-ease-out) both;
}
.hint-icon { font-size: 17px; color: var(--kb-gold-deep); flex-shrink: 0; }
.hint-text { margin: 0; font-size: var(--kb-fs-sm, 13px); color: var(--kb-fg-2); line-height: 1.6; }
.hint-text code {
  font-family: var(--kb-font-mono); font-size: 12px;
  background: var(--kb-bg-elevated); border: 1px solid var(--kb-border);
  padding: 2px 7px; border-radius: 5px; color: var(--kb-primary);
  overflow-wrap: anywhere;
}

/* ── Panels ─────────────────────────────────────────────── */
.panel {
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius-lg);
  box-shadow: var(--kb-shadow-sm);
  margin-bottom: 18px;
  overflow: hidden;
  animation: kb-fade-up 0.5s var(--kb-ease-out) both;
}
.create-card { animation-delay: 0.08s; }
.list-card { animation-delay: 0.14s; }

.panel-head {
  display: flex; align-items: center; gap: 9px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--kb-border);
  background: linear-gradient(180deg, var(--kb-bg-subtle), transparent);
}
.panel-icon { font-size: 17px; color: var(--kb-primary); flex-shrink: 0; }
.panel-title {
  font-size: var(--kb-fs-h3, 16px); font-weight: 700;
  color: var(--kb-fg); margin: 0;
  font-family: var(--kb-font-serif); letter-spacing: -0.2px;
}
.count-pill {
  margin-left: auto;
  font-size: 11.5px; font-weight: 700;
  color: var(--kb-primary);
  background: var(--kb-primary-soft);
  border-radius: 999px; padding: 2px 10px;
}

/* ── Create row ─────────────────────────────────────────── */
.create-row {
  display: flex; gap: 10px; align-items: center;
  padding: 18px 20px;
  flex-wrap: wrap;
}
.name-input { flex: 1 1 240px; min-width: 0; height: 40px; }
.ttl-select { flex: 0 0 130px; width: 130px; }
.ttl-select :deep(.ant-select-selector) { height: 40px !important; }
.ttl-select :deep(.ant-select-selection-item) { line-height: 38px !important; }
.create-btn { height: 40px; padding-inline: 22px; font-weight: 600; }

.fresh {
  margin: 0 20px 20px;
  padding: 14px 16px;
  border-radius: var(--kb-radius);
  background: var(--kb-emerald-soft);
  border: 1px solid var(--kb-emerald);
  overflow: hidden;
}
.fresh-head {
  display: flex; align-items: center; gap: 8px;
  font-size: var(--kb-fs-sm, 13px); color: var(--kb-emerald); font-weight: 700;
  margin-bottom: 10px; flex-wrap: wrap;
}
.fresh-icon { font-size: 15px; }
.copy-btn { margin-left: auto; }
.fresh-value {
  display: block;
  font-family: var(--kb-font-mono); font-size: 12.5px;
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  padding: 10px 12px; border-radius: var(--kb-radius-sm);
  color: var(--kb-fg); overflow-wrap: anywhere;
  user-select: all;
}
.fresh-pop-enter-active { transition: opacity 0.28s var(--kb-ease-out), transform 0.28s var(--kb-ease-out); }
.fresh-pop-enter-from { opacity: 0; transform: translateY(-6px) scale(0.99); }

.error {
  display: flex; align-items: center; gap: 9px;
  margin-bottom: 18px; padding: 12px 16px;
  border-radius: var(--kb-radius);
  background: var(--kb-rose-soft);
  border: 1px solid var(--kb-rose);
  color: var(--kb-rose);
  font-size: var(--kb-fs-sm, 13px);
}

/* ── Table (desktop) ────────────────────────────────────── */
.table-wrap { overflow-x: auto; }
.token-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.token-table th {
  text-align: left; padding: 11px 16px;
  font-family: var(--kb-font-serif); font-size: 12.5px; font-weight: 700;
  letter-spacing: 0.03em; color: var(--kb-gold-deep);
  background: var(--kb-bg-subtle);
  border-bottom: 1px solid var(--kb-border);
  white-space: nowrap;
}
.token-table td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--kb-border);
  color: var(--kb-fg-2);
  vertical-align: middle;
}
.token-table tbody tr { transition: background 0.18s var(--kb-ease); }
.token-table tbody tr:hover { background: var(--kb-primary-tint); }
.token-table tbody tr:last-child td { border-bottom: none; }
.td-name {
  font-weight: 600; color: var(--kb-fg);
  max-width: 190px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.td-mono { font-family: var(--kb-font-mono); font-size: 12px; color: var(--kb-fg-3); white-space: nowrap; }
.td-action { text-align: right; }
.th-action { width: 90px; }
.token-table code, .tc-prefix {
  font-family: var(--kb-font-mono); font-size: 12px;
  background: var(--kb-bg-subtle); border: 1px solid var(--kb-border);
  padding: 2px 7px; border-radius: 5px; color: var(--kb-fg-2);
}
.dash { color: var(--kb-fg-mute); }

.status-pill {
  display: inline-flex; align-items: center;
  font-size: 11.5px; font-weight: 700;
  padding: 3px 10px; border-radius: 999px;
  border: 1px solid transparent; white-space: nowrap;
}
.status-pill.active { color: var(--kb-emerald); background: var(--kb-emerald-soft); border-color: var(--kb-emerald); }
/* --kb-amber on --kb-amber-soft measures 3.12:1 in light mode, under AA for
   small text. --kb-gold-deep is the same warm hue at 5.6:1. */
.status-pill.expired { color: var(--kb-gold-deep); background: var(--kb-amber-soft); border-color: var(--kb-gold); }
.status-pill.revoked { color: var(--kb-rose); background: var(--kb-rose-soft); border-color: var(--kb-rose); }
.revoke-btn { font-weight: 600; }

/* ── Cards (mobile) ─────────────────────────────────────── */
.token-cards { display: none; list-style: none; margin: 0; padding: 12px; gap: 12px; flex-direction: column; }
.token-card {
  display: flex; flex-direction: column; gap: 10px;
  padding: 14px;
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius);
  background: var(--kb-bg);
}
.tc-top { display: flex; align-items: center; gap: 10px; }
.tc-name {
  font-size: 14px; font-weight: 700; color: var(--kb-fg);
  flex: 1; min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.tc-prefix { align-self: flex-start; overflow-wrap: anywhere; }
.tc-meta { display: flex; flex-direction: column; gap: 6px; margin: 0; }
.tc-meta > div { display: flex; align-items: baseline; gap: 10px; }
.tc-meta dt { font-size: 11px; color: var(--kb-fg-mute); text-transform: uppercase; letter-spacing: 0.04em; flex: 0 0 62px; margin: 0; }
.tc-meta dd { margin: 0; font-size: 12.5px; color: var(--kb-fg-2); font-family: var(--kb-font-mono); }

.loading-state { display: grid; place-items: center; padding: 48px; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.25s var(--kb-ease-out); }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ── Adaptive: swap table → cards when the reading column is narrow ── */
@container (max-width: 780px) {
  .table-wrap { display: none; }
  .token-cards { display: flex; }
}
@container (max-width: 620px) {
  .header-icon { width: 44px; height: 44px; font-size: 20px; border-radius: 12px; }
  .header-title { font-size: 21px; }
  .create-row { flex-direction: column; align-items: stretch; padding: 16px; }
  .name-input, .ttl-select, .create-btn { flex: 1 1 auto; width: 100%; }
  .ttl-select { width: 100%; }
  .fresh { margin: 0 16px 16px; }
  .panel-head { padding: 14px 16px; }
}
@container (max-width: 420px) {
  .hint-card { align-items: flex-start; }
  .tc-meta dt { flex-basis: 54px; font-size: 10px; }
}
</style>
