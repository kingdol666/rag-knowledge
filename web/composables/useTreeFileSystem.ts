import { ref } from 'vue'
import type {
  TreeNodeResponse,
  CreateFolderRequest,
  CreateFileRequest,
  UpdateFolderRequest,
  UpdateFileRequest,
  DeleteResponse
} from '~/types/tree-file-system'

export interface TreeNode extends TreeNodeResponse {
  children?: TreeNode[]
}

export interface TreeStats {
  folders: number
  files: number
  total: number
}

export const useTreeFileSystem = () => {
  const treeData = ref<TreeNode[]>([])
  const currentNode = ref<TreeNode | null>(null)
  const children = ref<TreeNode[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const stats = ref<TreeStats>({ folders: 0, files: 0, total: 0 })

  const fetchTree = async () => {
    loading.value = true
    error.value = null
    try {
      const response = await $fetch<TreeNodeResponse[]>('/api/filesystem')
      treeData.value = response as TreeNode[]
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch tree'
      console.error('Fetch tree error:', err)
    } finally {
      loading.value = false
    }
  }

  const fetchChildren = async (parentId: string | null = null) => {
    loading.value = true
    error.value = null
    try {
      const url = parentId
        ? `/api/filesystem?action=children&parentId=${parentId}`
        : '/api/filesystem?action=children'
      const response = await $fetch<TreeNodeResponse[]>(url)
      children.value = response as TreeNode[]
      return children.value
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch children'
      console.error('Fetch children error:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  const fetchNode = async (id: string) => {
    loading.value = true
    error.value = null
    try {
      const response = await $fetch<TreeNodeResponse>(`/api/filesystem?action=node&id=${id}`)
      currentNode.value = response as TreeNode
      return currentNode.value
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch node'
      console.error('Fetch node error:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const fetchStats = async () => {
    try {
      const response = await $fetch<{ folders: number; files: number; total: number }>('/api/filesystem?action=count')
      stats.value = response as TreeStats
      return stats.value
    } catch (err: any) {
      console.error('Fetch stats error:', err)
      return { folders: 0, files: 0, total: 0 }
    }
  }

  const createFolder = async (request: CreateFolderRequest) => {
    loading.value = true
    error.value = null
    try {
      const response = await $fetch('/api/filesystem/nodes', {
        method: 'POST',
        body: { type: 'folder', ...request }
      })
      await fetchTree()
      await fetchStats()
      return response
    } catch (err: any) {
      error.value = err.message || 'Failed to create folder'
      console.error('Create folder error:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const createFile = async (request: CreateFileRequest) => {
    loading.value = true
    error.value = null
    try {
      const response = await $fetch('/api/filesystem/nodes', {
        method: 'POST',
        body: { type: 'file', ...request }
      })
      await fetchTree()
      await fetchStats()
      return response
    } catch (err: any) {
      error.value = err.message || 'Failed to create file'
      console.error('Create file error:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateFolder = async (id: string, request: UpdateFolderRequest) => {
    loading.value = true
    error.value = null
    try {
      const response = await $fetch(`/api/filesystem/nodes/${id}`, {
        method: 'PATCH',
        body: request
      })
      await fetchTree()
      return response
    } catch (err: any) {
      error.value = err.message || 'Failed to update folder'
      console.error('Update folder error:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateFile = async (id: string, request: UpdateFileRequest) => {
    loading.value = true
    error.value = null
    try {
      const response = await $fetch(`/api/filesystem/nodes/${id}`, {
        method: 'PATCH',
        body: request
      })
      await fetchTree()
      return response
    } catch (err: any) {
      error.value = err.message || 'Failed to update file'
      console.error('Update file error:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const deleteNode = async (id: string): Promise<DeleteResponse> => {
    loading.value = true
    error.value = null
    try {
      const response = await $fetch<DeleteResponse>(`/api/filesystem/nodes/${id}`, {
        method: 'DELETE'
      })
      await fetchTree()
      await fetchStats()
      return response
    } catch (err: any) {
      error.value = err.message || 'Failed to delete node'
      console.error('Delete node error:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const convertToTreeData = (nodes: TreeNodeResponse[], depth: number = 0): TreeNode[] => {
    return nodes.map(node => ({
      ...node,
      key: node.id,
      title: node.name,
      depth,
      children: node.children ? convertToTreeData(node.children, depth + 1) : undefined
    })) as TreeNode[]
  }

  const findNodeById = (nodes: TreeNode[], id: string): TreeNode | null => {
    for (const node of nodes) {
      if (node.id === id) {
        return node
      }
      if (node.children && node.children.length > 0) {
        const found = findNodeById(node.children, id)
        if (found) return found
      }
    }
    return null
  }

  const uploadFile = async (file: File, parentId: string | null = null, description: string = '') => {
    loading.value = true
    error.value = null
    try {
      const formData = new FormData()
      if (parentId) {
        formData.append('parentId', parentId)
      }
      if (description) {
        formData.append('description', description)
      }
      formData.append('file', file)

      const response = await $fetch<{ success: boolean; file?: any; error: string }>('/api/filesystem/upload', {
        method: 'POST',
        body: formData
      })

      if (response.success) {
        await fetchTree()
        await fetchStats()
        return response.file
      } else {
        throw new Error(response.error || 'Upload failed')
      }
    } catch (err: any) {
      error.value = err.message || 'Failed to upload file'
      console.error('Upload file error:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  interface UploadFileItem {
    file: File
    description?: string
  }

  interface UploadResult {
    success: boolean
    file?: any
    error?: string
    fileName: string
  }

  const uploadFiles = async (
    files: UploadFileItem[],
    parentId: string | null = null,
    onProgress?: (completed: number, total: number, currentFile: string) => void
  ): Promise<UploadResult[]> => {
    const results: UploadResult[] = []
    const total = files.length

    for (let i = 0; i < files.length; i++) {
      const { file, description } = files[i]
      const fileName = file.name

      try {
        if (onProgress) {
          onProgress(i, total, fileName)
        }

        const result = await uploadFile(file, parentId, description)
        results.push({
          success: true,
          file: result,
          fileName
        })
      } catch (err: any) {
        results.push({
          success: false,
          error: err.message || 'Upload failed',
          fileName
        })
      }
    }

    if (onProgress) {
      onProgress(total, total, '')
    }

    await fetchTree()
    await fetchStats()

    return results
  }

  return {
    treeData,
    currentNode,
    children,
    loading,
    error,
    stats,
    fetchTree,
    fetchChildren,
    fetchNode,
    fetchStats,
    createFolder,
    createFile,
    updateFolder,
    updateFile,
    deleteNode,
    uploadFile,
    uploadFiles,
    convertToTreeData,
    findNodeById
  }
}
