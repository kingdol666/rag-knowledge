#!/usr/bin/env node
/**
 * validate_skills.cjs — Cross-skill consistency validator
 * ════════════════════════════════════════════════════════════════════════
 * Validates that all knowledgebase-* skills are internally consistent:
 *   1. No trigger keyword appears in multiple scenario rows (routing conflict)
 *   2. Shared thresholds reference the authoritative source (sub-kb-creation.md)
 *   3. All relative file references resolve to existing files
 *   4. No broken MEMORY.md references (host-path, not in repo)
 *   5. All skills have valid frontmatter (name + description)
 *   6. Phase/step numbering is consistent (e.g., O0-O13 claim matches content)
 *
 * Exit code: 0 = all pass, 1 = issues found.
 * Run: node scripts/validate_skills.cjs
 *
 * Integrate into CI or pre-commit to prevent regression.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const SKILLS_DIR = path.join(ROOT, '.claude', 'skills');
const CLAUDE_MD = path.join(ROOT, 'CLAUDE.md');

const issues = [];
const warnings = [];
let checks = 0;

function ok(msg) { checks++; }
function warn(msg) { warnings.push(msg); }
function fail(msg) { issues.push(msg); }

// ── 1. Load all skill files ──────────────────────────────────────────
function loadSkills() {
  const skills = {};
  if (!fs.existsSync(SKILLS_DIR)) { fail('Skills directory not found: ' + SKILLS_DIR); return skills; }
  for (const dir of fs.readdirSync(SKILLS_DIR)) {
    if (!dir.startsWith('knowledgebase')) continue;
    const skillMd = path.join(SKILLS_DIR, dir, 'SKILL.md');
    if (!fs.existsSync(skillMd)) continue;
    const content = fs.readFileSync(skillMd, 'utf8');
    skills[dir] = { dir, path: skillMd, content };
  }
  return skills;
}

// ── 2. Parse frontmatter ─────────────────────────────────────────────
function parseFrontmatter(content) {
  // Handle both \n and \r\n line endings
  const m = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!m) return null;
  const fm = {};
  // Handle multiline description (>) and simple key: value
  const lines = m[1].split(/\r?\n/);
  let currentKey = null;
  for (const line of lines) {
    const kv = line.match(/^(\w+):\s*(.*)/);
    if (kv) {
      currentKey = kv[1];
      if (kv[2] && !kv[2].startsWith('>')) fm[currentKey] = kv[2];
      else fm[currentKey] = '';
    } else if (currentKey && line.trim().startsWith('Triggered by:')) {
      fm[currentKey] += line;
    }
  }
  return fm;
}

// ── Check 1: Trigger keyword conflicts in dispatcher ─────────────────
function checkTriggerConflicts(skills) {
  const dispatcher = skills['knowledgebase'];
  if (!dispatcher) { fail('Dispatcher skill (knowledgebase) not found'); return; }

  // Extract the classification table rows
  const tableMatch = dispatcher.content.match(/\| Signal keywords[\s\S]*?(?=\n\n|\n>)/);
  if (!tableMatch) { warn('Could not find classification table in dispatcher'); return; }

  const rows = tableMatch[0].split('\n')
    .filter(l => l.startsWith('|') && !l.includes('---') && !l.includes('Signal keywords'))
    .map(l => {
      const cells = l.split('|').map(c => c.trim()).filter(Boolean);
      // First cell = keywords, last cell = route
      const keywordsCell = cells[0];
      const route = cells[cells.length - 1];
      const keywords = keywordsCell.split(/[,，]/).map(k => k.trim().replace(/\*\*/g, '')).filter(Boolean);
      return { keywords, route, raw: l };
    });

  // Build keyword → scenarios map
  const keywordMap = {};
  for (const row of rows) {
    for (const kw of row.keywords) {
      if (!keywordMap[kw]) keywordMap[kw] = [];
      const scenario = row.route.match(/knowledgebase-(\w+)/);
      keywordMap[kw].push(scenario ? scenario[1] : row.route);
    }
  }

  // Find conflicts (same keyword in multiple scenarios)
  let conflicts = 0;
  for (const [kw, scenarios] of Object.entries(keywordMap)) {
    const unique = [...new Set(scenarios)];
    if (unique.length > 1) {
      fail(`Trigger conflict: "${kw}" maps to ${unique.join(' + ')}`);
      conflicts++;
    }
  }

  // Check longest-match rule is documented (REQUIRED — prevents prefix hijack bugs)
  if (!dispatcher.content.includes('最长匹配') && !dispatcher.content.includes('Longest-Match')) {
    fail('Dispatcher missing longest-match rule documentation (required to prevent prefix-hijack routing bugs)');
  }

  ok();
  return conflicts;
}

