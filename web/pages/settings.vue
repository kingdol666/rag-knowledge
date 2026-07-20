<template>
  <div class="settings-page">
    <!-- Header -->
    <div class="settings-header">
      <div class="header-title-row">
        <div class="header-icon">
          <SettingOutlined />
        </div>
        <div class="header-text">
          <h1 class="page-title">{{ $t('settings.title') }}</h1>
          <p class="page-subtitle">{{ $t('settings.subtitle') }}</p>
        </div>
      </div>
      <div class="header-actions">
        <a-tag :color="effectiveMode === 'dev' ? 'blue' : 'green'" class="mode-tag">
          <CodeOutlined /> {{ effectiveMode === 'dev' ? $t('settings.devMode') : $t('settings.prodMode') }}
        </a-tag>
        <a-tag v-if="effective.vector_enabled" color="cyan"><ThunderboltOutlined /> {{ $t('settings.vectorSearch') }}</a-tag>
        <a-tag v-if="effective.graph_enabled" color="purple"><ShareAltOutlined /> {{ $t('settings.knowledgeGraph') }}</a-tag>
        <a-tag v-if="effective.mineru_enabled" color="orange"><FileTextOutlined /> MinerU</a-tag>
        <a-button @click="loadConfig" :loading="loading" class="reload-btn">
          <ReloadOutlined />刷新
        </a-button>
      </div>
    </div>

    <!-- Effective Values Banner -->
    <div class="effective-banner">
      <div class="banner-item">
        <span class="banner-label">{{ $t('settings.backendPort') }}</span>
        <span class="banner-value">{{ effective.backend_port }}</span>
      </div>
      <div class="banner-divider"></div>
      <div class="banner-item">
        <span class="banner-label">{{ $t('settings.frontendPort') }}</span>
        <span class="banner-value">{{ effective.frontend_port }}</span>
      </div>
      <div class="banner-divider"></div>
      <div class="banner-item">
        <span class="banner-label">{{ $t('settings.backendUrl') }}</span>
        <span class="banner-value mono">{{ effective.backend_url }}</span>
      </div>
      <div class="banner-divider"></div>
      <div class="banner-item">
        <span class="banner-label">{{ $t('settings.storagePath') }}</span>
        <span class="banner-value mono">{{ effective.tree_storage_path }}</span>
      </div>
    </div>

    <!-- Main Layout: Sidebar + Content -->
    <div class="settings-body">
      <!-- Sidebar Navigation -->
      <div class="settings-sidebar">
        <div
          v-for="(section, key) in sectionsWithEnv"
          :key="key"
          class="nav-item"
          :class="{ active: activeSection === key }"
          @click="activeSection = key as string"
        >
          <component :is="iconMap[section.icon]" class="nav-icon" />
          <span class="nav-label">{{ section.label }}</span>
        </div>
      </div>

      <!-- Content Area -->
      <div class="settings-content">
        <a-spin :spinning="loading">
          <!-- Config Sections -->
          <template v-if="activeSection !== '__env'">
            <div class="section-card" v-if="currentSection">
              <div class="section-header">
                <div class="section-title-area">
                  <h2 class="section-title">{{ currentSection.label }}</h2>
                  <p class="section-desc">{{ currentSection.description }}</p>
                </div>
              </div>
              <div class="section-fields">
                <template v-for="(field, fieldKey) in currentSection.fields" :key="fieldKey">
                  <!-- Group field (nested) -->
                  <div v-if="field.type === 'group'" class="field-group">
                    <div class="group-header">
                      <span class="group-title">{{ field.label }}</span>
                      <span class="group-desc">{{ field.description }}</span>
                    </div>
                    <div class="group-fields">
                      <div v-for="(subField, subKey) in field.fields" :key="subKey" class="field-row">
                        <ConfigField
                          :field="subField"
                          :value="getConfigValue(activeSection, fieldKey, subKey)"
                          @update:value="setConfigValue(activeSection, fieldKey, subKey, $event)"
                        />
                      </div>
                    </div>
                  </div>
                  <!-- Regular field -->
                  <div v-else class="field-row">
                    <ConfigField
                      :field="field"
                      :value="getConfigValue(activeSection, fieldKey)"
                      @update:value="setConfigValue(activeSection, fieldKey, undefined, $event)"
                    />
                  </div>
                </template>
              </div>
            </div>
          </template>

          <!-- Environment Variables Section -->
          <template v-else>
            <div class="section-card">
              <div class="section-header">
                <div class="section-title-area">
                  <h2 class="section-title">{{ envSchema.label }}</h2>
                  <p class="section-desc">{{ envSchema.description }}</p>
                </div>
              </div>
              <div class="section-fields">
                <div v-for="(field, fieldKey) in envSchema.fields" :key="fieldKey" class="field-row">
                  <ConfigField
                    :field="field"
                    :value="envData[fieldKey] ?? ''"
                    @update:value="envData[fieldKey] = $event"
                  />
                </div>
              </div>
            </div>
          </template>
        </a-spin>
      </div>
    </div>

    <!-- Fixed Bottom Action Bar -->
    <transition name="slide-up">
      <div v-if="hasChanges" class="action-bar">
        <div class="action-info">
          <ExclamationCircleOutlined class="action-icon" />
          <span>有 {{ changedCount }} 项配置已修改，保存后将自动持久化并热生效</span>
        </div>
        <div class="action-buttons">
          <a-button @click="discardChanges" :disabled="saving">放弃修改</a-button>
          <a-button type="primary" @click="saveConfig" :loading="saving" class="save-btn">
            <CheckOutlined />保存并热生效
          </a-button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch, defineComponent, h } from 'vue'
