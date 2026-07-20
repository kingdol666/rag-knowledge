import { ref } from 'vue'

export interface KbCatalogEntry {
  kbId: string
  name: string
  description: string
  documentCount: number
  path: string
  parentId?: string | null
}

export interface KbSearchHit {
  kbId: string
  kbName: string
  docName: string
  description: string
  path: string
  score: number
}

export interface KbDocument {
  name: string
  description?: string
  path: string
  file_type: string
  file_size?: number
}

export interface KbDocumentContent {
  content: string
  totalLines: number
  truncated: boolean
}

/**
 * Knowledge-base search composable.
 * Wraps the /api/kb/* read-only endpoints.
 */
export const useKnowledgeSearch = () => {
  const loading = ref(false)
  const error = ref<string | null>(null)

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

  const search = async (query: string, topK = 10): Promise<KbSearchHit[]> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ hits: KbSearchHit[] }>('/api/kb/search', {
        params: { query, top_k: topK },
      })
      return res.hits || []
    } catch (err: any) {
      error.value = err.message || 'Search failed'
      return []
    } finally {
      loading.value = false
    }
  }

  const fetchKbDocuments = async (kbId: string): Promise<KbDocument[]> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ documents: KbDocument[] }>('/api/kb/documents', {
        params: { kb_id: kbId },
      })
      return res.documents || []
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch documents'
      return []
    } finally {
      loading.value = false
    }
  }

  const readDocument = async (
    path: string,
    opts: { offset?: number; limit?: number; maxChars?: number } = {},
  ): Promise<KbDocumentContent> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<KbDocumentContent>('/api/kb/document', {
        params: {
          path,
          offset: opts.offset ?? 0,
          limit: opts.limit ?? 200,
          max_chars: opts.maxChars ?? 20000,
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

  return {
    loading,
    error,
    fetchCatalog,
    search,
    fetchKbDocuments,
    readDocument,
  }
}