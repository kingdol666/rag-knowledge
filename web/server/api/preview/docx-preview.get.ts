import { defineEventHandler, getQuery, createError } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'
import { readFile } from 'fs/promises'
import mammoth from 'mammoth'
import { resolveSafePath } from '~/server/utils/safe-paths'

/** Escape a user-controlled string for safe interpolation into HTML text/attribute context.
 * Guards preview templates against stored XSS via crafted filenames. */
function escapeHtml(value: unknown): string {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const fileId = query.id as string

  if (!fileId) {
    throw createError({ statusCode: 400, statusMessage: 'File ID is required' })
  }

  const treeService = await getTreeFileSystemService()
  await treeService.reloadMetadata()

  const file = await treeService.getFileById(fileId)

  if (!file) {
    throw createError({ statusCode: 404, statusMessage: 'File not found' })
  }

  // Check whether it's a docx file
  const isDocx = file.fileType?.toLowerCase() === 'docx' ||
    file.mimeType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

  if (!isDocx) {
    throw createError({ statusCode: 400, statusMessage: 'File is not a docx document' })
  }

  const filePath = resolveSafePath(file.path)

  try {
    const buffer = await readFile(filePath)

    // Use mammoth to convert docx to HTML
    const result = await mammoth.convertToHtml({ buffer }, {
      styleMap: [
        "p[style-name='Heading 1'] => h1",
        "p[style-name='Heading 2'] => h2",
        "p[style-name='Heading 3'] => h3",
        "p[style-name='Heading 4'] => h4",
        "p[style-name='Heading 5'] => h5",
        "p[style-name='Heading 6'] => h6",
      ]
    })

    // Return HTML content
    event.node.res.setHeader('Content-Type', 'text/html; charset=utf-8')

    const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(file.name)}</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      line-height: 1.6;
      color: #333;
      max-width: 800px;
      margin: 0 auto;
      padding: 40px 20px;
      background: #fff;
    }
    h1, h2, h3, h4, h5, h6 {
      color: #1a1a1a;
      margin-top: 24px;
      margin-bottom: 16px;
    }
    h1 { font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: 10px; }
    h2 { font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 8px; }
    h3 { font-size: 1.25em; }
    p { margin-bottom: 16px; }
    table {
      border-collapse: collapse;
      width: 100%;
      margin-bottom: 16px;
    }
    th, td {
      border: 1px solid #dfe2e5;
      padding: 8px 12px;
      text-align: left;
    }
    th {
      background-color: #f6f8fa;
      font-weight: 600;
    }
    ul, ol {
      margin-bottom: 16px;
      padding-left: 2em;
    }
    li {
      margin-bottom: 4px;
    }
    blockquote {
      margin: 0 0 16px 0;
      padding: 0 16px;
      color: #6a737d;
      border-left: 4px solid #dfe2e5;
    }
    code {
      background-color: rgba(27, 31, 35, 0.05);
      padding: 2px 6px;
      border-radius: 3px;
      font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
      font-size: 85%;
    }
    pre {
      background-color: #f6f8fa;
      padding: 16px;
      overflow: auto;
      border-radius: 6px;
      margin-bottom: 16px;
    }
    pre code {
      background-color: transparent;
      padding: 0;
    }
    img {
      max-width: 100%;
      height: auto;
    }
    a {
      color: #0366d6;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    .docx-header {
      border-bottom: 2px solid #e1e4e8;
      padding-bottom: 16px;
      margin-bottom: 24px;
    }
    .docx-header h1 {
      margin: 0;
      border: none;
      padding: 0;
    }
    .docx-meta {
      color: #586069;
      font-size: 14px;
      margin-top: 8px;
    }
  </style>
</head>
<body>
  <div class="docx-header">
    <h1>${escapeHtml(file.name)}</h1>
    <div class="docx-meta">
      文件大小: ${formatFileSize(file.fileSize)} | 更新时间: ${new Date(file.updatedAt).toLocaleString('zh-CN')}
    </div>
  </div>
  <div class="docx-content">
    ${result.value}
  </div>
</body>
</html>
    `

    return html
  } catch (error) {
    console.error('Error converting docx:', error)
    throw createError({ statusCode: 500, statusMessage: 'Failed to convert docx file' })
  }
})

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