import { message } from 'ant-design-vue'
import {
  SettingOutlined, CloudServerOutlined, DatabaseOutlined, ThunderboltOutlined,
  ExperimentOutlined, ShareAltOutlined, SearchOutlined, FileTextOutlined,
  CodeOutlined, ReloadOutlined, CheckOutlined, ExclamationCircleOutlined,
} from '@ant-design/icons-vue'

// ── Types ──────────────────────────────────────────────────────────────
interface ConfigField {
  label: string
  type: 'string' | 'int' | 'float' | 'boolean' | 'list' | 'select' | 'password' | 'group'
  description: string
  default?: any
  min?: number
  max?: number
  step?: number
  options?: string[]
  env_only?: boolean
  optional?: boolean
  fields?: Record<string, ConfigField>
}

interface ConfigSection {
  label: string
  icon: string
  description: string
  fields: Record<string, ConfigField>
}

// ── Icon Map ───────────────────────────────────────────────────────────
const iconMap: Record<string, any> = {
  CloudServerOutlined, DatabaseOutlined, ThunderboltOutlined,
  ExperimentOutlined, ShareAltOutlined, SearchOutlined, FileTextOutlined,
  SettingOutlined,
}

// ── State ──────────────────────────────────────────────────────────────
const loading = ref(false)
const saving = ref(false)
const activeSection = ref('server')
const configData = reactive<Record<string, any>>({})
const originalConfig = ref<Record<string, any>>({})
const envData = reactive<Record<string, string>>({})
const originalEnv = ref<Record<string, string>>({})
const schema = ref<Record<string, ConfigSection>>({})
const envSchema = ref<ConfigSection>({ label: '', icon: '', description: '', fields: {} })
const effective = reactive({
  app_mode: 'dev',
  backend_port: '',
  frontend_port: '',
  backend_url: '',
  tree_storage_path: '',
  vector_enabled: false,
  graph_enabled: false,
  mineru_enabled: false,
})

const effectiveMode = computed(() => effective.app_mode)

// ── Computed ───────────────────────────────────────────────────────────
const sections = computed(() => schema.value)

const currentSection = computed(() => {
  if (activeSection.value === '__env') return null
  return schema.value[activeSection.value]
})

const hasChanges = computed(() => {
  return JSON.stringify(configData) !== JSON.stringify(originalConfig.value) ||
    JSON.stringify(envData) !== JSON.stringify(originalEnv.value)
})

