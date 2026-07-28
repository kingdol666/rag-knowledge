/**
 * Knowledge Base YAML File Type Definitions
 * For Agentic RAG Knowledge Retrieval
 */

export interface KnowledgeBaseDocument {
  /** File UUID (from .tree-fs.json, consistent with the file system) */
  id?: string
  /** File Name */
  name: string
  /** File Description */
  description?: string
  /** File Relative Path */
  path: string
  /** File Type */
  file_type: string
  /** File Size (bytes) */
  file_size?: number
  /** Added At */
  added_at: string
  /** Last Updated At */
  updated_at?: string
  /** File Metadata */
  metadata?: Record<string, any>
  /** Document Tags */
  tags?: string[]
  /** Vector Index Metadata (written by backend) */
  vector_index?: Record<string, any>
}

export interface KnowledgeBaseInfo {
  /** KB ID (UUID v4) */
  id: string
  /** KB Folder Relative Path */
  path: string
  /** KB Name */
  name: string
  /** KB Description */
  description?: string
  /** Created At */
  created_at: string
  /** Last Updated At */
  updated_at: string
  /** Root Directory Path */
  root_path: string
  /** Total Documents */
  total_documents: number
  /** KB Metadata */
  metadata?: Record<string, any>
}

export interface KnowledgeBaseYaml {
  /** KB Basic Info */
  knowledge_base: KnowledgeBaseInfo
  /** Document List */
  documents: KnowledgeBaseDocument[]
}

/** Default YAML File Name */
export const KNOWLEDGE_BASE_YAML_FILENAME = '.knowledge-base.yml'

/** Meditation configuration for knowledge base automatic insight extraction. */
export interface MeditationConfig {
  /** Whether meditation is enabled for this KB */
  enabled: boolean
  /** Harness engine: omp, claude, or heuristic */
  harness: 'omp' | 'claude' | 'heuristic'
  /** Model name to use (e.g. claude-sonnet-4-20250514) */
  model: string
  /** Hours between automatic runs (0 = manual only) */
  interval_hours: number
  /** Minimum cluster size to trigger analysis */
  min_cluster_count: number
  /** Maximum drafts to produce per run */
  max_drafts_per_run: number
  /** Maximum USD budget per run */
  max_budget_usd: number
  /** Auto-publish drafts above confidence threshold */
  auto_publish: boolean
  /** Enable incremental mode (only new/changed docs) */
  incremental_enabled: boolean
}

/** Meditation run status summary. */
export interface MeditationRunStatus {
  last_run_at: string | null
  last_run_status: string | null
  total_runs: number
  total_experiences_generated: number
}

/** Meditation harness health status. */
export interface MeditationHarnessStatus {
  available: boolean
  harness: string
  details: string
}

/** Meditation history entry. */
export interface MeditationRunHistory {
  id: string
  kb_id: string
  started_at: string
  finished_at: string | null
  status: string
  drafts_generated: number
  experiences_published: number
  budget_usd: number
  error: string | null
}
