<template>
  <div class="subagent-sidebar">
    <!-- ═══ 1. Header bar (sticky) ═══ -->
    <header class="sb-header">
      <div class="sb-title">
        <RobotOutlined class="sb-title-icon" />
        <span class="sb-title-text">子 Agent</span>
        <span class="sb-engine" :title="engineLabel">{{ engineEmoji }}</span>
      </div>

      <div class="sb-count" :title="`运行中 ${runningCount} / 共 ${totalCount}`">
        <span class="sb-count-run">{{ runningCount }}</span>
        <span class="sb-count-sep">/</span>
        <span class="sb-count-tot">{{ totalCount }}</span>
      </div>

      <div class="sb-actions">
        <a-tooltip title="清除已完成">
          <button
            type="button"
            class="sb-icon-btn"
            :disabled="totalCount === 0"
            aria-label="清除已完成的子 Agent"
            @click="clearFinished"
          >
            <DeleteOutlined />
          </button>
        </a-tooltip>
        <button
          type="button"
          class="sb-icon-btn"
          aria-label="关闭子 Agent 面板"
          @click="emit('close')"
        >
          <CloseOutlined />
        </button>
      </div>
    </header>

    <!-- ═══ 2. Card list (scrollable) ═══ -->
    <div class="sb-list">
      <!-- Empty state -->
      <EmptyState
        v-if="sessions.length === 0"
        :icon="RobotOutlined"
        title="暂无子 Agent"
        hint="当主 Agent 委托 Task/Agent 工具时，子 Agent 会在此显示"
        size="compact"
        fill
      />

      <!-- Session cards -->
      <button
        v-for="session in sessions"
        :key="session.id"
        type="button"
        :class="[
          'subagent-card',
          `st-${session.status}`,
          { selected: session.id === selectedId },
        ]"
        :aria-current="session.id === selectedId ? 'true' : undefined"
        @click="select(session.id)"
      >
        <!-- Row 1: status lamp + type + engine + time -->
        <div class="card-row1">
          <AgentStatusLight :status="session.status" size="small" />
          <span class="type-badge">{{ session.type || 'task' }}</span>
          <span
            class="engine-tag"
            :title="session.engine === 'omp' ? 'OMP 引擎' : 'Claude 引擎'"
          >{{ session.engine === 'omp' ? '⚡' : '🤖' }}</span>
          <span class="card-time">{{ relativeTime(session.updatedAt) }}</span>
        </div>

        <!-- Row 2: description (2-line clamp) -->
        <p class="card-desc">{{ session.description || '(无描述)' }}</p>

        <!-- Row 3: footer chips -->
        <div class="card-foot">
          <span class="foot-chip" title="工具调用次数">🔧 {{ session.toolCount }}</span>
          <span class="foot-chip" title="消息数">💬 {{ session.messages.length }}</span>
          <span v-if="session.error" class="foot-err">{{ session.error }}</span>
        </div>
      </button>
    </div>

    <!-- ═══ 3. Detail drawer ═══ -->
    <a-drawer
      v-model:open="drawerOpen"
      :title="drawerTitle"
      placement="right"
      :width="560"
      :body-style="{ padding: '0', display: 'flex', flexDirection: 'column', overflow: 'hidden' }"
      class="subagent-drawer"
    >
      <template v-if="selected">
        <!-- Rich header -->
        <div class="drawer-head">
          <AgentStatusLight :status="selected.status" size="medium" />
          <div class="dh-meta">
            <div class="dh-line1">
              <span class="dh-type">{{ selected.type || 'task' }}</span>
              <span class="dh-engine">{{ selected.engine === 'omp' ? '⚡ OMP' : '🤖 Claude' }}</span>
            </div>
            <p class="dh-desc">{{ selected.description || '(无描述)' }}</p>
            <div class="dh-stats">
              <span>{{ formatClock(selected.createdAt) }}</span>
              <span class="dh-dot">·</span>
              <span>🔧 {{ selected.toolCount }}</span>
              <span class="dh-dot">·</span>
              <span>💬 {{ selected.messages.length }}</span>
            </div>
          </div>
        </div>

        <!-- Transcript -->
        <div class="subagent-transcript">
          <div
            v-for="m in selected.messages"
            :key="m.id"
            :class="['msg', m.kind]"
          >
            <!-- user -->
            <template v-if="m.kind === 'user'">
              <div class="msg-head"><UserOutlined /> You</div>
              <div class="msg-text markdown-body" v-html="md(m.text)"></div>
            </template>

            <!-- assistant -->
            <template v-else-if="m.kind === 'assistant'">
              <div class="msg-head"><RobotOutlined /> {{ selected.engine === 'omp' ? 'OMP' : 'Claude' }}</div>
              <div class="msg-text markdown-body" v-html="md(m.html)"></div>
            </template>

            <!-- thinking -->
            <template v-else-if="m.kind === 'thinking'">
              <details class="think-details">
                <summary><BulbOutlined /> Thinking <span class="muted">({{ m.text.length }} chars)</span></summary>
                <div class="think-body">{{ m.text }}</div>
              </details>
            </template>

            <!-- tool_use -->
            <template v-else-if="m.kind === 'tool_use'">
              <div class="tool-card use">
                <div class="tool-head">
                  <span class="tool-badge" :class="{ mcp: m.isMcp }">
                    <CodeOutlined /> {{ MessageProcessor.parseToolName(m.toolName).display }}
                  </span>
                  <span class="tool-preview">{{ MessageProcessor.formatInputPreview(m.toolName, m.input) }}</span>
                </div>
                <details>
                  <summary class="muted">Input</summary>
                  <pre class="tool-input">{{ fmtInput(m.input) }}</pre>
                </details>
              </div>
            </template>

            <!-- tool_result -->
            <template v-else-if="m.kind === 'tool_result'">
              <div class="tool-card result" :class="{ err: m.isError }">
                <div class="tool-head">
                  <span class="tool-badge" :class="{ err: m.isError }">
                    {{ m.isError ? '✗ Failed' : '✓ Done' }} · {{ m.display }}
                  </span>
                </div>
                <details>
                  <summary class="muted">{{ m.result.length }} chars</summary>
                  <pre class="tool-result-pre">{{ truncate(m.result, 2000) }}</pre>
                </details>
              </div>
            </template>

            <!-- plan -->
            <template v-else-if="m.kind === 'plan'">
              <div class="plan-card">
                <div class="plan-head"><FileTextOutlined /> Plan</div>
                <div class="plan-body markdown-body" v-html="md(m.plan)"></div>
              </div>
            </template>

            <!-- todo -->
            <template v-else-if="m.kind === 'todo'">
              <div class="todo-card">
                <div class="todo-head"><CheckSquareOutlined /> Task List</div>
                <div v-for="(t, i) in m.todos" :key="i" :class="['todo-item', t.status]">
                  <span class="todo-check">{{ t.status === 'completed' ? '✓' : t.status === 'in_progress' ? '◐' : '○' }}</span>
                  <span class="todo-text">{{ t.content }}</span>
                </div>
              </div>
            </template>

            <!-- ask_user (read-only) -->
            <template v-else-if="m.kind === 'ask_user'">
              <div class="ask-card">
                <div class="ask-head"><QuestionCircleOutlined /> {{ m.header }}</div>
                <div class="ask-question">{{ m.question }}</div>
                <div v-if="m.options.length" class="ask-options">
                  <div v-for="opt in m.options" :key="opt.label" class="ask-opt">
                    <strong>{{ opt.label }}</strong>
                    <span v-if="opt.description" class="muted">{{ opt.description }}</span>
                  </div>
                </div>
              </div>
            </template>

            <!-- system -->
            <template v-else-if="m.kind === 'system'">
              <details class="sys-details">
                <summary class="sys-head"><ThunderboltOutlined /> System · {{ m.subtype }}</summary>
                <div class="sys-body markdown-body" v-html="md(m.text)"></div>
              </details>
            </template>

            <!-- result -->
            <template v-else-if="m.kind === 'result'">
              <div class="result-card" :class="{ err: m.isError }">
                <div class="msg-text markdown-body" v-html="md(m.html)"></div>
              </div>
            </template>

            <!-- error -->
            <template v-else-if="m.kind === 'error'">
              <div class="err-card">❌ {{ m.text }}</div>
            </template>
          </div>

          <!-- ⭐ Live typewriter bubble (running + streaming text) -->
          <div v-if="selected.status === 'running' && selected.streamingText" class="msg assistant streaming-msg">
            <div class="msg-head"><SyncOutlined :spin="true" /> {{ selected.engine === 'omp' ? 'OMP' : 'Claude' }}</div>
            <div class="msg-text markdown-body" v-html="md(selected.streamingText)"></div>
            <span class="stream-cursor"></span>
          </div>

          <!-- ⭐ Working indicator (running, no streaming text yet) -->
          <div v-else-if="selected.status === 'running'" class="msg assistant typing-msg">
            <div class="msg-head"><SyncOutlined :spin="true" /> {{ selected.engine === 'omp' ? 'OMP' : 'Claude' }}</div>
            <div class="typing-dots"><span></span><span></span><span></span></div>
          </div>
        </div>
      </template>

      <!-- Footer: streaming thinking -->
      <template v-if="selected && selected.streamingThinking" #footer>
        <details class="think-foot">
          <summary><BulbOutlined /> Thinking <span class="muted">({{ selected.streamingThinking.length }} chars)</span></summary>
          <div class="think-body">{{ selected.streamingThinking }}</div>
        </details>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import AgentStatusLight from './AgentStatusLight.vue'