const changedCount = computed(() => {
  let count = 0
  for (const section of Object.keys(schema.value)) {
    const orig = originalConfig.value[section] || {}
    const curr = configData[section] || {}
    if (JSON.stringify(orig) !== JSON.stringify(curr)) count++
  }
  if (JSON.stringify(envData) !== JSON.stringify(originalEnv.value)) count++
  return count
})

// ── Config Value Accessors ─────────────────────────────────────────────
function getConfigValue(section: string, groupKey: string, subKey?: string): any {
  const sec = configData[section]
  if (!sec) return undefined
  if (subKey !== undefined) {
    return sec[groupKey]?.[subKey]
  }
  return sec[groupKey]
}

function setConfigValue(section: string, groupKey: string, subKey: string | undefined, value: any) {
  if (!configData[section]) configData[section] = {}
  if (subKey !== undefined) {
    if (!configData[section][groupKey]) configData[section][groupKey] = {}
    configData[section][groupKey][subKey] = value
  } else {
    configData[section][groupKey] = value
  }
}

// ── API ────────────────────────────────────────────────────────────────
async function loadConfig() {
  loading.value = true
  try {
    const res = await $fetch<any>('/api/config')
    if (res.success) {
      // Deep copy config
      Object.keys(configData).forEach(k => delete configData[k])
      Object.assign(configData, JSON.parse(JSON.stringify(res.config)))

      originalConfig.value = JSON.parse(JSON.stringify(res.config))

      // Env data
      Object.keys(envData).forEach(k => delete envData[k])
      Object.assign(envData, res.env || {})
      originalEnv.value = { ...res.env }

      // Schema
      schema.value = res.schema || {}
      envSchema.value = res.env_schema || { label: '', icon: '', description: '', fields: {} }

      // Effective values
      if (res.effective) {
        Object.assign(effective, res.effective)
      }

      // Add env section to sidebar
      if (envSchema.value.label) {
        // already in schema via __env pseudo-key
      }
    }
  } catch (e: any) {
    message.error('加载配置失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  saving.value = true
  try {
    const res = await $fetch<any>('/api/config', {
      method: 'PUT',
      body: {
        config: configData,
        env: envData,
      },
    })
    if (res.success) {
      // Update originals
      originalConfig.value = JSON.parse(JSON.stringify(res.config))
      Object.keys(envData).forEach(k => delete envData[k])
      Object.assign(envData, res.env || {})
      originalEnv.value = { ...res.env }

      if (res.effective) {
        Object.assign(effective, res.effective)
      }

      // ── Refresh frontend config (hot-reload) ──
      // After saving, the server-side config cache is invalidated and runtimeConfig
      // is updated. We also fetch fresh config for the client side.
      try {
        const { refreshConfig } = useConfigRefresh()
        const { config: freshCfg, needsReload } = await refreshConfig()

        // Update the effective banner with fresh values
        effective.backend_url = freshCfg.backend_url
        effective.frontend_port = freshCfg.frontend_port
        effective.tree_storage_path = freshCfg.tree_storage_path
        effective.app_mode = freshCfg.app_mode
        effective.vector_enabled = freshCfg.vector_enabled
        effective.graph_enabled = freshCfg.graph_enabled
        effective.mineru_enabled = freshCfg.mineru_enabled

        if (needsReload) {
          message.success('配置已保存并热生效！存储路径变更需要刷新页面。', 5)
          // Auto-reload after 2 seconds to let the user see the message
          setTimeout(() => {
            window.location.reload()
          }, 2000)
        } else {
          message.success('配置已保存并热生效！前后端均已刷新。')
        }
      } catch {
        // Config refresh failed, but the save itself succeeded
        message.success('配置已保存并热生效！（前端配置刷新失败，可能需要手动刷新页面）')
      }
    } else {
      message.error('保存失败')
    }
  } catch (e: any) {
    message.error('保存配置失败: ' + (e.message || e))
  } finally {
    saving.value = false
  }
}

function discardChanges() {
  Object.keys(configData).forEach(k => delete configData[k])
  Object.assign(configData, JSON.parse(JSON.stringify(originalConfig.value)))

  Object.keys(envData).forEach(k => delete envData[k])
  Object.assign(envData, { ...originalEnv.value })

  message.info('已放弃修改')
}

// ── Lifecycle ──────────────────────────────────────────────────────────
onMounted(() => {
  loadConfig()
})

// Watch for env schema and add to sections
watch(envSchema, (val) => {
  if (val.label && !(schema.value as any).__env) {
    // Use a watcher to add env to sidebar - handled in template via __env key
  }
})

// Expose __env for sidebar
const sectionsWithEnv = computed(() => {
  const result = { ...schema.value }
  if (envSchema.value.label) {
    (result as any).__env = {
      label: envSchema.value.label,
      icon: envSchema.value.icon,
      description: envSchema.value.description,
    }
  }
  return result
})

// Override sections to include env
watch(sectionsWithEnv, () => {}, { immediate: true })

// ── ConfigField Component ──────────────────────────────────────────────
const ConfigField = defineComponent({
  props: {
    field: { type: Object as () => ConfigField, required: true },
    value: { type: [String, Number, Boolean, Array], default: undefined },
  },
  emits: ['update:value'],
  setup(props, { emit }) {
    const localValue = ref<any>(props.value)

    watch(() => props.value, (val) => {
      localValue.value = val
    })

    const onChange = (val: any) => {
      localValue.value = val
      emit('update:value', val)
    }

    return () => {
      const f = props.field
      const val = localValue.value

      let input: any

      if (f.type === 'boolean') {
        input = h('div', { class: 'toggle-wrapper' }, [
          h('button', {
            class: ['toggle-btn', { on: val }],
            onClick: () => onChange(!val),
            type: 'button',
          }, [
            h('span', { class: 'toggle-track' }, [
              h('span', { class: 'toggle-thumb' }),
            ]),
            h('span', { class: 'toggle-label' }, val ? '已开启' : '已关闭'),
          ]),
        ])
      } else if (f.type === 'select') {
        input = h('select', {
          class: 'field-select',
          value: val ?? '',
          onChange: (e: Event) => onChange((e.target as HTMLSelectElement).value),
        }, [
          ...(f.options || []).map((opt: string) =>
            h('option', { value: opt, selected: opt === val }, opt || '(不设置)')
          ),
        ])
      } else if (f.type === 'int') {
        input = h('input', {
          class: 'field-input',
          type: 'number',
          value: val ?? '',
          min: f.min,
          max: f.max,
          step: 1,
          onInput: (e: Event) => {
            const v = (e.target as HTMLInputElement).value
            onChange(v === '' ? '' : parseInt(v))
          },
        })
      } else if (f.type === 'float') {
        input = h('input', {
          class: 'field-input',
          type: 'number',
          value: val ?? '',
          min: f.min,
          max: f.max,
          step: f.step || 0.01,
          onInput: (e: Event) => {
            const v = (e.target as HTMLInputElement).value
            onChange(v === '' ? '' : parseFloat(v))
          },
        })
      } else if (f.type === 'password') {
        input = h('input', {
          class: 'field-input',
          type: 'password',
          value: val ?? '',
          placeholder: '••••••••',
          onInput: (e: Event) => onChange((e.target as HTMLInputElement).value),
        })
      } else if (f.type === 'list') {
        const items = Array.isArray(val) ? val : []
        input = h('div', { class: 'list-editor' }, [
          h('div', { class: 'list-items' }, items.map((item: string, idx: number) =>
            h('div', { class: 'list-item', key: idx }, [
              h('span', { class: 'list-item-text' }, item),
              h('button', {
                class: 'list-item-remove',
                onClick: () => {
                  const next = [...items]
                  next.splice(idx, 1)
                  onChange(next)
                },
                type: 'button',
              }, '×'),
            ])
          )),
          h('input', {
            class: 'field-input list-add-input',
            type: 'text',
            placeholder: '输入值后按回车添加',
            onKeydown: (e: KeyboardEvent) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                const inputEl = e.target as HTMLInputElement
                const v = inputEl.value.trim()
                if (v) {
                  onChange([...items, v])
                  inputEl.value = ''
                }
              }
            },
          }),
        ])
      } else {
        // string
        input = h('input', {
          class: 'field-input',
          type: 'text',
          value: val ?? '',
          onInput: (e: Event) => onChange((e.target as HTMLInputElement).value),
        })
      }

      return h('div', { class: 'config-field' }, [
        h('div', { class: 'field-label-area' }, [
          h('label', { class: 'field-label' }, f.label),
          h('div', { class: 'field-desc' }, f.description),
          h('div', { class: 'field-meta' }, [
            f.default !== undefined ? h('span', { class: 'meta-tag default-tag' }, `默认: ${typeof f.default === 'boolean' ? (f.default ? 'true' : 'false') : f.default}`) : null,
            f.min !== undefined ? h('span', { class: 'meta-tag' }, `最小: ${f.min}`) : null,
            f.max !== undefined ? h('span', { class: 'meta-tag' }, `最大: ${f.max}`) : null,
            f.env_only ? h('span', { class: 'meta-tag env-tag' }, '环境变量') : null,
            f.optional ? h('span', { class: 'meta-tag optional-tag' }, '可选') : null,
          ].filter(Boolean)),
        ]),
        h('div', { class: 'field-control' }, input),
      ])
    }
  },
})
</script>

