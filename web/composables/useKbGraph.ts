import { ref } from 'vue'

export interface GraphNode {
  id: string
  label: string
  type: 'document' | 'kb' | 'tag'
  kb_id?: string
  kb_name?: string
  doc_count?: number
  tags?: string[]
  description?: string
  path?: string
  degree?: number
  weight?: number
  score?: number
  centrality?: number
  bridging_kbs?: string[]
  relation_type?: string
}

export interface GraphEdge {
  source: string
  target: string
  type: 'belongs_to' | 'has_tag' | 'related' | 'shared_tag' | 'vector_similar' | 'agent_judged'
  weight?: number
  reason?: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface GraphStats {
  total_nodes: number
  total_edges: number
  total_documents: number
  total_kbs: number
  total_tags: number
  avg_degree: number
  max_degree: number
}

export interface GraphNeighbor {
  node: GraphNode
  edge: GraphEdge
}

export interface CrossKbDocument {
  doc_path: string
  doc_name: string
  kb_id: string
  kb_name: string
  bridging_kbs: string[]
  relation_type: string
  related_docs: number
  tags: string[]
}

export interface CentralDocument {
  doc_path: string
  doc_name: string
  kb_id: string
  kb_name: string
  degree: number
  centrality: number
  tags: string[]
}

export interface DocumentPath {
  found: boolean
  path: Array<{
    doc_path: string
    doc_name: string
    kb_name: string
    step: number
  }>
  length: number
}

export interface KbOverview {
  kb_id: string
  kb_name: string
  document_count: number
  tag_distribution: Array<{ tag: string; count: number }>
  related_kbs: Array<{ kb_id: string; kb_name: string; shared_tags: number }>
  top_documents: Array<{ doc_path: string; doc_name: string; degree: number }>
}

/**
 * Knowledge Graph composable
 * Provides graph stats, search, neighbor queries, build, document centrality,
 * cross-KB analysis, path discovery, and more
 */
export const useKbGraph = () => {
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * Fetch graph stats
   */
  const fetchStats = async (): Promise<GraphStats | null> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ success?: boolean; stats?: GraphStats }>('/api/graph/stats')
      return res.stats || (res as any) || null
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch graph stats'
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Graph search
   * @param keyword Search keyword
   * @param type Search type: documents | kbs | tags
   */
  const searchGraph = async (
    keyword: string,
    type: 'documents' | 'kbs' | 'tags' = 'documents',
    opts: { limit?: number; kbId?: string } = {}
  ): Promise<any> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<any>('/api/graph/search', {
        params: {
          keyword,
          type,
          limit: String(opts.limit ?? 50),
        },
      })
      return res || {}
    } catch (err: any) {
      error.value = err.message || 'Graph search failed'
      return {}
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch node neighbors
   */
  const fetchNeighbors = async (
    nodeId: string,
    opts: { depth?: number; nodeType?: string } = {}
  ): Promise<GraphData> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ success?: boolean; graph?: GraphData }>('/api/graph/neighbors', {
        params: {
          node_id: nodeId,
          node_type: opts.nodeType || 'document',
          depth: String(opts.depth ?? 1),
        },
      })
      return (res.graph ?? { nodes: [], edges: [] }) as GraphData
    } catch (err: any) {
      error.value = err.message || 'Failed to get neighbors'
      return { nodes: [], edges: [] }
    } finally {
      loading.value = false
    }
  }

  /**
   * Get document-centered graph view
   * Backend returns structured object: { document, tags, related_documents, cross_kb_links }
   * Transforms to frontend format { nodes: [], edges: [] }
   * @param docPath Document path
   */
  const getDocumentGraph = async (docPath: string): Promise<GraphData> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ success?: boolean; graph?: any }>('/api/graph/document', {
        params: { doc_path: docPath },
      })
      const g = res.graph || res
      // If already in nodes/edges format (local build), return as-is
      if (g.nodes && g.edges) {
        return g as GraphData
      }
      // Transform structured graph data into nodes/edges format
      const nodes: GraphNode[] = []
      const edges: GraphEdge[] = []
      const nodeMap = new Map<string, GraphNode>()

      // Center document node
      const doc = g.document || {}
      const centerId = `doc:${doc.path || docPath}`
      const centerNode: GraphNode = {
        id: centerId,
        label: doc.name || (doc.path || docPath).split(/[\\/]/).pop() || '',
        type: 'document',
        kb_id: doc.kb_id || '',
        kb_name: doc.kb_name || doc.kb_id || '',
        tags: doc.tags || g.tags || [],
        description: doc.description || '',
        path: doc.path || docPath,
      }
      nodes.push(centerNode)
      nodeMap.set(centerId, centerNode)

      // KB node for center document
      if (centerNode.kb_id) {
        const kbNodeId = `kb:${centerNode.kb_id}`
        if (!nodeMap.has(kbNodeId)) {
          const kbNode: GraphNode = {
            id: kbNodeId,
            label: centerNode.kb_name || centerNode.kb_id,
            type: 'kb',
            kb_id: centerNode.kb_id,
            kb_name: centerNode.kb_name || centerNode.kb_id,
          }
          nodes.push(kbNode)
          nodeMap.set(kbNodeId, kbNode)
        }
        edges.push({ source: centerId, target: kbNodeId, type: 'belongs_to', weight: 1 })
      }

      // Tag nodes for center document
      const docTags = doc.tags || g.tags || []
      for (const tag of docTags) {
        const tagNodeId = `tag:${tag}`
        if (!nodeMap.has(tagNodeId)) {
          const tagNode: GraphNode = { id: tagNodeId, label: tag, type: 'tag' }
          nodes.push(tagNode)
          nodeMap.set(tagNodeId, tagNode)
        }
        edges.push({ source: centerId, target: tagNodeId, type: 'has_tag', weight: 1 })
      }

      // Related documents (same KB + cross KB)
      const allRelated = [
        ...(g.related_documents || []),
        ...(g.cross_kb_links || []),
      ]
      const seenPaths = new Set<string>()
      for (const r of allRelated) {
        const rPath = r.path || r.doc_path || ''
        if (!rPath || seenPaths.has(rPath)) continue
        seenPaths.add(rPath)

        const rNodeId = `doc:${rPath}`
        if (!nodeMap.has(rNodeId)) {
          const rNode: GraphNode = {
            id: rNodeId,
            label: r.name || rPath.split(/[\\/]/).pop() || '',
            type: 'document',
            kb_id: r.kb_id || '',
            kb_name: r.kb_name || r.kb_id || '',
            path: rPath,
          }
          nodes.push(rNode)
          nodeMap.set(rNodeId, rNode)
        }

        // KB node for related doc
        if (r.kb_id) {
          const rkbNodeId = `kb:${r.kb_id}`
          if (!nodeMap.has(rkbNodeId)) {
            const rkbNode: GraphNode = {
              id: rkbNodeId,
              label: r.kb_name || r.kb_id,
              type: 'kb',
              kb_id: r.kb_id,
              kb_name: r.kb_name || r.kb_id,
            }
            nodes.push(rkbNode)
            nodeMap.set(rkbNodeId, rkbNode)
          }
          edges.push({ source: rNodeId, target: rkbNodeId, type: 'belongs_to', weight: 1 })
        }

        // Edge between center doc and related doc
        edges.push({
          source: centerId,
          target: rNodeId,
          type: r.reason === 'shared_tag' ? 'shared_tag' : r.reason === 'vector_similar' ? 'vector_similar' : 'related',
          weight: r.weight || 1,
          reason: r.reason,
        })
      }

      return { nodes, edges }
    } catch (err: any) {
      error.value = err.message || 'Failed to get document graph'
      return { nodes: [], edges: [] }
    } finally {
      loading.value = false
    }
  }

  /**
   * Get related documents for a document
   */
  const getRelatedDocuments = async (docPath: string, limit: number = 20): Promise<any[]> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ success?: boolean; related?: any[] }>('/api/graph/related', {
        params: { doc_path: docPath, limit: String(limit) },
      })
      return res.related || []
    } catch (err: any) {
      error.value = err.message || 'Failed to get related documents'
      return []
    } finally {
      loading.value = false
    }
  }

  /**
   * Get cross-KB bridge documents
   * Backend fields: path, name, kb_id, related_kbs, link_count
   * Frontend maps to: doc_path, doc_name, kb_id, kb_name, bridging_kbs, relation_type, related_docs, tags
   */
  const getCrossKbDocuments = async (limit: number = 50): Promise<CrossKbDocument[]> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ success?: boolean; documents?: any[] }>('/api/graph/cross-kb', {
        params: { limit: String(limit) },
      })
      const raw = res.documents || []
      // Map backend response fields to frontend expected fields
      return raw.map((d: any) => ({
        doc_path: d.path || d.doc_path || '',
        doc_name: d.name || d.doc_name || (d.path || d.doc_path || '').split(/[\\/]/).pop() || '',
        kb_id: d.kb_id || '',
        kb_name: d.kb_name || d.kb_id || '',
        bridging_kbs: d.bridging_kbs || d.related_kbs || [],
        relation_type: d.relation_type || 'shared_tag',
        related_docs: d.related_docs ?? d.link_count ?? 0,
        tags: d.tags || [],
      }))
    } catch (err: any) {
      error.value = err.message || 'Failed to get cross-KB documents'
      return []
    } finally {
      loading.value = false
    }
  }

  /**
   * Get central documents in a KB (sorted by degree centrality)
   */
  const getCentralDocuments = async (kbId: string, topN: number = 20): Promise<CentralDocument[]> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ success?: boolean; documents?: CentralDocument[] }>('/api/graph/central', {
        params: { kb_id: kbId, top_n: String(topN) },
      })
      return res.documents || []
    } catch (err: any) {
      error.value = err.message || 'Failed to get central documents'
      return []
    } finally {
      loading.value = false
    }
  }

  /**
   * Find shortest path between two documents
   * Backend returns: { doc_a, doc_b, paths: [{doc_path: [...], reasons: [...], hops: N}], path_count }
   * Convert to frontend: { found: boolean, path: [{doc_path, doc_name, kb_name, step}], length: number }
   */
  const findDocumentPaths = async (docA: string, docB: string, maxDepth: number = 4): Promise<DocumentPath | null> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ success?: boolean; result?: any }>('/api/graph/paths', {
        params: { doc_a: docA, doc_b: docB, max_depth: String(maxDepth) },
      })
      const result = res.result || null
      if (!result) return null

      // If already in the expected format
      if (result.found !== undefined && result.path) {
        return result as DocumentPath
      }

      // Transform backend format
      const paths = result.paths || []
      if (paths.length === 0 || result.path_count === 0) {
        return { found: false, path: [], length: 0 }
      }

      // Take the first (shortest) path
      const firstPath = paths[0]
      const docPaths: string[] = firstPath.doc_path || []
      const steps = docPaths.map((dp: string, i: number) => {
        const parts = dp.split(/[\\/]/)
        const docName = parts.pop() || dp
        const kbName = parts[0] || ''
        return {
          doc_path: dp,
          doc_name: docName,
          kb_name: kbName,
          step: i + 1,
        }
      })

      return {
        found: true,
        path: steps,
        length: firstPath.hops || steps.length - 1,
      }
    } catch (err: any) {
      error.value = err.message || 'Path search failed'
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Get KB graph overview
   */
  const getKbOverview = async (kbId: string): Promise<KbOverview | null> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ success?: boolean; overview?: KbOverview }>('/api/graph/kb-overview', {
        params: { kb_id: kbId },
      })
      return res.overview || null
    } catch (err: any) {
      error.value = err.message || 'Failed to get KB overview'
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Find documents by tag
   */
  const getDocumentsByTag = async (tagName: string, limit: number = 50): Promise<any[]> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ success?: boolean; documents?: any[] }>('/api/graph/documents-by-tag', {
        params: { tag_name: tagName, limit: String(limit) },
      })
      return res.documents || []
    } catch (err: any) {
      error.value = err.message || 'Tag search failed'
      return []
    } finally {
      loading.value = false
    }
  }

  /**
   * Build full knowledge graph from catalog + document list (local, no backend Neo4j dependency)
   */
  const buildLocalGraph = async (): Promise<GraphData> => {
    loading.value = true
    error.value = null
    try {
      const catalogRes = await $fetch<{ knowledgeBases: any[] }>('/api/kb/catalog')
      const kbs = catalogRes.knowledgeBases || []

      const nodes: GraphNode[] = []
      const edges: GraphEdge[] = []
      const tagSet = new Map<string, GraphNode>()

      for (const kb of kbs) {
        const kbNodeId = `kb:${kb.kbId}`
        nodes.push({
          id: kbNodeId,
          label: kb.name,
          type: 'kb',
          kb_id: kb.kbId,
          kb_name: kb.name,
          doc_count: kb.documentCount,
          description: kb.description,
        })

        try {
          const docsRes = await $fetch<{ documents: any[] }>('/api/kb/documents', {
            params: { kb_id: kb.kbId },
          })
          const docs = docsRes.documents || []

          for (const doc of docs) {
            const docNodeId = `doc:${doc.path}`
            nodes.push({
              id: docNodeId,
              label: doc.name,
              type: 'document',
              kb_id: kb.kbId,
              kb_name: kb.name,
              tags: doc.tags || [],
              description: doc.description,
              path: doc.path,
            })
            edges.push({
              source: docNodeId,
              target: kbNodeId,
              type: 'belongs_to',
              weight: 1,
            })

            if (doc.tags && Array.isArray(doc.tags)) {
              for (const tag of doc.tags) {
                const tagNodeId = `tag:${tag}`
                if (!tagSet.has(tagNodeId)) {
                  tagSet.set(tagNodeId, {
                    id: tagNodeId,
                    label: tag,
                    type: 'tag',
                  })
                }
                edges.push({
                  source: docNodeId,
                  target: tagNodeId,
                  type: 'has_tag',
                  weight: 1,
                })
              }
            }
          }
        } catch {
          // Skip KBs that failed to fetch documents
        }
      }

      for (const tagNode of tagSet.values()) {
        nodes.push(tagNode)
      }

      return { nodes, edges }
    } catch (err: any) {
      error.value = err.message || 'Failed to build graph'
      return { nodes: [], edges: [] }
    } finally {
      loading.value = false
    }
  }

  /**
   * Build backend Neo4j graph (full rebuild)
   * Three-phase build: metadata+tags → vector similarity → cross-KB associations
   */
  const buildBackendGraph = async (force: boolean = false, enableVectorSimilarity: boolean = true): Promise<any> => {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<any>('/api/graph/build-all', {
        method: 'POST',
        body: { force, enable_vector_similarity: enableVectorSimilarity },
      })
      return res
    } catch (err: any) {
      error.value = err.message || 'Failed to build graph'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Check Neo4j graph health
   */
  const checkHealth = async (): Promise<{ healthy: boolean; detail?: any }> => {
    try {
      const res = await $fetch<{ success?: boolean; health?: any }>('/api/graph/health')
      return {
        healthy: res.health?.available || res.health?.connected || false,
        detail: res.health,
      }
    } catch {
      return { healthy: false }
    }
  }

  /**
   * Build association graph from search results
   * Extract document, KB, tag nodes and their relationship edges from search results
   */
  const buildGraphFromSearchResults = (results: any[]): GraphData => {
    const nodes: GraphNode[] = []
    const edges: GraphEdge[] = []
    const nodeMap = new Map<string, GraphNode>()
    const tagSet = new Map<string, GraphNode>()

    for (const hit of results) {
      const docPath = hit.path || hit.doc_id || ''
      const docNodeId = `doc:${docPath}`
      if (!nodeMap.has(docNodeId)) {
        const docNode: GraphNode = {
          id: docNodeId,
          label: hit.docName || hit.doc_name || docPath.split(/[\\/]/).pop() || docPath,
          type: 'document',
          kb_id: hit.kb_id || '',
          kb_name: hit.kbName || hit.kb_name || '',
          tags: hit.tags || [],
          description: hit.description || '',
          path: docPath,
          score: hit.score || hit.combined_score || hit.vector_score,
        }
        nodes.push(docNode)
        nodeMap.set(docNodeId, docNode)
      }

      // KB node
      const kbName = hit.kbName || hit.kb_name || ''
      const kbId = hit.kb_id || kbName
      if (kbName) {
        const kbNodeId = `kb:${kbId}`
        if (!nodeMap.has(kbNodeId)) {
          const kbNode: GraphNode = {
            id: kbNodeId,
            label: kbName,
            type: 'kb',
            kb_id: kbId,
            kb_name: kbName,
          }
          nodes.push(kbNode)
          nodeMap.set(kbNodeId, kbNode)
        }
        edges.push({
          source: docNodeId,
          target: `kb:${kbId}`,
          type: 'belongs_to',
          weight: 1,
        })
      }

      // Tag node
      const tags = hit.tags || []
      for (const tag of tags) {
        const tagNodeId = `tag:${tag}`
        if (!tagSet.has(tagNodeId)) {
          const tagNode: GraphNode = {
            id: tagNodeId,
            label: tag,
            type: 'tag',
          }
          nodes.push(tagNode)
          tagSet.set(tagNodeId, tagNode)
        }
        edges.push({
          source: docNodeId,
          target: tagNodeId,
          type: 'has_tag',
          weight: 1,
        })
      }
    }

    // Add shared-tag edges between documents
    const tagToDocs = new Map<string, string[]>()
    for (const edge of edges) {
      if (edge.type === 'has_tag') {
        const tagId = edge.target
        if (!tagToDocs.has(tagId)) tagToDocs.set(tagId, [])
        tagToDocs.get(tagId)!.push(edge.source)
      }
    }
    for (const [tagId, docIds] of tagToDocs) {
      for (let i = 0; i < docIds.length; i++) {
        for (let j = i + 1; j < docIds.length; j++) {
          edges.push({
            source: docIds[i],
            target: docIds[j],
            type: 'shared_tag',
            weight: 0.5,
          })
        }
      }
    }

    return { nodes, edges }
  }

  return {
    loading,
    error,
    fetchStats,
    searchGraph,
    fetchNeighbors,
    getDocumentGraph,
    getRelatedDocuments,
    getCrossKbDocuments,
    getCentralDocuments,
    findDocumentPaths,
    getKbOverview,
    getDocumentsByTag,
    buildLocalGraph,
    buildBackendGraph,
    checkHealth,
    buildGraphFromSearchResults,
  }
}
