import assert from 'node:assert/strict'
import test from 'node:test'
import { mkdtemp, mkdir, readFile, rm, stat } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createJiti } from 'jiti'

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const jiti = createJiti(import.meta.url, { alias: { '~': webRoot } })
const { assertSafeFilename } = await jiti.import('../server/utils/safe-filename.ts')
const { TreeFileSystemService } = await jiti.import('../server/services/tree-file-system-service.ts')
const { saveParsedFiles } = await jiti.import('../server/api/parse/save-parsed-files.post.ts')

const unsafeNames = [
  '../escaped.md',
  '../../outside-storage.md',
  '..\\escaped.md',
  '/absolute.md',
  '\\rooted.md',
  'C:\\escaped.md',
  'C:drive-relative.md',
  '\\\\server\\share\\escaped.md',
  'CON.txt',
  'nul.md',
  'LPT1.log',
  'name:stream.md',
  'bad?.md',
  'trailing.',
  'trailing ',
  'control\u0001name.md',
]

async function createTestService(t) {
  const sandbox = await mkdtemp(join(tmpdir(), 'safe-filename-sink-'))
  t.after(() => rm(sandbox, { recursive: true, force: true }))
  const base = join(sandbox, 'storage')
  await mkdir(base)
  const service = new TreeFileSystemService(base)
  await service.initialize()
  const folder = await service.createFolder({ name: 'kb', description: 'test', isKnowledgeBase: false })
  return { base, service, folder }
}

test('portable filename validator rejects traversal and Windows-unsafe basenames but permits Unicode', () => {
  for (const name of unsafeNames) assert.throws(() => assertSafeFilename(name), /Invalid filename/)
  assert.doesNotThrow(() => assertSafeFilename('中文知识库-研究记录.md'))
  assert.doesNotThrow(() => assertSafeFilename('report (1).md'))
})

test('TreeFileSystemService upload sink rejects unsafe names before writing outside storage', async t => {
  const { base, service, folder } = await createTestService(t)
  const outsideCandidates = [
    resolve(base, '..', 'escaped.md'),
    resolve(base, '..', 'outside-storage.md'),
    resolve(base, '..', 'absolute.md'),
    resolve(base, '..', 'rooted.md'),
  ]

  for (const name of unsafeNames) {
    await assert.rejects(service.uploadFile(folder.id, Buffer.from('must not be written'), name), /Invalid filename/)
  }

  for (const path of outsideCandidates) {
    await assert.rejects(stat(path), { code: 'ENOENT' })
  }
  assert.deepEqual(service['metadata'].files, [])

  const saved = await service.uploadFile(folder.id, Buffer.from('合法内容'), '中文知识库-研究记录.md')
  assert.equal(saved.name, '中文知识库-研究记录.md')
  assert.equal(await readFile(join(base, 'kb', saved.name), 'utf8'), '合法内容')
})

test('inline markdown parse save rejects traversal source_filename without writing outside storage', async t => {
  const { base, service, folder } = await createTestService(t)
  const outsidePath = resolve(base, '..', 'parse-escape.md')
  const escapedKbPath = join(base, 'parse-escape.md')
  const result = await saveParsedFiles({
    parentId: folder.id,
    results: [
      { filename: 'fallback.pdf', source_filename: '../parse-escape.pdf', success: true, markdown: 'bad source' },
      { filename: '../../parse-escape.pdf', success: true, markdown: 'bad fallback' },
    ],
  }, service, { storagePath: base })

  assert.equal(result.success, false)
  assert.equal(result.savedCount, 0)
  assert.equal(result.failedCount, 2)
  for (const item of result.items) assert.match(item.error, /Invalid filename/)
  await assert.rejects(stat(outsidePath), { code: 'ENOENT' })
  await assert.rejects(stat(escapedKbPath), { code: 'ENOENT' })
  assert.deepEqual(service['metadata'].files, [])
})

test('inline markdown parse save preserves legitimate Chinese source filenames', async t => {
  const { base, service, folder } = await createTestService(t)
  const result = await saveParsedFiles({
    parentId: folder.id,
    results: [{
      filename: 'fallback.pdf',
      source_filename: '中文研究资料.pdf',
      success: true,
      markdown: '# 测试内容',
    }],
  }, service, { storagePath: base })

  assert.equal(result.success, true)
  assert.equal(result.files[0].name, '中文研究资料.md')
  assert.equal(await readFile(join(base, 'kb', '中文研究资料.md'), 'utf8'), '# 测试内容')
})
