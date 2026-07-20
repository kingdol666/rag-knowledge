/**
 * Tree File System Service
 * Manages the tree-file-system metadata, disk operations, and KB YAML sync
 */

import { join, dirname, basename, extname } from 'path'
import { mkdir, writeFile, readFile, unlink, rmdir, rm, readdir, stat, rename, cp } from 'fs/promises'
import { existsSync } from 'fs'
import { v4 as uuidv4 } from 'uuid'
import type {
  BaseNode,
  FolderNode,
  FileNode,
  CreateFolderRequest,
  CreateFileRequest,
  UpdateFolderRequest,
  UpdateFileRequest,
  FolderResponse,
  FileResponse,
  TreeNodeResponse,
  DeleteResponse
} from '~/types/tree-file-system'
import { KnowledgeBaseYamlService } from './knowledge-base-yaml-service'
import { getServerConfig } from '~/utils/paths.mjs'
import { writeJsonAtomic } from '~/server/utils/atomic-write'
import { withTreeLock } from '~/server/utils/kb-mutex'

const METADATA_FILE = '.tree-fs.json'

interface FileSystemMetadata {
  folders: FolderResponse[]
  files: FileResponse[]
}

async function ensureDirectory(dirPath: string): Promise<void> {
  try {
    await mkdir(dirPath, { recursive: true })
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'EEXIST') {
      throw error
    }
  }
}

export class TreeFileSystemService {
  private basePath: string
  private metadataPath: string
  private metadata: FileSystemMetadata
  private yamlService: KnowledgeBaseYamlService
  /**
   * Write-after-invalidation cache flag.
   * - true: memory may be stale (initial startup / external changes), must reload before next read/write;
   * - false: memory is fresh (just loaded or after mutate+save), use directly.
   *
   * Fixes bug: Originally each request unconditionally called reloadMetadata(),
   * which caused concurrent writes to lose updates (late reload overwrote memory
   * changes from the previous request). With "dirty flag + lock visibility",
   * write operations complete mutate->save inside withTreeLock, memory is always
   * authoritative, and reads no longer blindly reload from disk.
   */
  private _dirty = true

  constructor(basePath: string) {
    this.basePath = basePath
    this.metadataPath = join(basePath, METADATA_FILE)
    this.metadata = { folders: [], files: [] }
    this.yamlService = new KnowledgeBaseYamlService(basePath)
  }

  async initialize(): Promise<void> {
    await ensureDirectory(this.basePath)
    await this.reloadMetadata()
  }

  /**
   * Only reload from disk when _dirty (executed inside withTreeLock).
   * When _dirty=false, this is a fast no-op that uses the in-memory cache —
   * avoids per-request disk reloads that could lose updates.
   */
  async reloadMetadata(): Promise<void> {
    if (this._dirty) {
      await withTreeLock(() => this._loadFromDisk())
    }
  }

  private async _loadFromDisk(): Promise<void> {
    try {
      if (existsSync(this.metadataPath)) {
        const content = await readFile(this.metadataPath, 'utf-8')
        this.metadata = JSON.parse(content)
        // After loading, reconcile with disk: remove phantom nodes that exist in index
        // but not on disk (createFile writes metadata without disk content, or external
        // file deletions leave stale metadata). Runs once on load, logs before deletion.
        await this.reconcileWithDisk()
      } else {
        await this.saveMetadata()
      }
    } catch (error) {
      console.error('Error loading metadata:', error)
      this.metadata = { folders: [], files: [] }
    }
    this._dirty = false
  }

  /**
   * Disk consistency reconciliation: remove folder/file entries that exist in .tree-fs.json but not on disk.
   * Fixes "phantom node" problem (fs_get_tree returning mcp_test_folder / fs-test-file.md with no disk counterpart).
   * Returns total number of removed entries.
   */
  private async reconcileWithDisk(): Promise<number> {
    if (!this.metadata?.folders || !this.metadata?.files) return 0
    const beforeFolders = this.metadata.folders.length
    const beforeFiles = this.metadata.files.length

    this.metadata.folders = this.metadata.folders.filter(node => {
      if (!existsSync(join(this.basePath, node.path))) {
        console.warn(`[tree-fs] reconcile: remove phantom folder '${node.path}' (not on disk)`)
        return false
      }
      return true
    })
    this.metadata.files = this.metadata.files.filter(node => {
      if (!existsSync(join(this.basePath, node.path))) {
        console.warn(`[tree-fs] reconcile: remove phantom file '${node.path}' (not on disk)`)
        return false
      }
      return true
    })

    const removedFolders = beforeFolders - this.metadata.folders.length
    const removedFiles = beforeFiles - this.metadata.files.length
    if (removedFolders > 0 || removedFiles > 0) {
      await this.saveMetadata()
      console.warn(`[tree-fs] reconcile: removed ${removedFolders} folder(s), ${removedFiles} file(s)`)
    }
    return removedFolders + removedFiles
  }

  private async saveMetadata(): Promise<void> {
    await writeJsonAtomic(this.metadataPath, this.metadata)
  }

