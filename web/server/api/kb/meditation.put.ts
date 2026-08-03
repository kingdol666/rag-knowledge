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
 * Update meditation config for a KB (MERGE semantics — preserves all
 * existing fields, including SOUL extension fields like meditation_mode /
 * max_questions_per_run / rounds_per_run / max_budget_usd).
 *
 * Body: { kb_id: string, config: Partial<MeditationConfig> }
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

    // MERGE: preserve everything, update only provided fields
    const med = data.knowledge_base.metadata.meditation || {}
    const cfg = body.config

    const num = (v: any, d: number) => (v === undefined || v === null || v === '' ? d : Number(v))
    const bool = (v: any, d: boolean) => (v === undefined || v === null ? d : !!v)
    const str = (v: any, d: string) => (v === undefined || v === null ? d : String(v))

    const updated: any = { ...med }
    if (cfg.enabled !== undefined) updated.enabled = bool(cfg.enabled, false)
    if (cfg.harness !== undefined) updated.harness = str(cfg.harness, 'omp')
    if (cfg.model !== undefined) updated.model = str(cfg.model, '')
    if (cfg.interval_hours !== undefined) updated.interval_hours = num(cfg.interval_hours, 24)
    if (cfg.min_cluster_count !== undefined) updated.min_cluster_count = num(cfg.min_cluster_count, 2)
    if (cfg.max_drafts_per_run !== undefined) updated.max_drafts_per_run = num(cfg.max_drafts_per_run, 3)
    if (cfg.max_budget_usd !== undefined) updated.max_budget_usd = num(cfg.max_budget_usd, 0.05)
    if (cfg.max_questions_per_run !== undefined) updated.max_questions_per_run = num(cfg.max_questions_per_run, 10)
    if (cfg.rounds_per_run !== undefined) updated.rounds_per_run = num(cfg.rounds_per_run, 1)
    if (cfg.min_pas_auto_approve !== undefined) updated.min_pas_auto_approve = num(cfg.min_pas_auto_approve, 4.0)
    if (cfg.auto_publish !== undefined) updated.auto_publish = bool(cfg.auto_publish, false)
    if (cfg.incremental_enabled !== undefined) updated.incremental_enabled = bool(cfg.incremental_enabled, true)
    if (cfg.meditation_mode !== undefined) updated.meditation_mode = str(cfg.meditation_mode, 'experience')
    if (cfg.timeout_sec !== undefined) updated.timeout_sec = num(cfg.timeout_sec, 600)

    updated.updated_at = new Date().toISOString()
    if (!updated.created_at) updated.created_at = updated.updated_at

    data.knowledge_base.metadata.meditation = updated
    data.knowledge_base.updated_at = updated.updated_at

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