import { useSubagentStore } from '~/composables/useSubagentStore'
import { MessageProcessor } from '~/utils/claude-messages'
import { renderMd as md, formatJsonInput as fmtInput } from '~/utils/markdown'
import {
  RobotOutlined, CodeOutlined, CheckSquareOutlined, FileTextOutlined,
  ThunderboltOutlined, BulbOutlined, QuestionCircleOutlined,
  DeleteOutlined, CloseOutlined, SyncOutlined, UserOutlined,
} from '@ant-design/icons-vue'

interface Props {
  /** Header label engine; default 'claude'. Does not filter the store. */
  engine?: 'claude' | 'omp'
}

const props = withDefaults(defineProps<Props>(), {
  engine: 'claude',
})

const emit = defineEmits<{
  close: []
  select: [payload: string | null]
}>()

const {
  sessions,
  runningCount,
  totalCount,
  selectedId,
  selected,
  select,
  clearFinished,
} = useSubagentStore()

// Drawer open state mirrors selectedId (open ⟺ a session is selected).
const drawerOpen = computed<boolean>({
  get: () => selectedId.value !== null,
  set: (open) => {
    if (!open) select(null)
  },
})

// Notify parent on any selection change.
watch(selectedId, (id) => emit('select', id))

const engineLabel = computed(() => (props.engine === 'omp' ? 'OMP' : 'Claude'))
const engineEmoji = computed(() => (props.engine === 'omp' ? '⚡' : '🤖'))

