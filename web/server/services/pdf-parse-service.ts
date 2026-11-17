import { constants } from 'fs'
import { lstat, open, realpath } from 'fs/promises'
import { isAbsolute, join, relative, resolve, sep } from 'path'
import type {
  ParsePDFVTResponse,
  BatchParsePDFFileVTResponse,
  BatchParsePDFFileVTItem,
  MineruParseResult,
} from '~/types/pdf-parse'
import { getPdfParserApiUrl, getTreeStorageAbsolutePath, resolveProjectPath } from '~/server/utils/runtime-paths'
import { getDynamicAuthConfig } from '~/server/utils/dynamic-config'
// undici Agent with bodyTimeout disabled: MinerU OCR can be silent for
// minutes between chunks; the default ~5min body timeout kills the stream.
// Loaded via dynamic import() so this works in Nuxt's ESM nitro runtime
// (require is undefined there). undici ships with Node and powers fetch().

/**
 * Backend v1 batch envelope (before normalization).
 * Each item wraps a MineruParseResult under 
esult and uses status.
 */
interface BackendBatchEnvelope {
  total: number
  successful: number
  failed: number
  results: Array<{
    index: number
    filename: string
    status: 'completed' | 'failed'
    result?: MineruParseResult
    error?: string
  }>
  error?: string
}

/**
 * Back-fill markdown content by reading the .md file the backend wrote to disk.
 * The v1 API returns paths only; the proxy reads the file so the frontend can
 * (a) preview content and (b) write it into the tree-fs / knowledge-base store.
 * Falls back to undefined when the path is missing or unreadable.
 */
export interface ParseArtifactRoots {
  project: string
  output: string
  storage: string
}

function getParseArtifactRoots(): ParseArtifactRoots {
  return {
    project: resolveProjectPath('.'),
    output: resolveProjectPath('./backend/output'),
    // This is the one explicitly configured external root permitted for parse
    // artifacts. No path supplied by a request is ever promoted to an allowed root.
    storage: getTreeStorageAbsolutePath(),
  }
}

function isWithin(path: string, root: string): boolean {
  const rel = relative(root, path)
  return rel === '' || (rel !== '..' && !rel.startsWith(`..${sep}`) && !isAbsolute(rel))
}

function sameFileIdentity(a: { dev: number; ino: number; size: number; mtimeMs: number; ctimeMs: number }, b: { dev: number; ino: number; size: number; mtimeMs: number; ctimeMs: number }): boolean {
  return a.dev === b.dev && a.ino === b.ino && a.size === b.size && a.mtimeMs === b.mtimeMs && a.ctimeMs === b.ctimeMs
}

function samePath(a: string, b: string): boolean {
  return process.platform === 'win32' ? a.toLowerCase() === b.toLowerCase() : a === b
}

/** Match the backend policy: never trust a redirected implicit backend/output root. */
async function resolveDefaultOutputRoot(project: string, output: string): Promise<string | null> {
  try {
    const canonicalProject = await realpath(project)
    if (!samePath(resolve(output), resolve(canonicalProject, 'backend', 'output'))) return null

    let current = canonicalProject
    for (const segment of ['backend', 'output']) {
      current = join(current, segment)
      const info = await lstat(current)
      if (info.isSymbolicLink() || !info.isDirectory() || !samePath(await realpath(current), current)) return null
    }
    return current
  } catch {
    return null
  }
}

/** Canonicalize an artifact beneath backend/output or the configured storage root.
 * The configured storage root may intentionally be external to the checkout; it is
 * still the only external path trusted here. Artifact paths must be absolute.
 */
