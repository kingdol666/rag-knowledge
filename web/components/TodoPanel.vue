<template>
  <div class="todo-panel" :class="{ compact }">
    <!-- ── Empty state: no snapshot or no todos ────────────────────── -->
    <EmptyState
      v-if="total === 0"
      :icon="CheckSquareOutlined"
      title="暂无任务清单"
      hint="Agent 使用 TodoWrite 时会在此实时显示进度"
      size="compact"
    />

    <template v-else>
      <!-- ── Header (hidden in compact mode) ─────────────────────────── -->
      <div v-if="!compact" class="todo-header">
        <div class="todo-title-row">
          <CheckSquareOutlined class="todo-title-icon" />
          <span class="todo-title-text">任务清单</span>
          <SyncOutlined v-if="inProgress > 0" class="todo-active-indicator" />
          <span class="todo-progress-chip">{{ done }} / {{ total }}</span>
        </div>
        <div
          class="todo-progress-track"
          role="progressbar"
          :aria-valuenow="progressPct"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-label="`任务进度 ${progressPct}%`"
        >
          <div class="todo-progress-fill" :style="{ width: `${progressPct}%` }" />
        </div>
        <div class="todo-legend">
          <span class="legend-item">
            <span class="legend-dot dot-completed" />完成 {{ done }}
          </span>
          <span class="legend-item">
            <span class="legend-dot dot-in-progress" />进行中 {{ inProgress }}
          </span>
          <span class="legend-item">
            <span class="legend-dot dot-pending" />待办 {{ pending }}
          </span>
        </div>
      </div>

      <!-- ── Todo list ──────────────────────────────────────────────── -->
      <ul class="todo-list">
        <li
          v-for="(t, i) in todos"
          :key="i"
          class="todo-item"
          :class="`status-${t.status}`"
        >
          <span class="todo-glyph" :class="`glyph-${t.status}`" aria-hidden="true">
            <template v-if="t.status === 'completed'">✓</template>
            <template v-else-if="t.status === 'in_progress'">◐</template>
            <template v-else>○</template>
          </span>
          <div class="todo-body">
            <span class="todo-content">{{ t.content }}</span>
            <span
              v-if="t.status === 'in_progress' && t.activeForm && t.activeForm !== t.content"
              class="todo-active-form"
            >{{ t.activeForm }}</span>
          </div>
        </li>
      </ul>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { CheckSquareOutlined, SyncOutlined } from '@ant-design/icons-vue'
import { useLatestTodoStore } from '~/composables/useLatestTodoStore'
import type { TodoItem } from '~/utils/claude-messages'

interface Props {
  /** Which engine's todo snapshot to show. */
  engine?: 'claude' | 'omp'
  /** Compact mode: render as a flat list (sidebar); false = header + progress. */
  compact?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  engine: 'claude',
  compact: false,
})

const todo = useLatestTodoStore()
const snap = todo.snapshot(props.engine)

const todos = computed<TodoItem[]>(() => snap.value?.todos ?? [])
const total = computed(() => todos.value.length)
const done = computed(() => todos.value.filter((t) => t.status === 'completed').length)
const inProgress = computed(() => todos.value.filter((t) => t.status === 'in_progress').length)
const pending = computed(() => todos.value.filter((t) => t.status === 'pending').length)
const progressPct = computed(() =>
  total.value ? Math.round((done.value / total.value) * 100) : 0,
)
</script>

<style scoped>
.todo-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 14px;
  color: var(--kb-fg-2);
  padding: 10px;
}

.todo-panel.compact {
  gap: 4px;
  padding: 6px;
  font-size: 12px;
}

/* ── Header ──────────────────────────────────────────────────── */
.todo-header {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.todo-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.todo-title-icon {
  color: var(--kb-primary);
  font-size: 15px;
}

.todo-title-text {
  font-weight: 600;
  color: var(--kb-fg);
  font-size: 13.5px;
  letter-spacing: 0.02em;
}

.todo-active-indicator {
  color: var(--kb-primary);
  font-size: 12px;
  animation: kb-todo-spin 1.8s linear infinite;
}

.todo-progress-chip {
  margin-left: auto;
  font-family: var(--kb-font-mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--kb-primary);
  background: var(--kb-primary-soft);
  border-radius: var(--kb-radius-pill);
  padding: 1px 8px;
  line-height: 1.5;
}

/* Progress bar */
.todo-progress-track {
  height: 4px;
  border-radius: 2px;
  background: var(--kb-border);
  overflow: hidden;
}

.todo-progress-fill {
  height: 100%;
  border-radius: 2px;
  background: var(--kb-primary);
  transition: width var(--kb-dur) var(--kb-ease-out);
}

/* Categorical status legend */
.todo-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 11px;
  color: var(--kb-fg-3);
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.legend-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  display: inline-block;
}

.dot-completed { background: var(--kb-emerald); }
.dot-in-progress { background: var(--kb-primary); }
.dot-pending { background: var(--kb-fg-mute); }

/* ── List ────────────────────────────────────────────────────── */
.todo-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.todo-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  border-left: 3px solid transparent;
  transition: background var(--kb-dur-fast) var(--kb-ease);
}

.todo-panel.compact .todo-item {
  padding: 5px 6px;
  gap: 6px;
}

.todo-item:hover {
  background: var(--kb-primary-tint, transparent);
}

.todo-item.status-in_progress {
  border-left-color: var(--kb-primary);
}

/* Status glyph */
.todo-glyph {
  flex-shrink: 0;
  width: 15px;
  text-align: center;
  line-height: 1.5;
  font-size: 13px;
  user-select: none;
}

.glyph-completed { color: var(--kb-emerald); }
.glyph-in_progress {
  color: var(--kb-primary);
  animation: kb-todo-spin 2.4s linear infinite;
}
.glyph-pending { color: var(--kb-fg-mute); }

/* Body */
.todo-body {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
  flex: 1;
}

.todo-content {
  color: var(--kb-fg-2);
  line-height: 1.5;
  word-break: break-word;
}

.todo-active-form {
  font-size: 11px;
  color: var(--kb-fg-3);
  font-style: italic;
  line-height: 1.4;
}

/* Completed: struck through + dimmed */
.todo-item.status-completed .todo-content {
  text-decoration: line-through;
  text-decoration-color: var(--kb-fg-mute);
  color: var(--kb-fg-mute);
  opacity: 0.6;
}

/* ── Spin keyframe ───────────────────────────────────────────── */
@keyframes kb-todo-spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .glyph-in_progress,
  .todo-active-indicator {
    animation: none;
  }
}
</style>
