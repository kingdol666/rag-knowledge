<template>
  <div class="automation-settings">
    <a-spin :spinning="loading">
      <!-- Header -->
      <div class="auto-header">
        <div class="auto-header-left">
          <ThunderboltOutlined class="auto-icon" />
          <span class="auto-title">{{ $t('automation.title') }}</span>
        </div>
        <a-tag v-if="status?.enabled" color="green">{{ $t('automation.enabled') }}</a-tag>
        <a-tag v-else color="default">{{ $t('automation.disabled') }}</a-tag>
      </div>

      <a-alert
        v-if="!activeKbId"
        type="info" show-icon
        :message="$t('automation.noKb')"
        style="margin-bottom: 12px;"
      />

      <template v-if="activeKbId && status">
        <!-- Switch -->
        <div class="auto-switch-row">
          <div>
            <div class="auto-switch-label">{{ $t('automation.enableLabel') }}</div>
            <div class="form-hint">{{ $t('automation.enableHint', { interval: status.interval }) }}</div>
          </div>
          <a-switch
            :checked="status.enabled"
            :loading="toggling"
            @change="(v: boolean) => handleToggle(v)"
          />
        </div>

        <!-- Counter / progress -->
        <a-descriptions size="small" :column="2" bordered style="margin-top: 12px;">
          <a-descriptions-item :label="$t('automation.counter')">
            <a-badge
              :count="status.doc_counter"
              :number-style="{ backgroundColor: status.enabled ? 'var(--kb-primary, #1677ff)' : '#999' }"
            />
          </a-descriptions-item>
          <a-descriptions-item :label="$t('automation.nextTrigger')">
            {{ $t('automation.nextTriggerValue', { n: status.next_trigger_at }) }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('automation.triggerCount')">
            {{ status.trigger_count }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('automation.totalDocs')">
            {{ status.total_docs ?? '-' }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('automation.lastTrigger')" :span="2">
            {{ status.last_trigger_at ? formatTime(status.last_trigger_at) : $t('automation.never') }}
          </a-descriptions-item>
        </a-descriptions>

        <!-- Progress bar: counter → next trigger -->
        <a-progress
          v-if="status.enabled"
          :percent="Math.min(100, Math.round((status.doc_counter % status.interval) / status.interval * 100))"
          size="small"
          :format="() => `${status.doc_counter % status.interval}/${status.interval}`"
          style="margin-top: 8px;"
        />

        <!-- Actions -->
        <div class="auto-actions">
          <a-button
            type="primary"
            :loading="summarizing"
            :disabled="!status.enabled && status.trigger_count === 0"
            @click="handleSummarize"
          >
            <FileDoneOutlined />
            {{ $t('automation.summarizeNow') }}
          </a-button>
          <a-button :disabled="!status.summary_exp_id" :loading="viewing" @click="openSummaryExp">
            <ExportOutlined />
            {{ $t('automation.viewSummary') }}
          </a-button>
        </div>

        <!-- Summary result feedback -->
        <a-alert
          v-if="summaryResult"
          :type="summaryResult.success ? 'success' : 'error'"
          :message="summaryResult.success
            ? $t('automation.summarizeOk', { action: summaryResult.action === 'created' ? $t('automation.actionCreated') : $t('automation.actionUpdated') })
            : $t('automation.summarizeFail')"
          :description="summaryResult.success
            ? $t('automation.summarizeDetail', { round: summaryResult.round, docs: summaryResult.docs_total })
            : summaryResult.error"
          closable
          style="margin-top: 12px;"
          @close="summaryResult = null"
        />

        <!-- History -->
        <div v-if="(status.history || []).length" class="auto-history">
          <div class="auto-history-title">{{ $t('automation.historyTitle') }}</div>
          <a-timeline style="margin-top: 8px;">
            <a-timeline-item v-for="(h, i) in [...status.history].reverse()" :key="i" :color="h.manual ? 'blue' : 'green'">
              <span>{{ $t('automation.historyItem', { round: h.round, action: h.action === 'created' ? $t('automation.actionCreated') : $t('automation.actionUpdated'), docs: h.docs_total }) }}</span>
              <span class="form-hint" style="margin-left: 6px;">{{ formatTime(h.at) }}</span>
            </a-timeline-item>
          </a-timeline>
        </div>
      </template>
    </a-spin>

    <!-- Summary experience viewer -->
    <a-modal
      v-model:open="showSummaryModal"
      :title="$t('automation.viewSummary')"
      :footer="null"
      :width="720"
    >
      <a-spin :spinning="viewing">
        <div v-if="summaryHtml" class="summary-markdown" v-html="summaryHtml"></div>
        <a-empty v-else-if="!viewing" />
      </a-spin>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { message } from 'ant-design-vue'
import { ThunderboltOutlined, FileDoneOutlined, ExportOutlined } from '@ant-design/icons-vue'
import { renderMarkdown } from '~/utils/markdown'

const { t } = useI18n()

const props = defineProps<{
  activeKbId: string
}>()

interface AutomationStatus {
  success: boolean
  enabled: boolean
  doc_counter: number
  interval: number
  next_trigger_at: number
  trigger_count: number
  summary_exp_id: string
  history: Array<{ round: number; at: string; action: string; docs_total: number; manual?: boolean }>
  last_trigger_at?: string
  total_docs?: number
}

const loading = ref(false)
const toggling = ref(false)
const summarizing = ref(false)
const viewing = ref(false)
const showSummaryModal = ref(false)
const summaryHtml = ref('')
const status = ref<AutomationStatus | null>(null)
const summaryResult = ref<{ success: boolean; action?: string; round?: number; docs_total?: number; error?: string } | null>(null)

async function fetchStatus() {
  if (!props.activeKbId) {
    status.value = null
    return
  }
  loading.value = true
  try {
    status.value = await $fetch<AutomationStatus>('/api/kb/automation', {
      query: { kb_id: props.activeKbId },
    })
  } catch (e: any) {
    console.warn(`[kb-automation] status fetch failed: ${e?.message || e}`)
    status.value = null
  } finally {
    loading.value = false
  }
}

async function handleToggle(enabled: boolean) {
  toggling.value = true
  try {
    await $fetch('/api/kb/automation/toggle', {
      method: 'POST',
      body: { kbId: props.activeKbId, enabled },
    })
    message.success(enabled ? t('automation.toggleOn') : t('automation.toggleOff'))
    await fetchStatus()
  } catch (e: any) {
    message.error(`${t('automation.loadFail')}: ${e?.message || e}`)
  } finally {
    toggling.value = false
  }
}

async function handleSummarize() {
  summarizing.value = true
  try {
    const r = await $fetch<any>('/api/kb/automation/summarize', {
      method: 'POST',
      body: { kbId: props.activeKbId },
    })
    summaryResult.value = r
    message.success(t('automation.summarizeOk', {
      action: r.action === 'created' ? t('automation.actionCreated') : t('automation.actionUpdated'),
    }))
    await fetchStatus()
  } catch (e: any) {
    summaryResult.value = { success: false, error: e?.message || String(e) }
  } finally {
    summarizing.value = false
  }
}

function openSummaryExp() {
  if (!status.value?.summary_exp_id || !props.activeKbId) return
  viewSummary()
}

/** 读取总结经验正文（experience/*.md 未注册 tree-fs，走 kb_id+doc_path 磁盘兜底） */
async function viewSummary() {
  viewing.value = true
  showSummaryModal.value = true
  summaryHtml.value = ''
  try {
    const res = await $fetch<any>('/api/kb/document', {
      query: {
        kb_id: props.activeKbId,
        doc_path: `experience/${status.value!.summary_exp_id}.md`,
        max_chars: 30000,
      },
    })
    summaryHtml.value = renderMarkdown(res.content || '')
  } catch (e: any) {
    message.error(`${t('automation.loadFail')}: ${e?.message || e}`)
    showSummaryModal.value = false
  } finally {
    viewing.value = false
  }
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

onMounted(fetchStatus)
watch(() => props.activeKbId, fetchStatus)

defineExpose({ fetchStatus })
</script>

<style scoped>
.automation-settings {
  padding: 4px 0;
}
.auto-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.auto-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.auto-icon {
  font-size: 18px;
  color: var(--kb-primary, #1677ff);
}
.auto-title {
  font-size: 15px;
  font-weight: 600;
}
.auto-switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--kb-border, #f0f0f0);
  border-radius: 8px;
}
.auto-switch-label {
  font-weight: 500;
}
.auto-actions {
  display: flex;
  gap: 8px;
  margin-top: 14px;
}
.auto-history {
  margin-top: 18px;
}
.auto-history-title {
  font-weight: 500;
  border-bottom: 1px solid var(--kb-border, #f0f0f0);
  padding-bottom: 6px;
}
.form-hint {
  font-size: 12px;
  color: var(--kb-fg-3, #999);
}
.summary-markdown {
  max-height: 60vh;
  overflow-y: auto;
  line-height: 1.7;
}
.summary-markdown :deep(h3) {
  margin: 14px 0 6px;
  font-size: 14px;
  font-weight: 600;
}
.summary-markdown :deep(ul) {
  padding-left: 20px;
}
</style>