const drawerTitle = computed(() => {
  const s = selected.value
  if (!s) return '子 Agent 详情'
  return `${s.type || 'task'} · 子 Agent`
})


/** Truncate a long result string, marking the cut. */
function truncate(s: string, max: number): string {
  if (s.length <= max) return s
  return s.slice(0, max) + '\n…(truncated)'
}

/** Compact relative time: 12s / 5m / 3h / 2d. */
function relativeTime(ts: number): string {
  const diff = Date.now() - ts
  if (diff < 60_000) return Math.max(1, Math.round(diff / 1000)) + 's'
  if (diff < 3_600_000) return Math.round(diff / 60_000) + 'm'
  if (diff < 86_400_000) return Math.round(diff / 3_600_000) + 'h'
  return Math.round(diff / 86_400_000) + 'd'
}

/** HH:MM:SS clock for the drawer meta. */
function formatClock(ts: number): string {
  const d = new Date(ts)
  const h = d.getHours().toString().padStart(2, '0')
  const m = d.getMinutes().toString().padStart(2, '0')
  const s = d.getSeconds().toString().padStart(2, '0')
  return `${h}:${m}:${s}`
}
</script>

<style scoped>
/* ════════════════════════════════════════════════════════════════
 * Root — flex column filling the parent's side column.
 * ════════════════════════════════════════════════════════════════ */
