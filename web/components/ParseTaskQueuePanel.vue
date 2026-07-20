<template>
  <div class="parse-queue-trigger">
    <!-- Floating trigger button -->
    <a-badge :count="runningCount" :overflow-count="99" :offset="[-4, 4]">
      <a-button
        shape="circle"
        size="large"
        class="queue-btn"
        @click="openPanel"
      >
        <template #icon><FileTextOutlined /></template>
      </a-button>
    </a-badge>

    <!-- Drawer panel -->
    <a-drawer
      v-model:open="panelOpen"
      title="解析任务队列"
      placement="right"
      :width="420"
    >
      <!-- Empty state -->
      <div v-if="tasks.length === 0" class="queue-empty">
        <a-empty :description="$t('parseQueue.noTasks')" />
      </div>

      <!-- Task list -->
      <a-list v-else :data-source="tasks" class="queue-list">
        <template #renderItem="{ item }">
          <a-list-item class="queue-task-item">
            <a-list-item-meta>
              <template #title>
                <div class="task-header">
                  <a-tooltip :title="item.fileNames.join(', ')" placement="topLeft">
                    <span class="task-name">{{ item.name }}</span>
                  </a-tooltip>
                  <a-tag v-if="item.status === 'running'" color="processing">解析中</a-tag>
                  <a-tag v-else-if="item.status === 'saving'" color="warning">保存中</a-tag>
                  <a-tag v-else-if="item.status === 'done'" color="success">完成</a-tag>
                  <a-tag v-else-if="item.status === 'error'" color="error">{{ $t("parseQueue.failed") }}</a-tag>
                </div>
              </template>
              <template #description>
                <div class="task-body">
                  <!-- Progress bar for in-flight tasks -->
                  <div v-if="item.status === 'running' || item.status === 'saving'" class="task-progress">
                    <a-progress
                      :percent="item.progress.total > 0
                        ? Math.round((item.progress.completed / item.progress.total) * 100)
                        : 0"
                      :status="item.status === 'saving' ? 'active' : undefined"
                      size="small"
                    />
                    <div v-if="item.progress.currentFile" class="progress-file">
                      当前: {{ item.progress.currentFile }}
                    </div>
                  </div>

                  <!-- Result summary for completed tasks -->
                  <div v-if="item.status === 'done' && item.result" class="task-result">
                    <span :class="item.result.success ? 'result-ok' : 'result-fail'">
                      {{ item.result.successfulFiles }}/{{ item.result.totalFiles }} 成功
                      <template v-if="item.result.failedFiles > 0">
                        · {{ item.result.failedFiles }} 失败
                      </template>
                      <template v-if="item.result.savedCount != null">
                        · 入库 {{ item.result.savedCount }} 个
                      </template>
                    </span>
                    <div v-if="item.parentName" class="result-target">
                      目标: {{ item.parentName }}
                    </div>
                  </div>

                  <!-- Error message for failed tasks -->
                  <div v-if="item.status === 'error' && item.error" class="task-error">
                    {{ item.error }}
                  </div>

                  <!-- Timestamp -->
                  <div class="task-meta">
                    <span class="task-time">{{ formatTime(item.createdAt) }}</span>
                    <span v-if="item.finishedAt" class="task-time">
                      耗时 {{ elapsed(item.createdAt, item.finishedAt) }}
                    </span>
                  </div>
                </div>
              </template>
            </a-list-item-meta>

            <!-- Actions -->
            <template #actions>
              <a-tooltip
                v-if="item.status === 'done' || item.status === 'error'"
                :title="$t('parseQueue.remove')"
              >
                <DeleteOutlined @click="removeTask(item.id)" />
              </a-tooltip>
            </template>
          </a-list-item>
        </template>

        <!-- Footer action: clear completed -->
        <template #footer>
          <div v-if="tasks.some(t => t.status === 'done' || t.status === 'error')" class="queue-footer">
            <a-button size="small" @click="clearCompleted">{{ $t("parseQueue.clear") }}</a-button>
          </div>
        </template>
      </a-list>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import {
  FileTextOutlined,
  DeleteOutlined,
} from '@ant-design/icons-vue'
import { useParseTaskQueue } from '~/composables/useParseTaskQueue'

const { tasks, runningCount, panelOpen, openPanel, removeTask, clearCompleted } = useParseTaskQueue()

function formatTime(ts: number): string {
  const d = new Date(ts)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`
}

function elapsed(start: number, end: number): string {
  const s = Math.round((end - start) / 1000)
  if (s < 60) return `${s}s`
  return `${Math.floor(s / 60)}m${s % 60}s`
}
</script>

<style scoped>
.parse-queue-trigger {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 1050;
}
.queue-btn {
  width: 48px;
  height: 48px;
  font-size: 20px;
  box-shadow: var(--kb-shadow-md);
}
.queue-empty {
  margin-top: 60px;
}
.queue-list {
  padding: 0;
}
.queue-task-item {
  padding: 12px 0 !important;
}
.task-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.task-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}
.task-body {
  margin-top: 4px;
}
.task-progress {
  margin-bottom: 6px;
}
.progress-file {
  font-size: 12px;
  color: var(--kb-fg-mute);
  margin-top: 2px;
}
.task-result {
  margin-bottom: 4px;
}
.result-ok {
  color: var(--kb-emerald);
  font-weight: 500;
}
.result-fail {
  color: var(--kb-rose);
  font-weight: 500;
}
.result-target {
  font-size: 12px;
  color: var(--kb-fg-mute);
  margin-top: 2px;
}
.task-error {
  color: var(--kb-rose);
  font-size: 13px;
  margin-bottom: 4px;
  word-break: break-word;
}
.task-meta {
  display: flex;
  gap: 12px;
  margin-top: 4px;
}
.task-time {
  font-size: 11px;
  color: var(--kb-fg-mute);
}
.queue-footer {
  text-align: center;
  padding: 8px 0;
}
</style>
