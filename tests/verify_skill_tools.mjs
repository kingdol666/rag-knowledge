/**
 * Cross-verify: all tools referenced in skills exist in server.py
 */
import fs from 'fs'
import path from 'path'

const SKILLS_DIR = path.resolve('.claude/skills')
const SERVER_PY = path.resolve('kb-mcp/server.py')

// Extract all tool function names from server.py
const serverContent = fs.readFileSync(SERVER_PY, 'utf-8')
const toolDefs = new Set()
const toolRegex = /async def (\w+)\s*\(/g
let match
while ((match = toolRegex.exec(serverContent)) !== null) {
  toolDefs.add(match[1])
}

console.log(`Found ${toolDefs.size} tool functions in server.py:`)
console.log([...toolDefs].sort().join(', '))
console.log()

// Collect all skill files
const skillDirs = fs.readdirSync(SKILLS_DIR, { withFileTypes: true })
  .filter(d => d.isDirectory())
  .map(d => d.name)

let allReferenced = new Set()
let missing = []

for (const dir of skillDirs) {
  const skillFile = path.join(SKILLS_DIR, dir, 'SKILL.md')
  if (!fs.existsSync(skillFile)) continue

  const content = fs.readFileSync(skillFile, 'utf-8')
  
  // Find tool references: patterns like `tool_name(` or `tool_name `
  // Match identifiers that look like tool calls: word followed by (
  const refRegex = /`?(kb_\w+|fs_\w+|parse_\w+|preview_\w+|experience_\w+|backend_\w+|health_\w+)\s*\(/g
  let m
  while ((m = refRegex.exec(content)) !== null) {
    const toolName = m[1]
    allReferenced.add(toolName)
    if (!toolDefs.has(toolName)) {
      missing.push({ skill: dir, tool: toolName })
    }
  }
}

console.log(`\nReferenced tools in skills: ${allReferenced.size}`)
console.log([...allReferenced].sort().join(', '))

if (missing.length === 0) {
  console.log('\n✅ All tool references in skills are defined in server.py!')
} else {
  console.log(`\n❌ ${missing.length} missing tool definitions:`)
  for (const m of missing) {
    console.log(`   ${m.skill}: ${m.tool}`)
  }
}

// Also check references in agent files
const agentFile = path.resolve('.claude/agents/knowledge-admin.md')
if (fs.existsSync(agentFile)) {
  const agentContent = fs.readFileSync(agentFile, 'utf-8')
  const agentRefs = new Set()
  const aRegex = /`?(kb_\w+|fs_\w+|parse_\w+|preview_\w+|experience_\w+|backend_\w+|health_\w+)\s*\(/g
  let am
  while ((am = aRegex.exec(agentContent)) !== null) {
    agentRefs.add(am[1])
  }
  const agentMissing = [...agentRefs].filter(t => !toolDefs.has(t))
  if (agentMissing.length === 0) {
    console.log('\n✅ All tool references in knowledge-admin.md are defined!')
  } else {
    console.log(`\n❌ Agent missing tools: ${agentMissing.join(', ')}`)
  }
}

process.exit(missing.length === 0 ? 0 : 1)
