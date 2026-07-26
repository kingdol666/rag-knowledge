/**
 * useLatestTodoStore — reactive store for the latest TodoWrite snapshot.
 * ─────────────────────────────────────────────────────────────────────
 * Claude Code and OMP emit TodoWrite tool calls to track their plan.
 * Previously the todo list was rendered inline (one card per call), flooding
 * the timeline. This store keeps ONLY the latest snapshot so a dedicated
 * sidebar panel can show live task progress without scrolling noise.
 *
 * The store is per-engine (Claude and OMP each have isolated todo state),
 * matching the per-engine chat isolation in claude-chat.vue.
 */
import { ref, computed, type ComputedRef, type Ref } from 'vue'
import type { TodoItem } from '~/utils/claude-messages'

interface TodoSnapshot {
  todos: TodoItem[]
  updatedAt: number
  /** The tool_use_id of the TodoWrite call that produced this snapshot. */
  sourceId: string
}

type EngineName = 'claude' | 'omp'

const _snapshots: Ref<Record<EngineName, TodoSnapshot | null>> = ref({
  claude: null,
  omp: null,
})

export function useLatestTodoStore() {
  const snapshot = (engine: EngineName): ComputedRef<TodoSnapshot | null> =>
    computed(() => _snapshots.value[engine])

  /** Replace the snapshot for an engine (called on each TodoWrite tool_use). */
  function update(engine: EngineName, todos: TodoItem[], sourceId: string): void {
    _snapshots.value = {
      ..._snapshots.value,
      [engine]: { todos, updatedAt: Date.now(), sourceId },
    }
  }

  function clear(engine: EngineName): void {
    _snapshots.value = { ..._snapshots.value, [engine]: null }
  }

  function clearAll(): void {
    _snapshots.value = { claude: null, omp: null }
  }

  return { snapshot, update, clear, clearAll }
}