  async createFolder(request: CreateFolderRequest): Promise<FolderResponse> {
    return withTreeLock(async () => {
    const id = uuidv4()
    const now = new Date()

    let folderPath: string
    let relativePath: string

    if (request.parentId) {
      const parentFolder = this.metadata.folders.find(f => f.id === request.parentId)
      if (!parentFolder) {
        throw new Error(`Parent folder not found: ${request.parentId}`)
      }
      relativePath = join(parentFolder.path, request.name)
    } else {
      relativePath = request.name
    }

    folderPath = join(this.basePath, relativePath)
    await ensureDirectory(folderPath)

    // Compute kb_id: KB folder uses its own id; sub-folder inherits nearest ancestor KB id
    let kb_id: string | null = null
    if (request.isKnowledgeBase) {
      kb_id = id
    } else if (request.parentId) {
      const parentFolder = this.metadata.folders.find(f => f.id === request.parentId)
      if (parentFolder) {
        kb_id = parentFolder.kb_id || null
      }
    }

    const folder: FolderResponse = {
      id,
      name: request.name,
      description: request.description || '',
      parentId: request.parentId || null,
      path: relativePath,
      type: 'folder',
      childCount: 0,
      documentCount: 0,
      isKnowledgeBase: request.isKnowledgeBase || false,
      kb_id: kb_id as any,
      createdAt: now.toISOString(),
      updatedAt: now.toISOString()
    }

    this.metadata.folders.push(folder)

    if (folder.parentId) {
      const parentFolder = this.metadata.folders.find(f => f.id === folder.parentId)
      if (parentFolder) {
        parentFolder.childCount++
        parentFolder.updatedAt = now.toISOString()
      }
    }

    // Write KB YAML during folder creation
    // Sub-KBs also write an entry into the parent KB's YAML index
    if (request.isKnowledgeBase) {
      try {
        await this.yamlService.create(
          relativePath,
          request.name,
          request.description,
          { id: folder.id }
        )

        // If this KB has a parent KB, add it as a sub-KB document entry in the parent YAML
        if (request.parentId) {
          const parentFolder = this.metadata.folders.find(f => f.id === request.parentId)
          if (parentFolder) {
            const parentKnowledgeBaseId = this.getKnowledgeBaseId(parentFolder.path)
            if (parentKnowledgeBaseId) {
              await this.yamlService.addDocument(parentKnowledgeBaseId, {
                name: request.name,
                description: request.description || `${request.name} sub-knowledge-base`,
                path: relativePath,
                fileType: 'knowledge-base',
                metadata: {
                  type: 'sub-knowledge-base',
                  isKnowledgeBase: true,
                  parentPath: parentFolder.path
                }
              })
            }
          }
        }
      } catch (error) {
        console.error('Failed to create knowledge base YAML:', error)
      }
    }

    await this.saveMetadata()
      this._dirty = false

      return folder
    })
  }

  async createFile(request: CreateFileRequest): Promise<FileResponse> {
    return withTreeLock(async () => {
    const id = uuidv4()
    const now = new Date()

    let filePath: string
    let relativePath: string

    if (request.parentId) {
      const parentFolder = this.metadata.folders.find(f => f.id === request.parentId)
      if (!parentFolder) {
        throw new Error(`Parent folder not found: ${request.parentId}`)
      }
      relativePath = join(parentFolder.path, request.name)
    } else {
      relativePath = request.name
    }

    filePath = join(this.basePath, relativePath)
    const dirPath = dirname(filePath)
    await ensureDirectory(dirPath)

    // Create an empty file on disk so that reconcileWithDisk() doesn't
    // remove it as a "phantom node" on the next metadata reload.
    // fs_create_file is metadata-only (no content), but the file must
    // physically exist for the tree index to remain consistent.
    if (!existsSync(filePath)) {
      await writeFile(filePath, '', 'utf-8')
    }

    const file: FileNode = {
      id,
      name: request.name,
      parentId: request.parentId || null,
      path: relativePath,
      type: 'file',
      fileType: request.fileType || 'unknown',
      fileSize: request.fileSize || 0,
      mimeType: request.mimeType,
      status: 'pending',
      metadata: request.metadata || {},
      description: request.description || '',
      createdAt: now.toISOString(),
      updatedAt: now.toISOString()
    }

    this.metadata.files.push(file)

    if (file.parentId) {
      const parentFolder = this.metadata.folders.find(f => f.id === file.parentId)
      if (parentFolder) {
        parentFolder.documentCount++
        parentFolder.updatedAt = now.toISOString()
      }
    }

    // Sync with KB YAML index
    await this.updateYamlForFile(file)

    await this.saveMetadata()
      this._dirty = false

      return file
    })
  }

  /**
   * Generate a unique filename within a parent folder. If a file with the same
   * name already exists (in metadata or on disk), append a numeric suffix:
   * "doc.md" -> "doc (1).md" -> "doc (2).md" -> ...
   *
   * This prevents accidental overwrites when re-uploading or re-parsing a
   * document that lands in the same folder.
   */
  getUniqueFileName(parentId: string | null, fileName: string): string {
    const ext = extname(fileName)
    const baseName = basename(fileName, ext)

    const isDuplicate = (candidateName: string): boolean => {
      let candidatePath: string
     if (parentId) {
        const norm = (p: string) => p.replace(/\\/g, '/').toLowerCase()
        const parentFolder = this.metadata.folders.find(f => f.id === parentId || norm(f.path) === norm(parentId))
       if (!parentFolder) return false
       candidatePath = join(parentFolder.path, candidateName)
      } else {
        candidatePath = candidateName
      }

      const norm = (p: string) => p.replace(/\\/g, '/').toLowerCase()
      const existsInMetadata = this.metadata.files.some(
        f => norm(f.path) === norm(candidatePath)
      )
      if (existsInMetadata) return true

      return existsSync(join(this.basePath, candidatePath))
    }

    if (!isDuplicate(fileName)) return fileName

    let counter = 1
    let candidate = `${baseName} (${counter})${ext}`
    while (isDuplicate(candidate)) {
      counter++
      candidate = `${baseName} (${counter})${ext}`
    }
    return candidate
  }

