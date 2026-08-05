<template>
  <aside class="persona-rail">
    <div class="rail-head">
      <span>{{ t('soul.rail.title') }}</span>
      <span class="rail-count">{{ souls.length }}</span>
    </div>
    <div v-if="loading && !souls.length" class="rail-loading">{{ t('soul.rail.loading') }}</div>
    <div v-else-if="!souls.length" class="rail-empty">{{ t('soul.rail.empty') }}</div>
    <div class="rail-items">
      <div
        v-for="soul in souls"
        :key="soul.kb_id"
        class="rail-item"
        :class="{ active: selectedKbId === soul.kb_id }"
        @click="$emit('select', soul)"
      >
        <div class="rail-item-top">
          <i
            class="state-light"
            :class="{
              training: soul._training,
              warn: !soul._training && (soul._status?.drafts_pending_review > 0),
              idle: !soul._training && !(soul._status?.drafts_pending_review > 0),
            }"
          ></i>
          <span class="rail-name">{{ soul.name }}</span>
          <span class="rail-mem">{{ soul._status?.total_memories ?? 0 }} {{ t('soul.rail.memories') }}</span>
        </div>
        <div class="rail-scope">{{ scopeLabels(soul).slice(0, 2).join(' · ') || (soul.kb_scope || []).join(' · ') || t('soul.rail.qaOnly') }}</div>
        <div class="rail-meta">
          <span class="pill pill-harness">{{ soul.meditation?.harness || 'omp' }}</span>
          <span v-if="soul.meditation?.enabled" class="pill pill-sched">{{ t('soul.rail.scheduled') }} {{ soul.meditation.interval_hours }}h</span>
          <span v-if="soul._status?.drafts_pending_review" class="pill pill-warn">{{ t('soul.rail.pendingReview') }} {{ soul._status.drafts_pending_review }}</span>
          <span v-if="soul._status?.judge_divergence_count" class="pill pill-err">{{ t('soul.rail.divergence') }} {{ soul._status.judge_divergence_count }}</span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

interface Soul {
  kb_id: string
  name: string
  summary?: string
  kb_scope?: string[]
  domain_labels?: string[]
  supported_task_types?: string[]
  route_weight?: number
  is_template?: boolean
  meditation?: {
    harness?: string
    model?: string
    enabled?: boolean
    meditation_mode?: string
    interval_hours?: number
    rounds_per_run?: number
    max_questions_per_run?: number
    max_budget_usd?: number
  }
  _status?: any
  _training?: boolean
  _trainingMsg?: string
}

const props = defineProps<{
  souls: Soul[]
  selectedKbId: string
  loading: boolean
  kbCatalog?: any[]
}>()

defineEmits<{
  select: [soul: Soul]
}>()

function scopeLabels(soul: Soul): string[] {
  const out: string[] = []
  const cat = props.kbCatalog || []
  for (const kb of cat) {
    if ((soul.kb_scope || []).includes(kb.kbId) || (soul.kb_scope || []).includes(kb.name)) {
      out.push(kb.name)
    }
  }
  return out
}
</script>

<style scoped>
/* ═══ Persona Rail — 独立滚动、暖象牙铜金主题 ═══ */
.persona-rail {
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-radius: 8px;
  overflow: hidden;
  position: sticky;
  top: 16px;
  height: calc(100vh - 170px);
  display: flex;
  flex-direction: column;
}

/* ── 自定义细滚动条 ── */
.rail-items {
  overflow-y: auto;
  flex: 1;
}
.rail-items::-webkit-scrollbar {
  width: 6px;
}
.rail-items::-webkit-scrollbar-track {
  background: transparent;
}
.rail-items::-webkit-scrollbar-thumb {
  background: var(--kb-border-strong);
  border-radius: 3px;
}
.rail-items::-webkit-scrollbar-thumb:hover {
  background: var(--kb-fg-mute);
}

/* ── Rail head ── */
.rail-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 11px 14px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--kb-fg-3);
  letter-spacing: .04em;
  border-bottom: 1px solid var(--kb-border);
  text-transform: uppercase;
  flex-shrink: 0;
}
.rail-count {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  background: var(--kb-gold-soft);
  color: var(--kb-gold-deep);
  padding: 1px 7px;
  border-radius: 10px;
}
.rail-loading,
.rail-empty {
  padding: 22px 14px;
  font-size: 12.5px;
  color: var(--kb-fg-3);
  text-align: center;
}

/* ── Rail item ── */
.rail-item {
  padding: 11px 14px;
  border-bottom: 1px solid var(--kb-border);
  cursor: pointer;
  transition: background .15s, border-color .15s;
  border-left: 2px solid transparent;
}
.rail-item:hover {
  background: var(--kb-bg-subtle);
}
.rail-item.active {
  background: var(--kb-gold-soft);
  border-left-color: var(--kb-gold);
}
.rail-item-top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.state-light {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.state-light.idle {
  background: var(--kb-emerald);
  opacity: .75;
}
.state-light.warn {
  background: var(--kb-gold);
  animation: rail-breathe 2s infinite;
}
.state-light.training {
  background: var(--kb-primary);
  animation: rail-breathe 1.2s infinite;
}
@keyframes rail-breathe {
  0%, 100% { opacity: .35; }
  50% { opacity: 1; }
}
.rail-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--kb-fg);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rail-mem {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--kb-fg-3);
  flex-shrink: 0;
}
.rail-scope {
  font-size: 11.5px;
  color: var(--kb-fg-3);
  margin: 4px 0 6px 16px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rail-meta {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
  margin-left: 16px;
}
.pill {
  font-size: 10.5px;
  padding: 1px 7px;
  border-radius: 9px;
  border: 1px solid var(--kb-border);
  color: var(--kb-fg-3);
  background: var(--kb-bg-subtle);
}
.pill-harness {
  color: var(--kb-gold-deep);
  border-color: var(--kb-gold);
}
.pill-sched {
  color: var(--kb-primary);
  border-color: var(--kb-primary);
}
.pill-warn {
  color: var(--kb-gold-deep);
  background: var(--kb-gold-soft);
  border-color: var(--kb-gold);
}
.pill-err {
  color: #b0442a;
  border-color: #d99a86;
  background: var(--kb-primary-soft);
}
</style>