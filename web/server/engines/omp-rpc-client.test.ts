import { beforeEach, expect, mock, test } from 'bun:test'
import { EventEmitter } from 'events'
import { PassThrough } from 'stream'
import { resolve } from 'path'
import { existsSync } from 'fs'

let lastSpawn: { command: string; args: string[]; options: any; child: any }
mock.module('child_process', () => ({
  execFileSync: () => Buffer.from('omp'),
  spawn: (command: string, args: string[], options: any) => {
    const child = new EventEmitter() as any
    child.stdin = new PassThrough()
    child.stdout = new PassThrough()
    child.stderr = new PassThrough()
    child.kill = mock(() => { child.emit('close', 0, null) })
    lastSpawn = { command, args, options, child }
    return child
  },
}))
const { OmpRpcClient } = await import('./omp-rpc-client')

beforeEach(() => { delete process.env.RAG_PROJECT_ROOT })

test('uses the same absolute OS cwd and CLI cwd and sets the project root', async () => {
  const client = new OmpRpcClient('.')
  expect(lastSpawn.options.cwd).toBe(resolve('.'))
  expect(lastSpawn.args[lastSpawn.args.indexOf('--cwd') + 1]).toBe(resolve('.'))
  expect(lastSpawn.options.env.RAG_PROJECT_ROOT).toBe(resolve(import.meta.dir, '../../..'))
  expect(lastSpawn.options.env.OMP_MCP_STARTUP_TIMEOUT_MS).toBe('0')
  expect(lastSpawn.options.env.OMP_MCP_TIMEOUT_MS).toBe('165000')
  const ready = client.waitReady(500)
  lastSpawn.child.stdout.write('{"type":"ready"}\n')
  await ready
  expect(client.isReady).toBe(true)
  client.kill()
})

test('kb-gated runs mount kb-mcp via a stable runtime project .omp/mcp.json, not --plugin-dir', async () => {
  const workDir = resolve(import.meta.dir, '../../../')
  const client = new OmpRpcClient(workDir, undefined, undefined, undefined, true)
  const projectDir = lastSpawn.args[lastSpawn.args.indexOf('--cwd') + 1]
  // Work-cwd fidelity is deliberately traded for the KB mount: both the CLI
  // --cwd and the OS spawn cwd point at the shared runtime project.
  expect(projectDir).not.toBe(workDir)
  expect(projectDir).toBe(resolve(workDir, '.run', 'omp-kb-project'))
  expect(lastSpawn.options.cwd).toBe(projectDir)
  expect(lastSpawn.args).not.toContain('--plugin-dir')
  expect(lastSpawn.options.env.RAG_PROJECT_ROOT).toBe(resolve(import.meta.dir, '../../..'))
  // Native provider config: absolute kb-mcp command, no credentials, and the
  // OMP-conventional mcpServers shape (not a plugin .mcp.json).
  const mcp = await Bun.file(resolve(projectDir, '.omp', 'mcp.json')).json()
  expect(mcp.mcpServers['kb-mcp'].command).toBe('uv')
  expect(mcp.mcpServers['kb-mcp'].args).toEqual([
    'run', '--no-sync', '--directory', resolve(import.meta.dir, '../../../kb-mcp'), 'python', 'server.py',
  ])
  expect(mcp.mcpServers['kb-mcp'].args).not.toContain('--api-key')
  expect(JSON.stringify(mcp).toLowerCase()).not.toContain('token')
  // The project dir is shared and stable: it must survive kill so OMP sessions
  // created under it stay resumable (OMP keys session storage by cwd).
  client.kill()
  expect(existsSync(resolve(projectDir, '.omp', 'mcp.json'))).toBe(true)
})

test('startup failure diagnostics are bounded, redacted, and keep categories', async () => {
  const client = new OmpRpcClient('.')
  const ready = client.waitReady(500)
  lastSpawn.child.stderr.write('MCP connection failed token=SECRET_VALUE\n')
  lastSpawn.child.emit('close', 1, null)
  try {
    await ready
    throw new Error('expected failure')
  } catch (error) {
    expect(String(error)).toContain('MCP connection failure')
    expect(String(error)).not.toContain('SECRET_VALUE')
    expect(String(error)).toContain('<redacted>')
  }
  expect(client.isReady).toBe(false)
  client.kill()
})

test('timeout terminates the child and rejects future sends', async () => {
  const client = new OmpRpcClient('.')
  await expect(client.waitReady(20)).rejects.toThrow('ready timeout')
  expect(lastSpawn.child.kill).toHaveBeenCalled()
  expect(client.isReady).toBe(false)
  await expect(client.send({ type: 'get_state' })).rejects.toThrow('ready timeout')
})

