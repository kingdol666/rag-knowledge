import { defineEventHandler, readBody } from 'h3'
import { promises as fs } from 'fs'
import * as yaml from 'js-yaml'
import * as path from 'path'
import { getTreeFileSystemService } from '~/server/utils/tree-service'
import { getTreeStorageAbsolutePath } from '~/server/utils/runtime-paths'
import { writeTextAtomic } from '~/server/utils/atomic-write'
import { KNOWLEDGE_BASE_YAML_FILENAME } from '~/types/knowledge-base-yaml'

/**
 * PUT /api/kb/meditation
 *
 * Update meditation config for a KB. Writes to .knowledge-base.yml metadata.
 * Body: { kb_id: string, config: MeditationConfig }
 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)

  if (!body?.kb_id || !body?.config) {
    return { success: false, error: 'kb_id and config are required' }
  }

  try {
    const treeService = await getTreeFileSystemService()
    await treeService.reloadMetadata()

    const kb = await treeService.getKnowledgeBaseById(body.kb_id)
    if (!kb) {
      return { success: false, error: `Knowledge base not found: ${body.kb_id}` }
    }

    const storageRoot = getTreeStorageAbsolutePath()
    const yamlPath = path.join(storageRoot, kb.path, KNOWLEDGE_BASE_YAML_FILENAME)

    // Read existing YAML
    let data: any = {}
    try {
      const content = await fs.readFile(yamlPath, 'utf-8')
      data = yaml.load(content) || {}
    } catch {
      // YAML may not exist yet — start fresh
    }

    // Ensure knowledge_base.metadata exists
    if (!data.knowledge_base) data.knowledge_base = {}
    if (!data.knowledge_base.metadata) data.knowledge_base.metadata = {}

    // Preserve previous run-stats fields before overwriting
    const prev = data.knowledge_base.metadata.meditation || {}

    // Update meditation config — keep only known fields
    const cfg = body.config
    data.knowledge_base.metadata.meditation = {
      enabled: !!cfg.enabled,
      harness: cfg.harness || 'omp',
      model: cfg.model || '',  // Empty = use engine default
      interval_hours: Number(cfg.interval_hours) || 24,
      min_cluster_count: Number(cfg.min_cluster_count) || 2,
      max_drafts_per_run: Number(cfg.max_drafts_per_run) || 3,
      max_budget_usd: Number(cfg.max_budget_usd) || 0.05,
      auto_publish: !!cfg.auto_publish,
      incremental_enabled: cfg.incremental_enabled !== false,
      updated_at: new Date().toISOString(),
      // Preserve run stats
      last_run_at: prev.last_run_at ?? null,
      last_run_status: prev.last_run_status ?? null,
      total_runs: prev.total_runs ?? 0,
      total_experiences_generated: prev.total_experiences_generated ?? 0,
      last_run_report: prev.last_run_report ?? null,
    }

    data.knowledge_base.updated_at = new Date().toISOString()

    // Write atomically
    const yamlContent = yaml.dump(data, {
      indent: 2,
      lineWidth: -1,
      noRefs: true,
      sortKeys: false,
    })
    await writeTextAtomic(yamlPath, yamlContent)

    return { success: true, config: data.knowledge_base.metadata.meditation }
  } catch (e: any) {
    return { success: false, error: e?.message || String(e) }
  }
})
