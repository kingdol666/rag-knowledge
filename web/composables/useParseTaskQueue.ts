import { ref, computed } from 'vue'
import type { BatchParsePDFFileVTResponse, SaveParsedFilesResponse } from '~/types/pdf-parse'

// -- types --------------------------------------------------------
export interface ParseTaskProgress {
  completed: number
  total: number
  currentFile: string
}

export interface ParseTaskResult {
  success: boolean
  totalFiles: number
  successfulFiles: number
  failedFiles: number
  /** Number of documents saved into the KB (0 if not saved). */
  savedCount?: number
}

export interface ParseTask {
  id: string
  /** Human-readable label for the queue panel (first filename or "N files"). */
  name: string
  fileNames: string[]
  fileCount: number
  parentId?: string
  parentName?: string
  useOcr: boolean
  outputDir?: string

  /** running → saving → done / error. */
  status: 'running' | 'saving' | 'done' | 'error'
  progress: ParseTaskProgress

  result?: ParseTaskResult
  error?: string

  createdAt: number
  finishedAt?: number
}

// ─── singleton reactive store ──────────────────────────────────────
const _tasks = ref<ParseTask[]>([])
const _panelOpen = ref(false)

let _idSeq = 0
function _nextId(): string {
  _idSeq += 1
  return `parse_${Date.now()}_${_idSeq}`
}

/** Sort newest-first. */
const sortedTasks = computed(() =>
  [..._tasks.value].sort((a, b) => b.createdAt - a.createdAt),
)

const runningCount = computed(() =>
  _tasks.value.filter((t) => t.status === 'running' || t.status === 'saving').length,
)

const panelOpen = computed({
  get: () => _panelOpen.value,
  set: (v: boolean) => { _panelOpen.value = v },
})

// ─── public API ────────────────────────────────────────────────────
export function useParseTaskQueue() {
  function addTask(opts: {
    fileNames: string[]
    parentId?: string
    parentName?: string
    useOcr: boolean
    outputDir?: string
  }): string {
    const id = _nextId()
    const label =
      opts.fileNames.length === 1
        ? opts.fileNames[0]
        : opts.fileNames[0] + ` and ${opts.fileNames.length} more files`

    const task: ParseTask = {
      id,
      name: label,
      fileNames: opts.fileNames,
      fileCount: opts.fileNames.length,
      parentId: opts.parentId,
      parentName: opts.parentName,
      useOcr: opts.useOcr,
      outputDir: opts.outputDir,
      status: 'running',
      progress: { completed: 0, total: opts.fileNames.length, currentFile: '' },
      createdAt: Date.now(),
    }
    _tasks.value.push(task)
    // Auto-reveal the queue panel so the user sees the new task at once.
    _panelOpen.value = true
    return id
  }

  function updateProgress(taskId: string, progress: ParseTaskProgress): void {
    const t = _tasks.value.find((t) => t.id === taskId)
    if (t) t.progress = { ...progress }
  }

  /** Call when the SSE stream is done and saveParsedFiles is about to start. */
  function markSaving(taskId: string): void {
    const t = _tasks.value.find((t) => t.id === taskId)
    if (t) t.status = 'saving'
  }

  /** Complete successfully. */
  function completeTask(
    taskId: string,
    summary: BatchParsePDFFileVTResponse,
    savedCount?: number,
  ): void {
    const t = _tasks.value.find((t) => t.id === taskId)
    if (!t) return
    t.status = 'done'
    t.finishedAt = Date.now()
    t.progress.completed = summary.total_files || summary.results?.length || 0
    t.progress.currentFile = ''
    t.result = {
      success: summary.success,
      totalFiles: summary.total_files,
      successfulFiles: summary.successful_files,
      failedFiles: summary.failed_files,
      savedCount,
    }
  }

  /** Mark as failed. */
  function failTask(taskId: string, errorMessage: string): void {
    const t = _tasks.value.find((t) => t.id === taskId)
    if (!t) return
    t.status = 'error'
    t.finishedAt = Date.now()
    t.error = errorMessage
  }

  function removeTask(taskId: string): void {
    _tasks.value = _tasks.value.filter((t) => t.id !== taskId)
  }

  function clearCompleted(): void {
    _tasks.value = _tasks.value.filter((t) => t.status === 'running' || t.status === 'saving')
  }

  function openPanel(): void { _panelOpen.value = true }
  function closePanel(): void { _panelOpen.value = false }

  return {
    tasks: sortedTasks,
    runningCount,
    panelOpen,
    openPanel,
    closePanel,
    addTask,
    updateProgress,
    markSaving,
    completeTask,
    failTask,
    removeTask,
    clearCompleted,
  }
}
