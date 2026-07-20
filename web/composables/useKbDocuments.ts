import { ref } from 'vue'
import type { KbCatalogEntry, KbDocumentContent } from './useKnowledgeSearch'

export interface KbDoc {
  name: string
  description?: string
  path: string
  file_type: string
  file_size?: number
  tags?: string[]
  updated_at?: string
  doc_id?: string
}

// KbCatalogEntry and KbDocumentContent are imported from useKnowledgeSearch
// to avoid Nuxt auto-import duplicate warnings

/**
 * Knowledge base document management composable
 * Provides document CRUD, move, tag management, content editing
 */
export const useKbDocuments = () => {
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * Fetch top-level KB catalog (parentId === null)
   */
  const fetchCatalog = async (): Promise<KbCatalogEntry[]> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ knowledgeBases: KbCatalogEntry[] }>('/api/kb/catalog')
      return res.knowledgeBases || []
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch catalog'
      return []
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch sub-KB catalog (sub-KBs under a specified parent KB)
   */
  const fetchSubCatalog = async (parentKbId: string): Promise<KbCatalogEntry[]> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ knowledgeBases: KbCatalogEntry[] }>('/api/kb/catalog', {
        params: { kb_id: parentKbId },
      })
      return res.knowledgeBases || []
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch sub-KB'
      return []
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch all documents under a knowledge base
   */
  const fetchDocuments = async (kbId: string): Promise<KbDoc[]> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ documents: KbDoc[] }>('/api/kb/documents', {
        params: { kb_id: kbId },
      })
      return res.documents || []
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch document list'
      return []
    } finally {
      loading.value = false
    }
  }

  /**
   * Read document content
   */
  const readDocument = async (
    path: string,
    opts: { offset?: number; limit?: number; maxChars?: number } = {}
  ): Promise<KbDocumentContent> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<KbDocumentContent>('/api/kb/document', {
        params: {
          path,
          offset: opts.offset ?? 0,
          limit: opts.limit ?? 200,
          max_chars: opts.maxChars ?? 50000,
        },
      })
      return res
    } catch (err: any) {
      error.value = err.message || 'Failed to read document'
      return { content: '', totalLines: 0, truncated: false }
    } finally {
      loading.value = false
    }
  }

  /**
   * Create new document
   */
  const createDocument = async (
    kbId: string,
    name: string,
    content: string,
    description?: string
  ): Promise<any> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ success: boolean; document: any }>('/api/kb/documents/create', {
        method: 'POST',
        body: { kbId, name, content, description },
      })
      return res
    } catch (err: any) {
      error.value = err.message || 'Failed to create document'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Update document metadata
   */
  const updateDocumentMeta = async (
    kbId: string,
    docPath: string,
    meta: { name?: string; description?: string; metadata?: Record<string, any> }
  ): Promise<any> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ success: boolean; document: any }>('/api/kb/documents/update', {
        method: 'PATCH',
        body: { kbId, docPath, ...meta },
      })
      return res
    } catch (err: any) {
      error.value = err.message || 'Failed to update document'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Update document content
   */
  const updateDocumentContent = async (
    kbId: string,
    docPath: string,
    content: string
  ): Promise<any> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ success: boolean; document: any }>('/api/kb/documents/content', {
        method: 'PUT',
        body: { kbId, docPath, content },
      })
      return res
    } catch (err: any) {
      error.value = err.message || 'Failed to update content'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Delete document
   */
  const deleteDocument = async (kbId: string, docPath: string): Promise<any> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch('/api/kb/documents/delete', {
        method: 'DELETE',
        body: { kbId, docPath },
      })
      return res
    } catch (err: any) {
      error.value = err.message || 'Failed to delete document'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Batch delete documents
   */
  const batchDeleteDocuments = async (kbId: string, docPaths: string[]): Promise<any> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch('/api/kb/documents/batch-delete', {
        method: 'POST',
        body: { kbId, docPaths },
      })
      return res
    } catch (err: any) {
      error.value = err.message || 'Failed to batch delete'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Move document to another knowledge base
   */
  const moveDocument = async (docPath: string, targetKbId: string): Promise<any> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ success: boolean; document: any }>('/api/kb/documents/move', {
        method: 'POST',
        body: { docPath, targetKbId },
      })
      return res
    } catch (err: any) {
      error.value = err.message || 'Failed to move document'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Update document tags
   */
  const updateDocumentTags = async (kbId: string, docPath: string, tags: string[]): Promise<any> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch('/api/kb/documents/tags', {
        method: 'PATCH',
        body: { kbId, docPath, tags },
      })
      return res
    } catch (err: any) {
      error.value = err.message || 'Failed to update tags'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch all tags
   */
  const fetchAllTags = async (): Promise<string[]> => {
    try {
      const res = await $fetch<{ tags?: string[] }>('/api/kb/tags')
      return res.tags || []
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch tags'
      return []
    }
  }

  /**
   * Search documents by tag
   */
  const searchByTag = async (tag: string, kbId?: string): Promise<any[]> => {
    loading.value = true
    error.value = null
    try {
      const params: Record<string, string> = { tag }
      if (kbId) params.kb_id = kbId
      const res = await $fetch<{ documents?: any[] }>('/api/kb/documents/by-tag', { params })
      return res.documents || []
    } catch (err: any) {
      error.value = err.message || 'Tag search failed'
      return []
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    fetchCatalog,
    fetchSubCatalog,
    fetchDocuments,
    readDocument,
    createDocument,
    updateDocumentMeta,
    updateDocumentContent,
    deleteDocument,
    batchDeleteDocuments,
    moveDocument,
    updateDocumentTags,
    fetchAllTags,
    searchByTag,
  }
}
