/**
 * Tree File System Type Definitions
 */

/**
 * File Status Enum
 */
export type FileStatus = 'pending' | 'processing' | 'completed' | 'failed'

/**
 * Node Type
 */
export type NodeType = 'folder' | 'file'

/**
 * Base Node Interface - Common properties of all nodes
 */
export interface BaseNode {
  id: string
  name: string
  parentId: string | null
  path: string
  type: NodeType
  description?: string
  createdAt: string
  updatedAt: string
}

/**
 * Folder Node Interface
 */
export interface FolderNode extends BaseNode {
  type: 'folder'
  children: TreeNode[]
  childCount: number
  documentCount: number
  isKnowledgeBase?: boolean
  /** Associated KB ID (UUID). KB folder's own id equals itself, non-KB folders inherit the nearest ancestor KB's id */
  kb_id?: string | null
  // UI State Properties
  depth: number
  expanded?: boolean
  selected?: boolean
  loading?: boolean
}

/**
 * File Node Interface
 */
export interface FileNode extends BaseNode {
  type: 'file'
  fileType: string
  fileSize: number
  mimeType?: string
  status?: FileStatus
  metadata?: Record<string, any>
}

/**
 * TreeNode Union Type
 */
export type TreeNode = FolderNode | FileNode

/**
 * Folder Response Interface (For API Response, without children)
 */
export interface FolderResponse extends Omit<FolderNode, 'children' | 'depth' | 'expanded' | 'selected' | 'loading'> {
  isKnowledgeBase?: boolean
}

/**
 * File Response Interface
 */
export interface FileResponse extends FileNode {
  description?: string
}

/**
 * TreeNode Response Interface (Common API Response Format)
 * Merges all properties of FolderResponse and FileResponse
 */
export interface TreeNodeResponse {
  id: string
  name: string
  type: NodeType
  parentId: string | null
  path: string
  description?: string
  createdAt: string
  updatedAt: string

  // Folder-specific Properties
  children?: TreeNodeResponse[]
  childCount?: number
  documentCount?: number
  isKnowledgeBase?: boolean

  // File-specific Properties
  fileType?: string
  fileSize?: number
  mimeType?: string
  status?: FileStatus
  metadata?: Record<string, any>

  // UI State Properties
  depth?: number
  expanded?: boolean
  selected?: boolean
  loading?: boolean
}

/**
 * Create Folder Request
 */
export interface CreateFolderRequest {
  name: string
  parentId?: string | null
  description?: string
  isKnowledgeBase?: boolean
}

/**
 * Create File Request
 */
export interface CreateFileRequest {
  name: string
  parentId?: string | null
  fileType?: string
  mimeType?: string
  fileSize?: number
  description?: string
  metadata?: Record<string, any>
}

/**
 * Update Folder Request
 */
export interface UpdateFolderRequest {
  name?: string
  description?: string
}

/**
 * Update File Request
 */
export interface UpdateFileRequest {
  name?: string
  description?: string
  metadata?: Record<string, any>
}

/**
 * Delete Response
 */
export interface DeleteResponse {
  success: boolean
  deletedId: string
  message?: string
}

/**
 * Tree Stats
 */
export interface TreeStats {
  folders: number
  files: number
  total: number
}