  async uploadFile(
    parentId: string | null,
    fileBuffer: Buffer,
    originalFilename: string,
    description: string = ''
  ): Promise<FileResponse> {
    return withTreeLock(async () => {
    const id = uuidv4()
    const now = new Date()
    // Auto-dedup: never overwrite an existing file; append " (n)" suffix instead.
    const dedupedFilename = this.getUniqueFileName(parentId, originalFilename)
    const ext = extname(dedupedFilename).toLowerCase()
    const baseName = basename(dedupedFilename, ext)

    let relativePath: string

   if (parentId) {
      const norm = (p: string) => p.replace(/\\/g, '/').toLowerCase()
      const parentFolder = this.metadata.folders.find(f => f.id === parentId || norm(f.path) === norm(parentId))
     if (!parentFolder) {
       throw new Error(`Parent folder not found: ${parentId}`)
     }
      relativePath = join(parentFolder.path, dedupedFilename)
    } else {
      relativePath = dedupedFilename
    }

    const filePath = join(this.basePath, relativePath)
    const dirPath = dirname(filePath)
    await ensureDirectory(dirPath)

    await writeFile(filePath, fileBuffer)

    const stats = await stat(filePath)

    const fileType = ext.replace('.', '') || 'unknown'
    const mimeType = this.getMimeType(ext)

    const file: FileResponse = {
      id,
      name: dedupedFilename,
      parentId: parentId || null,
      path: relativePath,
      fileType,
      fileSize: stats.size,
      mimeType,
      type: 'file',
      status: 'completed',
      metadata: {},
      description: description || '',
      createdAt: now.toISOString(),
      updatedAt: now.toISOString()
    }

    this.metadata.files.push(file)

    if (parentId) {
      const parentFolder = this.metadata.folders.find(f => f.id === parentId)
      if (parentFolder) {
        parentFolder.documentCount++
        parentFolder.updatedAt = now.toISOString()
      }
    }

    await this.saveMetadata()

    // Sync with KB YAML index
    await this.updateYamlForFile(file)

    this._dirty = false
      return file
    })
  }

  private getMimeType(ext: string): string {
    const mimeTypes: Record<string, string> = {
      '.txt': 'text/plain',
      '.md': 'text/markdown',
      '.markdown': 'text/markdown',
      '.json': 'application/json',
      '.xml': 'application/xml',
      '.csv': 'text/csv',
      '.pdf': 'application/pdf',
      '.doc': 'application/msword',
      '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      '.xls': 'application/vnd.ms-excel',
      '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      '.ppt': 'application/vnd.ms-powerpoint',
      '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      // Image
      '.png': 'image/png',
      '.jpg': 'image/jpeg',
      '.jpeg': 'image/jpeg',
      '.gif': 'image/gif',
      '.bmp': 'image/bmp',
      '.webp': 'image/webp',
      '.svg': 'image/svg+xml',
      '.ico': 'image/x-icon',
      // Video
      '.mp4': 'video/mp4',
      '.webm': 'video/webm',
      '.ogv': 'video/ogg',
      '.mov': 'video/quicktime',
      '.mkv': 'video/x-matroska',
      '.avi': 'video/x-msvideo',
      '.flv': 'video/x-flv',
      '.wmv': 'video/x-ms-wmv',
      // Audio
      '.mp3': 'audio/mpeg',
      '.wav': 'audio/wav',
      '.ogg': 'audio/ogg',
      '.aac': 'audio/aac',
      '.flac': 'audio/flac',
      '.m4a': 'audio/mp4',
      '.wma': 'audio/x-ms-wma',
      '.opus': 'audio/opus',
      '.html': 'text/html',
      '.htm': 'text/html',
      '.css': 'text/css',
      '.js': 'application/javascript',
      '.ts': 'application/typescript',
      '.py': 'text/x-python',
      '.java': 'text/x-java',
      '.c': 'text/x-c',
      '.cpp': 'text/x-c++',
      '.h': 'text/x-c-header',
      '.go': 'text/x-go',
      '.rs': 'text/x-rust',
      '.rb': 'text/x-ruby',
      '.php': 'text/x-php',
      '.sql': 'text/x-sql',
      '.sh': 'application/x-sh',
      '.bat': 'application/x-bat',
      '.ps1': 'application/x-powershell',
      '.yaml': 'text/yaml',
      '.yml': 'text/yaml',
      '.zip': 'application/zip',
      '.rar': 'application/x-rar-compressed',
      '.7z': 'application/x-7z-compressed',
      '.tar': 'application/x-tar',
      '.gz': 'application/gzip'
    }
    return mimeTypes[ext.toLowerCase()] || 'application/octet-stream'
  }

  /**
   * Traverse upward from a folder to find the nearest knowledge base ID
   * Supports sub-KBs: returns the folder if it is a KB, otherwise traverses parentId chain
   */
  getKnowledgeBaseIdByFolder(folder: FolderResponse | null): string | null {
    if (!folder) return null
    let cur: FolderResponse | undefined = folder
    while (cur) {
      if (cur.isKnowledgeBase) return cur.path
      cur = cur.parentId
        ? this.metadata.folders.find(f => f.id === cur!.parentId)
        : undefined
    }
    return null
  }

  /**
   * Traverse upward from a file path to find the nearest knowledge base ID
   * Shorten path segments and match folders with isKnowledgeBase=true
   */
  private getKnowledgeBaseId(filePath: string): string | null {
    const parts = filePath.split(/[/\\]/)

    // Walk from longest path to shortest to find the nearest KB ancestor
    for (let i = parts.length; i > 0; i--) {
      // Rebuild candidate path by joining the first i segments
      const candidatePath = parts.slice(0, i).join('/')
      const norm = (p: string) => p.replace(/\\/g, '/').toLowerCase()
      const folder = this.metadata.folders.find(
        f => f.isKnowledgeBase && norm(f.path) === norm(candidatePath)
      )
      if (folder) return folder.path
    }

    return null
  }

