/**
 * Knowledge Base YAML Service
 * Manages KB description YAML files for Agentic RAG search.
 */

import { promises as fs } from 'fs'
import * as path from 'path'
import * as yaml from 'js-yaml'
import { v4 as uuidv4 } from 'uuid'
import type {
  KnowledgeBaseYaml,
  KnowledgeBaseInfo,
  KnowledgeBaseDocument
} from '~/types/knowledge-base-yaml'
import { KNOWLEDGE_BASE_YAML_FILENAME } from '~/types/knowledge-base-yaml'
import { writeTextAtomic } from '~/server/utils/atomic-write'
import { withKbLock } from '~/server/utils/kb-mutex'

export class KnowledgeBaseYamlService {
  private baseDir: string

  constructor(baseDir: string) {
    this.baseDir = baseDir
  }

  /**
   * Get KB YAML file path
   */
  private getYamlPath(knowledgeBaseId: string): string {
    return path.join(this.baseDir, knowledgeBaseId, KNOWLEDGE_BASE_YAML_FILENAME)
  }

  /**
   * Check if YAML file exists
   */
  async exists(knowledgeBaseId: string): Promise<boolean> {
    try {
      await fs.access(this.getYamlPath(knowledgeBaseId))
      return true
    } catch {
      return false
    }
  }

  /**
   * Read KB YAML file
   */
  async read(knowledgeBaseId: string): Promise<KnowledgeBaseYaml | null> {
    try {
      const yamlPath = this.getYamlPath(knowledgeBaseId)
      const content = await fs.readFile(yamlPath, 'utf-8')
      return yaml.load(content) as KnowledgeBaseYaml
    } catch (error) {
      console.error(`Failed to read knowledge base YAML for ${knowledgeBaseId}:`, error)
      return null
    }
  }

  /**
   * Write KB YAML file
   */
  private async write(knowledgeBaseId: string, data: KnowledgeBaseYaml): Promise<void> {
    try {
      const yamlPath = this.getYamlPath(knowledgeBaseId)
      const content = yaml.dump(data, {
        indent: 2,
        lineWidth: -1,
        noRefs: true,
        sortKeys: false
      })
      await writeTextAtomic(yamlPath, content)
    } catch (error) {
      console.error(`Failed to write knowledge base YAML for ${knowledgeBaseId}:`, error)
      throw error
    }
  }

  /**
   * Create new KB YAML file
   * @param knowledgeBasePath KB folder relative path (used to locate the YAML file)
   * @param name KB name
   * @param description KB description
   * @param options Optional config; id must be UUID v4; auto-generated if omitted
   */
  async create(
    knowledgeBasePath: string,
    name: string,
    description?: string,
    options?: { id?: string }
  ): Promise<KnowledgeBaseYaml> {
    const now = new Date().toISOString()
    const id = options?.id && this.isValidKnowledgeBaseId(options.id)
      ? options.id
      : uuidv4()

    const data: KnowledgeBaseYaml = {
      knowledge_base: {
        id,
        path: knowledgeBasePath,
        name,
        description,
        created_at: now,
        updated_at: now,
        root_path: path.join(this.baseDir, knowledgeBasePath),
        total_documents: 0
      },
      documents: []
    }

    await this.write(knowledgeBasePath, data)
    return data
  }

  /**
   * Validate KB ID is a valid UUID v4
   */
  private isValidKnowledgeBaseId(id: string): boolean {
    const UUID_V4_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
    return UUID_V4_RE.test(id)
  }

  /**
   * Read YAML and return a valid knowledge_base.id
   * If id is missing or not a UUID, fallback to knowledge_base.path (read-only compatible)
   */
  ensureKbId(data: KnowledgeBaseYaml | null): string {
    if (!data) return ''
    const { id, path: kbPath } = data.knowledge_base
    if (id && this.isValidKnowledgeBaseId(id)) {
      return id
    }
    if (kbPath) {
      console.warn(`Knowledge base id is not a valid UUID, falling back to path: ${kbPath}`)
      return kbPath
    }
    return ''
  }

  /**
   * Update KB basic info
   */
  async updateInfo(
    knowledgeBaseId: string,
    updates: Partial<Pick<KnowledgeBaseInfo, 'name' | 'description'>>
  ): Promise<KnowledgeBaseYaml | null> {
    return withKbLock(knowledgeBaseId, async () => {
    const data = await this.read(knowledgeBaseId)
    if (!data) return null

    if (updates.name !== undefined) {
      data.knowledge_base.name = updates.name
    }
    if (updates.description !== undefined) {
      data.knowledge_base.description = updates.description
    }
    data.knowledge_base.updated_at = new Date().toISOString()

    await this.write(knowledgeBaseId, data)
    return data
    })
  }

