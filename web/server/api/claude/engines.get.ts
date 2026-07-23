/**
 * GET /api/claude/engines
 *
 * Reports which chat engines are available in this deployment.
 *   - Claude: the @anthropic-ai/claude-agent-sdk npm package is resolvable
 *     (runs in-process).
 *   - OMP: the `omp` CLI binary is on PATH (or resolvable as
 *     @oh-my-pi/pi-coding-agent's bundled cli.js). OMP runs as a child process
 *     via the `omp --mode rpc` JSONL protocol.
 *
 * Response: { engines: { claude: { available }, omp: { available } } }
 */
import { createRequire } from 'module'
import { execFileSync } from 'child_process'

const require = createRequire(import.meta.url)

function isResolvable(spec: string): boolean {
  try {
    require.resolve(spec)
    return true
  } catch {
    return false
  }
}

/** Is the `omp` CLI available — either on PATH or as the bundled cli.js? */
function isOmpAvailable(): boolean {
  // 1) Try resolving the bundled CLI from the (optional) pi-coding-agent pkg.
  try {
    const cliPath = require.resolve('@oh-my-pi/pi-coding-agent/dist/cli.js')
    if (cliPath) return true
  } catch { /* package not installed — fall through */ }
  // 2) Try the bare `omp` binary on PATH.
  try {
    const cmd = process.platform === 'win32' ? 'where' : 'which'
    execFileSync(cmd, ['omp'], { stdio: 'ignore' })
    return true
  } catch {
    return false
  }
}

export default defineEventHandler(() => {
  return {
    engines: {
      claude: { available: isResolvable('@anthropic-ai/claude-agent-sdk') },
      omp: { available: isOmpAvailable() },
    },
  }
})
