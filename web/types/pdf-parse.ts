/**
 * PDF Parser API Types
 * Corresponds to the backend v1 API (MineruParseResult / batch shape).
 */

/**
 * Backend v1 `MineruParseResult` for a single parse.
 * The backend writes .md + images to disk and returns PATHS, not content.
 * We back-fill `markdown` on the proxy layer by reading markdown_path.
 */
export interface MineruParseResult {
  success: boolean
 output_dir?: string
 markdown_path?: string
  markdown?: string
 images_dir?: string
 source_filename?: string
  image_count?: number
  has_markdown?: boolean
  metadata?: Record<string, any>
  error?: string
}

// Single file parse response (VT mode) - v1-aligned.
export interface ParsePDFVTResponse {
  success: boolean
  // Back-filled by the proxy from markdown_path; may be empty if read fails.
  markdown?: string
  markdown_path?: string
  // v1 native fields
  output_dir?: string
  images_dir?: string
  source_filename?: string
  image_count?: number
  has_markdown?: boolean
  metadata?: Record<string, any>
  // Legacy aliases kept for older consumers.
  image_dir?: string
  parse_method?: string
  error?: string
}

// One item inside a batch parse result.
// Backend v1 batch returns each item as:
//   { index, filename, status: 'completed'|'failed', result: MineruParseResult }
// We normalize to this flat shape on the proxy so the frontend can treat
// single and batch results uniformly.
export interface BatchParsePDFFileVTItem {
  filename: string
  success: boolean
  // Back-filled markdown content.
  markdown?: string
  markdown_path?: string
  output_dir?: string
  images_dir?: string
  source_filename?: string
  image_count?: number
  has_markdown?: boolean
  metadata?: Record<string, any>
  // Legacy aliases.
  image_dir?: string
  parse_method?: string
  error?: string
}

export interface BatchParsePDFFileVTItemWithDescription extends BatchParsePDFFileVTItem {
  description?: string
}

export interface BatchParsePDFFileVTResponse {
  success: boolean
  total_files: number
  successful_files: number
  failed_files: number
  results: BatchParsePDFFileVTItem[]
  error?: string
}

export interface SaveParsedFilesRequest {
  parentId: string
  split?: boolean
  agentPlan?: Record<string, unknown>
  results: Array<BatchParsePDFFileVTItemWithDescription & { recoveryReceipt?: string }>
}

export interface SaveParsedFilesResponse {
  success: boolean
  /** Fully confirmed document records only. */
  savedCount: number
  files: Array<Record<string, any>>
  /** Incomplete records that may have been written before an item failed. */
  partialCount: number
  partialFiles: Array<Record<string, any>>
  /** Existing content duplicates, reported without modifying their metadata/images. */
  existingCount: number
  existingFiles: Array<Record<string, any>>
  /** Number of input items not fully saved (including parse failures). */
  failedCount: number
  items: Array<{
    index: number
    filename: string
    success: boolean
    files: Array<Record<string, any>>
    /** Newly published images, including images retained on failure. */
    createdImages: Array<{ path: string; identity: { dev: number; ino: number } }>
    error?: string
    /** Opaque, process-local bearer capability. Keep in volatile memory only. */
    recoveryReceipt?: string
  }>
}

// Request options
export interface ParsePDFVTOptions {
  output_dir?: string
  use_ocr?: boolean
  // Optional target KB folder; when set the proxy writes the parsed .md
  // directly into it (.tree-fs.json + .knowledge-base.yml). Omit for a
  // pure parse (persist via save-parsed-files instead).
  parent_id?: string
}

export interface BatchParsePDFVTOptions extends ParsePDFVTOptions {
  files: File[]
}
