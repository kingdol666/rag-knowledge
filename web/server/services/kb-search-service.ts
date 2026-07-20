import { readFile } from 'fs/promises'
import { existsSync } from 'fs'
import { join, normalize, isAbsolute, resolve } from 'path'
import * as yaml from 'js-yaml'
import { getTreeStorageAbsolutePath } from '~/server/utils/runtime-paths'
import type {
  KnowledgeBaseYaml,
  KnowledgeBaseDocument,
} from '~/types/knowledge-base-yaml'

/**
 * Read-only knowledge-base search service.
 *
 * Reads the on-disk index files (.tree-fs.json + .knowledge-base.yml) directly,
 * so it adds zero load to the FastAPI backend. The kbId used everywhere here is
 * the knowledge-base folder's `path` (== yaml's knowledge_base.id == the value
 * TreeFileSystemService.getKnowledgeBaseId returns).
 */

interface TreeFsFile {
  name: string
  parentId: string | null
  path: string
  fileType?: string
  fileSize?: number
}
interface TreeFsFolder {
  id: string
  name: string
  description?: string
  parentId: string | null
  path: string
  documentCount?: number
  isKnowledgeBase?: boolean
}
interface TreeFsMetadata {
  folders: TreeFsFolder[]
  files: TreeFsFile[]
}

export interface KbCatalogEntry {
  kbId: string
  name: string
  description: string
  documentCount: number
  path: string
  parentId: string | null
}

export interface KbSearchHit {
  kbId: string
  kbName: string
  docName: string
  description: string
  path: string
  score: number
}

export interface KbDocumentContent {
  content: string
  totalLines: number
  truncated: boolean
}

export class KbSearchService {
  private basePath: string

  constructor(basePath?: string) {
    this.basePath = basePath || getTreeStorageAbsolutePath()
  }

  /** All knowledge bases (including sub-KBs). */
  async getCatalog(): Promise<KbCatalogEntry[]> {
    const meta = await this.readTreeFs()
    return meta.folders
      .filter((f) => f.isKnowledgeBase)
      .map((f) => ({
        kbId: f.id,
        name: f.name,
        description: f.description || '',
        documentCount: f.documentCount ?? 0,
        path: f.path,
        parentId: f.parentId ?? null,
      }))
  }

  /** Top-level knowledge bases (parentId is null). */
  async getTopLevelCatalog(): Promise<KbCatalogEntry[]> {
    const all = await this.getCatalog()
    return all.filter((kb) => !kb.parentId)
  }

  /** Sub-knowledge bases under a given parent KB. */
  async getSubCatalog(parentKbId: string): Promise<KbCatalogEntry[]> {
    const all = await this.getCatalog()
    return all.filter((kb) => kb.parentId === parentKbId)
  }

  /**
   * Cross-KB metadata keyword search. Searches ONLY document name and description
   * (NOT the full document body). Score: name match > description match.
   * Returns top-K hits. Pure metadata — does NOT read or scan document content.
   */
  async searchAll(query: string, topK = 10): Promise<KbSearchHit[]> {
    const q = query.trim().toLowerCase()
    if (!q) return []

    const catalog = await this.getCatalog()
    const hits: KbSearchHit[] = []

    for (const kb of catalog) {
      const docs = await this.readKbDocuments(kb.path)
      for (const doc of docs) {
        const score = this.scoreDocument(doc, q)
        if (score > 0) {
          hits.push({
            kbId: kb.kbId,
            kbName: kb.name,
            docName: doc.name,
            description: doc.description || '',
            path: doc.path,
            score,
          })
        }
      }
    }

    hits.sort((a, b) => b.score - a.score)
    return hits.slice(0, topK)
  }

  /** Full document list of one knowledge base (`kbId` can be UUID or folder path). */
  async getKbDocuments(kbId: string): Promise<KnowledgeBaseDocument[]> {
    return this.readKbDocuments(kbId)
  }

  /**
   * Read a markdown document, optionally paginated. `path` may be relative to
   * the tree-fs root or absolute; `..` escapes outside the root are rejected.
   */
  async readDocument(
    path: string,
    offset = 0,
    limit = 200,
    maxChars = 20000,
  ): Promise<KbDocumentContent> {
    const absPath = this.resolveSafePath(path)
    if (!existsSync(absPath)) {
      const err = new Error('Document not found')
      ;(err as any).statusCode = 404
      throw err
    }

    const raw = await readFile(absPath, 'utf-8')
    const allLines = raw.split(/\r?\n/)
    const totalLines = allLines.length

    const start = Math.max(0, offset)
    const end = limit > 0 ? start + limit : totalLines
    let slice = allLines.slice(start, end).join('\n')

    let truncated = false
    if (maxChars > 0 && slice.length > maxChars) {
      slice = slice.slice(0, maxChars)
      truncated = true
    }
    if (end < totalLines) truncated = true

    return { content: slice, totalLines, truncated }
  }

  // ---- internals -----------------------------------------------------------

  private async readTreeFs(): Promise<TreeFsMetadata> {
    const p = join(this.basePath, '.tree-fs.json')
    if (!existsSync(p)) return { folders: [], files: [] }
    const content = await readFile(p, 'utf-8')
    try {
      return JSON.parse(content) as TreeFsMetadata
    } catch {
      return { folders: [], files: [] }
    }
  }

  private async readKbDocuments(kbId: string): Promise<KnowledgeBaseDocument[]> {
    const meta = await this.readTreeFs()
    const folder = meta.folders.find(
      (f) => f.isKnowledgeBase && (f.id === kbId || f.path === kbId)
    )
    const folderPath = folder?.path ?? kbId
    const ymlPath = join(this.basePath, folderPath, '.knowledge-base.yml')
    if (!existsSync(ymlPath)) return []
    try {
      const content = await readFile(ymlPath, 'utf-8')
      const data = yaml.load(content) as KnowledgeBaseYaml | null
      return data?.documents ?? []
    } catch {
      return []
    }
  }

  private scoreDocument(doc: KnowledgeBaseDocument, q: string): number {
    const name = (doc.name || '').toLowerCase()
    const desc = (doc.description || '').toLowerCase()
    let score = 0
    if (name.includes(q)) score += 10
    if (desc.includes(q)) score += 5
    return score
  }

  /** Resolve `path` under the storage root; reject escapes. */
  private resolveSafePath(path: string): string {
    const root = normalize(this.basePath)
    const abs = isAbsolute(path) ? normalize(path) : normalize(join(root, path))
    const resolved = resolve(abs)
    if (!resolved.toLowerCase().startsWith(root.toLowerCase())) {
      const err = new Error('Path is outside the knowledge-base root')
      ;(err as any).statusCode = 403
      throw err
    }
    return resolved
  }
}

let instance: KbSearchService | null = null
export function getKbSearchService(): KbSearchService {
  if (!instance) instance = new KbSearchService()
  return instance
}