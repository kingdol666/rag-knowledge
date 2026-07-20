import { defineEventHandler, getQuery, createError } from 'h3'
import { readFile } from 'fs/promises'
import { marked } from 'marked'
import { getTreeFileSystemService } from '~/server/utils/tree-service'
import {
  joinTreeStoragePath,
  toTreeStorageRelativePath,
} from '~/server/utils/runtime-paths'

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

  const isMarkdown =
    file.fileType?.toLowerCase() === 'md' ||
    file.fileType?.toLowerCase() === 'markdown' ||
    file.mimeType === 'text/markdown'

  if (!isMarkdown) {
    throw createError({
      statusCode: 400,
      statusMessage: 'File is not a markdown document',
    })
  }

  const filePath = joinTreeStoragePath(file.path)

  try {
    let content = await readFile(filePath, 'utf-8')

    // Rewrite image paths so they resolve to the file-preview endpoint.
    // Handles three realities of the parsed-doc storage:
    //  1. Absolute Windows paths (C:\...) → tree-storage-relative.
    //  2. Relative paths (images/xxx.jpg) → resolved against the md file's dir.
    //  3. Parse-pipeline subfolder layout: the markdown references a FLAT
    //     `images/<hash>.jpg` while the actual file often lives under a
    //     per-document subfolder `images/<docName>/<hash>.jpg`. We probe
    //     candidate paths on disk and pick the first that exists, so images
    //     actually render instead of 404'ing.
    const mdRelDir = (file.path || '')
      .replace(/\\/g, '/')
      .split('/')
      .slice(0, -1)
      .join('/')
    const docBasename = (file.name || '').replace(/\.(md|markdown)$/i, '')

    const { access } = await import('fs/promises')

    async function resolveImageRef(
      imagePath: string,
    ): Promise<string | null> {
      const cleaned = imagePath.trim().replace(/^["']|["']$/g, '')

      // Absolute Windows path -> tree-storage-relative
      if (/^[a-zA-Z]:[\\/]/.test(cleaned)) {
        const relativePath = toTreeStorageRelativePath(cleaned)
        return relativePath
          ? `/api/preview/file?path=${encodeURIComponent(relativePath)}`
          : null
      }

      // Skip URLs, data URIs, and already-rewritten preview URLs
      if (/^(https?:|data:|\/api\/)/.test(cleaned)) {
        return null
      }

      // Build candidate tree-storage-relative paths (POSIX-style)
      let base: string
      if (cleaned.startsWith('/')) {
        base = cleaned.replace(/^\/+/, '')
      } else {
        base = mdRelDir
          ? `${mdRelDir}/${cleaned}`.replace(/\/+/g, '/')
          : cleaned
      }

      const candidates = new Set<string>([base])
      // Fallback: parse pipeline stores images under images/<docName>/<file>.
      // Insert the doc basename before the filename when the flat path misses.
      if (docBasename) {
        const slash = base.lastIndexOf('/')
        const dirPart = slash >= 0 ? base.slice(0, slash) : ''
        const filePart = slash >= 0 ? base.slice(slash + 1) : base
        candidates.add(`${dirPart}/${docBasename}/${filePart}`.replace(/\/+/g, '/'))
      }

      for (const cand of candidates) {
        try {
          await access(joinTreeStoragePath(cand))
          return `/api/preview/file?path=${encodeURIComponent(cand)}`
        } catch {
          /* try next candidate */
        }
      }
      // Nothing on disk — keep the flat path so the alt text still renders
      return `/api/preview/file?path=${encodeURIComponent(base)}`
    }

    // Apply a set of (index, length, replacement) edits to `content` safely,
    // even when the same source string appears more than once.
    function applyRewrites(
      content: string,
      rewrites: { index: number; length: number; replacement: string }[],
    ): string {
      rewrites.sort((a, b) => b.index - a.index) // back-to-front keeps indices valid
      for (const r of rewrites) {
        content =
          content.slice(0, r.index) + r.replacement + content.slice(r.index + r.length)
      }
      return content
    }

    // Markdown image syntax: ![alt](src)
    const mdImgMatches = [...content.matchAll(/!\[([^\]]*)\]\(([^)]+)\)/g)]
    const mdImgUrls = await Promise.all(
      mdImgMatches.map((m) => resolveImageRef(m[2])),
    )
    content = applyRewrites(
      content,
      mdImgMatches
        .map((m, i) =>
          m.index !== undefined && mdImgUrls[i]
            ? { index: m.index, length: m[0].length, replacement: `![${m[1]}](${mdImgUrls[i]})` }
            : null,
        )
        .filter((r): r is { index: number; length: number; replacement: string } => !!r),
    )

    // Raw HTML <img src="..."> tags (robustness for non-standard markdown)
    const htmlImgMatches = [
      ...content.matchAll(/<img\s+([^>]*?)src=(["'])([^"']+)\2([^>]*?)\/?>/gi),
    ]
    const htmlImgUrls = await Promise.all(
      htmlImgMatches.map((m) => resolveImageRef(m[3])),
    )
    content = applyRewrites(
      content,
      htmlImgMatches
        .map((m, i) =>
          m.index !== undefined && htmlImgUrls[i]
            ? { index: m.index, length: m[0].length, replacement: `<img ${m[1]}src="${htmlImgUrls[i]}"${m[4]}/>` }
            : null,
        )
        .filter((r): r is { index: number; length: number; replacement: string } => !!r),
    )

    // Use the shared markdown engine (KaTeX math + GFM + breaks).
    // Falls back to plain marked.parse if the import fails (e.g. bundling issue).
    let htmlContent: string
    try {
      const { renderMarkdown } = await import('~/utils/markdown')
      htmlContent = renderMarkdown(content)
    } catch {
      htmlContent = await marked.parse(content, { gfm: true, breaks: true }) as string
      htmlContent = `<div class="markdown-body">${htmlContent}</div>`
    }

    event.node.res.setHeader('Content-Type', 'text/html; charset=utf-8')

    const html = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${file.name}</title>
  <!-- KaTeX: math formula rendering (CSS only; the HTML is pre-rendered server-side) -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.22/dist/katex.min.css" crossorigin="anonymous">
  <style>
    /* ═══ Standalone Markdown Preview — matches the app's "Warm Wisdom" design system ═══ */
    :root {
      --kb-bg: #f2ede8;
      --kb-bg-elevated: #faf7f4;
      --kb-bg-subtle: #eae3db;
      --kb-bg-code: #1e1a17;
      --kb-fg: #1c1815;
      --kb-fg-2: #4a423c;
      --kb-fg-3: #7a7168;
      --kb-fg-mute: #a69b90;
      --kb-border: #e2dad1;
      --kb-border-strong: #cfc4b8;
      --kb-primary: #b84724;
      --kb-primary-hover: #9e3818;
      --kb-primary-soft: #f6e7e0;
      --kb-cyan: #3a6b8f;
      --kb-emerald: #5a8f5a;
      --kb-amber: #c49a4a;
      --kb-rose: #b84a5a;
      --kb-rose-soft: #f5e6e8;
      --kb-shadow-sm: 0 1px 3px rgba(28,24,21,0.07), 0 1px 2px rgba(28,24,21,0.04);
      --kb-shadow-md: 0 4px 16px rgba(28,24,21,0.08), 0 1px 3px rgba(28,24,21,0.05);
      --kb-shadow-lg: 0 12px 32px rgba(28,24,21,0.11), 0 4px 12px rgba(28,24,21,0.06);
      --kb-font: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Noto Sans SC', 'Microsoft YaHei', sans-serif;
      --kb-font-mono: 'JetBrains Mono', 'Fira Code', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      --kb-ease-out: cubic-bezier(0.16, 1, 0.3, 1);
    }
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: var(--kb-font);
      -webkit-font-smoothing: antialiased;
      line-height: 1.78;
      color: var(--kb-fg-2);
      max-width: 920px;
      margin: 0 auto;
      padding: 48px 32px 80px;
      background: var(--kb-bg-elevated);
    }

    /* ── Header ── */
    .markdown-header {
      border-bottom: 2px solid var(--kb-border-strong);
      padding-bottom: 20px;
      margin-bottom: 36px;
    }
    .markdown-header h1 {
      font-size: 2em; font-weight: 800; color: var(--kb-fg);
      letter-spacing: -0.5px; line-height: 1.3;
    }
    .markdown-header h1::after {
      content: ''; display: block; width: 56px; height: 3px;
      background: linear-gradient(90deg, var(--kb-primary), transparent);
      margin-top: 12px; border-radius: 2px;
    }
    .markdown-meta {
      color: var(--kb-fg-3); font-size: 13px; margin-top: 14px;
      display: flex; gap: 16px; flex-wrap: wrap;
    }
    .markdown-meta span { display: inline-flex; align-items: center; gap: 5px; }

    /* ── Markdown body ── */
    .markdown-body { font-size: 16px; }

    /* Headings */
    .markdown-body h1,.markdown-body h2,.markdown-body h3,
    .markdown-body h4,.markdown-body h5,.markdown-body h6 {
      color: var(--kb-fg); margin: 28px 0 14px; font-weight: 700; line-height: 1.35;
      scroll-margin-top: 80px;
    }
    .markdown-body h1 { font-size: 1.75em; border-bottom: 2px solid var(--kb-border-strong); padding-bottom: 10px; }
    .markdown-body h2 {
      font-size: 1.42em; border-bottom: 1px solid var(--kb-border); padding-bottom: 7px; position: relative;
    }
    .markdown-body h2::before {
      content: ''; display: inline-block; width: 4px; height: 0.85em;
      background: var(--kb-primary); border-radius: 3px; margin-right: 9px; vertical-align: -0.05em;
    }
    .markdown-body h3 { font-size: 1.22em; }
    .markdown-body h3::before { content: '◆'; color: var(--kb-primary); font-size: 0.72em; margin-right: 8px; }
    .markdown-body h4 { font-size: 1.05em; color: var(--kb-fg-2); }
    .markdown-body h5 { font-size: 0.92em; color: var(--kb-fg-3); text-transform: uppercase; letter-spacing: 0.04em; }
    .markdown-body h6 { font-size: 0.85em; color: var(--kb-fg-mute); }

    /* Paragraphs & inline */
    .markdown-body p { margin: 14px 0; }
    .markdown-body a { color: var(--kb-primary); text-decoration: none; border-bottom: 1px solid transparent; transition: all 0.2s; }
    .markdown-body a:hover { color: var(--kb-primary-hover); border-bottom-color: var(--kb-primary); }
    .markdown-body strong { font-weight: 700; color: var(--kb-fg); }
    .markdown-body em { font-style: italic; }
    .markdown-body del, .markdown-body s { color: var(--kb-fg-mute); }
    .markdown-body mark { background: linear-gradient(180deg, transparent 55%, #f5ede0 55%); padding: 0 3px; border-radius: 2px; }

    /* Inline code */
    .markdown-body code {
      background: var(--kb-bg-subtle); padding: 2px 7px; border-radius: 5px;
      font-family: var(--kb-font-mono); font-size: 0.88em; color: var(--kb-primary);
      font-weight: 500; border: 1px solid var(--kb-border);
    }

    /* Code block wrapper + language label */
    .markdown-body .code-block-wrapper {
      position: relative; margin: 18px 0; border-radius: 10px; overflow: hidden;
      box-shadow: var(--kb-shadow-sm);
    }
    .markdown-body .code-block-wrapper .code-lang-label {
      position: absolute; top: 0; right: 0;
      font-family: var(--kb-font-mono); font-size: 10.5px; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.08em;
      color: #c8d3e0; background: rgba(255,255,255,0.07);
      padding: 4px 12px; border-radius: 0 10px 0 7px;
      z-index: 2; user-select: none; pointer-events: none; backdrop-filter: blur(6px);
    }
    .markdown-body .code-block-wrapper pre { margin: 0; border-radius: 10px; }

    /* Preformatted code blocks */
    .markdown-body pre {
      background: var(--kb-bg-code); color: #e6e1dc; padding: 20px 22px;
      border-radius: 10px; overflow-x: auto; font-size: 14px; line-height: 1.65;
      border: 1px solid rgba(255,255,255,0.06); font-family: var(--kb-font-mono);
    }
    .markdown-body pre code { background: transparent; padding: 0; color: inherit; font-size: inherit; border: none; }

    /* Highlight.js token colors — warm dark theme */
    .hljs { color: #e6e1dc; }
    .hljs-comment, .hljs-quote { color: #7c7268; font-style: italic; }
    .hljs-keyword, .hljs-selector-tag, .hljs-type { color: #e8907a; font-weight: 500; }
    .hljs-string, .hljs-addition { color: #b5d97f; }
    .hljs-number, .hljs-literal { color: #c8a3e6; }
    .hljs-title, .hljs-title.function_, .hljs-section, .hljs-name { color: #8ccae8; }
    .hljs-attribute, .hljs-variable, .hljs-template-variable { color: #e8c87a; }
    .hljs-built_in, .hljs-selector-class, .hljs-selector-id { color: #e8c87a; }
    .hljs-regexp { color: #f0a3a3; }
    .hljs-symbol, .hljs-bullet, .hljs-link { color: #8ccae8; }
    .hljs-meta, .hljs-meta .hljs-keyword { color: #8ccae8; font-weight: 500; }
    .hljs-tag { color: #e8907a; }
    .hljs-tag .hljs-name { color: #e8907a; font-weight: 500; }
    .hljs-tag .hljs-attr { color: #e8c87a; }
    .hljs-doctag { color: #e8907a; }
    .hljs-deletion { color: #f0a3a3; }
    .hljs-emphasis { font-style: italic; }
    .hljs-strong { font-weight: 700; }
    .hljs-params { color: #e6e1dc; }

    /* Blockquotes */
    .markdown-body blockquote {
      margin: 18px 0; padding: 12px 20px; color: var(--kb-fg-3);
      border-left: 3px solid var(--kb-primary);
      background: linear-gradient(135deg, rgba(184,71,36,0.04), rgba(184,71,36,0.01));
      border-radius: 0 10px 10px 0;
    }
    .markdown-body blockquote p:first-child { margin-top: 0; }
    .markdown-body blockquote p:last-child { margin-bottom: 0; }

    /* Lists */
    .markdown-body ul, .markdown-body ol { margin: 14px 0; padding-left: 28px; }
    .markdown-body ul { list-style: disc; }
    .markdown-body ol { list-style: decimal; }
    .markdown-body li { margin: 6px 0; }
    .markdown-body li::marker { color: var(--kb-primary); }
    .markdown-body li > ul, .markdown-body li > ol { margin: 6px 0; }
    .markdown-body .task-list-item { list-style-type: none; padding-left: 0; margin-left: -20px; }
    .markdown-body .task-list-item input[type="checkbox"] {
      margin: 0 7px 0 0; vertical-align: middle; width: 15px; height: 15px;
      accent-color: var(--kb-primary);
    }

    /* Tables */
    .markdown-body table {
      border-collapse: separate; border-spacing: 0; width: 100%; margin: 20px 0;
      display: block; overflow-x: auto; border-radius: 10px;
      border: 1px solid var(--kb-border); box-shadow: 0 1px 2px rgba(28,24,21,0.05);
      font-size: 14px;
    }
    .markdown-body thead { background: linear-gradient(180deg, var(--kb-bg-subtle), var(--kb-bg-elevated)); }
    .markdown-body th {
      font-weight: 700; text-align: left; color: var(--kb-fg);
      padding: 12px 16px; border-bottom: 2px solid var(--kb-border-strong); white-space: nowrap;
    }
    .markdown-body td { padding: 10px 16px; border-bottom: 1px solid var(--kb-border); color: var(--kb-fg-2); line-height: 1.55; }
    .markdown-body tr:last-child td { border-bottom: none; }
    .markdown-body tbody tr:nth-child(even) td { background: rgba(184,71,36,0.022); }
    .markdown-body tbody tr:hover td { background: rgba(184,71,36,0.06); }

    /* Images */
    .markdown-body img {
      max-width: 100%; height: auto; border-radius: 10px; margin: 14px 0;
      box-shadow: var(--kb-shadow-md);
      transition: transform 0.3s var(--kb-ease-out), box-shadow 0.3s var(--kb-ease-out);
    }
    .markdown-body img:hover { transform: scale(1.01); box-shadow: var(--kb-shadow-lg); }

    /* Horizontal rule */
    .markdown-body hr { border: none; height: 1px; background: linear-gradient(90deg, transparent, var(--kb-border-strong), transparent); margin: 32px 0; }

    /* Details / Summary */
    .markdown-body details {
      margin: 16px 0; padding: 14px 18px; background: var(--kb-bg);
      border: 1px solid var(--kb-border); border-radius: 10px; transition: border-color 0.2s;
    }
    .markdown-body details[open] { border-color: var(--kb-primary); }
    .markdown-body summary {
      font-weight: 600; cursor: pointer; color: var(--kb-fg);
      padding: 4px 0; user-select: none; list-style: none; position: relative; padding-left: 20px;
    }
    .markdown-body summary::-webkit-details-marker { display: none; }
    .markdown-body summary::before {
      content: '▶'; position: absolute; left: 0; font-size: 0.7em;
      color: var(--kb-primary); transition: transform 0.2s; top: 50%; transform: translateY(-50%);
    }
    .markdown-body details[open] summary::before { transform: translateY(-50%) rotate(90deg); }
    .markdown-body details[open] summary { margin-bottom: 10px; }

    /* Keyboard, abbreviation, sub/sup */
    .markdown-body kbd {
      font-family: var(--kb-font-mono); font-size: 0.85em; font-weight: 500;
      background: var(--kb-bg); border: 1px solid var(--kb-border-strong);
      border-bottom-width: 2px; border-radius: 5px; padding: 2px 7px; color: var(--kb-fg-2);
    }
    .markdown-body abbr[title] { border-bottom: 1px dotted var(--kb-fg-mute); cursor: help; text-decoration: none; }
    .markdown-body sub, .markdown-body sup { font-size: 0.78em; line-height: 0; }

    /* Footnotes */
    .markdown-body .footnotes { margin-top: 40px; padding-top: 18px; border-top: 1px solid var(--kb-border); font-size: 13px; color: var(--kb-fg-3); }
    .markdown-body .footnotes ol { padding-left: 22px; }

    /* KaTeX math */
    .markdown-body .math-inline { display: inline; }
    .markdown-body .math-inline .katex { font-size: 1.1em; }
    .markdown-body .math-block {
      display: block; overflow-x: auto; margin: 24px 0; padding: 20px 14px;
      text-align: center; background: var(--kb-bg); border: 1px solid var(--kb-border); border-radius: 10px;
    }
    .markdown-body .math-block .katex { font-size: 1.25em; }
    .markdown-body .math-block .katex-display { margin: 0; }
    .markdown-body .math-error { background: var(--kb-rose-soft); padding: 6px 12px; border-radius: 6px; color: var(--kb-rose); font-family: var(--kb-font-mono); }

    /* Mermaid diagrams */
    .markdown-body .mermaid,
    .markdown-body pre.mermaid,
    .markdown-body .mermaid-code-block,
    .markdown-body pre.mermaid-code-block {
      text-align: center; margin: 24px 0; padding: 20px;
      background: var(--kb-bg); border-radius: 10px;
      border: 1px solid var(--kb-border); overflow-x: auto; position: relative;
    }
    .markdown-body .mermaid-code-block code.language-mermaid {
      background: transparent; font-family: var(--kb-font-mono); font-size: 13px; color: var(--kb-fg-3); border: none;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--kb-border-strong); border-radius: 999px; border: 2px solid transparent; background-clip: content-box; }
    ::-webkit-scrollbar-thumb:hover { background: var(--kb-fg-mute); background-clip: content-box; }
    ::selection { background: var(--kb-primary-soft); color: var(--kb-primary-hover); }

    /* Print */
    @media print {
      body { max-width: none; padding: 0; background: #fff; }
      .markdown-body pre, .markdown-body blockquote, .markdown-body table { page-break-inside: avoid; }
    }

    /* Responsive */
    @media (max-width: 640px) {
      body { padding: 24px 16px 60px; }
      .markdown-body { font-size: 14.5px; }
      .markdown-body pre { padding: 14px; font-size: 12.5px; }
    }
  </style>
</head>
<body>
  <div class="markdown-header">
    <h1>${file.name}</h1>
    <div class="markdown-meta">
      <span>📄 文件大小: ${formatFileSize(file.fileSize)}</span>
      <span>🕐 更新时间: ${new Date(file.updatedAt).toLocaleString('zh-CN')}</span>
    </div>
  </div>
  <div class="markdown-body">
    ${htmlContent}
  </div>
  <!-- Mermaid: diagram rendering (only loads if mermaid blocks are present) -->
  <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js" crossorigin="anonymous"><\/script>
  <script>
    (function () {
      function processMermaid() {
        var blocks = document.querySelectorAll('pre.mermaid-code-block code.language-mermaid, pre code.language-mermaid, .mermaid');
        if (!blocks.length) return;
        try {
          mermaid.initialize({
            startOnLoad: false,
            theme: 'default',
            securityLevel: 'loose',
            themeVariables: {
              primaryColor: '#b84724',
              primaryBorderColor: '#9e3818',
              primaryTextColor: '#1c1815',
              lineColor: '#4a423c',
              textColor: '#1c1815',
              secondaryColor: '#f2ede8',
              tertiaryColor: '#eae3db'
            }
          });
          var idx = 0;
          blocks.forEach(function (block) {
            var code = block.textContent || '';
            if (!code.trim()) return;
            var parent = block.closest('pre') || block.parentElement;
            if (!parent) return;
            var id = 'mmd-' + (idx++);
            mermaid.render(id, code).then(function (res) {
              var wrapper = document.createElement('div');
              wrapper.className = 'mermaid-rendered';
              wrapper.innerHTML = res.svg;
              parent.replaceWith(wrapper);
            }).catch(function (err) {
              console.warn('Mermaid render error:', err);
              var badge = document.createElement('div');
              badge.className = 'mermaid-error-badge';
              badge.textContent = '⚠ 图表渲染错误';
              badge.title = String(err && err.message || err);
              parent.style.position = 'relative';
              parent.insertBefore(badge, parent.firstChild);
            });
          });
        } catch (e) {
          console.warn('Mermaid init failed:', e);
        }
      }
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', processMermaid);
      } else {
        processMermaid();
      }
    })();
  <\/script>
</body>
</html>
    `

    return html
  } catch (error) {
    console.error('Error reading markdown:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to read markdown file',
    })
  }
})

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
