import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { createJiti } from 'jiti'

const jiti = createJiti(import.meta.url)
const { resolveBackendUrl, getRawConfig, getEnvConfig, resolveMonorepoPath } = await jiti.import('../server/utils/dynamic-config.ts')
import {
  createChildEnvironment,
  createLaunchPlan,
  loadDotenv,
  parseArgs,
  resolveAppMode,
  resolveStartupOptions,
} from '../start.mjs'

test('startup mode gives explicit process env precedence over dotenv and npm command', () => {
  assert.equal(resolveAppMode({
    processEnv: { APP_MODE: 'prod' },
    dotenv: { APP_MODE: 'dev' },
    lifecycleEvent: 'dev',
  }), 'prod')
  assert.equal(resolveAppMode({
    dotenv: { APP_MODE: 'dev' },
    lifecycleEvent: 'start',
  }), 'dev')
  assert.equal(resolveAppMode({ lifecycleEvent: 'start' }), 'prod')
  assert.equal(resolveAppMode({ lifecycleEvent: 'dev' }), 'dev')
  assert.throws(() => resolveAppMode({ processEnv: { APP_MODE: 'staging' } }), /Invalid APP_MODE/)
})

test('startup options prioritize process env, then dotenv, then selected mode config', () => {
  const modeConfig = { host: '0.0.0.0', frontend_port: '3000', backend_url: 'http://localhost:8001' }
  assert.deepEqual(resolveStartupOptions({
    processEnv: { APP_MODE: 'prod', WEB_PORT: '9400', PORT: '9401', BACKEND_PORT: '9500' },
    dotenv: { APP_MODE: 'dev', WEB_PORT: '6789', BACKEND_URL: 'http://dotenv:8001' },
    modeConfig,
  }), {
    mode: 'prod', host: '0.0.0.0', port: '9400', backendUrl: 'http://localhost:9500',
  })
  assert.deepEqual(resolveStartupOptions({
    processEnv: { APP_MODE: 'prod' },
    dotenv: { WEB_PORT: '3001', BACKEND_URL: 'http://dotenv:8001' },
    modeConfig,
  }), {
    mode: 'prod', host: '0.0.0.0', port: '3001', backendUrl: 'http://dotenv:8001',
  })
  assert.deepEqual(resolveStartupOptions({ processEnv: { APP_MODE: 'prod' } }), {
    mode: 'prod', host: '0.0.0.0', port: '3000', backendUrl: 'http://localhost:8001',
  })
  assert.deepEqual(resolveStartupOptions({ processEnv: { APP_MODE: 'dev' } }), {
    mode: 'dev', host: '0.0.0.0', port: '6789', backendUrl: 'http://localhost:8765',
  })
  assert.deepEqual(resolveStartupOptions({
    cliOpts: { host: '127.0.0.1', port: '4000', mode: 'prod' },
    processEnv: { APP_MODE: 'dev', WEB_PORT: '6789' },
    modeConfig,
  }), {
    mode: 'prod', host: '127.0.0.1', port: '4000', backendUrl: 'http://localhost:8001',
  })
  assert.throws(() => resolveStartupOptions({ processEnv: { PORT: '0' } }), /Invalid frontend port/)
})

test('dynamic backend resolver preserves source precedence and mode fallbacks', () => {
  const modeConfig = { backend_url: 'http://prod-config:8001' }
  const dotenv = { BACKEND_URL: 'http://dotenv:8765', BACKEND_PORT: '8765' }
  assert.equal(resolveBackendUrl({ processEnv: { BACKEND_URL: 'https://override.invalid' }, dotenv, mode: 'prod', modeConfig }), 'https://override.invalid')
  assert.equal(resolveBackendUrl({ processEnv: { BACKEND_PORT: '9100' }, dotenv, mode: 'prod', modeConfig }), 'http://localhost:9100')
  assert.equal(resolveBackendUrl({ dotenv, mode: 'prod', modeConfig }), 'http://dotenv:8765')
  assert.equal(resolveBackendUrl({ mode: 'prod', modeConfig }), 'http://prod-config:8001')
  assert.equal(resolveBackendUrl({ mode: 'prod' }), 'http://localhost:8001')
  assert.equal(resolveBackendUrl({ mode: 'dev' }), 'http://localhost:8765')
})

