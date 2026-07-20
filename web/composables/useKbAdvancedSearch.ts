import { ref } from 'vue'

/**
 * Vector search result entry (mapped frontend format)
 */
export interface VectorSearchHit {
  doc_id: string
  doc_name: string
  kb_id: string
  kb_name: string
  path: string
  score: number
  content_preview?: string
  description?: string
  tags?: string[]
  chunk_index?: number
  source?: string
}

/**
 * Two-stage search result entry (mapped frontend format)
 */
export interface TwoStageHit {
  doc_id: string
  doc_name: string
  kb_id: string
  kb_name: string
  path: string
  bm25_score: number
  vector_score: number
  combined_score: number
  content_preview?: string
  description?: string
  tags?: string[]
  source?: string
  stage1_sources?: string[]
}

export interface SearchStats {
  total_documents: number
  indexed_documents: number
  total_kbs: number
  vector_index_coverage: number
}

export type SearchMode = 'keyword' | 'vector' | 'two-stage'

/**
 * KB info cache: kb_id / kb_path → { name, kb_id, path }
 * Avoids re-fetching catalog on every search
 */
let _kbCache: Map<string, { name: string; kb_id: string; path: string }> | null = null

async function _getKbLookup(): Promise<Map<string, { name: string; kb_id: string; path: string }>> {
  if (_kbCache && _kbCache.size > 0) return _kbCache
  _kbCache = new Map()
  try {
    const res = await $fetch<{ knowledgeBases: any[] }>('/api/kb/catalog')
    for (const kb of res.knowledgeBases || []) {
      const entry = { name: kb.name || kb.path, kb_id: kb.kbId, path: kb.path }
      _kbCache.set(kb.kbId, entry)
      if (kb.path) _kbCache.set(kb.path, entry)
    }
  } catch {
    // ignore — search still works without KB names
  }
  return _kbCache
}

/**
 * Document metadata cache: doc_path → { name, description, tags }
 * Cleared via invalidateDocCache() when KB structure changes
 */
let _docCache: Map<string, { name: string; description: string; tags: string[] }> | null = null

async function _getDocLookup(kbId?: string): Promise<Map<string, { name: string; description: string; tags: string[] }>> {
  if (_docCache && _docCache.size > 0) return _docCache
  _docCache = new Map()
  try {
    const lookup = await _getKbLookup()
    const kbs = kbId
      ? [lookup.get(kbId)].filter(Boolean)
      : Array.from(lookup.values())
    // Deduplicate by kb_id
    const seen = new Set<string>()
    for (const kb of kbs) {
      if (!kb || seen.has(kb.kb_id)) continue
      seen.add(kb.kb_id)
      try {
        const docsRes = await $fetch<{ documents: any[] }>('/api/kb/documents', {
          params: { kb_id: kb.kb_id },
        })
        for (const doc of docsRes.documents || []) {
          const dp = doc.path || ''
          if (dp) {
            _docCache.set(dp, {
              name: doc.name || dp.split(/[\\/]/).pop() || dp,
              description: doc.description || '',
              tags: doc.tags || [],
            })
          }
        }
      } catch {
        // skip KB on error
      }
    }
  } catch {
    // ignore
  }
  return _docCache
}

/**
 * Advanced KB search composable
 * Supports keyword search, vector search, two-stage search (BM25 + vector)
 */