  /**
   * Synchronize the KB YAML index update.
   * First match by path, then traverse parentId chain upward for sub-KBs.
   */
  private async updateYamlForFile(file: FileNode, preservedTags?: string[]): Promise<void> {
    try {
      // First match by path
      let knowledgeBaseId = this.getKnowledgeBaseId(file.path)
      // Then traverse parentId chain (supports sub-KBs)
      if (!knowledgeBaseId && file.parentId) {
        let cur = this.metadata.folders.find(f => f.id === file.parentId)
        while (cur) {
          if (cur.isKnowledgeBase) { knowledgeBaseId = cur.path; break }
          cur = cur.parentId
            ? this.metadata.folders.find(f => f.id === cur!.parentId)
            : undefined
        }
      }
      if (!knowledgeBaseId) return

      await this.yamlService.addDocument(knowledgeBaseId, {
        id: file.id,
        name: file.name,
        description: file.description,
        path: file.path,
        fileType: file.fileType,
        fileSize: file.fileSize,
        metadata: file.metadata,
        tags: preservedTags,
      })
    } catch (error) {
      console.error('Failed to update knowledge base YAML:', error)
    }
  }

  /**
   * Read tags recorded in KB YAML for a file (call before removeFileFromYaml to preserve tags during update).
   */
  private async readYamlDocTags(filePath: string): Promise<string[] | undefined> {
    try {
      const knowledgeBaseId = this.getKnowledgeBaseId(filePath)
      if (!knowledgeBaseId) return undefined
      const data = await this.yamlService.read(knowledgeBaseId)
      if (!data?.documents) return undefined
      const norm = (p: string) => p.replace(/\\/g, '/')
      const existing = data.documents.find(d => norm(d.path || '') === norm(filePath))
      return existing?.tags
    } catch {
      return undefined
    }
  }

  private async removeFileFromYaml(file: FileResponse): Promise<void> {
    try {
      let knowledgeBaseId = this.getKnowledgeBaseId(file.path)
      // Fallback: walk the parentId chain up to the nearest KB ancestor.
      if (!knowledgeBaseId && file.parentId) {
        let cur = this.metadata.folders.find(f => f.id === file.parentId)
        while (cur) {
          if (cur.isKnowledgeBase) { knowledgeBaseId = cur.path; break }
          cur = cur.parentId
            ? this.metadata.folders.find(f => f.id === cur!.parentId)
            : undefined
        }
      }
      if (!knowledgeBaseId) return

      await this.yamlService.removeDocument(knowledgeBaseId, file.path)
    } catch (error) {
      console.error('Failed to remove file from knowledge base YAML:', error)
    }
  }

  async getFolderById(id: string): Promise<FolderResponse | null> {
    const norm = (p: string) => p.replace(/\\/g, '/').toLowerCase()
    return this.metadata.folders.find(f => f.id === id || norm(f.path) === norm(id)) || null
  }

  async getFileById(id: string): Promise<FileResponse | null> {
    return this.metadata.files.find(f => f.id === id) || null
  }

  async getNodeById(id: string): Promise<TreeNodeResponse | null> {
    const folder = this.metadata.folders.find(f => f.id === id)
    if (folder) {
      return this.serializeFolder(folder, 0)
    }

    const file = this.metadata.files.find(f => f.id === id)
    if (file) {
      return this.serializeFile(file)
    }

    return null
  }

  async getChildren(parentId: string | null = null): Promise<TreeNodeResponse[]> {
    const result: TreeNodeResponse[] = []

    const childFolders = this.metadata.folders.filter(f => f.parentId === parentId)
    for (const folder of childFolders) {
      result.push(this.serializeFolder(folder, 0))
    }

    const childFiles = this.metadata.files.filter(f => f.parentId === parentId)
    for (const file of childFiles) {
      result.push(this.serializeFile(file))
    }

    return result
  }

  async getAllNodes(): Promise<TreeNodeResponse[]> {
    const rootFolders = this.metadata.folders.filter(f => f.parentId === null)
    const result: TreeNodeResponse[] = []

    for (const folder of rootFolders) {
      result.push(await this.buildTreeNode(folder, 0))
    }

    const rootFiles = this.metadata.files.filter(f => f.parentId === null)
    for (const file of rootFiles) {
      result.push(this.serializeFile(file))
    }

    return result
  }

  async getTree(): Promise<TreeNodeResponse[]> {
    return this.getAllNodes()
  }

  private async buildTreeNode(folder: FolderResponse, depth: number): Promise<TreeNodeResponse> {
    const node = this.serializeFolder(folder, depth)

    const childFolders = this.metadata.folders.filter(f => f.parentId === folder.id)
    for (const childFolder of childFolders) {
      node.children = node.children || []
      node.children.push(await this.buildTreeNode(childFolder, depth + 1))
    }

    const childFiles = this.metadata.files.filter(f => f.parentId === folder.id)
    for (const childFile of childFiles) {
      node.children = node.children || []
      node.children.push(this.serializeFile(childFile))
    }

    return node
  }