<style scoped>
/* ============================================================
 * Settings Page — System Configuration
 * ============================================================ */
.settings-page {
  padding: 0;
}

/* ── Header ── */
.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 16px;
}
.header-title-row { display: flex; align-items: center; gap: 16px; }
.header-icon {
  width: 52px; height: 52px; border-radius: 15px;
  display: grid; place-items: center; font-size: 24px; color: #fff;
  background: linear-gradient(135deg, var(--kb-primary), var(--kb-gold-deep));
  box-shadow: var(--kb-shadow-primary);
  flex-shrink: 0;
}
.page-title { font-size: 26px; font-weight: 700; color: var(--kb-fg); margin: 0; letter-spacing: -0.5px; font-family: var(--kb-font-serif); }
.page-subtitle { font-size: 14px; color: var(--kb-fg-3); margin: 4px 0 0; }
.header-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.mode-tag { display: inline-flex; align-items: center; gap: 5px; font-weight: 600; }
.reload-btn { border-radius: var(--kb-radius-sm); }

/* ── Effective Banner ── */
.effective-banner {
  display: flex; align-items: center; gap: 0;
  padding: 16px 24px; margin-bottom: 20px;
  background: linear-gradient(135deg, var(--kb-primary-tint), var(--kb-cyan-soft));
  border: 1px solid var(--kb-border); border-radius: var(--kb-radius-lg);
  overflow-x: auto;
}
.banner-item { display: flex; flex-direction: column; gap: 2px; padding: 0 24px; white-space: nowrap; }
.banner-label { font-size: 11.5px; font-weight: 600; color: var(--kb-fg-mute); text-transform: uppercase; letter-spacing: 0.5px; }
.banner-value { font-size: 16px; font-weight: 700; color: var(--kb-fg); }
.banner-value.mono { font-family: var(--kb-font-mono); font-size: 14px; }
.banner-divider { width: 1px; height: 36px; background: var(--kb-border-strong); }

