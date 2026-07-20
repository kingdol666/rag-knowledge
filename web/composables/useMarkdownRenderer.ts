/**
 * useMarkdownRenderer — Client-Side Mermaid Diagram Initialization
 * ─────────────────────────────────────────────────────────────
 * Lazily loads Mermaid.js and initializes diagram blocks after
 * markdown content has been rendered into the DOM.
 *
 * Usage:
 *   const { initMermaid } = useMarkdownRenderer()
 *   await initMermaid(containerEl)  // scans for .language-mermaid blocks
 */

let mermaidModule: any = null
let mermaidLoading: Promise<any> | null = null

async function loadMermaid(): Promise<any> {
  if (mermaidModule) return mermaidModule
  if (mermaidLoading) return mermaidLoading

  mermaidLoading = import('mermaid').then((mod) => {
    mermaidModule = mod.default
    mermaidModule.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'loose',
      // Custom theme colors to match the warm aesthetic
      themeVariables: {
        primaryColor: '#b84724',
        primaryBorderColor: '#9e3818',
        primaryTextColor: '#1c1815',
        secondaryColor: '#f2ede8',
        tertiaryColor: '#eae3db',
        lineColor: '#4a423c',
        textColor: '#1c1815',
      },
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis',
      },
      sequence: {
        useMaxWidth: true,
        actorMargin: 50,
        messageMargin: 40,
      },
      gantt: {
        useMaxWidth: true,
      },
    })
    return mermaidModule
  }).catch((err) => {
    mermaidLoading = null
    console.warn('Failed to load Mermaid.js:', err)
    throw err
  })

  return mermaidLoading
}

export function useMarkdownRenderer() {
  /**
   * Scan a container element for Mermaid code blocks and render them as diagrams.
   * Safe to call multiple times — already-rendered blocks are skipped.
   *
   * @param container - A DOM element or CSS selector string
   * @returns The number of diagrams rendered (or -1 if Mermaid failed to load)
   */
  async function initMermaid(container: Element | string): Promise<number> {
    const el: Element | null =
      typeof container === 'string'
        ? document.querySelector(container)
        : container

    if (!el) {
      console.debug('useMarkdownRenderer: container not found')
      return 0
    }

    // Find unprocessed mermaid blocks
    const blocks = el.querySelectorAll<HTMLElement>(
      'pre code.language-mermaid:not([data-mermaid-processed]), ' +
      'pre.mermaid:not([data-mermaid-processed]), ' +
      '.mermaid-code-block code.language-mermaid:not([data-mermaid-processed])',
    )

    if (!blocks.length) return 0

    try {
      const mermaid = await loadMermaid()

      let count = 0
      for (const block of Array.from(blocks)) {
        try {
          const parent = block.closest('pre') || block.parentElement
          if (!parent) continue

          const code = block.textContent || ''
          if (!code.trim()) continue

          // Generate a unique ID for this diagram
          const id = `mermaid-${Math.random().toString(36).slice(2, 10)}`

          // Render the diagram
          const { svg } = await mermaid.render(id, code)

          // Replace the parent <pre> with the SVG
          const wrapper = document.createElement('div')
          wrapper.className = 'mermaid-rendered'
          wrapper.innerHTML = svg

          // Mark as processed
          block.setAttribute('data-mermaid-processed', 'true')

          parent.replaceWith(wrapper)
          count++
        } catch (renderErr: any) {
          console.warn('Mermaid render error for block:', renderErr)
          // Mark as errored so we don't retry
          block.setAttribute('data-mermaid-processed', 'error')
          block.setAttribute('data-mermaid-error', String(renderErr?.message || renderErr))

          // Add error indicator
          const errorDiv = document.createElement('div')
          errorDiv.className = 'mermaid-error-badge'
          errorDiv.textContent = '⚠ Diagram render error'
          errorDiv.title = String(renderErr?.message || '')
          const pre = block.closest('pre')
          if (pre) {
            pre.style.position = 'relative'
            pre.insertBefore(errorDiv, pre.firstChild)
          }
        }
      }

      return count
    } catch (err) {
      console.warn('useMarkdownRenderer: Mermaid not available:', err)
      return -1
    }
  }

  /** Check if Mermaid is available (has been loaded). */
  function isMermaidReady(): boolean {
    return mermaidModule !== null
  }

  return { initMermaid, isMermaidReady }
}