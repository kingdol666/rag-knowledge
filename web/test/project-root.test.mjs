import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { stripTypeScriptTypes } from 'node:module'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { pathToFileURL } from 'node:url'

const source = readFileSync(new URL('../server/utils/project-root.ts', import.meta.url), 'utf8')
const runtime = await import(`data:text/javascript;base64,${Buffer.from(stripTypeScriptTypes(source)).toString('base64')}`)

function makeRepo() {
  const root = mkdtempSync(path.join(os.tmpdir(), 'rag-project-root-'))
  mkdirSync(path.join(root, 'kb-mcp'))
  mkdirSync(path.join(root, 'web', 'server', 'utils'), { recursive: true })
  writeFileSync(path.join(root, 'config.yml'), 'server: {}\n')
  writeFileSync(path.join(root, 'kb-mcp', 'server.py'), '')
  return root
}

test('finds a validated project from a real module anchor when cwd is unrelated', () => {
  const root = makeRepo()
  const unrelated = mkdtempSync(path.join(os.tmpdir(), 'rag-unrelated-cwd-'))
  try {
    assert.equal(runtime.resolveProjectRoot({
      configuredRoot: '',
      cwd: unrelated,
      moduleUrl: pathToFileURL(path.join(root, 'web', 'server', 'utils', 'project-root.mjs')).href,
    }), root)
    assert.throws(() => runtime.resolveProjectRoot({
      configuredRoot: '',
      cwd: unrelated,
      moduleUrl: 'file:///_entry.js',
    }), /Cannot locate project root/)
  } finally {
    rmSync(root, { recursive: true, force: true })
    rmSync(unrelated, { recursive: true, force: true })
  }
})

test('prefers cwd checkout, validates explicit root, and rejects partial markers', () => {
  const root = makeRepo()
  const other = mkdtempSync(path.join(os.tmpdir(), 'rag-partial-root-'))
  try {
    assert.equal(runtime.resolveProjectRoot({ configuredRoot: '', cwd: path.join(root, 'web'), moduleUrl: 'file:///_entry.js' }), root)
    assert.equal(runtime.resolveProjectRoot({ configuredRoot: root, cwd: other }), root)
    writeFileSync(path.join(other, 'config.yml'), 'server: {}\n')
    assert.throws(() => runtime.resolveProjectRoot({ configuredRoot: other, cwd: root }), /RAG_PROJECT_ROOT must be an absolute project directory/)
    assert.throws(() => runtime.resolveProjectRoot({ configuredRoot: 'relative', cwd: root }), /RAG_PROJECT_ROOT must be an absolute project directory/)
  } finally {
    rmSync(root, { recursive: true, force: true })
    rmSync(other, { recursive: true, force: true })
  }
})
