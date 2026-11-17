// @ts-nocheck -- Bun supplies test globals; the web tsc configuration targets Nuxt.
import { expect, mock, test } from 'bun:test'
import { EventEmitter } from 'events'
import { PassThrough } from 'stream'

let child: any
let emittedNames: string[] = []
let commands: string[] = []
mock.module('child_process', () => ({
  execFileSync: () => Buffer.from('omp'),
  spawn: () => {
    child = new EventEmitter()
    child.stdin = new PassThrough()
    child.stdout = new PassThrough()
    child.stderr = new PassThrough()
    child.kill = () => child.emit('close', 0, null)
    child.stdin.on('data', (data: Buffer) => {
      const command = JSON.parse(data.toString())
      commands.push(command.type)
      if (command.type === 'get_state') {
        child.stdout.write(JSON.stringify({
          id: command.id, type: 'response', success: true,
          data: { sessionId: 'omp-session', dumpTools: [{ name: 'mcp__kb_mcp_kb_list' }] },
        }) + '\n')
      } else if (command.type === 'prompt') {
        child.stdout.write(JSON.stringify({ id: command.id, type: 'response', success: true }) + '\n')
        child.stdout.write(JSON.stringify({ type: 'turn_start' }) + '\n')
        child.stdout.write(JSON.stringify({
          type: 'message_update',
          assistantMessageEvent: { type: 'toolcall_end', toolCall: { id: 'first', name: emittedNames[0], arguments: {} } },
        }) + '\n')
        child.stdout.write(JSON.stringify({
          type: 'message_end', message: { role: 'assistant', content: [
            { type: 'toolCall', id: 'first', name: emittedNames[0], arguments: {} },
            // OMP 18.12.2 runs MCP tools through native read/write calls on
            // xd:// virtual devices — the frame name is the native tool and
            // the real MCP tool name is in arguments.path.
            { type: 'toolCall', id: 'second', name: 'write', arguments: { path: 'xd://mcp__kb_mcp_kb_search', content: '{}' } },
          ] },
        }) + '\n')
        child.stdout.write(JSON.stringify({
          type: 'agent_end', messages: [{ role: 'assistant', stopReason: 'stop', content: [{ type: 'text', text: 'answer' }] }],
        }) + '\n')
      }
    })
    queueMicrotask(() => child.stdout.write('{"type":"ready"}\n'))
    return child
  },
}))

const { OmpEngine } = await import('../server/engines/omp-engine')

test('OMP RPC adapter forwards KB and non-KB tool frames and a successful result', async () => {
  emittedNames = ['mcp__kb_mcp_kb_list', 'mcp__other_kb_list']
  commands = []
  const messages: any[] = []
  for await (const message of new OmpEngine().query({
    prompt: 'test', fullPromptText: 'test', cwd: '.', permissionMode: 'default',
    allowedTools: [], maxTurns: 1, requireKbMcp: true,
  })) messages.push(message)

  const names = messages.flatMap((message) => message.type === 'assistant'
    ? message.message.content.filter((block: any) => block.type === 'tool_use').map((block: any) => block.name)
    : [])
  // First call keeps its frame name; the xd:// device call is remapped from
  // the native `write` frame name to the real mcp__kb-mcp__kb_search tool.
  expect(names).toEqual(['mcp__kb_mcp_kb_list', 'mcp__kb-mcp__kb_search'])
  expect(messages.find((message) => message.type === 'result')).toMatchObject({
    subtype: 'success', is_error: false, result: 'answer',
  })
  expect(commands.indexOf('get_state')).toBeLessThan(commands.indexOf('prompt'))
})
