<template>
  <div class="meditation-settings">
    <a-spin :spinning="loading">
      <!-- Header -->
      <div class="med-header">
        <div class="med-header-left">
          <ExperimentOutlined class="med-icon" />
          <span class="med-title">{{ $t('meditation.title') }}</span>
        </div>
        <a-tag v-if="config.enabled" color="green">{{ $t('meditation.enabled') }}</a-tag>
        <a-tag v-else color="default">{{ $t('meditation.disabled') }}</a-tag>
      </div>

      <!-- Run status -->
      <div v-if="runStatus" class="med-status-bar">
        <a-descriptions size="small" :column="2" bordered>
          <a-descriptions-item :label="$t('meditation.lastRun')">{{ runStatus.last_run_at || $t('meditation.neverRun') }}</a-descriptions-item>
          <a-descriptions-item :label="$t('meditation.lastStatus')">
            <a-tag v-if="runStatus.last_run_status === 'completed'" color="green">{{ $t('meditation.statusCompleted') }}</a-tag>
            <a-tag v-else-if="runStatus.last_run_status === 'failed'" color="red">{{ $t('meditation.statusFailed') }}</a-tag>
            <a-tag v-else-if="runStatus.last_run_status === 'running'" color="blue">{{ $t('meditation.statusRunning') }}</a-tag>
            <span v-else>{{ runStatus.last_run_status || '-' }}</span>
          </a-descriptions-item>
          <a-descriptions-item :label="$t('meditation.totalRuns')">{{ runStatus.total_runs }}</a-descriptions-item>
          <a-descriptions-item :label="$t('meditation.totalExp')">{{ runStatus.total_experiences_generated }}</a-descriptions-item>
        </a-descriptions>
      </div>

      <!-- Config form -->
      <a-form :model="config" layout="vertical" class="med-form">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item :label="$t('meditation.enableLabel')">
              <a-switch v-model:checked="config.enabled" />
              <span class="form-hint ml-2">{{ config.enabled ? $t('meditation.enabledHintOn') : $t('meditation.enabledHintOff') }}</span>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item :label="$t('meditation.autoPublish')">
              <a-switch v-model:checked="config.auto_publish" />
              <span class="form-hint ml-2">{{ $t('meditation.autoPublishHint') }}</span>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item :label="$t('meditation.incremental')">
              <a-switch v-model:checked="config.incremental_enabled" />
              <span class="form-hint ml-2">{{ $t('meditation.incrementalHint') }}</span>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item :label="$t('meditation.harness')">
              <a-select
                v-model:value="config.harness"
                :loading="harnessLoading"
                show-search
                option-filter-prop="label"
              >
                <a-select-option
                  v-for="h in harnessOptions"
                  :key="h.id"
                  :value="h.id"
                  :label="h.label"
                  :disabled="h.process_model !== 'inprocess' && !h.installed"
                >
                  <span
                    :style="h.installed || h.process_model === 'inprocess'
                      ? '' : 'color: var(--kb-fg-3, #999); text-decoration: line-through;'"
                    :title="engineText(h, 'description') + (engineText(h, 'notes') ? ' · ' + engineText(h, 'notes') : '')"
                  >
                    <template v-if="h.installed || h.process_model === 'inprocess'">✅</template>
                    <template v-else>❌</template>
                    {{ engineText(h, 'label') }}
                    <a-tag v-if="h.installed || h.process_model === 'inprocess'" color="green" style="margin-left:6px">
                      {{ $t('meditation.harnessInstalled') }}
                    </a-tag>
                    <a-tag v-else color="red" style="margin-left:6px">
                      {{ $t('meditation.harnessNotInstalled') }}
                    </a-tag>
                    <a-tag v-if="h.default" color="blue" style="margin-left:2px">{{ $t('meditation.harnessDefault') }}</a-tag>
                  </span>
                </a-select-option>
              </a-select>
              <div v-if="activeHarnessInfo" class="form-hint" style="display:block;">
                {{ engineText(activeHarnessInfo, 'description') }}
                <template v-if="activeHarnessInfo.requires_env?.length">
                  · {{ $t('meditation.harnessEnvHint') }}: {{ activeHarnessInfo.requires_env.join(' | ') }}
                </template>
                <template v-if="activeHarnessInfo.capabilities?.context_stats"> · {{ $t('meditation.harnessUsageStats') }}</template>
              </div>
              <a-alert
                v-if="activeHarnessInfo && !activeHarnessInfo.installed && activeHarnessInfo.process_model !== 'inprocess'"
                type="warning"
                show-icon
                style="margin-top:8px"
                :message="$t('meditation.harnessNotInstalled')"
                :description="engineText(activeHarnessInfo, 'notes') || engineText(activeHarnessInfo, 'description')"
              />
              <a-alert
                v-else-if="activeHarnessInfo && activeHarnessInfo.installed && activeHarnessInfo.process_model !== 'inprocess' && missingEnv(activeHarnessInfo).length"
                type="warning"
                show-icon
                style="margin-top:8px"
                :message="$t('meditation.harnessNotConfigured')"
                :description="missingEnv(activeHarnessInfo).join(' | ')"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item :label="$t('meditation.model')">
              <a-select v-model:value="config.model">
                <a-select-option
                  v-for="m in availableModels"
                  :key="m.value"
                  :value="m.value"
                >
                  {{ m.label }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item :label="$t('meditation.intervalHours')">
              <a-input-number
                v-model:value="config.interval_hours"
                :min="0"
                :max="168"
                :step="1"
                style="width: 100%"
              />
              <span class="form-hint ml-2">{{ $t('meditation.intervalZeroHint') }}</span>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item :label="$t('meditation.minCluster')">
              <a-input-number
                v-model:value="config.min_cluster_count"
                :min="1"
                :max="100"
                :step="1"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item :label="$t('meditation.maxDrafts')">
              <a-input-number
                v-model:value="config.max_drafts_per_run"
                :min="1"
                :max="50"
                :step="1"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item :label="$t('meditation.maxBudget')">
              <a-input-number
                v-model:value="config.max_budget_usd"
                :min="0"
                :max="100"
                :step="0.5"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>

      <!-- Actions -->
      <div class="med-actions">
        <a-button
          type="primary"
          :loading="running"
          :disabled="!activeKbId || (activeHarnessInfo && !activeHarnessInfo.installed && activeHarnessInfo.process_model !== 'inprocess')"
          @click="handleRun"
        >
          <ThunderboltOutlined />
          {{ $t('meditation.runNow') }}
        </a-button>
        <a-button
          type="default"
          :loading="saving"
          :disabled="!activeKbId"
          @click="handleSave"
        >
          <SaveOutlined />
          {{ $t('meditation.saveConfig') }}
        </a-button>
      </div>

      <!-- Run result feedback -->
      <a-alert
        v-if="runResult"
        :type="runResult.success ? 'success' : 'error'"
        :message="runResult.success ? $t('meditation.triggerSuccess') : $t('meditation.triggerFailed')"
        :description="runResult.success ? `Run ID: ${runResult.run_id || 'N/A'}` : runResult.error"
        closable
        style="margin-top: 16px;"
        @close="runResult = null"
      />
      <a-alert
        v-if="saveResult"
        :type="saveResult.success ? 'success' : 'error'"
        :message="saveResult.success ? $t('meditation.saveSuccess') : $t('meditation.saveFailed')"
        :description="saveResult.error || ''"
        closable
        style="margin-top: 16px;"
        @close="saveResult = null"
      />
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { message } from 'ant-design-vue'
import { ExperimentOutlined, ThunderboltOutlined, SaveOutlined } from '@ant-design/icons-vue'
import type { MeditationConfig, MeditationRunStatus } from '~/types/knowledge-base-yaml'

const { t, te } = useI18n()

const props = defineProps<{
  activeKbId: string
}>()

const loading = ref(false)
const saving = ref(false)
const running = ref(false)
const harnessLoading = ref(false)
const runResult = ref<{ success: boolean; run_id?: string; error?: string } | null>(null)
const saveResult = ref<{ success: boolean; error?: string } | null>(null)

const config = ref<MeditationConfig>({
  enabled: false,
  harness: 'omp',
  model: '',       // Empty = use engine default (OMP: deepseek-v4-pro, Claude: sonnet)
  interval_hours: 24,
  min_cluster_count: 2,
  max_drafts_per_run: 3,
  max_budget_usd: 0.05,
  auto_publish: false,
  incremental_enabled: true,
})

const runStatus = ref<MeditationRunStatus>({
  last_run_at: null,
  last_run_status: null,
  total_runs: 0,
  total_experiences_generated: 0,
})

interface HarnessOption {
  id: string
  label: string
  description: string
  process_model: string
  capabilities: Record<string, boolean>
  requires_env: string[]
  notes: string
  models: string[]
  installed: boolean
  version?: string
  default?: boolean
}
// 注册表派生选项（后端 /harnesses 单一事实源）
const harnessOptions = ref<HarnessOption[]>([])
const activeHarnessInfo = computed(() =>
  harnessOptions.value.find(h => h.id === config.value.harness) || null
)
// 引擎文案走 i18n（harness.engines.<id>.*），注册表值作回退 —— 中英双语
function engineText(h: HarnessOption | null, field: 'label' | 'description' | 'notes'): string {
  if (!h) return ''
  const key = `harness.engines.${h.id}.${field}`
  return te(key) ? t(key) : String((h as any)[field] || '')
}
function missingEnv(h: HarnessOption): string[] {
  return (h.requires_env || []).filter((n: string) => !n.includes('|'))
}

// 当前引擎的模型目录（切引擎自动刷新）
const modelsLoading = ref(false)
const harnessModels = ref<Array<{ id: string; name: string; provider: string }>>([])
async function loadHarnessModels(harness: string) {
  if (!harness) return
  modelsLoading.value = true
  try {
    const res = await $fetch<any>('/api/meditation/models', { params: { harness } })
    if (res?.success && res.models) {
      harnessModels.value = res.models
    }
  } catch {
    harnessModels.value = []
  }
  modelsLoading.value = false
}
// Dynamic model list based on harness
const availableModels = computed(() => {
  const defaultOption = { value: '', label: t('meditation.modelDefault') }
  const fromHarness = harnessModels.value
    .filter(m => m.id)
    .map(m => ({ value: m.id, label: m.provider ? `${m.name} (${m.provider})` : m.name }))
  if (fromHarness.length > 0) return [defaultOption, ...fromHarness]
  // 引擎目录为空时的静态兜底（claude 常用模型）
  return [
    defaultOption,
    { value: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
    { value: 'claude-opus-4-20250514', label: 'Claude Opus 4' },
    { value: 'claude-haiku-4-20250514', label: 'Claude Haiku 4' },
  ]
})
/** Load meditation config + run status + OMP models from backend */
async function loadConfig() {
  if (!props.activeKbId) return
  loading.value = true
  try {
    const res = await $fetch<any>('/api/kb/meditation', {
      params: { kbId: props.activeKbId },
    })
    if (res?.success && res.config) {
      config.value = { ...config.value, ...res.config }
    }
    if (res?.run_status) {
      runStatus.value = { ...runStatus.value, ...res.run_status }
    }
    // Fetch harness registry（单一事实源：全部引擎 + 可用性 + 能力面）
    const hRes = await $fetch<any>('/api/meditation/harnesses')
    if (hRes?.success && hRes.harnesses) {
      harnessOptions.value = hRes.harnesses.map((h: any) => ({
        ...h,
        default: h.id === (hRes.default || 'omp'),
      }))
    }
    // Fetch current harness model catalog
    if (config.value.harness) {
      await loadHarnessModels(config.value.harness)
    }
  } catch (err: any) {
    console.debug('Meditation config load skipped:', err?.message)
  }
  loading.value = false
}

/** Save meditation config */
async function handleSave() {
  if (!props.activeKbId) return
  saving.value = true
  saveResult.value = null
  try {
    const res = await $fetch<any>('/api/kb/meditation', {
      method: 'PUT',
      body: { kb_id: props.activeKbId, config: config.value },
    })
    if (res?.success) {
      saveResult.value = { success: true }
      message.success(t('meditation.saveSuccess'))
    } else {
      saveResult.value = { success: false, error: res?.error || t('meditation.unknownError') }
    }
  } catch (err: any) {
    saveResult.value = { success: false, error: err?.message || t('meditation.saveFailed') }
    message.error(t('meditation.saveFailed'))
  } finally {
    saving.value = false
  }
}

/** Trigger a meditation run（带上当前选中的引擎作为本次作业覆盖） */
async function handleRun() {
  if (!props.activeKbId) return
  running.value = true
  runResult.value = null
  try {
    const res = await $fetch<any>('/api/meditation/run', {
      method: 'POST',
      body: { kb_id: props.activeKbId, trigger: 'manual', harness: config.value.harness || undefined },
    })
    if (res?.success) {
      const report = res.report || {}
      runResult.value = {
        success: true,
        run_id: report.drafts_created === 0 ? 'no-drafts' : `drafts:${report.drafts_created}`,
      }
      message.success(report.summary || t('meditation.triggerSuccess'))
      setTimeout(() => loadConfig(), 2000)
    } else {
      runResult.value = { success: false, error: res?.error || res?.report?.error || t('meditation.unknownError') }
      message.error(t('meditation.triggerFailed'))
    }
  } catch (err: any) {
    runResult.value = { success: false, error: err?.message || t('meditation.triggerFailed') }
    message.error(t('meditation.triggerFailed'))
  } finally {
    running.value = false
  }
}

watch(() => props.activeKbId, (newId) => {
  if (newId) loadConfig()
})

// 切引擎 → 刷新该引擎的模型目录
watch(() => config.value.harness, (h) => {
  if (h) loadHarnessModels(h)
})

onMounted(() => {
  if (props.activeKbId) loadConfig()
})
</script>

<style scoped>
.meditation-settings {
  padding: 0;
}

.med-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.med-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--kb-fg);
}

.med-icon {
  font-size: 18px;
  color: var(--kb-primary);
}

.med-title {
  flex: 1;
}

.med-status-bar {
  margin-bottom: 20px;
}

.med-form {
  margin-bottom: 8px;
}

.form-hint {
  color: var(--kb-fg-3);
  font-size: 12px;
  margin-left: 8px;
}

.ml-2 {
  margin-left: 8px;
}

.med-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--kb-border);
}
</style>