.subagent-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--kb-bg-subtle);
  border-left: 1px solid var(--kb-border);
}

/* ═══ Header ═══ */
.sb-header {
  flex: none;
  display: flex;
  align-items: center;
  gap: var(--kb-space-sm);
  padding: 10px 12px;
  background: var(--kb-bg-elevated);
  border-bottom: 1px solid var(--kb-border);
  position: sticky;
  top: 0;
  z-index: 2;
}
.sb-title {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.sb-title-icon {
  color: var(--kb-gold-deep);
  font-size: 16px;
}
.sb-title-text {
  font-family: var(--kb-font-serif);
  font-weight: 600;
  font-size: 15px;
  color: var(--kb-fg);
  letter-spacing: 0.01em;
}
.sb-engine {
  font-size: 13px;
  line-height: 1;
}
.sb-count {
  margin-left: auto;
  display: inline-flex;
  align-items: baseline;
  gap: 3px;
  font-family: var(--kb-font-mono);
  font-size: 12.5px;
  padding: 2px 9px;
  border-radius: var(--kb-radius-pill);
  background: var(--kb-primary-tint);
  color: var(--kb-primary);
}
.sb-count-run { font-weight: 700; }
.sb-count-sep { opacity: 0.5; }
.sb-count-tot { color: var(--kb-fg-3); }
.sb-actions {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.sb-icon-btn {
  display: inline-grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--kb-fg-3);
  border-radius: var(--kb-radius-sm);
  cursor: pointer;
  font-size: 14px;
  transition: background var(--kb-dur-fast) var(--kb-ease), color var(--kb-dur-fast) var(--kb-ease);
}
.sb-icon-btn:hover:not(:disabled) {
  background: var(--kb-primary-tint);
  color: var(--kb-primary);
}
.sb-icon-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

/* ═══ Card list ═══ */
.sb-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px;
}

/* ── Session card ── */
.subagent-card {
  display: block;
  width: 100%;
  text-align: left;
  font: inherit;
  color: inherit;
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-left-width: 3px;
  border-radius: var(--kb-radius);
  padding: 10px 12px;
  margin-bottom: 8px;
  cursor: pointer;
  box-shadow: var(--kb-shadow-xs);
  transition:
    transform var(--kb-dur-fast) var(--kb-ease-out),
    box-shadow var(--kb-dur-fast) var(--kb-ease-out),
    border-color var(--kb-dur-fast) var(--kb-ease-out);
}
.subagent-card:last-child { margin-bottom: 0; }
.subagent-card:hover {
  transform: translateY(-1px);
  box-shadow: var(--kb-shadow-md);
  border-color: var(--kb-border-strong);
}
.subagent-card:focus-visible {
  outline: none;
  border-color: var(--kb-primary);
  box-shadow: 0 0 0 3px var(--kb-primary-glow);
}
/* Status accent (left border) */
.subagent-card.st-running { border-left-color: var(--kb-primary); }
.subagent-card.st-done { border-left-color: var(--kb-emerald); }
.subagent-card.st-error { border-left-color: var(--kb-rose); }
/* Selected ring */
.subagent-card.selected {
  border-color: var(--kb-primary);
  box-shadow: 0 0 0 2px var(--kb-primary-glow), var(--kb-shadow-md);
}