  /**
   * Add document to KB
   * @param knowledgeBaseId KB ID
   * @param fileInfo file information
   */
  async addDocument(
    knowledgeBaseId: string,
    fileInfo: {
      id?: string
      name: string
      description?: string
      path: string
      fileType: string
      fileSize?: number
      metadata?: Record<string, any>
      tags?: string[]
    }
  ): Promise<KnowledgeBaseYaml | null> {
    return withKbLock(knowledgeBaseId, async () => {
    let data = await this.read(knowledgeBaseId)
    if (!data) {
      // If YAML doesn't exist, create it first (create does not hold lock, avoids deadlock on non-reentrant lock)
      data = await this.create(knowledgeBaseId, knowledgeBaseId)
    }

    const now = new Date().toISOString()

    // Check if a document with the same path already exists (normalize path separators for Windows \ vs / compatibility)
    const norm = (p: string) => (p || '').replace(/\\/g, '/')
    const existingIndex = data.documents.findIndex(
      doc => norm(doc.path) === norm(fileInfo.path)
    )

    const document: KnowledgeBaseDocument = {
      id: fileInfo.id ?? (existingIndex >= 0 ? data.documents[existingIndex].id : undefined),
      name: fileInfo.name,
      description: fileInfo.description,
      path: fileInfo.path,
      file_type: fileInfo.fileType,
      file_size: fileInfo.fileSize,
      added_at: existingIndex >= 0 ? data.documents[existingIndex].added_at : now,
      updated_at: now,
      metadata: fileInfo.metadata,
      // Preserve existing tags: when updateFile / updateFileContent uses "delete-then-add" to rebuild entries,
      // tags would be silently cleared unless explicitly retained (fixes data bug of tag loss after update).
      // Prefer the caller-provided fileInfo.tags; otherwise fall back to the existing entry's tags.
      tags: fileInfo.tags ?? (existingIndex >= 0 ? data.documents[existingIndex].tags : undefined)
    }

    if (existingIndex >= 0) {
      // Update existing document
      data.documents[existingIndex] = document
    } else {
      // Add new document
      data.documents.push(document)
    }

    // Update KB info
    data.knowledge_base.total_documents = data.documents.length
    data.knowledge_base.updated_at = now

    await this.write(knowledgeBaseId, data)
    return data
    })
  }

  /**
   * Batch add documents
   */
  async addDocuments(
    knowledgeBaseId: string,
    files: Array<{
      id?: string
      name: string
      description?: string
      path: string
      fileType: string
      fileSize?: number
      metadata?: Record<string, any>
      tags?: string[]
    }>
  ): Promise<KnowledgeBaseYaml | null> {
    return withKbLock(knowledgeBaseId, async () => {
    let data = await this.read(knowledgeBaseId)
    if (!data) {
      data = await this.create(knowledgeBaseId, knowledgeBaseId)
    }

    const now = new Date().toISOString()

    const normFn = (p: string) => (p || '').replace(/\\/g, '/')
    for (const fileInfo of files) {
      const existingIndex = data.documents.findIndex(
        doc => normFn(doc.path) === normFn(fileInfo.path)
      )

      const document: KnowledgeBaseDocument = {
        id: fileInfo.id ?? (existingIndex >= 0 ? data.documents[existingIndex].id : undefined),
        name: fileInfo.name,
        description: fileInfo.description,
        path: fileInfo.path,
        file_type: fileInfo.fileType,
        file_size: fileInfo.fileSize,
        added_at: existingIndex >= 0 ? data.documents[existingIndex].added_at : now,
        updated_at: now,
        metadata: fileInfo.metadata,
        tags: fileInfo.tags ?? (existingIndex >= 0 ? data.documents[existingIndex].tags : undefined)
      }

      if (existingIndex >= 0) {
        data.documents[existingIndex] = document
      } else {
        data.documents.push(document)
      }
    }

    data.knowledge_base.total_documents = data.documents.length
    data.knowledge_base.updated_at = now

    await this.write(knowledgeBaseId, data)
    return data
    })
  }

  /**
   * Remove document
   * @param knowledgeBaseId KB ID
   * @param filePath file path
   */
  async removeDocument(
    knowledgeBaseId: string,
    filePath: string
  ): Promise<KnowledgeBaseYaml | null> {
    return withKbLock(knowledgeBaseId, async () => {
    const data = await this.read(knowledgeBaseId)
    if (!data) return null

    const initialLength = data.documents.length
    const norm = (p: string) => (p || '').replace(/\\/g, '/')
    data.documents = data.documents.filter(doc => norm(doc.path) !== norm(filePath))

    // Only update if a document was actually removed
    if (data.documents.length !== initialLength) {
      data.knowledge_base.total_documents = data.documents.length
      data.knowledge_base.updated_at = new Date().toISOString()
      await this.write(knowledgeBaseId, data)
    }

    return data
    })
  }