/* ── Body Layout ── */
.settings-body { display: flex; gap: 20px; align-items: flex-start; }

/* ── Sidebar ── */
.settings-sidebar {
  width: 220px; flex-shrink: 0;
  background: var(--kb-bg-elevated); border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius-lg); padding: 10px;
  position: sticky; top: 84px;
}
.nav-item {
  display: flex; align-items: center; gap: 11px;
  padding: 11px 14px; border-radius: var(--kb-radius-sm);
  cursor: pointer; font-size: 14px; font-weight: 500; color: var(--kb-fg-2);
  transition: all var(--kb-dur-fast) var(--kb-ease);
  margin-bottom: 2px;
}
.nav-item:hover { background: var(--kb-gold-soft); color: var(--kb-gold-deep); }
.nav-item.active {
  background: linear-gradient(135deg, var(--kb-primary-soft), rgba(212, 175, 106, 0.12)); color: var(--kb-primary-hover);
  font-weight: 600; box-shadow: inset 3px 0 0 var(--kb-primary), inset 0 0 0 1px rgba(184, 148, 90, 0.2);
}
.nav-icon { font-size: 17px; flex-shrink: 0; }

/* ── Content ── */
.settings-content { flex: 1; min-width: 0; }

.section-card {
  background: var(--kb-bg-elevated); border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius-lg); overflow: hidden;
}
.section-header {
  padding: 22px 26px; border-bottom: 1px solid var(--kb-border);
  background: linear-gradient(135deg, var(--kb-bg-subtle), var(--kb-bg-elevated));
}
.section-title { font-size: 19px; font-weight: 700; color: var(--kb-fg); margin: 0; font-family: var(--kb-font-serif); letter-spacing: -0.2px; }
.section-desc { font-size: 13.5px; color: var(--kb-fg-3); margin: 5px 0 0; line-height: 1.5; }
.section-fields { padding: 8px 0; }

