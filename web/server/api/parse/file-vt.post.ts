import { defineEventHandler, readMultipartFormData, createError } from 'h3'
import { getPDFParseService } from '~/server/services/pdf-parse-service'
import { resolveTreeStorageOutputPath } from '~/server/utils/runtime-paths'
import type { ParsePDFVTResponse } from '~/types/pdf-parse'

/**
 * Parse a single file using MinerU OCR engine.
 * POST /api/parse/file-vt
 *
 * **Atomic operation**: ONLY parses the file and returns the result
 * (markdown content, markdown_path, images_dir, etc.).
 *
 * Does NOT upload to KB, does NOT write YAML, does NOT index.
 * Callers should chain: parse → upload (POST /api/filesystem/upload) → index (POST /api/v1/search/index-document).
 */
export default defineEventHandler(async (event): Promise<ParsePDFVTResponse> => {
  try {
    const formData = await readMultipartFormData(event)
    if (!formData) {
      throw createError({ statusCode: 400, statusMessage: 'No form data provided' })
    }

    const fileField = formData.find(field => field.name === 'file')
    if (!fileField || !fileField.data) {
      throw createError({ statusCode: 400, statusMessage: 'File is required' })
    }

    const filename = fileField.filename || 'unknown.pdf'
    const SUPPORTED = ['.pdf', '.png', '.jpg', '.jpeg', '.docx', '.xlsx']
    const lower = filename.toLowerCase()
    if (!SUPPORTED.some(ext => lower.endsWith(ext)))
      throw createError({ statusCode: 400, statusMessage: 'Only PDF/PNG/JPG/DOCX/XLSX files are supported' })

    const outputDirField = formData.find(field => field.name === 'output_dir')
    const useOcrField = formData.find(field => field.name === 'use_ocr')

    const options = {
      output_dir: resolveTreeStorageOutputPath(outputDirField?.data?.toString()),
      use_ocr: useOcrField?.data?.toString() === 'true'
    }

    // 1. Call backend - parses, writes .md + images, returns paths
    //    (service back-fills `markdown` content from markdown_path).
    const pdfService = getPDFParseService()
    const result = await pdfService.parseFileVT(fileField.data, filename, options)

    return result
  } catch (error: any) {
    console.error('Parse error:', error)
    return { success: false, error: error.message || 'Parsing failed' }
  }
})
