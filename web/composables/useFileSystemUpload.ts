import { ref, type Ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { message, type UploadFile } from 'ant-design-vue'
import type { TreeNode } from './useTreeFileSystem'

/**
 * Shared upload-related state and handlers extracted from file-system.vue.
 *
 * The upload feature owns its own dialog/list/progress state, but depends on a
 * few pieces of component-level state (`createParentId`, `selectedNode`) and the
 * file-system API. Those are injected via `options`, keeping the Vue reactivity
 * graph intact while letting the component shed ~100 lines of inline logic.
 */
export interface UploadProgress {
  completed: number
  total: number
  currentFile: string
}

export interface UseFileSystemUploadOptions {
  /** Shared with create-folder/edit flows, so it stays owned by the component. */
  createParentId: Ref<string | null>
  selectedNode: Ref<TreeNode | null>
  uploadFile: (file: File, parentId: string | null, description: string) => Promise<unknown>
  uploadFiles: (
    files: { file: File; description?: string }[],
    parentId: string | null,
    onProgress?: (completed: number, total: number, currentFile: string) => void
  ) => Promise<{ success: boolean; file?: unknown; error?: string; fileName: string }[]>
  fetchChildren: (id: string) => Promise<unknown>
  handleRefresh: () => Promise<void>
}

/**
 * Resolve the raw File from an ant-design upload list item.
 * `originFileObj` holds the RcFile (a File subclass) once chosen; the `?? item`
 * fallback mirrors the original component behaviour for items that are already
 * File-like. ant-design's loose typing forces a single justified cast here.
 */
function resolveFile(item: UploadFile): File {
  return (item.originFileObj ?? (item as unknown as File)) as File
}

export function useFileSystemUpload(options: UseFileSystemUploadOptions) {
  const { t } = useI18n()
  const {
    createParentId,
    selectedNode,
    uploadFile,
    uploadFiles,
    fetchChildren,
    handleRefresh
  } = options

  // Single-file upload dialog state
  const showUploadFileDialog = ref(false)
  const uploadFileList = ref<UploadFile[]>([])
  const uploadDescription = ref('')
  const uploadingFile = ref(false)

  // Batch upload dialog state
  const showBatchUploadDialog = ref(false)
  const batchUploadFileList = ref<UploadFile[]>([])
  const batchUploadDescription = ref('')
  const batchFileDescriptions = ref<string[]>([])
  const batchUploading = ref(false)
  const batchUploadProgress = ref<UploadProgress>({ completed: 0, total: 0, currentFile: '' })

  const handleCreateFile = (parent: TreeNode) => {
    createParentId.value = parent.id
    uploadFileList.value = []
    showUploadFileDialog.value = true
  }

  const handleBatchCreateFile = (parent: TreeNode) => {
    createParentId.value = parent.id
    batchUploadFileList.value = []
    batchUploadDescription.value = ''
    batchFileDescriptions.value = []
    showBatchUploadDialog.value = true
  }

  const closeUploadFileDialog = () => {
    showUploadFileDialog.value = false
    uploadFileList.value = []
    uploadDescription.value = ''
    createParentId.value = null
  }

  const closeBatchUploadDialog = () => {
    showBatchUploadDialog.value = false
    batchUploadFileList.value = []
    batchUploadDescription.value = ''
    batchFileDescriptions.value = []
    batchUploadProgress.value = { completed: 0, total: 0, currentFile: '' }
    createParentId.value = null
  }

  // Returning false stops ant-design from auto-uploading; we drive it ourselves.
  const beforeUploadFile = (_file: UploadFile) => false
  const beforeBatchUploadFile = (_file: UploadFile) => false

  const handleUploadFile = async () => {
    if (uploadFileList.value.length === 0) {
      message.error(t('fs.selectFileRequired'))
      return
    }

    uploadingFile.value = true
    try {
      const fileItem = uploadFileList.value[0]
      const file = resolveFile(fileItem)

      await uploadFile(file, createParentId.value, uploadDescription.value)
      message.success(t('fs.uploadSuccess'))
      closeUploadFileDialog()
      await handleRefresh()
    } catch (error: unknown) {
      console.error('Upload file error:', error)
      const msg = error instanceof Error ? error.message : t('fs.uploadFailed')
      message.error(msg || t('fs.uploadFailed'))
    } finally {
      uploadingFile.value = false
    }
  }

  const handleBatchUpload = async () => {
    if (batchUploadFileList.value.length === 0) {
      message.error(t('fs.selectFileRequired'))
      return
    }

    batchUploading.value = true
    batchUploadProgress.value = { completed: 0, total: batchUploadFileList.value.length, currentFile: '' }

    try {
      const files = batchUploadFileList.value.map((item, index) => ({
        file: resolveFile(item),
        description: batchFileDescriptions.value[index] || batchUploadDescription.value || ''
      }))

      const results = await uploadFiles(
        files,
        createParentId.value,
        (completed, total, currentFile) => {
          batchUploadProgress.value = { completed, total, currentFile }
        }
      )

      const successCount = results.filter(r => r.success).length
      const failCount = results.length - successCount

      if (failCount === 0) {
        message.success(t('fs.uploadSuccess') + ` ${successCount} ` + t('fs.files'))
      } else {
        message.warning(t('fs.uploadSuccess') + `: ${successCount} ` + t('fs.files') + ` ${t('action.success')}, ${failCount} ` + t('fs.files') + ` ${t('action.error')}`)
      }

      closeBatchUploadDialog()

      if (selectedNode.value && selectedNode.value.type === 'folder') {
        await fetchChildren(selectedNode.value.id)
      }
    } catch (error: unknown) {
      console.error('Batch upload error:', error)
      const msg = error instanceof Error ? error.message : t('fs.uploadFailed')
      message.error(msg || t('fs.uploadFailed'))
    } finally {
      batchUploading.value = false
      batchUploadProgress.value = { completed: 0, total: 0, currentFile: '' }
    }
  }

  return {
    // single-file upload
    showUploadFileDialog,
    uploadFileList,
    uploadDescription,
    uploadingFile,
    handleCreateFile,
    handleUploadFile,
    beforeUploadFile,
    closeUploadFileDialog,
    // batch upload
    showBatchUploadDialog,
    batchUploadFileList,
    batchUploadDescription,
    batchFileDescriptions,
    batchUploading,
    batchUploadProgress,
    handleBatchCreateFile,
    handleBatchUpload,
    beforeBatchUploadFile,
    closeBatchUploadDialog
  }
}