/* ── Field Group ── */
.field-group {
  margin: 8px 26px 16px; padding: 18px;
  background: var(--kb-bg-subtle); border-radius: var(--kb-radius);
  border: 1px solid var(--kb-border);
}
.group-header { margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid var(--kb-border); }
.group-title { font-size: 14px; font-weight: 700; color: var(--kb-fg); display: block; }
.group-desc { font-size: 12.5px; color: var(--kb-fg-3); display: block; margin-top: 3px; }
.group-fields { display: flex; flex-direction: column; gap: 2px; }

/* ── Field Row ── */
.field-row { padding: 14px 26px; border-bottom: 1px solid var(--kb-border); transition: background var(--kb-dur-fast); }
.field-row:last-child { border-bottom: none; }
.field-row:hover { background: var(--kb-primary-tint); }

:deep(.config-field) { display: flex; align-items: flex-start; gap: 24px; }
:deep(.field-label-area) { flex: 1; min-width: 0; }
:deep(.field-label) { font-size: 14px; font-weight: 600; color: var(--kb-fg); display: block; margin-bottom: 4px; }
:deep(.field-desc) { font-size: 12.5px; color: var(--kb-fg-3); line-height: 1.55; margin-bottom: 6px; }
:deep(.field-meta) { display: flex; flex-wrap: wrap; gap: 6px; }
:deep(.meta-tag) {
  font-size: 11px; padding: 2px 7px; border-radius: 4px;
  background: var(--kb-bg-subtle); color: var(--kb-fg-mute);
  border: 1px solid var(--kb-border); font-family: var(--kb-font-mono);
}
:deep(.meta-tag.default-tag) { background: var(--kb-cyan-soft); color: var(--kb-cyan); border-color: transparent; }
:deep(.meta-tag.env-tag) { background: var(--kb-amber-soft); color: var(--kb-amber); border-color: transparent; }
:deep(.meta-tag.optional-tag) { background: var(--kb-emerald-soft); color: var(--kb-emerald); border-color: transparent; }
:deep(.field-control) { width: 320px; flex-shrink: 0; }

/* ── Inputs ── */
:deep(.field-input) {
  width: 100%; padding: 8px 12px; font-size: 14px;
  border: 1px solid var(--kb-border-strong); border-radius: var(--kb-radius-sm);
  background: var(--kb-bg-elevated); color: var(--kb-fg);
  transition: all var(--kb-dur-fast) var(--kb-ease);
  font-family: var(--kb-font);
}
:deep(.field-input:focus) {
  border-color: var(--kb-gold) !important;
  box-shadow: 0 0 0 3px rgba(212, 175, 106, 0.15);
  outline: none;
}
:deep(.field-select) {
  width: 100%; padding: 8px 12px; font-size: 14px;
  border: 1px solid var(--kb-border-strong); border-radius: var(--kb-radius-sm);
  background: var(--kb-bg-elevated); color: var(--kb-fg);
  cursor: pointer;
}
:deep(.field-select:focus) {
  border-color: var(--kb-gold);
  box-shadow: 0 0 0 3px rgba(212, 175, 106, 0.15);
  outline: none;
}