export async function resolveParseArtifact(
  candidate?: string,
  roots: ParseArtifactRoots = getParseArtifactRoots(),
): Promise<string | null> {
  if (!candidate || !isAbsolute(candidate) || candidate.includes('\0') || candidate.startsWith('\\\\') || (process.platform === 'win32' && candidate.startsWith('//'))) return null
  if (candidate.split(process.platform === 'win32' ? /[\\/]/ : /\//).includes('..')) return null
  try {
    const target = await realpath(candidate)
    // A lexical request under the implicit root must never fall back to storage,
    // even when its redirected target is also the configured storage root.
    const defaultCandidate = isWithin(resolve(candidate), resolve(roots.output))
    const [output, storage] = await Promise.all([
      resolveDefaultOutputRoot(roots.project, roots.output),
      realpath(roots.storage).catch(() => null),
    ])
    if (defaultCandidate) return output && isWithin(target, output) ? target : null
    if (output && isWithin(target, output)) return target
    if (storage && isWithin(target, storage)) return target
  } catch { /* missing, inaccessible, or changed paths are not parse artifacts */ }
  return null
}

/** Open a validated artifact and read from the descriptor, not the checked path.
 * Re-resolve immediately before open, refuse links/non-files, and compare identity
 * before and after the read. This also prevents a path replacement from changing
 * the file that is consumed after validation. Node core does not expose a
 * Windows handle-relative/no-reparse open primitive for every path component;
 * a hostile parent-junction swap in the tiny interval between the final recheck
 * and open therefore remains a platform-level TOCTOU limitation. The opened
 * descriptor identity is still checked before any bytes are accepted.
 */
export async function readParseArtifact(
  candidate?: string,
  roots: ParseArtifactRoots = getParseArtifactRoots(),
  hooks: { beforeOpen?: (path: string) => Promise<void> } = {},
): Promise<{ path: string; buffer: Buffer } | null> {
  const safePath = await resolveParseArtifact(candidate, roots)
  if (!safePath) return null
  let handle: Awaited<ReturnType<typeof open>> | undefined
  try {
    // The canonical target is the path actually opened; O_NOFOLLOW is available
    // on POSIX. Windows lacks a portable openat/no-follow directory traversal API.
    const before = await lstat(safePath)
    if (!before.isFile() || before.isSymbolicLink()) return null
    await hooks.beforeOpen?.(safePath)
    // Re-resolve immediately before open. Compare the canonical path to the one
    // selected above, and compare opened descriptor identity below.
    const revalidated = await resolveParseArtifact(candidate, roots)
    if (!revalidated || !samePath(revalidated, safePath)) return null
    const noFollow = typeof constants.O_NOFOLLOW === 'number' ? constants.O_NOFOLLOW : 0
    handle = await open(safePath, constants.O_RDONLY | noFollow)
    const opened = await handle.stat()
    if (!opened.isFile() || !sameFileIdentity(before, opened)) return null

    // Check the name again after opening. If a parent directory/junction changed,
    // do not trust a descriptor whose name no longer resolves to this artifact.
    const afterOpenPath = await realpath(safePath)
    const current = await lstat(safePath)
    if (!samePath(afterOpenPath, safePath) || current.isSymbolicLink() || !sameFileIdentity(opened, current)) return null

    const buffer = await handle.readFile()
    const afterRead = await handle.stat()
    if (!sameFileIdentity(opened, afterRead) || afterRead.size !== buffer.length) return null
    return { path: safePath, buffer }
  } catch {
    return null
  } finally {
    await handle?.close().catch(() => undefined)
  }
}

async function backFillMarkdown(markdownPath?: string): Promise<string | undefined> {
  const artifact = await readParseArtifact(markdownPath)
  return artifact?.buffer.toString('utf-8')
}

/** Flatten one MineruParseResult into the v1-aligned item + back-fill markdown. */
async function toBatchItem(
  filename: string,
  raw: MineruParseResult,
): Promise<BatchParsePDFFileVTItem> {
  const markdown = raw.markdown || (await backFillMarkdown(raw.markdown_path))
  return {
    filename,
    success: true,
    markdown,
    markdown_path: raw.markdown_path,
    output_dir: raw.output_dir,
    images_dir: raw.images_dir,
    image_dir: raw.images_dir,
    source_filename: raw.source_filename,
    image_count: raw.image_count,
    has_markdown: raw.has_markdown,
    metadata: raw.metadata,
    parse_method: raw.metadata?.parse_method as string | undefined,
  }
}

/**
 * PDF Parse Service
 * Communicates with Python backend PDF parser API (v1).
 */
// Shared dispatcher: disable undici body/headers timeout so long OCR
// parses (which emit nothing for several minutes) are not aborted.
let _streamDispatcher: any = null
async function getStreamDispatcher() {
  if (!_streamDispatcher) {
    const undici = await import('undici')
    _streamDispatcher = new undici.Agent({
      bodyTimeout: 0,
      headersTimeout: 0,
    })
  }
  return _streamDispatcher
}

export class PDFParseService {
  private baseUrl: string

  constructor() {
    // Use dynamic config reader — always reads fresh config.yml/.env
    // (with 5s TTL cache) so config changes via Settings page are picked up.
    this.baseUrl = getPdfParserApiUrl()
  }

  /**
   * Get the current backend URL (dynamic, picks up config changes).
   */
  private getBaseUrl(): string {
    return getPdfParserApiUrl()
  }

  /**
   * Auth headers for direct backend calls (2026-09-09): this service uses
   * native fetch (not globalThis.$fetch), so the backend-auth Nitro plugin
   * cannot inject the token — do it here. MCP service token first, then the
   * legacy shared token.
   */
  private getAuthHeaders(): Record<string, string> {
    try {
      const token = getDynamicAuthConfig().token
      if (token) return { Authorization: `Bearer ${token}` }
    } catch { /* fall through — backend may have auth disabled */ }
    return {}
  }

  /**
   * Parse a single PDF file using VT (Traditional) mode
   * Corresponds to: POST /api/v1/parse/file/vt
   */
  async parseFileVT(
    file: Buffer,
    filename: string,
    options?: { output_dir?: string; use_ocr?: boolean },
  ): Promise<ParsePDFVTResponse> {
    const formData = new FormData()
    const uint8Array = new Uint8Array(file)
    const blob = new Blob([uint8Array], { type: 'application/pdf' })
    formData.append('file', blob, filename)

    if (options?.output_dir) {
      formData.append('output_dir', options.output_dir)
    }
    if (options?.use_ocr !== undefined) {
      formData.append('use_ocr', String(options.use_ocr))
    }

    const response = await fetch(`${this.getBaseUrl()}/api/v1/parse/file/vt`, {
      headers: this.getAuthHeaders(),
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`PDF parse failed: ${error}`)
    }

    const raw = (await response.json()) as MineruParseResult
    return normalizeSingleResult(raw)
  }

  /**
   * Batch parse multiple PDF files using VT mode
   * Corresponds to: POST /api/v1/batch/parse/file/vt
   */
  async batchParseFilesVT(
    files: Array<{ buffer: Buffer; filename: string }>,
    options?: { output_dir?: string; use_ocr?: boolean },
  ): Promise<BatchParsePDFFileVTResponse> {
    const formData = new FormData()
    for (const file of files) {
      const uint8Array = new Uint8Array(file.buffer)
      const blob = new Blob([uint8Array], { type: 'application/pdf' })
      formData.append('files', blob, file.filename)
    }
    if (options?.output_dir) {
      // The backend non-stream batch endpoint accepts one batch fallback under
      // `default_output` (unlike the single-file endpoint's `output_dir`).
      formData.append('default_output', options.output_dir)
    }
    if (options?.use_ocr !== undefined) {
      formData.append('use_ocr', String(options.use_ocr))
    }

    const response = await fetch(`${this.getBaseUrl()}/api/v1/batch/parse/file/vt`, {
      headers: this.getAuthHeaders(),
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Batch PDF parse failed: ${error}`)
    }

    const rawBatch = (await response.json()) as BackendBatchEnvelope
    return normalizeBatchResult(rawBatch)
  }

  /**
   * Batch parse multiple PDF files using VT mode with streaming progress
   * Corresponds to: POST /api/v1/batch/parse/file/vt/stream
   * Returns a readable stream for SSE (raw backend stream; the stream route
   * normalizes each SSE frame before forwarding to the client).
   */
  async batchParseFilesVTStream(
    files: Array<{ buffer: Buffer; filename: string }>,
    options?: { output_dir?: string; use_ocr?: boolean },
  ): Promise<ReadableStream> {
    const formData = new FormData()
    for (const file of files) {
      const uint8Array = new Uint8Array(file.buffer)
      const blob = new Blob([uint8Array], { type: 'application/pdf' })
      formData.append('files', blob, file.filename)
    }
    if (options?.output_dir) {
      formData.append('default_output', options.output_dir)
    }
    if (options?.use_ocr !== undefined) {
      formData.append('use_ocr', String(options.use_ocr))
    }

    const response = await fetch(`${this.getBaseUrl()}/api/v1/batch/parse/file/vt/stream`, {
      headers: this.getAuthHeaders(),
      method: 'POST',
      body: formData,
      // @ts-ignore - dispatcher is Node/undici specific
      dispatcher: await getStreamDispatcher(),
    })

    if (!response.ok || !response.body) {
      const error = await response.text()
      throw new Error(`Stream PDF parse failed: ${error}`)
    }

    return response.body
  }
}

/** Map a single backend MineruParseResult to the v1-aligned frontend shape. */
async function normalizeSingleResult(raw: MineruParseResult): Promise<ParsePDFVTResponse> {
  if (!raw || !raw.success) {
    return {
      success: false,
      error: raw?.error,
      source_filename: raw?.source_filename,
      output_dir: raw?.output_dir,
    }
  }
  const markdown = raw.markdown || (await backFillMarkdown(raw.markdown_path))
  return {
    success: true,
    markdown,
    markdown_path: raw.markdown_path,
    output_dir: raw.output_dir,
    images_dir: raw.images_dir,
    image_dir: raw.images_dir,
    source_filename: raw.source_filename,
    image_count: raw.image_count,
    has_markdown: raw.has_markdown,
    metadata: raw.metadata,
    parse_method: raw.metadata?.parse_method as string | undefined,
  }
}

/** Normalize the backend batch envelope into the frontend batch shape. */
async function normalizeBatchResult(rawBatch: BackendBatchEnvelope): Promise<BatchParsePDFFileVTResponse> {
  const items: BatchParsePDFFileVTItem[] = []
  for (const entry of rawBatch.results || []) {
    const ok = entry.status === 'completed' && entry.result?.success
    if (!ok) {
      items.push({
        filename: entry.filename,
        success: false,
        error: entry.error || entry.result?.error || 'parse failed',
      })
      continue
    }
    items.push(await toBatchItem(entry.filename, entry.result as MineruParseResult))
  }
  return {
    success: rawBatch.failed === 0,
    total_files: rawBatch.total ?? items.length,
    successful_files: rawBatch.successful ?? items.filter(i => i.success).length,
    failed_files: rawBatch.failed ?? items.filter(i => !i.success).length,
    results: items,
    error: rawBatch.error,
  }
}

// Singleton instance
let pdfParseService: PDFParseService | null = null

export function getPDFParseService(): PDFParseService {
  if (!pdfParseService) {
    pdfParseService = new PDFParseService()
  }
  return pdfParseService
}

// Re-exported so the stream route can reuse the same normalization for SSE frames.
export { backFillMarkdown, toBatchItem }