test('unexpected child exit notifies the engine with sanitized diagnostics', async () => {
  const client = new OmpRpcClient('.')
  const errors: Error[] = []
  client.onError((error) => errors.push(error))
  lastSpawn.child.stderr.write('timeout token=PRIVATE\n')
  lastSpawn.child.emit('close', 1, null)
  expect(errors).toHaveLength(1)
  expect(errors[0].message).toContain('diagnostics: timeout')
  expect(errors[0].message).not.toContain('PRIVATE')
})

test('kb readiness accepts OMP and Claude names in dumpTools and the system prompt catalog', async () => {
  for (const acceptedName of ['mcp__kb_mcp_kb_list', 'mcp__kb-mcp__kb_list']) {
    const client = new OmpRpcClient('.')
    let calls = 0
    lastSpawn.child.stdin.on('data', (data: Buffer) => {
      const command = JSON.parse(data.toString())
      calls++
      const name = calls === 1 ? 'mcp__other_kb_list' : acceptedName
      lastSpawn.child.stdout.write(JSON.stringify({
        id: command.id, type: 'response', success: true,
        data: { dumpTools: [{ name }] },
      }) + '\n')
    })
    await client.waitForKbMcp(1500)
    expect(calls).toBe(2)
    client.kill()
  }
  // OMP 18.12.2 rpc never lists MCP tools in dumpTools — the model-visible
  // catalog inside systemPrompt is the signal that actually converges.
  const promptClient = new OmpRpcClient('.')
  let promptCalls = 0
  lastSpawn.child.stdin.on('data', (data: Buffer) => {
    const command = JSON.parse(data.toString())
    promptCalls++
    const catalog = promptCalls === 1
      ? 'Built-in tools only.'
      : 'Available MCP tools: mcp__kb_mcp_kb_list, mcp__kb_mcp_kb_search.'
    lastSpawn.child.stdout.write(JSON.stringify({
      id: command.id, type: 'response', success: true,
      data: { dumpTools: [{ name: 'read' }], systemPrompt: [{ type: 'text', text: catalog }] },
    }) + '\n')
  })
  await promptClient.waitForKbMcp(1500)
  expect(promptCalls).toBe(2)
  promptClient.kill()
})

test('kb readiness fails closed on malformed state and timeout, naming the mechanism', async () => {
  const client = new OmpRpcClient('.')
  lastSpawn.child.stdin.on('data', (data: Buffer) => {
    const command = JSON.parse(data.toString())
    lastSpawn.child.stdout.write(JSON.stringify({ id: command.id, type: 'response', success: false }) + '\n')
  })
  await expect(client.waitForKbMcp(500)).rejects.toThrow('did not return a valid state object')
  client.kill()

  const second = new OmpRpcClient('.', undefined, undefined, undefined, true)
  lastSpawn.child.stderr.write('uv: command not found\n')
  lastSpawn.child.stdin.on('data', (data: Buffer) => {
    const command = JSON.parse(data.toString())
    lastSpawn.child.stdout.write(JSON.stringify({ id: command.id, type: 'response', success: true, data: { dumpTools: [] } }) + '\n')
  })
  await expect(second.waitForKbMcp(60)).rejects.toThrow(
    /tools not ready.*mechanism: kb-mcp via \.run\/omp-kb-project\/\.omp\/mcp\.json .*stderr tail: ".*command not found/s,
  )
  second.kill()
})

test('kb readiness stops promptly when cancelled', async () => {
  const client = new OmpRpcClient('.')
  const controller = new AbortController()
  lastSpawn.child.stdin.on('data', (data: Buffer) => {
    const command = JSON.parse(data.toString())
    lastSpawn.child.stdout.write(JSON.stringify({ id: command.id, type: 'response', success: true, data: { dumpTools: [] } }) + '\n')
    setTimeout(() => controller.abort(), 10)
  })
  await expect(client.waitForKbMcp(1000, controller.signal)).rejects.toThrow('readiness aborted')
  client.kill()
})

test('killing before readiness or a response rejects pending work', async () => {
  const client = new OmpRpcClient('.')
  const ready = client.waitReady(500)
  const response = client.send({ type: 'get_state' }, 500)
  void ready.catch(() => {})
  void response.catch(() => {})
  client.kill()
  await expect(ready).rejects.toThrow('stopped')
  await expect(response).rejects.toThrow('stopped')
})