/* ── Toggle ── */
:deep(.toggle-wrapper) { display: flex; align-items: center; }
:deep(.toggle-btn) {
  display: flex; align-items: center; gap: 10px;
  background: none; border: none; cursor: pointer; padding: 0;
}
:deep(.toggle-track) {
  display: inline-block; width: 44px; height: 24px; border-radius: 999px;
  background: var(--kb-border-strong); position: relative;
  transition: background var(--kb-dur-fast) var(--kb-ease);
}
:deep(.toggle-thumb) {
  position: absolute; top: 3px; left: 3px;
  width: 18px; height: 18px; border-radius: 50%;
  background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.15);
  transition: transform var(--kb-dur-fast) var(--kb-ease);
}
:deep(.toggle-btn.on .toggle-track) { background: var(--kb-primary); }
:deep(.toggle-btn.on .toggle-thumb) { transform: translateX(20px); }
:deep(.toggle-label) { font-size: 13px; font-weight: 600; color: var(--kb-fg-2); }
:deep(.toggle-btn.on .toggle-label) { color: var(--kb-primary); }

/* ── List Editor ── */
:deep(.list-editor) { display: flex; flex-direction: column; gap: 8px; }
:deep(.list-items) { display: flex; flex-wrap: wrap; gap: 6px; }
:deep(.list-item) {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 8px 4px 12px; border-radius: 999px;
  background: var(--kb-primary-soft); color: var(--kb-primary-hover);
  font-size: 12.5px; font-weight: 500; border: 1px solid rgba(184, 148, 90, 0.25);
}
:deep(.list-item-text) { font-family: var(--kb-font-mono); font-size: 12px; }
:deep(.list-item-remove) {
  width: 18px; height: 18px; border-radius: 50%; border: none;
  background: rgba(184, 148, 90, 0.18); color: var(--kb-primary);
  cursor: pointer; font-size: 14px; line-height: 1;
  display: grid; place-items: center;
  transition: all var(--kb-dur-fast);
}
:deep(.list-item-remove:hover) { background: var(--kb-rose); color: #fff; }
:deep(.list-add-input) { width: 100%; }

/* ── Action Bar ── */
.action-bar {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  z-index: 200;
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 24px; min-width: 520px; max-width: 90vw;
  background: var(--kb-bg-dark); border-radius: var(--kb-radius-lg);
  box-shadow: 0 16px 40px rgba(0,0,0,0.3);
  animation: kb-fade-up 0.3s var(--kb-ease-out);
}
.action-info { display: flex; align-items: center; gap: 10px; color: #c5cde0; font-size: 14px; }
.action-icon { color: var(--kb-amber); font-size: 18px; }
.action-buttons { display: flex; gap: 10px; }
.save-btn {
  background: linear-gradient(135deg, var(--kb-primary), #4f7cff) !important;
  border: none !important; font-weight: 600;
  box-shadow: var(--kb-shadow-primary) !important;
}

/* ── Slide-up transition ── */
.slide-up-enter-active, .slide-up-leave-active { transition: all 0.3s var(--kb-ease); }
.slide-up-enter-from { opacity: 0; transform: translate(-50%, 20px); }
.slide-up-leave-to { opacity: 0; transform: translate(-50%, 20px); }

/* ── Responsive ── */
@media (max-width: 900px) {
  .settings-body { flex-direction: column; }
  .settings-sidebar { width: 100%; position: static; display: flex; flex-wrap: wrap; gap: 6px; padding: 8px; }
  .nav-item { flex: 1; min-width: 140px; justify-content: center; margin-bottom: 0; }
  :deep(.field-control) { width: 100%; }
  :deep(.config-field) { flex-direction: column; gap: 10px; }
  .effective-banner { flex-wrap: wrap; gap: 12px; }
  .banner-divider { display: none; }
  .action-bar { min-width: 90vw; bottom: 12px; }
}
</style>

