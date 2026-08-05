import { defineEventHandler, readMultipartFormData, createError } from 'h3'
import { mkdtemp, writeFile, rm } from 'fs/promises'
import { tmpdir } from 'os'
import { join } from 'path'
import { runRagctlDistill } from '~/server/utils/soul-distill-runner'

/**
 * POST /api/soul/distill-seed — dot-skill/补天种子包导入落地(前端创建 SOUL 界面入口)
 *
 * FormData: name, kb_scope(逗号分隔)?, domain_labels?, harness? + 文件:
 *   meta.json(必), persona.md(必), work.md(必), values.md(选)
 *
 * 与 ragctl soul distill <种子目录> 同语义: dot-skill 产物目录即种子契约,
 * 前端上传后组包 → ragctl 落地。
 */
export default defineEventHandler(async (event) => {
  const form = await readMultipartFormData(event)
  if (!form) throw createError({ statusCode: 400, statusMessage: 'no form data' })

  const files = new Map<string, { data: Buffer; filename?: string }>()
  let name = ''
  let kbScope: string[] | undefined
  let domainLabels: string[] | undefined
  let harness: string | undefined
  for (const part of form) {
    if (part.filename) {
      files.set(part.filename, { data: part.data, filename: part.filename })
    } else {
      const key = part.name || ''
      const val = String(part.data)
      if (key === 'name') name = val.trim()
      else if (key === 'kb_scope') kbScope = val.split(',').map(s => s.trim()).filter(Boolean)
      else if (key === 'domain_labels') domainLabels = val.split(',').map(s => s.trim()).filter(Boolean)
      else if (key === 'harness') harness = val.trim() || undefined
    }
  }
  if (!name) throw createError({ statusCode: 400, statusMessage: 'name required' })
  for (const required of ['meta.json', 'persona.md', 'work.md']) {
    if (!files.has(required)) throw createError({ statusCode: 400, statusMessage: `missing seed file: ${required}` })
  }

  const tmp = await mkdtemp(join(tmpdir(), 'soul-seed-'))
  try {
    for (const [fname, f] of files) {
      // 只接受种子契约文件; 过滤路径穿越
      if (!/^(meta\.json|persona\.md|work\.md|values\.md)$/.test(fname)) continue
      await writeFile(join(tmp, fname), f.data)
    }
    return await runRagctlDistill(tmp, {
      name,
      kbScope,
      domainLabels,
      harness,
    })
  } catch (e: any) {
    const detail = String(e?.stderr || e?.stdout || e?.message || e).slice(-1500)
    return { success: false, name, error: `种子落地失败: ${detail}` }
  } finally {
    rm(tmp, { recursive: true, force: true }).catch(() => {})
  }
})