.card-row1 {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 5px;
  min-width: 0;
}
.type-badge {
  font-family: var(--kb-font-mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--kb-gold-deep);
  background: var(--kb-gold-soft);
  border: 1px solid rgba(212, 175, 106, 0.3);
  border-radius: 4px;
  padding: 1px 7px;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.engine-tag {
  font-size: 13px;
  line-height: 1;
}
.card-time {
  margin-left: auto;
  font-family: var(--kb-font-mono);
  font-size: 11px;
  color: var(--kb-fg-mute);
  flex-shrink: 0;
}
.card-desc {
  margin: 0 0 6px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--kb-fg-2);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-foot {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.foot-chip {
  font-family: var(--kb-font-mono);
  font-size: 11px;
  color: var(--kb-fg-3);
  white-space: nowrap;
}
.foot-err {
  font-size: 11px;
  font-weight: 600;
  color: var(--kb-rose);
  background: var(--kb-rose-soft);
  border: 1px solid rgba(184, 74, 90, 0.25);
  border-radius: 4px;
  padding: 1px 7px;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ════════════════════════════════════════════════════════════════
 * Detail drawer
 * ════════════════════════════════════════════════════════════════ */
.drawer-head {
  flex: none;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 20px;
  background: var(--kb-bg-elevated);
  border-bottom: 1px solid var(--kb-border);
}
.dh-meta {
  min-width: 0;
  flex: 1;
}
.dh-line1 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.dh-type {
  font-family: var(--kb-font-mono);
  font-size: 12px;
  font-weight: 700;
  color: var(--kb-gold-deep);
  background: var(--kb-gold-soft);
  border: 1px solid rgba(212, 175, 106, 0.3);
  border-radius: 4px;
  padding: 1px 8px;
}
.dh-engine {
  font-size: 12px;
  color: var(--kb-fg-3);
}
.dh-desc {
  margin: 0 0 6px;
  font-size: 13.5px;
  line-height: 1.55;
  color: var(--kb-fg);
  font-weight: 500;
}
.dh-stats {
  display: flex;
  align-items: center;
  gap: 7px;
  font-family: var(--kb-font-mono);
  font-size: 11.5px;
  color: var(--kb-fg-mute);
}
.dh-dot { opacity: 0.5; }

/* ── Transcript (scroll region) ── */
.subagent-transcript {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--kb-bg);
}

/* ═══ Message rows ═══ */
.msg {
  animation: sb-msg-in 0.4s var(--kb-ease-out) both;
}
@keyframes sb-msg-in {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
.msg.user {
  align-self: flex-end;
  max-width: 88%;
  background: var(--kb-primary-tint);
  border: 1px solid rgba(184, 71, 36, 0.18);
  border-radius: var(--kb-radius);
  padding: 10px 14px;
}
.msg.assistant {
  align-self: flex-start;
  max-width: 100%;
}
.msg-head {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  font-weight: 600;
  color: var(--kb-fg-2);
  margin-bottom: 5px;
}
.msg-head :deep(.anticon),
.msg-head > svg {
  display: inline-grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  font-size: 12px;
}
.msg.assistant .msg-head :deep(.anticon) {
  background: linear-gradient(135deg, var(--kb-primary), var(--kb-gold-deep));
  color: #fff;
  box-shadow: 0 2px 6px var(--kb-primary-glow);
}
.msg.user .msg-head :deep(.anticon) {
  background: var(--kb-primary);
  color: #fff;
}
.msg-text {
  font-size: 14px;
  line-height: 1.7;
  color: var(--kb-fg);
  word-break: break-word;
  overflow-wrap: break-word;
}
/* markdown-body global prose rules apply to .msg-text.markdown-body;
   a few local overrides keep the transcript tight. */
.msg-text :deep(p:first-child) { margin-top: 0; }
.msg-text :deep(p:last-child) { margin-bottom: 0; }
.msg-text :deep(pre) { font-size: 12.5px; }

/* ═══ Thinking ═══ */
.think-details {
  background: linear-gradient(135deg, var(--kb-gold-soft) 0%, transparent 100%);
  border: 1px solid var(--kb-gold-deep);
  border-left: 3px solid var(--kb-gold);
  border-radius: var(--kb-radius-sm);
  padding: var(--kb-space-sm) var(--kb-space);
}
.think-details summary {
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  font-family: var(--kb-font-serif);
  font-style: italic;
  color: var(--kb-gold-deep);
  display: flex;
  align-items: center;
  gap: var(--kb-space-xs);
  user-select: none;
}
.think-body {
  font-size: 12.5px;
  color: var(--kb-fg-3);
  white-space: pre-wrap;
  padding: var(--kb-space-sm) 0 0;
  border-top: 1px solid var(--kb-gold-deep);
  margin-top: var(--kb-space-sm);
  max-height: 320px;
  overflow-y: auto;
  line-height: 1.65;
  font-style: italic;
}
.muted { color: var(--kb-fg-mute); font-weight: 400; }

/* ═══ Tool cards ═══ */
.msg.tool_use,
.msg.tool_result {
  align-self: stretch;
  max-width: 100%;
}
.tool-card {
  background: var(--kb-bg-subtle);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius-sm);
  padding: 8px 10px;
}
.tool-card.result {
  border-color: var(--kb-emerald-soft);
  background: var(--kb-emerald-soft);
}
.tool-card.result.err {
  border-color: var(--kb-rose-soft);
  background: var(--kb-rose-soft);
}
.tool-head {
  display: flex;
  align-items: center;
  gap: var(--kb-space-sm);
  flex-wrap: wrap;
}
.tool-badge {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.3px;
  padding: 3px 10px;
  border-radius: 4px;
  background: var(--kb-amber-soft);
  color: var(--kb-gold-deep);
  font-family: var(--kb-font-mono);
  border: 1px solid rgba(212, 175, 106, 0.3);
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.tool-badge.mcp {
  background: rgba(124, 92, 255, 0.1);
  color: var(--kb-violet);
  border-color: rgba(124, 92, 255, 0.25);
}
.tool-badge.err {
  background: var(--kb-rose-soft);
  color: var(--kb-rose);
  border-color: rgba(184, 74, 90, 0.25);
}
.tool-preview {
  font-size: 11.5px;
  color: var(--kb-fg-3);
  font-family: var(--kb-font-mono);
  word-break: break-all;
  flex: 1;
  min-width: 0;
}
.tool-input,
.tool-result-pre {
  background: var(--kb-bg-code);
  color: #d5cfc6;
  padding: 9px 12px;
  border-radius: var(--kb-radius-sm);
  font-family: var(--kb-font-mono);
  font-size: 11.5px;
  line-height: 1.55;
  max-height: 240px;
  overflow: auto;
  margin: 6px 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid rgba(255, 255, 255, 0.06);
}
.tool-card details,
.tool-result-pre ~ details {
  margin-top: 4px;
}
.tool-card summary {
  cursor: pointer;
  font-size: 11px;
}

/* ═══ Plan ═══ */
.plan-card {
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-violet);
  border-radius: var(--kb-radius-sm);
  padding: 10px 12px;
}
.plan-head {
  font-weight: 700;
  margin-bottom: var(--kb-space-sm);
  color: var(--kb-violet);
  font-size: 13.5px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.plan-body {
  font-size: 13px;
  line-height: 1.65;
  color: var(--kb-fg-2);
}

/* ═══ Todo ═══ */
.todo-card {
  background: var(--kb-amber-soft);
  border: 1px solid var(--kb-amber);
  border-radius: var(--kb-radius-sm);
  padding: 10px 12px;
}
.todo-head {
  font-weight: 700;
  margin-bottom: var(--kb-space-sm);
  font-size: 13px;
  color: var(--kb-amber);
  display: flex;
  align-items: center;
  gap: 6px;
}
.todo-item {
  display: flex;
  gap: var(--kb-space-sm);
  padding: 3px 0;
  font-size: 13px;
  align-items: center;
  color: var(--kb-fg-2);
}
.todo-item.completed {
  color: var(--kb-emerald);
  text-decoration: line-through;
  text-decoration-color: var(--kb-emerald);
}
.todo-item.in_progress {
  color: var(--kb-primary);
  font-weight: 600;
}
.todo-check {
  width: 16px;
  text-align: center;
  font-weight: 700;
}
.todo-text { min-width: 0; }

/* ═══ Ask user (read-only) ═══ */
.ask-card {
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-amber);
  border-radius: var(--kb-radius-sm);
  padding: 10px 12px;
}
.ask-head {
  font-weight: 700;
  margin-bottom: var(--kb-space-xs);
  color: var(--kb-amber);
  font-size: 13.5px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.ask-question {
  margin-bottom: var(--kb-space-sm);
  font-size: 13px;
  color: var(--kb-fg-2);
  line-height: 1.6;
}
.ask-options {
  display: flex;
  flex-direction: column;
  gap: var(--kb-space-sm);
}
.ask-opt {
  padding: var(--kb-space-sm) var(--kb-space);
  border: 1px solid var(--kb-border-strong);
  border-radius: var(--kb-radius-sm);
  background: var(--kb-bg);
  display: flex;
  flex-direction: column;
  gap: 3px;
  color: var(--kb-fg-2);
  font-size: 12.5px;
}

/* ═══ System ═══ */
.sys-details {
  background: var(--kb-bg-subtle);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius-sm);
  padding: var(--kb-space-sm) var(--kb-space);
}
.sys-details summary,
.sys-head {
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: var(--kb-primary);
  user-select: none;
  display: flex;
  align-items: center;
  gap: var(--kb-space-xs);
}
.sys-body {
  font-size: 12px;
  padding: var(--kb-space-sm) 0 0;
  border-top: 1px solid var(--kb-border);
  margin-top: var(--kb-space-sm);
  color: var(--kb-fg-3);
  line-height: 1.6;
}

/* ═══ Result ═══ */
.result-card {
  align-self: stretch;
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border-strong);
  border-top: 3px solid var(--kb-emerald);
  border-radius: var(--kb-radius-sm);
  padding: 10px 12px;
}
.result-card.err {
  border-top-color: var(--kb-rose);
}
.result-card .msg-text :deep(table) { margin: 0; }
.result-card .msg-text :deep(th),
.result-card .msg-text :deep(td) {
  padding: 5px 10px;
  font-size: 12px;
}

/* ═══ Error ═══ */
.err-card {
  align-self: stretch;
  color: var(--kb-rose);
  background: var(--kb-rose-soft);
  border: 1px solid rgba(184, 74, 90, 0.25);
  border-radius: var(--kb-radius-sm);
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 500;
}

/* ═══ Streaming / typing ═══ */
.streaming-msg {
  align-self: flex-start;
}
.stream-cursor {
  display: inline-block;
  width: 7px;
  height: 16px;
  margin-left: 2px;
  vertical-align: text-bottom;
  background: linear-gradient(180deg, var(--kb-gold-bright), var(--kb-primary));
  border-radius: 1px;
  animation: sb-cursor-blink 1s steps(2, start) infinite;
}
@keyframes sb-cursor-blink {
  0%, 50% { opacity: 1; }
  50.01%, 100% { opacity: 0; }
}
.typing-dots {
  display: flex;
  gap: 6px;
  padding: 6px 0;
}
.typing-dots span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--kb-gold-bright), var(--kb-gold));
  animation: sb-typing 1.3s ease-in-out infinite;
}
.typing-dots span:nth-child(2) { animation-delay: 0.18s; }
.typing-dots span:nth-child(3) { animation-delay: 0.36s; }
@keyframes sb-typing {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.45; }
  30% { transform: translateY(-6px); opacity: 1; }
}

/* ═══ Drawer footer (streaming thinking) ═══ */
.think-foot {
  background: linear-gradient(135deg, var(--kb-gold-soft) 0%, transparent 100%);
  border: 1px solid var(--kb-gold-deep);
  border-left: 3px solid var(--kb-gold);
  border-radius: var(--kb-radius-sm);
  padding: var(--kb-space-sm) var(--kb-space);
}
.think-foot summary {
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  font-family: var(--kb-font-serif);
  font-style: italic;
  color: var(--kb-gold-deep);
  display: flex;
  align-items: center;
  gap: var(--kb-space-xs);
  user-select: none;
}

@media (prefers-reduced-motion: reduce) {
  .msg,
  .stream-cursor,
  .typing-dots span {
    animation: none !important;
  }
}
</style>
