import { ref, computed } from 'vue'
import type { TreeNode, FileNode } from '~/types/tree-file-system'

export type PreviewType = 'image' | 'pdf' | 'video' | 'audio' | 'text' | 'code' | 'docx' | 'markdown' | 'office' | 'unknown'

// Simplified node type for preview functionality
export interface PreviewNode {
  id: string
  name: string
  type: 'folder' | 'file'
  mimeType?: string
  fileType?: string
}

export interface UseFilePreviewOptions {
  onError?: (message: string) => void
}

// Type guard: check if node is a file
export function isFileNode(node: TreeNode | PreviewNode): node is FileNode {
  return node.type === 'file'
}

export function useFilePreview(options: UseFilePreviewOptions = {}) {
  const { onError } = options

  // State
  const previewLoading = ref(false)
  const previewContent = ref<string>('')
  const fullscreenPreviewNode = ref<FileNode | null>(null)
  const fullscreenPreviewContent = ref<string>('')
  const showFullscreenPreview = ref(false)

  // Check if it's a text file
  const isTextFile = (node: TreeNode | PreviewNode): boolean => {
    const mimeType = (node as FileNode).mimeType || ''
    const fileType = (node as FileNode).fileType || ''
    return (
      mimeType.startsWith('text/') ||
      fileType === 'txt' ||
      fileType === 'json' ||
      fileType === 'js' ||
      fileType === 'ts' ||
      fileType === 'vue' ||
      fileType === 'html' ||
      fileType === 'css' ||
      fileType === 'md'
    )
  }

  // Get file preview type
  const getFilePreviewType = (node: TreeNode | PreviewNode): PreviewType => {
    const mimeType = (node as FileNode).mimeType || ''
    const fileType = (node as FileNode).fileType?.toLowerCase() || ''

    // Image
    if (mimeType.startsWith('image/')) return 'image'

    // PDF
    if (mimeType === 'application/pdf') return 'pdf'

    // Video
    if (mimeType.startsWith('video/')) return 'video'

    // Audio
    if (mimeType.startsWith('audio/')) return 'audio'

    // DOCX files - can preview
    if (fileType === 'docx' || mimeType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
      return 'docx'
    }

    // Markdown files - can preview
    if (fileType === 'md' || fileType === 'markdown' || mimeType === 'text/markdown') {
      return 'markdown'
    }

    // Other Office documents
    const officeTypes = [
      'application/msword',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-powerpoint',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    ]
    if (officeTypes.includes(mimeType)) return 'office'

    // Code files
    const codeExtensions = ['js', 'ts', 'vue', 'jsx', 'tsx', 'py', 'java', 'cpp', 'c', 'h', 'go', 'rs', 'rb', 'php', 'sql', 'sh', 'bat', 'ps1', 'yaml', 'yml', 'xml', 'svg']
    if (codeExtensions.includes(fileType)) return 'code'

    // Text files
    const textTypes = ['text/', 'application/json', 'application/xml', 'application/javascript']
    if (textTypes.some(t => mimeType.startsWith(t))) return 'text'
    const textExtensions = ['txt', 'log', 'csv', 'ini', 'conf', 'properties']
    if (textExtensions.includes(fileType)) return 'text'

    return 'unknown'
  }

  // Load file preview content
  const loadFilePreview = async (node: TreeNode | PreviewNode) => {
    // Only text files need preloading of content
    if (!isTextFile(node)) {
      previewContent.value = ''
      return
    }

    previewLoading.value = true
    previewContent.value = ''

    try {
      const response = await fetch(`/api/preview/file?id=${node.id}`)
      if (response.ok) {
        previewContent.value = await response.text()
      } else {
        throw new Error('Failed to load file content')
      }
    } catch (error: any) {
      onError?.('Failed to load file: ' + error.message)
    } finally {
      previewLoading.value = false
    }
  }

  // Download file
  const downloadFile = (node: TreeNode | PreviewNode) => {
    if (node.type === 'file') {
      const link = document.createElement('a')
      link.href = `/api/preview/file?id=${node.id}`
      link.download = node.name
      link.click()
    }
  }

  // Open fullscreen preview
  const openFullscreenPreview = async (node: TreeNode | PreviewNode) => {
    if (!isFileNode(node)) {
      onError?.('Only files can be opened in fullscreen preview')
      return
    }

    fullscreenPreviewNode.value = node
    fullscreenPreviewContent.value = ''
    showFullscreenPreview.value = true

    const previewType = getFilePreviewType(node)

    // Text and code files need preloading of content
    if (previewType === 'text' || previewType === 'code') {
      try {
        const response = await fetch(`/api/preview/file?id=${node.id}`)
        if (response.ok) {
          fullscreenPreviewContent.value = await response.text()
        }
      } catch (error) {
        console.error('Failed to load file content:', error)
      }
    }
  }

  // Close fullscreen preview
  const closeFullscreenPreview = () => {
    showFullscreenPreview.value = false
    fullscreenPreviewNode.value = null
    fullscreenPreviewContent.value = ''
  }

  // Open file in new window
  const openInNewWindow = (node: TreeNode | PreviewNode) => {
    window.open(`/api/preview/file?id=${node.id}`, '_blank')
  }

  // Get preview URL
  const getPreviewUrl = (node: TreeNode | PreviewNode): string => {
    const previewType = getFilePreviewType(node)
    if (previewType === 'docx') {
      return `/api/preview/docx-preview?id=${node.id}`
    }
    if (previewType === 'markdown') {
      return `/api/preview/markdown-preview?id=${node.id}`
    }
    return `/api/preview/file?id=${node.id}`
  }

  // Clear preview state
  const clearPreview = () => {
    previewContent.value = ''
    previewLoading.value = false
  }

  return {
    // State
    previewLoading,
    previewContent,
    fullscreenPreviewNode,
    fullscreenPreviewContent,
    showFullscreenPreview,

    // Methods
    isTextFile,
    getFilePreviewType,
    loadFilePreview,
    downloadFile,
    openFullscreenPreview,
    closeFullscreenPreview,
    openInNewWindow,
    getPreviewUrl,
    clearPreview
  }
}