  async updateFolder(id: string, request: UpdateFolderRequest): Promise<FolderResponse> {
    const folderIndex = this.metadata.folders.findIndex(f => f.id === id)
    if (folderIndex === -1) {
      throw new Error(`Folder not found: ${id}`)
    }

    const folder = this.metadata.folders[folderIndex]
    const now = new Date().toISOString()

    // When name changes, sync path: rename dir on disk + update descendant paths
    let newPath = folder.path
    if (request.name && request.name !== folder.name) {
      const dir = dirname(folder.path)
      newPath = dir !== '.' ? join(dir, request.name) : request.name
      const oldAbs = join(this.basePath, folder.path)
      const newAbs = join(this.basePath, newPath)
      if (existsSync(oldAbs)) {
        await rename(oldAbs, newAbs)
      }
      // Update descendant folders' paths
      for (const df of this.metadata.folders) {
        if (df.id !== folder.id && df.path === folder.path) continue
        if (df.path.startsWith(folder.path + '\\') || df.path.startsWith(folder.path + '/')) {
          df.path = newPath + df.path.slice(folder.path.length)
        }
      }
      // Update descendant files' paths
      for (const df of this.metadata.files) {
        if (df.path.startsWith(folder.path + '\\') || df.path.startsWith(folder.path + '/')) {
          df.path = newPath + df.path.slice(folder.path.length)
        }
      }
      // Update YAML for knowledge-base folders (the .yml moved with dir rename)
      if (folder.isKnowledgeBase) {
        try {
          const yamlData = await this.yamlService.read(newPath)
          if (yamlData) {
            yamlData.knowledge_base.path = newPath
            yamlData.knowledge_base.root_path = join(this.basePath, newPath)
            if (request.name) yamlData.knowledge_base.name = request.name
            yamlData.knowledge_base.updated_at = now
            // Rebuild YAML at new path with correct path info
            const docs = [...(yamlData.documents || [])]
            await this.yamlService.create(
              newPath,
              yamlData.knowledge_base.name,
              request.description ?? yamlData.knowledge_base.description,
              { id: yamlData.knowledge_base.id || folder.id }
            )
            if (docs.length > 0) {
              // Rebase document paths from old KB path to new KB path
              const oldPrefix = folder.path + (folder.path.includes('\\') ? '\\' : '/')
              const newPrefix = newPath + (folder.path.includes('\\') ? '\\' : '/')
              for (const d of docs) {
                if (d.path && d.path.startsWith(oldPrefix)) {
                  d.path = newPrefix + d.path.slice(oldPrefix.length)
                }
              }
              await this.yamlService.addDocuments(newPath, docs.map(d => ({
                name: d.name,
                description: d.description,
                path: d.path,
                fileType: d.file_type,
                fileSize: d.file_size,
                metadata: d.metadata || {},
                tags: d.tags,
              })))
            }
          }
        } catch {
          // YAML may not exist yet; ok
        }
      }
    }

    const updatedFolder: FolderResponse = {
      ...folder,
      ...request,
      path: newPath,
      updatedAt: now
    }

    this.metadata.folders[folderIndex] = updatedFolder
    await this.saveMetadata()

    return updatedFolder
  }


  /**
   * Update file metadata and sync with KB YAML index.
   */
  async updateFile(id: string, request: UpdateFileRequest): Promise<FileResponse> {
    const fileIndex = this.metadata.files.findIndex(f => f.id === id)
    if (fileIndex === -1) {
      throw new Error(`File not found: ${id}`)
    }

    const file = this.metadata.files[fileIndex]
    const now = new Date().toISOString()

    // Clean undefined entries so name is not accidentally wiped.
    const cleanRequest: any = {}
    for (const key of Object.keys(request)) {
      if ((request as any)[key] !== undefined) {
        cleanRequest[key] = (request as any)[key]
      }
    }

    // If name changed, rename the file on disk and update path so they stay in sync.
    let newPath = file.path
    if (cleanRequest.name && cleanRequest.name !== file.name) {
      const dir = dirname(file.path)
      newPath = dir ? join(dir, cleanRequest.name) : cleanRequest.name
      const oldAbs = join(this.basePath, file.path)
      const newAbs = join(this.basePath, newPath)
      if (existsSync(oldAbs)) {
        await rename(oldAbs, newAbs)
      }
      const stats = await stat(newAbs).catch(() => null)
      if (stats) cleanRequest.fileSize = stats.size
    }

    const updatedFile: FileResponse = {
      ...file,
      ...cleanRequest,
      path: newPath,
      updatedAt: now
    }

    // Capture existing tags first -- removeFileFromYaml deletes the entire entry, and subsequent addDocument without existingIndex would lose tags
    const preservedTags = await this.readYamlDocTags(file.path)
    // Remove old entry from KB YAML, then add the updated one (path may have changed).
    await this.removeFileFromYaml(file)
    await this.updateYamlForFile(updatedFile, preservedTags)

    this.metadata.files[fileIndex] = updatedFile
    await this.saveMetadata()

    return updatedFile
  }

  async deleteFolder(id: string): Promise<DeleteResponse> {
    const folder = this.metadata.folders.find(f => f.id === id)
    if (!folder) {
      throw new Error(`Folder not found: ${id}`)
    }

    const childFolders = this.metadata.folders.filter(f => f.parentId === id)
    for (const childFolder of childFolders) {
      await this.deleteFolder(childFolder.id)
    }

    const childFiles = this.metadata.files.filter(f => f.parentId === id)
    for (const childFile of childFiles) {
      await this.deleteFile(childFile.id)
    }

    const folderPath = join(this.basePath, folder.path)
    if (existsSync(folderPath)) {
      await this.deleteDirectoryRecursive(folderPath)
    }

    this.metadata.folders = this.metadata.folders.filter(f => f.id !== id)

    if (folder.parentId) {
      const parentFolder = this.metadata.folders.find(f => f.id === folder.parentId)
      if (parentFolder) {
        parentFolder.childCount--
        parentFolder.updatedAt = new Date().toISOString()
      }
    }

    await this.saveMetadata()

    // Clean up KB YAML when deleting a knowledge-base folder
    if (folder.isKnowledgeBase) {
      try {
        await this.yamlService.delete(folder.path)
      } catch (error) {
        console.error('Failed to delete knowledge base YAML:', error)
      }

      // Clean up the parent KB's YAML index entry for this sub-KB
      if (folder.parentId) {
        const parentFolder = this.metadata.folders.find(f => f.id === folder.parentId)
        if (parentFolder && parentFolder.isKnowledgeBase) {
          try {
            await this.yamlService.removeDocument(parentFolder.path, folder.path)
          } catch (error) {
            console.error('Failed to remove sub-knowledge-base from parent YAML:', error)
          }
        }
      }
    }

    return {
      success: true,
      deletedId: id,
      message: `Folder "${folder.name}" deleted successfully`
    }
  }

