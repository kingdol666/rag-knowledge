import { defineEventHandler, readMultipartFormData, createError } from 'h3'
import { getPDFParseService } from '~/server/services/pdf-parse-service'
import { resolveTreeStorageOutputPath } from '~/server/utils/runtime-paths'
import type { BatchParsePDFFileVTResponse } from '~/types/pdf-parse'

/**
 * POST /api/parse/batch-file-vt
 *
 * **Atomic operation**: ONLY batch parses files and returns results
 * (markdown content, markdown_path, images_dir, etc. for each file).
 *
 * Does NOT upload to KB, does NOT write YAML, does NOT index, does NOT copy images.
 * Callers should chain: batch-parse → save (POST /api/parse/save-parsed-files) → index.
 */
export default defineEventHandler(async (event): Promise<BatchParsePDFFileVTResponse> => {
  try {
    const formData = await readMultipartFormData(event)
    if (!formData) {
      throw createError({ statusCode: 400, statusMessage: 'No form data provided' })
    }

    const fileFields = formData.filter(field => field.name === 'files')
    if (fileFields.length === 0) {
      throw createError({ statusCode: 400, statusMessage: 'At least one file is required' })
    }

    const files: Array<{ buffer: Buffer; filename: string }> = []
    for (const field of fileFields) {
      if (!field.data) continue
      const filename = field.filename || 'unknown.pdf'
      const SUPPORTED = ['.pdf', '.png', '.jpg', '.jpeg', '.docx', '.xlsx']
      const lower = filename.toLowerCase()
      if (!SUPPORTED.some(ext => lower.endsWith(ext)))
        throw createError({ statusCode: 400, statusMessage: 'Unsupported format: ' + filename })
      files.push({ buffer: field.data, filename })
    }
    if (files.length === 0) {
      throw createError({ statusCode: 400, statusMessage: 'No valid files provided' })
    }

    const outputDirField = formData.find(field => field.name === 'output_dir')
    const useOcrField = formData.find(field => field.name === 'use_ocr')

    const options = {
      output_dir: resolveTreeStorageOutputPath(outputDirField?.data?.toString()),
      use_ocr: useOcrField?.data?.toString() === 'true'
    }

    const pdfService = getPDFParseService()
    const result = await pdfService.batchParseFilesVT(files, options)

    return result
  } catch (error: any) {
    console.error('Batch parse error:', error)
    return {
      success: false,
      total_files: 0,
      successful_files: 0,
      failed_files: 0,
      results: [],
      error: error.message || 'Batch parsing failed'
    }
  }
})
