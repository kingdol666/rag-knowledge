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
