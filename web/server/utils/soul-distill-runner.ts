/**
 * soul-distill-runner.ts — 补天蒸馏执行器(共享)
 *
 * 供 /api/soul/distill-nuwa 与 /api/soul/distill-seed 复用:
 *   1. 在临时目录组装种子包(meta.json + persona.md + work.md [+ values.md])
 *   2. 调 ragctl soul distill 落地(建库 + 4 宪法文档 + bootstrap + 索引)
 *
 * 与 CLI/后端三入口同源: ragctl 是唯一编排实现, 此处不复制逻辑。
 */
import { execFile } from 'child_process'
import { promisify } from 'util'
import { access } from 'fs/promises'
import { join } from 'path'
import { getProjectRoot } from '~/server/utils/claude-config'

const execFileAsync = promisify(execFile)

export interface RagctlDistillOptions {
  name: string
  kbScope?: string[]
  domainLabels?: string[]
  harness?: string
}

export interface DistillRunResult {
  success: boolean
  name: string
  stdout: string
  stderr: string
}

/** 调 ragctl soul distill <seedDir> [--name] [--scope] [--labels] [--values] [--harness] */
export async function runRagctlDistill(seedDir: string, opts: RagctlDistillOptions): Promise<DistillRunResult> {
  const root = getProjectRoot()
  const ragctl = join(root, 'command', 'ragctl.js')
  const args = ['soul', 'distill', seedDir, '--name', opts.name]
  if (opts.kbScope?.length) args.push('--scope', opts.kbScope.join(','))
  if (opts.domainLabels?.length) args.push('--labels', opts.domainLabels.join(','))
  if (opts.harness) args.push('--harness', opts.harness)
  const valuesMd = join(seedDir, 'values.md')
  try {
    await access(valuesMd)
    args.push('--values', valuesMd)
  } catch { /* 无 values.md → 保持模板价值观 */ }

  const { stdout, stderr } = await execFileAsync('node', [ragctl, ...args], {
    cwd: root,
    timeout: 300_000,
    maxBuffer: 2 * 1024 * 1024,
    windowsHide: true,
  })
  return { success: true, name: opts.name, stdout: stdout.slice(-3000), stderr: stderr.slice(-1500) }
}