test('dynamic config and resolved paths follow root changes without stale cache', () => {
  const roots = [mkdtempSync(path.join(os.tmpdir(), 'rag-config-a-')), mkdtempSync(path.join(os.tmpdir(), 'rag-config-b-'))]
  const oldRoot = process.env.RAG_PROJECT_ROOT
  try {
    roots.forEach((root, index) => {
      mkdirSync(path.join(root, 'kb-mcp'))
      writeFileSync(path.join(root, 'kb-mcp', 'server.py'), '')
      writeFileSync(path.join(root, 'config.yml'), `storage:\n  tree_fs_root: "storage-${index}"\n`)
      writeFileSync(path.join(root, '.env'), `TEST_ROOT_INDEX=${index}\n`)
    })
    roots.forEach((root, index) => {
      process.env.RAG_PROJECT_ROOT = root
      assert.equal(getRawConfig().storage.tree_fs_root, `storage-${index}`)
      assert.equal(getEnvConfig().TEST_ROOT_INDEX, String(index))
      assert.equal(resolveMonorepoPath('artifact'), path.join(root, 'artifact'))
    })
  } finally {
    if (oldRoot === undefined) delete process.env.RAG_PROJECT_ROOT
    else process.env.RAG_PROJECT_ROOT = oldRoot
    roots.forEach(root => rmSync(root, { recursive: true, force: true }))
  }
})

test('dotenv loader returns provenance and never overrides explicit values', () => {
  const rootDir = mkdtempSync(path.join(os.tmpdir(), 'rag-web-dotenv-'))
  try {
    mkdirSync(path.join(rootDir, 'web'))
    writeFileSync(path.join(rootDir, '.env'), 'APP_MODE=dev\nWEB_PORT="6789"\nBACKEND_URL=http://dotenv:8001\n')
    writeFileSync(path.join(rootDir, 'web', '.env'), 'APP_MODE=prod\nWEB_PORT=3000\n')
    const env = { APP_MODE: 'prod' }
    const dotenv = loadDotenv({ env, rootDir })
    assert.equal(env.APP_MODE, 'prod')
    assert.equal(env.WEB_PORT, '6789')
    assert.equal(dotenv.APP_MODE, 'dev')
    assert.equal(dotenv.WEB_PORT, '6789')
    assert.equal(dotenv.BACKEND_URL, 'http://dotenv:8001')
  } finally {
    rmSync(rootDir, { recursive: true, force: true })
  }
})

test('production launch uses Nitro artifact without requiring Nuxt CLI', () => {
  const rootDir = mkdtempSync(path.join(os.tmpdir(), 'rag-web-prod-'))
  try {
    const artifact = path.join(rootDir, '.output', 'server', 'index.mjs')
    mkdirSync(path.dirname(artifact), { recursive: true })
    writeFileSync(artifact, '// test artifact\n')
    const plan = createLaunchPlan({ mode: 'prod', artifactPath: artifact })
    assert.equal(plan.command, process.execPath)
    assert.deepEqual(plan.args, [artifact])
    assert.equal(plan.description, 'built Nitro server')
    assert.deepEqual(createChildEnvironment({ UNRELATED: 'kept', PORT: 'old' }, {
      mode: 'prod', host: '127.0.0.1', port: '3001', backendUrl: 'http://localhost:8001',
    }), {
      UNRELATED: 'kept', HOST: '127.0.0.1', PORT: '3001', NITRO_HOST: '127.0.0.1', NITRO_PORT: '3001', APP_MODE: 'prod', BACKEND_URL: 'http://localhost:8001',
    })
    assert.throws(() => createLaunchPlan({
      mode: 'prod', artifactPath: path.join(rootDir, 'missing.mjs'), nuxtCliPath: '/unused/nuxt.mjs',
    }), /Production Nitro artifact not found/)
    assert.throws(() => createLaunchPlan({ mode: 'dev', artifactPath: artifact }), /Nuxt CLI entry/)
    assert.deepEqual(parseArgs(['--mode', 'prod', '--port', '3100']), { mode: 'prod', port: '3100' })
  } finally {
    rmSync(rootDir, { recursive: true, force: true })
  }
})
