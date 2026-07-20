import type {
  ParsePDFVTResponse,
  BatchParsePDFFileVTResponse,
  ParsePDFVTOptions,
  BatchParsePDFVTOptions,
  BatchParsePDFFileVTItem,
  BatchParsePDFFileVTItemWithDescription,
  SaveParsedFilesResponse,
} from '~/types/pdf-parse'

function normalizeDescription(value?: string | null): string | undefined {
  const text = value?.trim()
  return text ? text : undefined
}

function stripMarkdown(markdown: string): string {
  return markdown
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '$1')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/[*_~>-]+/g, ' ')
    .replace(/\|/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function buildFallbackDescription(markdown?: string): string | undefined {
  const plainText = stripMarkdown(markdown || '')
  if (!plainText) {
    return undefined
  }
  const maxChars = 160
  return plainText.length <= maxChars
    ? plainText
    : `${plainText.slice(0, maxChars).trim()}...`
}

/**
 * PDF Parser Composable
 * Frontend interface for PDF parsing API.
 *
 * NOTE: AI-generated content briefs were removed; descriptions now fall
 * back to a plain-text excerpt of the parsed markdown. AI enrichment is
 * handled externally by the agent harness via MCP.
 */
export function usePDFParser() {
  async function enrichParsedResultsWithDescriptions(
    results: BatchParsePDFFileVTItem[],
    customDescriptions: string[] = []
  ): Promise<BatchParsePDFFileVTItemWithDescription[]> {
    const enrichedResults: BatchParsePDFFileVTItemWithDescription[] = []

    for (const [index, item] of results.entries()) {
      const manualDescription = normalizeDescription(customDescriptions[index])

      if (!item.success) {
        enrichedResults.push({
          ...item,
          description: manualDescription
        })
        continue
      }

      const description = manualDescription || buildFallbackDescription(item.markdown)
      enrichedResults.push({
        ...item,
        description
      })
    }

    return enrichedResults
  }

  async function saveParsedFiles(
    parentId: string,
    results: BatchParsePDFFileVTItem[],
    customDescriptions: string[] = []
  ): Promise<SaveParsedFilesResponse> {
    if (!parentId) {
      throw new Error('parentId is required')
    }

    const resultsWithDescription = await enrichParsedResultsWithDescriptions(
      results,
      customDescriptions
    )

    const response = await fetch('/api/parse/save-parsed-files', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        parentId,
        results: resultsWithDescription
      })
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Save parsed files failed: ${error}`)
    }

    return await response.json() as SaveParsedFilesResponse
  }

  /**
   * Parse a single PDF file using VT mode
   */
  async function parseFileVT(
    file: File,
    options?: ParsePDFVTOptions
  ): Promise<ParsePDFVTResponse> {
    const formData = new FormData()
    formData.append('file', file)

    if (options?.output_dir) {
      formData.append('output_dir', options.output_dir)
    }
    if (options?.use_ocr !== undefined) {
      formData.append('use_ocr', String(options.use_ocr))
    }
    if (options?.parent_id) {
      formData.append('parent_id', options.parent_id)
    }

    const response = await fetch('/api/parse/file-vt', {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Parse failed: ${error}`)
    }

    return await response.json()
  }

  /**
   * Batch parse multiple PDF files using VT mode
   */
  async function batchParseFilesVT(
    files: File[],
    options?: Omit<BatchParsePDFVTOptions, 'files'>
  ): Promise<BatchParsePDFFileVTResponse> {
    const formData = new FormData()

    for (const file of files) {
      formData.append('files', file)
    }

    if (options?.output_dir) {
      formData.append('output_dir', options.output_dir)
    }
    if (options?.use_ocr !== undefined) {
      formData.append('use_ocr', String(options.use_ocr))
    }
    if (options?.parent_id) {
      formData.append('parent_id', options.parent_id)
    }

    const response = await fetch('/api/parse/batch-file-vt', {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Batch parse failed: ${error}`)
    }

    return await response.json()
  }

  /**
   * Batch parse multiple PDF files using VT mode with streaming progress
   */
  function batchParseFilesVTStream(
    files: File[],
    options?: Omit<BatchParsePDFVTOptions, 'files'>
  ): {
    eventSource: EventSource | null
    onProgress: (callback: (data: any) => void) => void
    onComplete: (callback: (summary: any) => void) => void
    onError: (callback: (error: string) => void) => void
    close: () => void
  } {
    const formData = new FormData()

    for (const file of files) {
      formData.append('files', file)
    }

    if (options?.output_dir) {
      formData.append('output_dir', options.output_dir)
    }
    if (options?.use_ocr !== undefined) {
      formData.append('use_ocr', String(options.use_ocr))
    }
    if (options?.parent_id) {
      formData.append('parent_id', options.parent_id)
    }

    let progressCallback: ((data: any) => void) | null = null
    let completeCallback: ((summary: any) => void) | null = null
    let errorCallback: ((error: string) => void) | null = null

    const controller = new AbortController()

    const startStreaming = async () => {
      try {
        const response = await fetch('/api/parse/batch-file-vt-stream', {
          method: 'POST',
          body: formData,
          signal: controller.signal
        })

        if (!response.ok || !response.body) {
          throw new Error('Failed to start streaming')
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))

                if (data.type === 'error' && errorCallback) {
                  errorCallback(data.message)
                } else if (data.type === 'progress' && progressCallback) {
                  progressCallback(data)
                } else if (data.type === 'complete' && completeCallback) {
                  completeCallback(data.summary)
                }
              } catch (e) {
                console.error('Failed to parse SSE data:', e)
              }
            }
          }
        }
      } catch (error: any) {
        if (error.name !== 'AbortError' && errorCallback) {
          errorCallback(error.message)
        }
      }
    }

    startStreaming()

    return {
      eventSource: null,
      onProgress: (cb: (data: any) => void) => { progressCallback = cb },
      onComplete: (cb: (summary: any) => void) => { completeCallback = cb },
      onError: (cb: (error: string) => void) => { errorCallback = cb },
      close: () => controller.abort()
    }
  }

  return {
    enrichParsedResultsWithDescriptions,
    parseFileVT,
    batchParseFilesVT,
    batchParseFilesVTStream,
    saveParsedFiles
  }
}