  async deleteFile(id: string): Promise<DeleteResponse> {
    const file = this.metadata.files.find(f => f.id === id)
    if (!file) {
      throw new Error(`File not found: ${id}`)
    }

    const filePath = join(this.basePath, file.path)
    if (existsSync(filePath)) {
      await unlink(filePath)
    }

    // Delete associated images (flat images/ dir, delete by metadata.imagePaths)
    const kbPath = this.getKnowledgeBaseId(file.path)
    if (kbPath) {
      // Prefer metadata.imagePaths (flat path images/xxx.jpg)
      const imgPaths: string[] = (file.metadata as any)?.imagePaths || []
      if (imgPaths.length > 0) {
        for (const relPath of imgPaths) {
          const absImg = join(this.basePath, kbPath, relPath)
          if (existsSync(absImg)) {
            try { await unlink(absImg) } catch {}
          }
        }
      }
      // Compat: legacy images/{docStem}/ subdirectory (pre-migration data)
      const docStem = file.name.replace(/\.[^.]+$/, '')
      const oldImagesDir = join(this.basePath, kbPath, 'images', docStem)
      if (existsSync(oldImagesDir)) {
        try { await this.deleteDirectoryRecursive(oldImagesDir) } catch {}
      }
    }

    this.metadata.files = this.metadata.files.filter(f => f.id !== id)

    if (file.parentId) {
      const parentFolder = this.metadata.folders.find(f => f.id === file.parentId)
      if (parentFolder) {
        parentFolder.documentCount--
        parentFolder.updatedAt = new Date().toISOString()
      }
    }

    await this.saveMetadata()

    // Sync delete doc entry from YAML
    await this.removeFileFromYaml(file)

    // Fire-and-forget: clean up vector chunks + graph node for the deleted file.
    // Without this, deleted documents leave orphaned vectors in ChromaDB and
    // stale nodes in Neo4j, causing phantom search results.
    this.cleanupIndexOnDelete(file).catch((e) => {
      console.warn(`[deleteFile] index cleanup failed (non-fatal):`, e)
    })

    return {
      success: true,
      deletedId: id,
      message: `File "${file.name}" deleted successfully`
    }
  }

  /**
   * Clean up vector chunks and graph node when a document is deleted.
   * Fire-and-forget: failures don't block the delete operation.
   */
  private async cleanupIndexOnDelete(file: FileResponse): Promise<void> {
    try {
      const config = getServerConfig()
      const backendUrl = process.env.BACKEND_URL || config.backend_url || 'http://localhost:8765'
      const kbId = this.getKnowledgeBaseId(file.path)
      const docPath = file.path

      // 1. Delete graph node (cross-KB shared entities are preserved)
      try {
        await fetch(`${backendUrl}/api/v1/graph/document?doc_path=${encodeURIComponent(docPath)}`, {
          method: 'DELETE',
        })
        console.log(`[deleteFile] cleaned graph node: ${docPath}`)
      } catch (e) { console.warn('[deleteFile] graph cleanup failed (non-fatal):', e) }

      // 2. Delete vector chunks
      if (kbId) {
        try {
          await fetch(`${backendUrl}/api/v1/search/document?kb_id=${encodeURIComponent(kbId)}&doc_path=${encodeURIComponent(docPath)}`, {
            method: 'DELETE',
          })
          console.log(`[deleteFile] cleaned vector chunks: ${docPath}`)
        } catch (e) { console.warn('[deleteFile] vector cleanup failed (non-fatal):', e) }
      }
    } catch (err) {
      console.error('[deleteFile] index cleanup failed (non-fatal):', err)
    }
  }

  /**
   * Recursively delete a directory tree.
   */
  private async deleteDirectoryRecursive(dirPath: string): Promise<void> {
    if (!existsSync(dirPath)) return

    try {
      const entries = await readdir(dirPath, { withFileTypes: true })

      for (const entry of entries) {
        const fullPath = join(dirPath, entry.name)
        if (entry.isDirectory()) {
          await this.deleteDirectoryRecursive(fullPath)
        } else {
          await unlink(fullPath)
        }
      }

      await rmdir(dirPath)
    } catch (error) {
      console.error(`Error deleting directory ${dirPath}:`, error)
    }
  }

  private serializeFolder(folder: FolderResponse, depth: number): TreeNodeResponse {
    return {
      id: folder.id,
      name: folder.name,
      type: 'folder',
      parentId: folder.parentId,
      path: folder.path,
      description: folder.description,
      childCount: folder.childCount,
      documentCount: folder.documentCount,
      isKnowledgeBase: folder.isKnowledgeBase,
      createdAt: folder.createdAt,
      updatedAt: folder.updatedAt,
      depth,
      expanded: false,
      selected: false,
      loading: false,
      children: []
    }
  }

  private serializeFile(file: FileResponse): TreeNodeResponse {
    return {
      id: file.id,
      name: file.name,
      type: 'file',
      parentId: file.parentId,
      path: file.path,
      description: file.description,
      fileType: file.fileType,
      fileSize: file.fileSize,
      mimeType: file.mimeType,
      createdAt: file.createdAt,
      updatedAt: file.updatedAt,
      depth: 0,
      expanded: false,
      selected: false
    }
  }

  async getFolderCount(): Promise<number> {
    return this.metadata.folders.length
  }

  getFolderCountSync(): number {
    return this.metadata.folders.length
  }

  async getFileCount(): Promise<number> {
    return this.metadata.files.length
  }

  getFileCountSync(): number {
    return this.metadata.files.length
  }

  async getTotalCount(): Promise<number> {
    return this.metadata.folders.length + this.metadata.files.length
  }

  // ---- Knowledge-base management helpers -----------------------------------

  /**
   * Look up a file node by its storage-relative path.
   */
  async getFileByPath(path: string): Promise<FileResponse | null> {
    const norm = (p: string) => p.replace(/\\/g, '/').toLowerCase()
    return this.metadata.files.find(f => norm(f.path) === norm(path)) || null
  }

