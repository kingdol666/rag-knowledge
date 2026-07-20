/**
 * GET /api/health/stats
 *
 * System health statistics for the home and settings pages.
 * Aggregates backend health, KB index coverage, and storage overview.
 */
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'
import { getTreeStorageAbsolutePath } from '~/server/utils/runtime-paths'
import { readFileSync, existsSync } from 'fs'
import { join } from 'path'

interface HealthStats {
  status: 'healthy' | 'degraded' | 'down'
  backend: { status: string; port?: string }
  neo4j: { available: boolean }
  storage: { kb_count: number; doc_count: number; total_size_mb: number }
  vector: { indexed_docs: number; total_docs: number; coverage_pct: number }
  graph: { node_count: number; edge_count: number }
}

export default defineEventHandler(async (): Promise<HealthStats> => {
  const result: HealthStats = {
    status: 'down',
    backend: { status: 'unknown' },
    neo4j: { available: false },
    storage: { kb_count: 0, doc_count: 0, total_size_mb: 0 },
    vector: { indexed_docs: 0, total_docs: 0, coverage_pct: 0 },
    graph: { node_count: 0, edge_count: 0 },
  }

  // 1. Backend health
  const backendUrl = getDynamicBackendUrl()
  try {
    const resp = await $fetch<{ status: string }>(`${backendUrl}/api/v1/health`, {
      timeout: 3000,
    }).catch(() => null)
    result.backend = { status: resp ? 'healthy' : 'unreachable', port: backendUrl.split(':').pop() }
  } catch {
    result.backend = { status: 'down', port: backendUrl.split(':').pop() }
  }

  // 2. KB + doc count from local storage (use runtime-paths for correct resolution in Nitro dev mode)
  const treePath = join(getTreeStorageAbsolutePath(), '.tree-fs.json')
  try {
    if (existsSync(treePath)) {
      const tree = JSON.parse(readFileSync(treePath, 'utf-8'))
      // Count KBs from the folders array (where isKnowledgeBase=true), not from files
      const kbFolders = (tree.folders || []).filter((f: any) => f.isKnowledgeBase)
      result.storage.kb_count = kbFolders.length
      // Count documents from the files array
      const docs = (tree.files || [])
      result.storage.doc_count = docs.length
      // Estimate size (fileSize is in bytes; some legacy entries use file_size)
      let totalBytes = 0
      docs.forEach((d: any) => { totalBytes += d.fileSize || d.file_size || 0 })
      result.storage.total_size_mb = Math.round((totalBytes / (1024 * 1024)) * 10) / 10
      result.vector.total_docs = docs.length
    }
  } catch { /* storage not available */ }

  // 3. Graph stats + health from backend
  try {
    const gStats = await $fetch<{ success?: boolean; stats?: { node_count?: number; edge_count?: number } }>(
      `${backendUrl}/api/v1/graph/stats`, { timeout: 3000 }
    ).catch(() => null)
    if (gStats?.success && gStats.stats) {
      result.graph.node_count = gStats.stats.node_count || 0
      result.graph.edge_count = gStats.stats.edge_count || 0
    }
    const gHealth = await $fetch<{ success?: boolean; health?: { available?: boolean } }>(
      `${backendUrl}/api/v1/graph/health`, { timeout: 2000 }
    ).catch(() => null)
    result.neo4j.available = !!(gHealth?.success && gHealth?.health?.available)
  } catch { /* graph not available */ }

  // 3b. Vector coverage from backend search stats (collections with chunks)
  try {
    const sStats = await $fetch<{ success?: boolean; stats?: { collections?: Array<{ collection: string; chunk_count: number }> } }>(
      `${backendUrl}/api/v1/search/stats`, { timeout: 3000 }
    ).catch(() => null)
    if (sStats?.success && sStats.stats?.collections && result.vector.total_docs > 0) {
      const indexedKbs = sStats.stats.collections.filter(c => c.chunk_count > 0).length
      if (result.storage.kb_count > 0) {
        result.vector.indexed_docs = Math.round((indexedKbs / result.storage.kb_count) * result.vector.total_docs)
        result.vector.indexed_docs = Math.min(result.vector.indexed_docs, result.vector.total_docs)
      }
      result.vector.coverage_pct = result.vector.total_docs > 0
        ? Math.round((result.vector.indexed_docs / result.vector.total_docs) * 100)
        : 0
    }
  } catch { /* search stats not available */ }

  // 4. Aggregate status
  if (result.backend.status === 'healthy' && result.vector.coverage_pct >= 50) {
    result.status = result.neo4j.available ? 'healthy' : 'degraded'
  } else if (result.backend.status === 'healthy') {
    result.status = 'degraded'
  }

  return result
})
