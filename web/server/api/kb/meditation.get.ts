import { defineEventHandler, getQuery } from 'h3'
import { promises as fs } from 'fs'
import * as yaml from 'js-yaml'
import * as path from 'path'
import { getTreeFileSystemService } from '~/server/utils/tree-service'
import { getTreeStorageAbsolutePath } from '~/server/utils/runtime-paths'
import { KNOWLEDGE_BASE_YAML_FILENAME } from '~/types/knowledge-base-yaml'

/**
 * GET /api/kb/meditation?kbId=X
 *
 * Read meditation config for a KB directly from its .knowledge-base.yml metadata.
 * Returns { success, config, run_status }
 */
export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const kbId = (query.kbId as string || '').trim()

  if (!kbId) {
    return { success: false, error: 'kbId is required' }
  }

  try {
    const treeService = await getTreeFileSystemService()
    await treeService.reloadMetadata()

    const kb = await treeService.getKnowledgeBaseById(kbId)
    if (!kb) {
      return { success: false, error: `Knowledge base not found: ${kbId}` }
    }

    // Default meditation config (all fields must match MeditationConfig interface)
    const defaultConfig = {
      enabled: false,
      harness: 'omp',
      model: 'claude-sonnet-4-20250514',
      interval_hours: 24,
      min_cluster_count: 3,
      max_drafts_per_run: 10,
      max_budget_usd: 0.05,
      auto_publish: false,
      incremental_enabled: true,
    }

    // Read YAML directly
    const storageRoot = getTreeStorageAbsolutePath()
    const yamlPath = path.join(storageRoot, kb.path, KNOWLEDGE_BASE_YAML_FILENAME)
    let savedConfig: any = {}
    try {
      const content = await fs.readFile(yamlPath, 'utf-8')
      const data = yaml.load(content) as any
      savedConfig = data?.knowledge_base?.metadata?.meditation || {}
    } catch {
      // YAML may not exist yet — use defaults
    }

    const config = { ...defaultConfig, ...savedConfig }

    // Extract run status fields
    const run_status = {
      last_run_at: config.last_run_at ?? null,
      last_run_status: config.last_run_status ?? null,
      total_runs: config.total_runs ?? 0,
      total_experiences_generated: config.total_experiences_generated ?? 0,
    }

    return { success: true, config, run_status }
  } catch (e: any) {
    return { success: false, error: e?.message || String(e) }
  }
})
