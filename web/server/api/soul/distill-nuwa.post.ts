import { defineEventHandler, readBody, createError } from 'h3'
import { mkdtemp, mkdir, writeFile, rm } from 'fs/promises'
import { tmpdir } from 'os'
import { join } from 'path'
import { execFile } from 'child_process'
import { promisify } from 'util'
import { getProjectRoot } from '~/server/utils/claude-config'
import { runRagctlDistill } from '~/server/utils/soul-distill-runner'

const execFileAsync = promisify(execFile)

/**
 * POST /api/soul/distill-nuwa — 女娲引擎蒸馏落地(前端创建 SOUL 界面入口)
 *
 * body: {
 *   name: string          // soul-<名字> 或 <名字>
 *   skill_md: string      // nuwa 产物 [person]-perspective/SKILL.md 全文
 *   kb_scope?: string[]   // 缺省 ["*"]
 *   domain_labels?: string[]
 *   harness?: string      // omp | claude | ''
 * }
 *
 * 流程: 写 SKILL.md → nuwa_to_seed.py 转种子包(确定性) → ragctl soul distill 落地。
 * 同步完成(约 30s), 返回 {success, name, stdout, stderr}。
 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const name = String(body?.name || '').trim()
  const skillMd = String(body?.skill_md || '').trim()
  if (!name) throw createError({ statusCode: 400, statusMessage: 'name required' })
  if (!skillMd) throw createError({ statusCode: 400, statusMessage: 'skill_md required (nuwa perspective SKILL.md)' })
  if (skillMd.length < 500) throw createError({ statusCode: 400, statusMessage: 'skill_md too short — not a nuwa perspective SKILL.md' })

  const root = getProjectRoot()
  const tmp = await mkdtemp(join(tmpdir(), 'soul-nuwa-'))
  try {
    // 1) 组装 nuwa 产物目录 → 转换种子包
    const skillDir = join(tmp, 'perspective')
    await mkdir(skillDir, { recursive: true })
    await writeFile(join(skillDir, 'SKILL.md'), skillMd, 'utf-8')
    const converter = join(root, '.claude', 'skills', 'butian', 'scripts', 'nuwa_to_seed.py')
    await execFileAsync('python', [converter, skillDir, '--out', join(tmp, 'seed')], {
      cwd: root, timeout: 60_000, windowsHide: true,
    })

    // 2) ragctl 落地(同一编排, 三入口一致)
    return await runRagctlDistill(join(tmp, 'seed'), {
      name,
      kbScope: Array.isArray(body?.kb_scope) ? body.kb_scope : undefined,
      domainLabels: Array.isArray(body?.domain_labels) ? body.domain_labels : undefined,
      harness: body?.harness ? String(body.harness) : undefined,
    })
  } catch (e: any) {
    const detail = String(e?.stderr || e?.stdout || e?.message || e).slice(-1500)
    return { success: false, name, error: `蒸馏失败: ${detail}` }
  } finally {
    rm(tmp, { recursive: true, force: true }).catch(() => {})
  }
})
