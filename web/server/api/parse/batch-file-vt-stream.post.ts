import { defineEventHandler, readMultipartFormData, createError, setHeader } from 'h3'
import { readFile } from 'fs/promises'
import { existsSync } from 'fs'
import { getPDFParseService } from '~/server/services/pdf-parse-service'
import { resolveTreeStorageOutputPath } from '~/server/utils/runtime-paths'
import type { MineruParseResult } from '~/types/pdf-parse'

/**
 * Batch parse multiple PDF files using VT mode with streaming progress
 * POST /api/parse/batch-file-vt-stream
 *
 * Proxies to Python backend SSE stream (POST /api/v1/batch/parse/file/vt/stream)
 * and NORMALIZES each event so the frontend always sees the v1-aligned shape:
 * the backend returns MineruParseResult (paths only), so we back-fill `markdown`
 * by reading markdown_path here, before forwarding each SSE frame.
 */
export default defineEventHandler(async (event) => {
  try {
    const formData = await readMultipartFormData(event)
    if (!formData) {
      throw createError({ statusCode: 400, statusMessage: 'No form data provided' })
    }

    const fileFields = formData.filter(field => field.name === 'files')
    if (fileFields.length === 0) {
      throw createError({ statusCode: 400, statusMessage: 'At least one PDF file is required' })
    }

    const files: Array<{ buffer: Buffer; filename: string }> = []
    for (const field of fileFields) {
      if (!field.data) continue
      const filename = field.filename || 'unknown.pdf'
      if (!['.pdf','.png','.jpg','.jpeg','.docx','.xlsx'].some(ext => filename.toLowerCase().endsWith(ext))) {
        throw createError({
          statusCode: 400,
          statusMessage: `Unsupported format: ${filename}`,
        })
      }
      files.push({ buffer: field.data, filename })
    }
    if (files.length === 0) {
      throw createError({ statusCode: 400, statusMessage: 'No valid files provided' })
    }

    const outputDirField = formData.find(field => field.name === 'output_dir')
    const useOcrField = formData.find(field => field.name === 'use_ocr')
    const parentIdField = formData.find(field => field.name === 'parent_id')
    const options = {
      output_dir: resolveTreeStorageOutputPath(outputDirField?.data?.toString()),
      use_ocr: useOcrField?.data?.toString() === 'true',
    }

    const pdfService = getPDFParseService()
    const stream = await pdfService.batchParseFilesVTStream(files, options)

    setHeader(event, 'Content-Type', 'text/event-stream')
    setHeader(event, 'Cache-Control', 'no-cache')
    setHeader(event, 'Connection', 'keep-alive')
    setHeader(event, 'X-Accel-Buffering', 'no')

    const reader = stream.getReader()
    const decoder = new TextDecoder()
    const res = event.node.res
    let sseBuffer = ''

    /** Back-fill markdown content for a backend MineruParseResult. */
    async function normalizeMineruResult(raw: MineruParseResult) {
      if (!raw || !raw.success) {
        return {
          success: false as const,
          error: raw?.error,
          source_filename: raw?.source_filename,
        }
      }
      let markdown: string | undefined
      if (raw.markdown_path && existsSync(raw.markdown_path)) {
        try {
          markdown = await readFile(raw.markdown_path, 'utf-8')
        } catch { /* leave undefined */ }
      }
      return {
        success: true as const,
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
     * Rewrite a decoded SSE payload in place: for `progress` events we
     * back-fill the embedded `result`; for `complete` events we rewrite each
     * `summary.results[].result` into the flat shape. Returns the new line.
     */

    async function rewriteSseData(data: Record<string, any>): Promise<string> {
      // Both progress.result and complete.summary.results[] are normalized to
      // the FLAT BatchParsePDFFileVTItem shape (filename + back-filled
      // markdown), so the frontend can pass them straight to saveParsedFiles
      // without any reshaping.
      if (data.type === 'progress' && data.result) {
        const norm = await normalizeMineruResult(data.result as MineruParseResult)
        data.result = { filename: data.filename, ...norm }
        data.status = data.result.success ? 'completed' : 'failed'
      } else if (data.type === 'complete' && data.summary?.results) {
        const flat: any[] = []
        for (const entry of data.summary.results) {
          const norm = entry.result
            ? await normalizeMineruResult(entry.result as MineruParseResult)
            : { success: false, error: entry.error }
          flat.push({ filename: entry.filename, ...norm })
        }
        data.summary.results = flat
      }
      return `data: ${JSON.stringify(data)}\n\n`
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      sseBuffer += decoder.decode(value, { stream: true })

      // SSE frames are separated by a blank line. Process complete frames.
      let idx: number
      while ((idx = sseBuffer.indexOf('\n\n')) !== -1) {
        const frame = sseBuffer.slice(0, idx)
        sseBuffer = sseBuffer.slice(idx + 2)

        // Only rewrite `data:` lines; pass anything else through verbatim.
        const dataLine = frame.split('\n').find(l => l.startsWith('data: '))
        if (!dataLine) {
          res.write(frame + '\n\n')
          continue
        }
        try {
          const parsed = JSON.parse(dataLine.slice(6))
          // Await normalizes markdown back-fill for this frame before sending.
          res.write(await rewriteSseData(parsed))
        } catch {
          // Unparseable frame - forward as-is so the client still advances.
          res.write(frame + '\n\n')
        }
      }
    }

    res.end()
    return null
  } catch (error: any) {
    console.error('Stream batch PDF parse error:', error)
    const errorData = {
      type: 'error',
      message: error.message || 'Stream parsing failed',
      timestamp: new Date().toISOString(),
    }
    return `data: ${JSON.stringify(errorData)}\n\n`
  }
})