  /**
   * Resolve a docPath to its full storage-relative path.
   *
   * If *docPath* already contains a path separator it is treated as a
   * full relative path.  If it is a bare filename, the KB folder path
   * looked up by *kbId* is prepended.
   *
   * Returns null when the resolved path does not match any stored file.
   */
    async resolveDocPath(kbId: string, docPath: string): Promise<string | null> {
    const hasSep = docPath.includes('\\') || docPath.includes('/')
    let resolved: string | null = null
    if (hasSep) {
      resolved = docPath.replace(/\\/g, '/')
    } else {
      const folder = this.metadata.folders.find(
        (f) => f.isKnowledgeBase && (f.id === kbId || f.path.replace(/\\/g, '/') === kbId)
      )
      if (folder) {
        resolved = folder.path.replace(/\\/g, '/') + '/' + docPath
      }
    }
    if (!resolved) return null
    const norm = (p: string) => p.replace(/\\/g, '/').toLowerCase()
    return this.metadata.files.find((f) => norm(f.path) === norm(resolved)) ? resolved : null
  }
  /**
   * Overwrite a file's on-disk content and refresh its size in metadata.
   */
  async updateFileContent(id: string, content: string | Buffer): Promise<FileResponse> {
    const fileIndex = this.metadata.files.findIndex(f => f.id === id)
    if (fileIndex === -1) {
      throw new Error(`File not found: ${id}`)
    }
    const file = this.metadata.files[fileIndex]
    const filePath = join(this.basePath, file.path)
    const buffer = typeof content === 'string' ? Buffer.from(content, 'utf-8') : content
    await writeFile(filePath, buffer)
    const stats = await stat(filePath)
    const now = new Date().toISOString()
    const updatedFile: FileResponse = {
      ...file,
      fileSize: stats.size,
      updatedAt: now,
    }
    // Capture existing tags first (same as updateFile, avoid tag loss in delete-then-add flow)
    const preservedTags = await this.readYamlDocTags(file.path)
    // Sync KB YAML index so document listings reflect the new size
    await this.removeFileFromYaml(file)
    await this.updateYamlForFile(updatedFile, preservedTags)
    this.metadata.files[fileIndex] = updatedFile
    await this.saveMetadata()
    return updatedFile
  }

  /**
   * Update file content by its storage-relative path.
   */
  async updateFileContentByPath(path: string, content: string | Buffer): Promise<FileResponse | null> {
    const file = await this.getFileByPath(path)
    if (!file) return null
    return this.updateFileContent(file.id, content)
  }

  /**
   * Move a file to a different parent folder, auto-dedup on collision.
   */
  async moveFile(id: string, targetParentId: string | null): Promise<FileResponse> {
    const fileIndex = this.metadata.files.findIndex(f => f.id === id)
    if (fileIndex === -1) {
      throw new Error(`File not found: ${id}`)
    }
    const file = this.metadata.files[fileIndex]

    let targetFolderPath: string
    if (targetParentId) {
      const targetFolder = this.metadata.folders.find(f => f.id === targetParentId)
      if (!targetFolder) {
        throw new Error(`Target folder not found: ${targetParentId}`)
      }
      targetFolderPath = targetFolder.path
    } else {
      targetFolderPath = ''
    }

    const newName = this.getUniqueFileName(targetParentId, file.name)
    const newRelativePath = targetFolderPath ? join(targetFolderPath, newName) : newName
    const oldAbs = join(this.basePath, file.path)
    const newAbs = join(this.basePath, newRelativePath)

    await ensureDirectory(dirname(newAbs))

    if (existsSync(oldAbs)) {
      await rename(oldAbs, newAbs)
    }

    // Move associated images (flat images/ dir, migrate by metadata.imagePaths)
    const docStem = file.name.replace(/\.[^.]+$/, '')
    const oldKbPath = this.getKnowledgeBaseId(file.path)
    const imgPaths: string[] = (file.metadata as any)?.imagePaths || []
    if (imgPaths.length > 0 && oldKbPath) {
      const newImagesDir = join(this.basePath, targetFolderPath, 'images')
      await ensureDirectory(newImagesDir)
      for (const relPath of imgPaths) {
        const oldImg = join(this.basePath, oldKbPath, relPath)
        const imgName = basename(relPath)
        const newImg = join(newImagesDir, imgName)
        if (existsSync(oldImg)) {
          try { await cp(oldImg, newImg); await unlink(oldImg).catch(() => {}) } catch {}
        }
      }
    }
    // Compat: legacy images/{docStem}/ subdirectory
    const oldImagesDir = oldKbPath ? join(this.basePath, oldKbPath, 'images', docStem) : ''
    if (existsSync(oldImagesDir)) {
      const newOldDir = join(this.basePath, targetFolderPath, 'images', docStem)
      await ensureDirectory(newOldDir)
      try {
        await cp(oldImagesDir, newOldDir, { recursive: true })
        await rm(oldImagesDir, { recursive: true, force: true }).catch(() => {})
      } catch {}
    }

    // Update imagePaths in metadata (flat path, no docStem prefix change needed)
    let updatedMetadata = file.metadata || {}

    if (file.parentId) {
      const oldParent = this.metadata.folders.find(f => f.id === file.parentId)
      if (oldParent) {
        oldParent.documentCount--
        oldParent.updatedAt = new Date().toISOString()
      }
    }

    const now = new Date().toISOString()
    const movedFile: FileResponse = {
      ...file,
      name: newName,
      parentId: targetParentId || null,
      path: newRelativePath,
      metadata: updatedMetadata,
      updatedAt: now,
    }
    this.metadata.files[fileIndex] = movedFile

    if (targetParentId) {
      const newParent = this.metadata.folders.find(f => f.id === targetParentId)
      if (newParent) {
        newParent.documentCount++
        newParent.updatedAt = now
      }
    }

    const preservedTags = await this.readYamlDocTags(file.path)
    await this.removeFileFromYaml(file)
    await this.updateYamlForFile(movedFile, preservedTags)
    await this.saveMetadata()

    // Fire-and-forget: clean old indexes (vector + graph) and index new path.
    // This was previously defined but never called — a critical bug that left
    // stale vector chunks and graph nodes at the old path after a move.
    this.triggerReindexAfterMove(file, movedFile).catch((e) => {
      console.warn(`[moveFile] index sync failed (non-fatal):`, e)
    })

    return movedFile
  }

