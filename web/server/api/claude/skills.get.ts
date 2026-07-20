/**
 * GET /api/claude/skills?cwd=<path>
 *
 * Scans each subdirectory under .claude/skills/ in the specified working directory,
 * parses the SKILL.md frontmatter, and returns a skills list (name + description).
 *
 * Used by the frontend to display project-level Skills catalog (as opposed to the
 * slash_commands from the SDK init message, this provides richer description info).
 */
import { resolve, join } from 'path'
import { existsSync, readdirSync, readFileSync, statSync } from 'fs'
import { getProjectRoot } from '~/server/utils/claude-config'

interface SkillInfo {
  name: string
  description: string
  path: string
  source: 'project' | 'user'
}

function parseFrontmatter(content: string): { name?: string; description?: string } {
  const m = content.match(/^---\s*\n([\s\S]*?)\n---/)
  if (!m) return {}
  const fm = m[1]
  const nameMatch = fm.match(/^name:\s*(.+)$/m)
  // description may be multi-line (> block scalar) or single line
  let desc = ''
  const descSingle = fm.match(/^description:\s*(.+)$/m)
  if (descSingle) {
    desc = descSingle[1].trim()
  } else {
    const descBlock = fm.match(/^description:\s*>\s*\n((?:\s+.+\n?)+)/m)
    if (descBlock) desc = descBlock[1].replace(/^\s+/gm, '').trim()
  }
  // Strip quotes
  desc = desc.replace(/^["']|["']$/g, '').trim()
  return {
    name: nameMatch?.[1]?.trim().replace(/^["']|["']$/g, ''),
    description: desc,
  }
}

function scanSkillsDir(skillsDir: string, source: 'project' | 'user'): SkillInfo[] {
  if (!existsSync(skillsDir)) return []
  const out: SkillInfo[] = []
  let entries: string[] = []
  try { entries = readdirSync(skillsDir) } catch { return [] }
  for (const entry of entries) {
    const skillPath = join(skillsDir, entry, 'SKILL.md')
    if (!existsSync(skillPath)) continue
    try {
      const content = readFileSync(skillPath, 'utf-8')
      const fm = parseFrontmatter(content)
      out.push({
        name: fm.name || entry,
        description: fm.description || '',
        path: skillPath,
        source,
      })
    } catch { /* Skip unreadable ones */ }
  }
  return out
}

export default defineEventHandler((event) => {
  const q = getQuery(event)
  const cwd = (q.cwd as string)?.trim() || getProjectRoot()

  const projectSkills = scanSkillsDir(join(cwd, '.claude', 'skills'), 'project')
  const userSkillsDir = resolve(process.env.USERPROFILE || process.env.HOME || '', '.claude', 'skills')
  const userSkills = scanSkillsDir(userSkillsDir, 'user')

  return {
    success: true,
    cwd,
    skills: [...projectSkills, ...userSkills],
    count: projectSkills.length + userSkills.length,
  }
})
