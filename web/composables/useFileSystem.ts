import { ref } from 'vue'
import { useTreeFileSystem } from './useTreeFileSystem'
import { usePDFParser } from './usePDFParser'
import type { TreeNode } from './useTreeFileSystem'

export const useFileSystem = () => {
  const treeFileSystem = useTreeFileSystem()
  const pdfParser = usePDFParser()

  const selectedNode = ref<TreeNode | null>(null)
  const selectedKeys = ref<string[]>([])
  const expandedKeys = ref<string[]>([])

  const downloadFile = (node: TreeNode) => {
    const url = `/api/preview/file?id=${node.id}`
    const link = document.createElement('a')
    link.href = url
    link.download = node.name
    link.click()
  }

  const runtimeConfig = useRuntimeConfig()
  const treeStoragePath = runtimeConfig.public.treeStoragePath as string

  return {
    ...treeFileSystem,
    ...pdfParser,
    selectedNode,
    selectedKeys,
    expandedKeys,
    downloadFile,
    treeStoragePath
  }
}