export const useKbAdvancedSearch = () => {
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * Vector semantic search
   */
  const vectorSearch = async (
    query: string,
    opts: { topK?: number; kbId?: string; balanceKbs?: boolean } = {}
  ): Promise<VectorSearchHit[]> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ results?: any[]; hits?: any[] }>('/api/search/vector', {
        method: 'POST',
        body: {
          query,
          top_k: opts.topK ?? 10,
          kb_id: opts.kbId || '',
          balance_kbs: opts.balanceKbs ?? false,
        },
      })
      const raw = res.results || res.hits || []
      // Enrich with KB name + doc metadata
      const kbLookup = await _getKbLookup()
      const docLookup = await _getDocLookup(opts.kbId || undefined)
      return raw.map((r: any): VectorSearchHit => {
        const dp = r.doc_path || r.path || ''
        const kid = r.kb_id || ''
        const kbInfo = kbLookup.get(kid) || (dp ? kbLookup.get(dp.split('/')[0]) : null)
        const docInfo = docLookup.get(dp)
        return {
          doc_id: r.doc_id || '',
          doc_name: docInfo?.name || r.doc_name || (dp ? dp.split(/[\\/]/).pop() || dp : ''),
          kb_id: kid,
          kb_name: kbInfo?.name || r.kb_name || kid,
          path: dp,
          score: r.score || 0,
          content_preview: r.content_preview || (r.content ? r.content.slice(0, 300) : ''),
          description: docInfo?.description || r.description || '',
          tags: docInfo?.tags || r.tags || [],
          chunk_index: r.chunk_index,
          source: r.source,
        }
      })
    } catch (err: any) {
      error.value = err.message || 'Vector search failed'
      return []
    } finally {
      loading.value = false
    }
  }

  /**
   * Two-stage search (BM25 keyword recall -> vector re-ranking)
   */
  const twoStageSearch = async (
    query: string,
    opts: { topK?: number; kbId?: string; bm25TopK?: number; balanceKbs?: boolean } = {}
  ): Promise<TwoStageHit[]> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{
        results?: any[]
        hits?: any[]
        stage2?: { results?: any[] }
        stage1?: { candidates?: any[] }
      }>('/api/search/two-stage', {
        method: 'POST',
        body: {
          query,
          stage1_top_k: opts.bm25TopK ?? 20,
          stage2_top_k: opts.topK ?? 10,
          kb_id: opts.kbId || '',
          balance_kbs: opts.balanceKbs ?? false,
        },
      })
      // Backend returns { stage2: { results: [...] } }
      const raw = res.results || res.hits || res.stage2?.results || []
      // Enrich with KB name + doc metadata
      const kbLookup = await _getKbLookup()
      const docLookup = await _getDocLookup(opts.kbId || undefined)
      return raw.map((r: any): TwoStageHit => {
        const dp = r.doc_path || r.path || ''
        const kid = r.kb_id || ''
        const kbInfo = kbLookup.get(kid) || (dp ? kbLookup.get(dp.split('/')[0]) : null)
        const docInfo = docLookup.get(dp)
        const score = r.score || 0
        const stage1Score = r.stage1_score || 0
        return {
          doc_id: r.doc_id || '',
          doc_name: docInfo?.name || r.doc_name || (dp ? dp.split(/[\\/]/).pop() || dp : ''),
          kb_id: kid,
          kb_name: kbInfo?.name || r.kb_name || kid,
          path: dp,
          bm25_score: stage1Score,
          vector_score: score,
          combined_score: score,
          content_preview: r.content_preview || (r.content ? r.content.slice(0, 300) : ''),
          description: docInfo?.description || r.description || '',
          tags: docInfo?.tags || r.tags || [],
          source: r.source,
          stage1_sources: r.stage1_sources,
        }
      })
    } catch (err: any) {
      error.value = err.message || 'Two-stage search failed'
      return []
    } finally {
      loading.value = false
    }
  }

  /**
   * Batch similar document query (find similar docs by doc path)
   */
  const batchVectorSearch = async (
    docPaths: string[],
    opts: { topK?: number; kbId?: string; scoreThreshold?: number } = {}
  ): Promise<Record<string, any[]>> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ results: Record<string, any[]>; success?: boolean }>('/api/search/batch-vector', {
        method: 'POST',
        body: {
          query_doc_paths: docPaths,
          top_k: opts.topK ?? 5,
          kb_id: opts.kbId || undefined,
          score_threshold: opts.scoreThreshold ?? 0.3,
        },
      })
      return res.results || {}
    } catch (err: any) {
      error.value = err.message || 'Batch search failed'
      return {}
    } finally {
      loading.value = false
    }
  }

  /**
   * Rebuild vector index
   */
  const reindex = async (opts: { kbId?: string; force?: boolean } = {}): Promise<any> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ success: boolean; message?: string; stats?: any }>('/api/search/reindex', {
        method: 'POST',
        body: {
          kb_id: opts.kbId || '',
          force: opts.force ?? false,
        },
      })
      // Invalidate caches after reindex
      _docCache = null
      return res
    } catch (err: any) {
      error.value = err.message || 'Rebuild index failed'
      throw err
    } finally {
      loading.value = false
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

  return {
    loading,
    error,
    vectorSearch,
    twoStageSearch,
    batchVectorSearch,
    reindex,
    searchByTag,
    fetchAllTags,
  }
}
