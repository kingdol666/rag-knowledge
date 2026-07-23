/**
 * Terminal composable — manages an xterm.js instance connected to the
 * /api/claude/terminal WebSocket PTY endpoint.
 *
 * Lifecycle:
 *   const term = useTerminal(containerEl, cwd)
 *   term.open()      → create Terminal + addons, attach to container, connect WS
 *   term.resize()    → manual resize (also auto-handled by FitAddon)
 *   term.setCwd(p)   → reconnect at a new working directory
 *   term.dispose()   → close WS + terminal
 *
 * The shell's native cwd is controlled at spawn time (server-side). To change
 * directory, we tear down and reconnect the socket with the new cwd — simpler
 * and more reliable than trying to `cd` inside an unknown shell.
 */
import { ref, type Ref } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import '@xterm/xterm/css/xterm.css'

export interface TerminalHandle {
  readonly terminal: Terminal | null
  readonly connected: Ref<boolean>
  readonly cwd: Ref<string>
  open(container: HTMLElement): void
  setCwd(cwd: string): void
  focus(): void
  dispose(): void
}

export function useTerminal(initialCwd?: string): TerminalHandle {
  const connected = ref(false)
  const cwd = ref(initialCwd || '')
  let terminal: Terminal | null = null
  let fitAddon: FitAddon | null = null
  let containerEl: HTMLElement | null = null
  let socket: WebSocket | null = null
  let disposed = false

  /** Build the WS URL for a given cwd. */
  function wsUrl(targetCwd: string): string {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const param = targetCwd ? `?cwd=${encodeURIComponent(targetCwd)}` : ''
    return `${proto}//${location.host}/api/claude/terminal${param}`
  }

  /** (Re)connect the socket; wires PTY output → terminal and vice-versa. */
  function connect(targetCwd: string): void {
    if (disposed || !terminal) return
    // Tear down any existing socket first.
    if (socket) {
      try { socket.onmessage = null; socket.onclose = null; socket.onerror = null; socket.close() } catch { /* noop */ }
      socket = null
    }
    connected.value = false

    socket = new WebSocket(wsUrl(targetCwd))
    socket.onopen = () => {
      connected.value = true
    }
    socket.onmessage = (ev) => {
      if (!terminal) return
      let payload: { type?: string; data?: string; exitCode?: number; message?: string; cwd?: string; shell?: string }
      try {
        payload = JSON.parse(ev.data)
      } catch {
        return
      }
      switch (payload.type) {
        case 'output':
          if (payload.data) terminal.write(payload.data)
          break
        case 'exit':
          connected.value = false
          if (payload.data) terminal.write(`\r\n\x1b[90m[process exited with code ${payload.exitCode}]\x1b[0m\r\n`)
          break
        case 'error':
          if (payload.message) terminal.write(`\r\n\x1b[31m${payload.message}\x1b[0m\r\n`)
          connected.value = false
          break
        case 'ready':
          // Server confirmed the shell + cwd; nothing to render.
          break
      }
    }
    socket.onclose = () => {
      connected.value = false
    }
    socket.onerror = () => {
      connected.value = false
    }

    // Forward keystrokes → PTY.
    terminal.onData((data: string) => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'input', data }))
      }
    })
  }

  /** Resize handler — debounced via rAF by FitAddon; forward to server. */
  function sendResize(cols: number, rows: number): void {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'resize', cols, rows }))
    }
  }

  function open(container: HTMLElement): void {
    if (disposed) return
    containerEl = container
    terminal = new Terminal({
      cursorBlink: true,
      fontSize: 13,
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace",
      theme: {
        background: '#0d1117',
        foreground: '#c9d1d9',
        cursor: '#58a6ff',
        cursorAccent: '#0d1117',
        selectionBackground: 'rgba(99, 102, 241, 0.35)',
        black: '#484f58',
        red: '#ff7b72',
        green: '#3fb950',
        yellow: '#d29922',
        blue: '#58a6ff',
        magenta: '#bc8cff',
        cyan: '#39c5cf',
        white: '#b1bac4',
        brightBlack: '#6e7681',
        brightRed: '#ffa198',
        brightGreen: '#56d364',
        brightYellow: '#e3b341',
        brightBlue: '#79c0ff',
        brightMagenta: '#d2a8ff',
        brightCyan: '#56d4dd',
        brightWhite: '#f0f6fc',
      },
      allowProposedApi: true,
    })
    fitAddon = new FitAddon()
    terminal.loadAddon(fitAddon)
    terminal.loadAddon(new WebLinksAddon())
    terminal.open(container)
    try { fitAddon.fit() } catch { /* container not yet sized */ }

    // Forward resizes (both initial and on container resize).
    terminal.onResize(({ cols, rows }) => sendResize(cols, rows))
    sendResize(terminal.cols, terminal.rows)

    // Re-fit on window resize.
    const onWinResize = () => { if (fitAddon && !disposed) { try { fitAddon.fit() } catch { /* noop */ } } }
    window.addEventListener('resize', onWinResize)
    ;(terminal as any).__onWinResize = onWinResize

    connect(cwd.value)
  }

  function setCwd(newCwd: string): void {
    cwd.value = newCwd
    if (terminal && containerEl) {
      // Clear screen + reconnect at the new cwd.
      terminal.reset()
      connect(newCwd)
    }
  }

  function focus(): void {
    terminal?.focus()
  }

  function dispose(): void {
    disposed = true
    const onWinResize = terminal ? (terminal as any).__onWinResize as (() => void) | undefined : undefined
    if (onWinResize) window.removeEventListener('resize', onWinResize)
    if (socket) {
      try { socket.onmessage = null; socket.onclose = null; socket.onerror = null; socket.close() } catch { /* noop */ }
      socket = null
    }
    if (fitAddon) { try { fitAddon.dispose() } catch { /* noop */ } fitAddon = null }
    if (terminal) { try { terminal.dispose() } catch { /* noop */ } terminal = null }
    containerEl = null
    connected.value = false
  }

  return {
    get terminal() { return terminal },
    connected,
    cwd,
    open,
    setCwd,
    focus,
    dispose,
  }
}
