﻿import { readFile } from 'fs/promises'
import { existsSync } from 'fs'
import type {
  ParsePDFVTResponse,
  BatchParsePDFFileVTResponse,
  BatchParsePDFFileVTItem,
  MineruParseResult,
} from '~/types/pdf-parse'
import { getPdfParserApiUrl } from '~/server/utils/runtime-paths'
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
async function backFillMarkdown(markdownPath?: string): Promise<string | undefined> {
  if (!markdownPath || !existsSync(markdownPath)) {
    return undefined
  }
  try {
    return await readFile(markdownPath, 'utf-8')
  } catch {
    return undefined
  }
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
      formData.append('output_dir', options.output_dir)
    }
    if (options?.use_ocr !== undefined) {
      formData.append('use_ocr', String(options.use_ocr))
    }

    const response = await fetch(`${this.getBaseUrl()}/api/v1/batch/parse/file/vt`, {
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
