/**
 * Shared Markdown Rendering Engine v3
 * ─────────────────────────────────────────────
 * Configures marked with:
 *  - Full GFM (tables, task-lists, strikethrough, autolinks)
 *  - Syntax highlighting via highlight.js (custom code renderer)
 *  - KaTeX math ($...$ / $$...$$)
 *  - Mermaid diagram blocks (```mermaid)
 *  - Code block language labels (badge)
 *
 * Used by:
 *  - server/api/preview/markdown-preview.get.ts   (server-side iframe)
 *  - pages/claude-chat.vue                        (chat messages)
 *  - pages/knowledge-base.vue                     (preview drawer fallback)
 */

import { marked } from 'marked'
import hljs from 'highlight.js/lib/common'
import katex from 'katex'

// ── Helpers ────────────────────────────────────────────────
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/** Highlight code with highlight.js; auto-detects if language is unknown. */
function highlightCode(code: string, lang?: string): string {
  if (lang && hljs.getLanguage(lang)) {
    try {
      return hljs.highlight(code, { language: lang }).value
    } catch {
      // fall through
    }
  }
  try {
    return hljs.highlightAuto(code).value
  } catch {
    return escapeHtml(code)
  }
}

// ── KaTeX Math Extension ──────────────────────────────────
// Processes inline $...$ and block $$...$$ delimiters.
// Uses a tokenizer + renderer pair so marked does NOT parse
// delimiter-looking characters inside code spans / fenced code.
const mathExtension: marked.MarkedExtension = {
  extensions: [
    {
      name: 'math',
      level: 'inline',
      start(src: string) {
        return src.indexOf('$')
      },
      tokenizer(this: any, src: string) {
        const blockMatch = src.match(/^\$\$([\s\S]+?)\$\$/)
        if (blockMatch) {
          return {
            type: 'math',
            raw: blockMatch[0],
            text: blockMatch[1].trim(),
            display: true,
          }
        }
        const inlineMatch = src.match(/^\$([^\$\n]+?)\$/)
        if (inlineMatch) {
          return {
            type: 'math',
            raw: inlineMatch[0],
            text: inlineMatch[1].trim(),
            display: false,
          }
        }
        return undefined
      },
      renderer(this: any, token: any) {
        try {
          const html = katex.renderToString(token.text, {
            displayMode: token.display,
            throwOnError: false,
            trust: true,
          })
          return token.display
            ? `<div class="math-block">${html}</div>`
            : `<span class="math-inline">${html}</span>`
        } catch {
          return token.display
            ? `<div class="math-block math-error">$$${token.text}$$</div>`
            : `<span class="math-inline math-error">$${token.text}$</span>`
        }
      },
    },
  ],
}

// ── Enhanced Code Block Renderer ───────────────────────────
// Highlights code with highlight.js, adds a language label badge,
// and handles Mermaid diagram blocks specially.
const codeBlockExtension: marked.MarkedExtension = {
  renderer: {
    code(this: any, token: any) {
      const lang = (token.lang || '').trim()
      const codeText = token.text || ''

      // Mermaid blocks: output raw code for Mermaid.js to process client-side.
      // The composable (useMarkdownRenderer) or iframe script replaces these with SVGs.
      if (lang === 'mermaid') {
        return `<pre class="mermaid-code-block"><code class="language-mermaid">${escapeHtml(codeText)}</code></pre>`
      }

      // Highlight the code
      const highlighted = highlightCode(codeText, lang || undefined)
      const langLabel = lang
        ? `<span class="code-lang-label">${escapeHtml(lang)}</span>`
        : ''
      const langClass = lang ? ` language-${escapeHtml(lang)}` : ''

      return `<div class="code-block-wrapper">${langLabel}<pre data-lang="${escapeHtml(lang || '')}"><code class="hljs${langClass}">${highlighted}</code></pre></div>`
    },
    // ── Task list support: add the `task-list-item` class to <li> with checkboxes ──
    // marked v17 does not emit this class by default; we add it for CSS compatibility.
    listitem(this: any, token: any) {
      const isTask = !!token.task
      const checked = !!token.checked
      // token.text already contains the rendered inner HTML (from sub-tokens)
      let inner = token.text || ''
      if (isTask) {
        // Remove the auto-generated checkbox from the text (marked embeds it)
        inner = inner.replace(/^<input[^>]*>\s*/, '')
        const checkbox = `<input type="checkbox" disabled${checked ? ' checked' : ''} class="task-list-checkbox">`
        return `<li class="task-list-item">${checkbox}${inner}</li>\n`
      }
      return `<li>${inner}</li>\n`
    },
  },
}

// ── Apply Configuration & Extensions ──────────────────────
marked.use({ gfm: true, breaks: true })
marked.use(mathExtension)
marked.use(codeBlockExtension)

// ── Public API ─────────────────────────────────────────────

/**
 * Render a markdown string to HTML.
 * Wraps in a `.markdown-body` div for consistent styling.
 */
export function renderMarkdown(md: string): string {
  if (!md) return ''
  try {
    const rendered = marked.parse(md.replace(/\r\n/g, '\n'), {
      gfm: true,
      breaks: true,
    }) as string
    return `<div class="markdown-body">${rendered}</div>`
  } catch {
    return md
  }
}

/**
 * Raw parse — returns the HTML string without wrapping.
 * Used when the caller already provides its own wrapper (e.g. chat messages).
 */
export function parseMarkdown(md: string): string {
  if (!md) return ''
  try {
    return marked.parse(md.replace(/\r\n/g, '\n'), {
      gfm: true,
      breaks: true,
    }) as string
  } catch {
    return md
  }
}

export { marked, katex, hljs }