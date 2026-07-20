/**
 * POST /api/claude/upload
 *
 * Upload attachment -> save to storage/claude-uploads/ -> return metadata.
 *
 * Frontend appends the returned attachment object to /api/claude/chat's attachments array.
 * chat.post.ts converts attachments to SDK image / document / text content blocks by type.
 *
 * Supports: images (png/jpg/gif/webp), PDF, text/code/Markdown, Office (docx/pptx/xlsx)
 * Size limits: images 20MB, others 50MB
 */
import { resolve, dirname, join } from 'path'
import { fileURLToPath } from 'url'
import { mkdirSync, existsSync, writeFileSync, statSync, readdirSync, unlinkSync } from 'fs'
import { readMultipartFormData } from 'h3'

const __dirname = dirname(fileURLToPath(import.meta.url))
const MONOREPO_ROOT = resolve(__dirname, '../../../..')
const UPLOAD_DIR = resolve(MONOREPO_ROOT, 'storage', 'claude-uploads')

const IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp']
const TEXT_TYPES = [
  'text/', 'application/json', 'application/xml', 'application/javascript',
  'application/x-yaml', 'application/x-sh', 'application/typescript',
]
const TEXT_EXTS = ['.md', '.txt', '.json', '.yaml', '.yml', '.xml', '.js', '.ts', '.jsx', '.tsx',
  '.py', '.java', '.c', '.cpp', '.h', '.go', '.rs', '.rb', '.php', '.sh', '.bat', '.ps1',
  '.html', '.css', '.scss', '.vue', '.toml', '.ini', '.cfg', '.conf', '.env', '.gitignore',
  '.dockerfile', '.makefile', '.sql', '.csv', '.tsv', '.log']
const MAX_IMAGE = 20 * 1024 * 1024
const MAX_OTHER = 50 * 1024 * 1024
const CLEANUP_AGE_MS = 24 * 60 * 60 * 1000 // 24 hours

function cleanupOldUploads() {
  try {
    if (!existsSync(UPLOAD_DIR)) return
    const now = Date.now()
    const entries = readdirSync(UPLOAD_DIR)
    for (const f of entries) {
      const fp = join(UPLOAD_DIR, f)
      try {
        if (statSync(fp).mtimeMs < now - CLEANUP_AGE_MS) {
          unlinkSync(fp)
        }
      } catch { /* Ignore individual file deletion failure */ }
    }
  } catch { /* Ignore if directory is not accessible */ }
}

function detectMime(filename: string, fallback?: string): string {
  if (fallback) return fallback
  const ext = filename.toLowerCase().match(/\.[^.]+$/)?.[0] || ''
  const map: Record<string, string> = {
    '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.gif': 'image/gif', '.webp': 'image/webp', '.svg': 'image/svg+xml',
    '.pdf': 'application/pdf',
    '.md': 'text/markdown', '.txt': 'text/plain', '.json': 'application/json',
    '.yaml': 'application/x-yaml', '.yml': 'application/x-yaml',
    '.xml': 'application/xml', '.js': 'text/javascript', '.ts': 'application/typescript',
    '.html': 'text/html', '.css': 'text/css', '.csv': 'text/csv',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  }
  return map[ext] || 'application/octet-stream'
}

function isImage(mime: string) { return IMAGE_TYPES.includes(mime) || mime.startsWith('image/') }
function isText(mime: string, filename: string) {
  if (TEXT_TYPES.some(t => mime.startsWith(t) || mime === t)) return true
  const ext = filename.toLowerCase().match(/\.[^.]+$/)?.[0] || ''
  return TEXT_EXTS.includes(ext)
}

export default defineEventHandler(async (event) => {
  mkdirSync(UPLOAD_DIR, { recursive: true })

  // Clean up attachments older than 24 hours
  cleanupOldUploads()

  const parts = await readMultipartFormData(event)
  if (!parts || !parts.length) {
    throw createError({ statusCode: 400, statusMessage: '未收到文件' })
  }

  const results = []
  for (const part of parts) {
    // Only process file fields (with filename), skip regular form fields
    if (!part.filename) continue
    const name = part.filename || 'unnamed'
    const data = part.data || Buffer.alloc(0)
    const size = data.length
    const mime = detectMime(name, part.type)

    if (isImage(mime) && size > MAX_IMAGE) {
      throw createError({ statusCode: 413, statusMessage: `图片 ${name} 超过 20MB 上限` })
    }
    if (size > MAX_OTHER) {
      throw createError({ statusCode: 413, statusMessage: `${name} 超过 50MB 上限` })
    }

    // Use timestamp + original name to prevent conflicts
    const stamp = Date.now()
    const safeName = name.replace(/[^\w.\-]+/g, '_')
    const storedName = `${stamp}_${safeName}`
    const fullPath = join(UPLOAD_DIR, storedName)
    writeFileSync(fullPath, data)

    results.push({
      id: `att_${stamp}_${Math.random().toString(36).slice(2, 8)}`,
      name,
      path: fullPath,
      relativePath: `storage/claude-uploads/${storedName}`,
      size,
      mime,
      isImage: isImage(mime),
      isText: isText(mime, name),
      isPdf: mime === 'application/pdf',
    })
  }

  return { success: true, count: results.length, attachments: results }
})