  /**
   * Batch remove documents
   */
  async removeDocuments(
    knowledgeBaseId: string,
    filePaths: string[]
  ): Promise<KnowledgeBaseYaml | null> {
    return withKbLock(knowledgeBaseId, async () => {
    const data = await this.read(knowledgeBaseId)
    if (!data) return null

    const norm = (p: string) => (p || '').replace(/\\/g, '/')
    const normPathSet = new Set(filePaths.map(p => norm(p)))
    const initialLength = data.documents.length
    data.documents = data.documents.filter(doc => !normPathSet.has(norm(doc.path)))

    if (data.documents.length !== initialLength) {
      data.knowledge_base.total_documents = data.documents.length
      data.knowledge_base.updated_at = new Date().toISOString()
      await this.write(knowledgeBaseId, data)
    }

    return data
    })
  }

  /**
   * Delete entire KB YAML file
   */
  async delete(knowledgeBaseId: string): Promise<boolean> {
    try {
      const yamlPath = this.getYamlPath(knowledgeBaseId)
      await fs.unlink(yamlPath)
      return true
    } catch {
      return false
    }
  }

  /**
   * List all KBs
   */
  async listAll(): Promise<KnowledgeBaseInfo[]> {
    try {
      const entries = await fs.readdir(this.baseDir, { withFileTypes: true })
      const knowledgeBases: KnowledgeBaseInfo[] = []

      for (const entry of entries) {
        if (entry.isDirectory()) {
          const data = await this.read(entry.name)
          if (data) {
            knowledgeBases.push(data.knowledge_base)
          }
        }
      }

      return knowledgeBases
    } catch (error) {
      console.error('Failed to list knowledge bases:', error)
      return []
    }
  }

  /**
   * Update a document's tags by path.
   */
  async updateDocumentTags(
    knowledgeBaseId: string,
    docPath: string,
    tags: string[]
  ): Promise<KnowledgeBaseYaml | null> {
    return withKbLock(knowledgeBaseId, async () => {
    const data = await this.read(knowledgeBaseId)
    if (!data) return null
    const normPath = docPath.replace(/\\/g, "/")
    const doc = data.documents.find(d => d.path.replace(/\\/g, "/") === normPath)
    if (!doc) {
      return null
    }
    doc.tags = tags
    doc.updated_at = new Date().toISOString()
    data.knowledge_base.updated_at = new Date().toISOString()
    await this.write(knowledgeBaseId, data)
    return data
    })
  }

  /**
   * Find document by doc_id (UUID) in the specified KB.
   * Returns matching document or null.
   */
  async getDocumentById(
    knowledgeBaseId: string,
    docId: string
  ): Promise<KnowledgeBaseDocument | null> {
    const data = await this.read(knowledgeBaseId)
    if (!data) return null
    return data.documents.find(d => d.id === docId) || null
  }

  /**
   * Search for a document ID across all KBs.
   * Returns { kb_id, doc } or null.
   */
  async findDocumentById(
    docId: string
  ): Promise<{ kbId: string; doc: KnowledgeBaseDocument } | null> {
    const kbs = await this.listAll()
    for (const kb of kbs) {
      const doc = await this.getDocumentById(kb.path, docId)
      if (doc) {
        return { kbId: kb.path, doc }
      }
    }
    return null
  }

  /**
   * Get documents filtered by tag.
   * Tag matching is case-insensitive to avoid misses on case mismatch.
   */
  async getDocumentsByTag(
    knowledgeBaseId: string,
    tag: string
  ): Promise<KnowledgeBaseDocument[]> {
    const data = await this.read(knowledgeBaseId)
    if (!data) return []
    const tagLower = tag.toLowerCase()
    return data.documents.filter(d =>
      (d.tags || []).some(t => t.toLowerCase() === tagLower)
    )
  }

  /**
   * Collect all tags used across all knowledge bases.
   */
  async getAllTags(): Promise<string[]> {
    const tags = new Set<string>()
    const kbs = await this.listAll()
    for (const kb of kbs) {
      const data = await this.read(kb.path)
      if (!data) continue
      for (const doc of data.documents) {
        for (const t of doc.tags || []) {
          tags.add(t)
        }
      }
    }
    return Array.from(tags)
  }
}

// Singleton instance
let serviceInstance: KnowledgeBaseYamlService | null = null

export function getKnowledgeBaseYamlService(baseDir: string): KnowledgeBaseYamlService {
  if (!serviceInstance) {
    serviceInstance = new KnowledgeBaseYamlService(baseDir)
  }
  return serviceInstance
}