// ── Check 2: Shared threshold consistency ────────────────────────────
function checkThresholdConsistency(skills) {
  const ingest = skills['knowledgebase-ingest'];
  const organize = skills['knowledgebase-organize'];
  const subKbRef = path.join(SKILLS_DIR, 'knowledgebase-ingest', 'references', 'sub-kb-creation.md');

  if (!fs.existsSync(subKbRef)) {
    fail('Authoritative threshold source not found: sub-kb-creation.md');
    return;
  }

  const refContent = fs.readFileSync(subKbRef, 'utf8');
  if (!refContent.includes('SUB_KB_CHECK_THRESHOLD') || !refContent.includes('SUB_KB_AUTO_SPLIT_THRESHOLD')) {
    fail('sub-kb-creation.md missing authoritative threshold definitions (SUB_KB_CHECK_THRESHOLD / SUB_KB_AUTO_SPLIT_THRESHOLD)');
  }

  // Verify both skills reference the shared source
  if (ingest && !ingest.content.includes('sub-kb-creation.md')) {
    fail('Ingest A8 does not reference sub-kb-creation.md threshold source');
  }
  if (organize && !organize.content.includes('sub-kb-creation.md')) {
    fail('Organize does not reference sub-kb-creation.md threshold source');
  }

  // Check for hardcoded thresholds that bypass the source
  // Ingest should use SUB_KB_AUTO_SPLIT_THRESHOLD (≥8)
  if (ingest && !ingest.content.includes('SUB_KB_AUTO_SPLIT_THRESHOLD')) {
    fail('Ingest A8 should reference SUB_KB_AUTO_SPLIT_THRESHOLD, not hardcode ≥8');
  }
  // Organize should use SUB_KB_CHECK_THRESHOLD (≥6)
  if (organize && !organize.content.includes('SUB_KB_CHECK_THRESHOLD')) {
    fail('Organize O3a should reference SUB_KB_CHECK_THRESHOLD, not hardcode ≥6');
  }

  ok();
}

// ── Check 3: File reference resolution ───────────────────────────────
function checkFileReferences(skills) {
  for (const [name, skill] of Object.entries(skills)) {
    // Find markdown links and parenthetical references: [text](path) or ](path)
    const refs = [...skill.content.matchAll(/\]\(([^)]+\.md[^)]*)\)/g)];
    for (const ref of refs) {
      let refPath = ref[1].split('#')[0].split(' ')[0]; // strip anchor and whitespace
      if (refPath.startsWith('http')) continue; // external URL
      const resolved = path.resolve(path.dirname(skill.path), refPath);
      if (!fs.existsSync(resolved)) {
        fail(`[${name}] Broken reference: ${ref[1]} → ${resolved}`);
      }
    }
  }
  ok();
}

// ── Check 4: No broken MEMORY.md references ──────────────────────────
function checkMemoryReferences(skills) {
  for (const [name, skill] of Object.entries(skills)) {
    // MEMORY.md references that point to host-path (not in repo)
    const memRefs = [...skill.content.matchAll(/MEMORY\.md[:\s]/g)];
    if (memRefs.length > 0) {
      // Check if MEMORY.md exists in repo (it shouldn't — it's host-path)
      const repoMemory = path.join(ROOT, 'MEMORY.md');
      if (!fs.existsSync(repoMemory)) {
        fail(`[${name}] References MEMORY.md which is host-path only (not in repo). Replace with inline content or repo-relative reference.`);
      }
    }
  }
  ok();
}

// ── Check 5: Valid frontmatter ───────────────────────────────────────
function checkFrontmatter(skills) {
  for (const [name, skill] of Object.entries(skills)) {
    const fm = parseFrontmatter(skill.content);
    if (!fm) {
      fail(`[${name}] Missing frontmatter`);
      continue;
    }
    if (!fm.name) fail(`[${name}] Frontmatter missing 'name'`);
    if (!fm.description && fm.description !== '') fail(`[${name}] Frontmatter missing 'description'`);
  }
  ok();
}