  /**
   * Sync vector + graph indexes after a document move.
   *
   * Strategy (lightweight, per-doc — avoids full-KB force reindex):
   *   1. Delete the OLD path's graph node (DELETE /graph/document)
   *   2. Delete the OLD path's vector chunks (DELETE /search/document)
   *   3. Index the NEW path (POST /search/index-document) — builds vector + graph
   *      and persists both vector_index & graph_index to the target KB's YAML.
   *
   * Cross-KB shared entities survive step 1 (graph_service.delete_document
   * only removes the doc's MENTIONED_IN edges + source_docs contribution).
   */
  private async triggerReindexAfterMove(sourceFile: FileResponse, movedFile: FileResponse): Promise<void> {
    try {
      const config = getServerConfig()
      const backendUrl = process.env.BACKEND_URL || config.backend_url || 'http://localhost:8765'
      const sourceKbId = this.getKnowledgeBaseId(sourceFile.path)
      const targetKbId = this.getKnowledgeBaseId(movedFile.path)
      const oldDocPath = sourceFile.path
      const newDocPath = movedFile.path

      // 1. Clean old-path graph nodes (cross-KB shared entities preserved)
      if (sourceKbId || oldDocPath) {
        try {
          await fetch(`${backendUrl}/api/v1/graph/document?doc_path=${encodeURIComponent(oldDocPath)}`, {
            method: 'DELETE',
          })
          console.log(`[moveFile] cleaned old graph node: ${oldDocPath}`)
        } catch (e) { console.warn('[moveFile] old graph cleanup failed (non-fatal):', e) }
      }

      // 2. Clean old-path vector chunks
      if (sourceKbId) {
        try {
          await fetch(`${backendUrl}/api/v1/search/document?kb_id=${encodeURIComponent(sourceKbId)}&doc_path=${encodeURIComponent(oldDocPath)}`, {
            method: 'DELETE',
          })
          console.log(`[moveFile] cleaned old vector chunks: ${oldDocPath}`)
        } catch (e) { console.warn('[moveFile] old vector cleanup failed (non-fatal):', e) }
      }

      // 3. Index new path (vector + graph + metadata write-back to target YAML)
      if (targetKbId) {
        try {
          const resp = await fetch(`${backendUrl}/api/v1/search/index-document`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              kb_id: targetKbId,
              doc_path: newDocPath,
              doc_name: movedFile.name,
              description: movedFile.description || '',
            }),
          })
          if (resp.ok) {
            const data = await resp.json()
            console.log(`[moveFile] indexed at new path: ${newDocPath} (ents=${data.graph_index?.entities ?? 0})`)
          }
        } catch (e) { console.warn('[moveFile] new path index failed (non-fatal):', e) }
      }
    } catch (err) {
      console.error('[moveFile] index sync after move failed (non-fatal):', err)
    }
  }

  /**
   * Index a document: vector embedding + knowledge graph construction + metadata write-back to .knowledge-base.yml.
   *
   * Design: each document ingestion/content-change API endpoint (upload/parse/save/updateContent)
   * completes file + metadata + YAML persistence, then calls index once. Moves handled separately by triggerReindexAfterMove.
   *
   * - Only indexes text files (.md/.markdown/.txt), skips non-text
   * - Non-blocking: fire-and-forget (fast upload response, YAML write-back after index auto-completes)
   * - Failure does not block main flow (doc already saved, index can be rebuilt manually later)
   */
  async indexDocument(file: FileResponse): Promise<void> {
    const ext = extname(file.name).toLowerCase()
    if (!['.md', '.markdown', '.txt'].includes(ext)) {
      return // Non-text files, skip index
    }
    // fire-and-forget -- does not block the caller
    this._doIndexDocument(file).catch((e) => {
      console.warn(`[indexDocument] failed for ${file.path} (non-fatal):`, e)
    })
  }

  private async _doIndexDocument(file: FileResponse): Promise<void> {
    const config = getServerConfig()
    const backendUrl = process.env.BACKEND_URL || config.backend_url || 'http://localhost:8765'
    const kbId = this.getKnowledgeBaseId(file.path)
    if (!kbId) {
      console.warn(`[indexDocument] cannot resolve KB for ${file.path} — skip`)
      return
    }
    try {
      const resp = await fetch(`${backendUrl}/api/v1/search/index-document`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          kb_id: kbId,
          doc_path: file.path,
          doc_name: file.name,
          description: file.description || '',
        }),
      })
      if (resp.ok) {
        const data = await resp.json()
        const gi = data.graph_index || {}
        console.log(`[indexDocument] ${file.path}: ents=${gi.entities ?? 0} rels=${gi.relations ?? 0} (vector+graph+metadata persisted)`)
      } else {
        console.warn(`[indexDocument] ${file.path}: backend returned ${resp.status}`)
      }
    } catch (e) {
      console.warn(`[indexDocument] ${file.path}: request failed (non-fatal):`, e)
    }
  }

  /**
   * Get a knowledge-base folder by its path id.
   */
  async getKnowledgeBaseById(kbId: string): Promise<FolderResponse | null> {
    const norm = (p: string) => p.replace(/\\/g, '/').toLowerCase()
    return this.metadata.folders.find(
      f => f.isKnowledgeBase && (norm(f.path) === norm(kbId) || f.id === kbId)
    ) || null
  }
}