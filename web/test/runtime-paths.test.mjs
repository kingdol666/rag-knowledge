import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { stripTypeScriptTypes } from 'node:module'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'

// Load the actual source, replacing only Nuxt's virtual import with inert stubs.
const rootSource = readFileSync(new URL('../server/utils/project-root.ts', import.meta.url), 'utf8')
const rootUrl = `data:text/javascript;base64,${Buffer.from(stripTypeScriptTypes(rootSource)).toString('base64')}`
const rootModule = await import(rootUrl)
const source = readFileSync(new URL('../server/utils/runtime-paths.ts', import.meta.url), 'utf8')
const js = stripTypeScriptTypes(source
  .replaceAll("'./project-root'", `'${rootUrl}'`)
  .replace(
    /import\s*\{\s*getDynamicBackendUrl,\s*getDynamicTreeStoragePath,\s*\}\s*from\s*['"]~\/server\/utils\/dynamic-config['"]/,
    "const getDynamicBackendUrl = () => ''; const getDynamicTreeStoragePath = () => './storage/tree-file-system'",
  ))
const runtime = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`)

function makeRepo() {
  const root = mkdtempSync(path.join(os.tmpdir(), 'rag-runtime-paths-'))
  mkdirSync(path.join(root, 'kb-mcp'))
  mkdirSync(path.join(root, 'web', '.output', 'server'), { recursive: true })
  writeFileSync(path.join(root, 'config.yml'), 'server: {}\n')
  writeFileSync(path.join(root, 'kb-mcp', 'server.py'), '')
  return root
}

test('resolves project and parse output by ascending from Nitro cwd', () => {
  const root = makeRepo()
  const oldCwd = process.cwd()
  const oldRoot = process.env.RAG_PROJECT_ROOT
  try {
    delete process.env.RAG_PROJECT_ROOT
    process.chdir(path.join(root, 'web', '.output', 'server'))
    assert.equal(runtime.getMonorepoRoot(), root)
    assert.equal(rootModule.resolveProjectRoot({ configuredRoot: '', cwd: path.join(root, 'web', '.output', 'server'), moduleUrl: 'file:///_entry.js' }), root)
    assert.equal(runtime.resolveProjectPath('backend/output/example.md'), path.join(root, 'backend', 'output', 'example.md'))
    const artifact = path.join(root, 'backend', 'output', 'example.md')
    mkdirSync(path.dirname(artifact), { recursive: true })
    writeFileSync(artifact, 'parsed markdown')
    assert.equal(readFileSync(runtime.resolveProjectPath('backend/output/example.md'), 'utf8'), 'parsed markdown')
    assert.equal(runtime.getTreeStorageAbsolutePath(), path.join(root, 'storage', 'tree-file-system'))
    const absolute = path.join(os.tmpdir(), 'absolute-example.md')
    assert.equal(runtime.resolveProjectPath(absolute), absolute)
  } finally {
    process.chdir(oldCwd)
    if (oldRoot === undefined) delete process.env.RAG_PROJECT_ROOT
    else process.env.RAG_PROJECT_ROOT = oldRoot
    rmSync(root, { recursive: true, force: true })
  }
})

test('validates RAG_PROJECT_ROOT and refuses unrelated cwd or partial markers', () => {
  const root = makeRepo()
  const other = mkdtempSync(path.join(os.tmpdir(), 'rag-runtime-unrelated-'))
  const oldCwd = process.cwd()
  const oldRoot = process.env.RAG_PROJECT_ROOT
  try {
    process.chdir(other)
    process.env.RAG_PROJECT_ROOT = root
    assert.equal(runtime.getMonorepoRoot(), root)
    process.env.RAG_PROJECT_ROOT = 'relative'
    assert.throws(() => runtime.getMonorepoRoot(), /RAG_PROJECT_ROOT must be an absolute project directory/)
    writeFileSync(path.join(other, 'config.yml'), 'server: {}\n')
    process.env.RAG_PROJECT_ROOT = other
    assert.throws(() => runtime.getMonorepoRoot(), /RAG_PROJECT_ROOT must be an absolute project directory/)
    delete process.env.RAG_PROJECT_ROOT
    assert.throws(() => runtime.getMonorepoRoot(), /Cannot locate project root/)
  } finally {
    process.chdir(oldCwd)
    if (oldRoot === undefined) delete process.env.RAG_PROJECT_ROOT
    else process.env.RAG_PROJECT_ROOT = oldRoot
    rmSync(root, { recursive: true, force: true })
    rmSync(other, { recursive: true, force: true })
  }
})