// ── Check 6: Step numbering consistency ──────────────────────────────
function checkStepNumbering(skills) {
  for (const [name, skill] of Object.entries(skills)) {
    const fm = parseFrontmatter(skill.content);
    if (!fm || !fm.description) continue;

    // Check O0-ON claims in organize
    if (name === 'knowledgebase-organize') {
      const claim = skill.content.match(/O(\d+)→O(\d+)/);
      if (claim) {
        const start = parseInt(claim[1]);
        const end = parseInt(claim[2]);
        // Find actual step headers
        const steps = [...skill.content.matchAll(/^## O(\d+)\b/gm)].map(m => parseInt(m[1]));
        if (steps.length === 0) continue;
        const actualMax = Math.max(...steps);
        if (end > actualMax) {
          fail(`[${name}] Claims O${start}→O${end} but content only goes to O${actualMax}`);
        }
      }
    }

    // Check A0-AN claims in ingest
    if (name === 'knowledgebase-ingest') {
      const claim = skill.content.match(/A(\d+)→A(\d+)/);
      if (claim) {
        const end = parseInt(claim[2]);
        const steps = [...skill.content.matchAll(/^## A(\d+)\b/gm)].map(m => parseInt(m[1]));
        if (steps.length > 0) {
          const actualMax = Math.max(...steps);
          if (end > actualMax) {
            fail(`[${name}] Claims A0→A${end} but content only goes to A${actualMax}`);
          }
        }
      }
    }
  }
  ok();
}

// ── Check 7: CLAUDE.md ↔ dispatcher keyword sync ─────────────────────
function checkClaudeMdSync(skills) {
  if (!fs.existsSync(CLAUDE_MD)) { warn('CLAUDE.md not found'); return; }
  const claudeMd = fs.readFileSync(CLAUDE_MD, 'utf8');
  const dispatcher = skills['knowledgebase'];
  if (!dispatcher) return;

  // "盘点" should NOT be in ingest keywords in either file
  // Check CLAUDE.md: 盘点 should be in an organize row, not mixed with ingest
  const ingestRow = claudeMd.match(/\| 入库.*?\|/);
  if (ingestRow && ingestRow[0].includes('盘点')) {
    fail('[CLAUDE.md] "盘点" is in ingest keyword row — should be in organize row');
  }

  // Check dispatcher: 盘点 should be in Organize row
  const dispatchRows = dispatcher.content.split('\n').filter(l => l.startsWith('|') && l.includes('**'));
  for (const row of dispatchRows) {
    if (row.includes('盘点') && row.includes('Ingest')) {
      fail('[dispatcher] "盘点" mapped to Ingest — should be Organize');
    }
  }

  ok();
}

// ── Check 8: Tag blacklist reference in Organize ─────────────────────
function checkTagBlacklistSource(skills) {
  const organize = skills['knowledgebase-organize'];
  if (!organize) return;

  // Organize L2 should reference tag-quality-rules.md, not maintain its own blacklist
  if (!organize.content.includes('tag-quality-rules.md')) {
    fail('[organize] L2 tag cleanup does not reference tag-quality-rules.md authoritative source');
  }

  // Should NOT have a hardcoded inline blacklist that duplicates the reference
  if (organize.content.includes('黑名单: "doc"') || organize.content.includes('黑名单: "doc,"')) {
    fail('[organize] L2 has hardcoded inline blacklist — should reference tag-quality-rules.md instead');
  }

  ok();
}

// ── Main ─────────────────────────────────────────────────────────────
const skills = loadSkills();
const skillCount = Object.keys(skills).length;

console.log('═'.repeat(64));
console.log('  Cross-Skill Consistency Validator');
console.log('═'.repeat(64));
console.log(`  Loaded ${skillCount} skills\n`);

checkTriggerConflicts(skills);
checkThresholdConsistency(skills);
checkFileReferences(skills);
checkMemoryReferences(skills);
checkFrontmatter(skills);
checkStepNumbering(skills);
checkClaudeMdSync(skills);
checkTagBlacklistSource(skills);

console.log('─'.repeat(64));
console.log(`  Checks passed: ${checks}`);
console.log(`  Warnings:      ${warnings.length}`);
console.log(`  Issues:        ${issues.length}`);
console.log('─'.repeat(64));

if (warnings.length > 0) {
  console.log('\n⚠️  Warnings:');
  warnings.forEach(w => console.log('   • ' + w));
}
if (issues.length > 0) {
  console.log('\n❌ Issues:');
  issues.forEach(i => console.log('   • ' + i));
  console.log('\n' + '═'.repeat(64));
  console.log('  RESULT: FAIL — fix the issues above');
  console.log('═'.repeat(64));
  process.exit(1);
} else {
  console.log('\n' + '═'.repeat(64));
  console.log('  RESULT: PASS — all skills are consistent');
  console.log('═'.repeat(64));
  process.exit(0);
}
