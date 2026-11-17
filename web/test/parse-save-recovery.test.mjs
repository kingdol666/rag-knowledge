import assert from 'node:assert/strict'
import test from 'node:test'
import { mkdtemp, mkdir, writeFile, readFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createJiti } from 'jiti'

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const jiti = createJiti(import.meta.url, { alias: { '~': webRoot } })
const { saveParsedFiles } = await jiti.import('../server/api/parse/save-parsed-files.post.ts')
const { TreeFileSystemService } = await jiti.import('../server/services/tree-file-system-service.ts')
const { usePDFParser, createParsedSaveRecoveries } = await jiti.import('../composables/usePDFParser.ts')
const { getLargeDocConfig } = await jiti.import('../server/utils/large-doc-split.ts')

// A small persistent fake models upload's content dedup and the physical files
// checked by the real recovery code, without running any KB service.
async function fixture() {
  const base = await mkdtemp(join(tmpdir(), 'parse-recovery-'))
  const project = join(base, 'project')
  const output = join(project, 'backend', 'output')
  const storage = join(base, 'storage')
  const source = join(output, 'images')
  await mkdir(source, { recursive: true })
  await mkdir(join(storage, 'kb'), { recursive: true })
  const roots = { project, output, storage }
  const files = []
  let updates = 0
  let failMetadata = false
  let failMetadataAfterWrite = false
  const service = {
    metadata: { folders: [{ id: 'kb-id', path: 'kb' }, { id: 'other', path: 'kb' }] },
    async uploadFile(parentId, data, name) {
      for (const file of files) {
        if (file.parentId === parentId && (await readFile(join(storage, file.path))).equals(data)) return { ...structuredClone(file), deduped: true }
      }
      const record = { id: String(files.length + 1), name, path: join('kb', name), parentId, metadata: {}, description: '' }
      await writeFile(join(storage, record.path), data)
      files.push(record)
      return structuredClone(record)
    },
    async getFileById(id) { return structuredClone(files.find(file => file.id === id) || null) },
    async updateFile(id, { metadata }) {
      updates++
      if (failMetadata) { failMetadata = false; throw new Error('transient metadata failure') }
      const record = files.find(file => file.id === id)
      record.metadata = JSON.parse(JSON.stringify(metadata))
      if (failMetadataAfterWrite) { failMetadataAfterWrite = false; throw new Error('metadata outcome uncertain') }
      return { ...structuredClone(record), persistence: { tree: true, yaml: true } }
    },
  }
  return { base, output, storage, source, roots, files, service,
    failNextMetadata() { failMetadata = true },
    failNextMetadataAfterWrite() { failMetadataAfterWrite = true },
    get updates() { return updates },
    async save(result, parentId = 'kb-id') { return saveParsedFiles({ parentId, results: [result] }, service, { storagePath: storage, roots }) },
    async cleanup() { await rm(base, { recursive: true, force: true }) },
  }
}

const parsed = { filename: 'paper.pdf', success: true, markdown: 'paper content' }

test('real caller sends only a receipt-bearing retry and never mutates an unrelated duplicate', async () => {
  const f = await fixture()
  const originalFetch = globalThis.fetch
  const sent = []
  try {
    await f.service.uploadFile('kb-id', Buffer.from('existing content'), 'existing.md')
    f.files[0].metadata = { keep: 'unchanged' }
    f.failNextMetadata()
    globalThis.fetch = async (url, init) => {
      assert.equal(url, '/api/parse/save-parsed-files')
      const body = JSON.parse(init.body)
      sent.push(body)
      const result = await saveParsedFiles(body, f.service, { storagePath: f.storage, roots: f.roots })
      return { ok: true, async json() { return result } }
    }
    const caller = usePDFParser()
    const parsedResults = [
      { filename: 'duplicate.pdf', success: true, markdown: 'existing content' },
      { filename: 'paper.pdf', success: true, markdown: 'paper content' },
      { filename: 'bad.pdf', success: false, error: 'parse failed' },
    ]
    const request = {
      parentId: 'kb-id', split: true,
      results: await caller.enrichParsedResultsWithDescriptions(parsedResults, ['duplicate note', ' Custom note ']),
    }
    const first = await caller.retrySaveParsedFiles(request)
    assert.equal(first.savedCount, 0)
    assert.equal(first.partialCount, 1)
    assert.equal(first.existingCount, 1)
    const pending = createParsedSaveRecoveries(request, first)
    assert.equal(pending.length, 1)
    assert.equal(pending[0].results[0].description, 'Custom note')
    const second = await caller.retrySaveParsedFiles(pending[0])
    assert.equal(second.success, true)
    assert.equal(second.savedCount, 1)
    assert.deepEqual(second.files.map(file => file.id), ['2'])
    assert.equal(sent.length, 2)
    assert.deepEqual(sent[1].results[0], { ...sent[0].results[1], recoveryReceipt: first.items[1].recoveryReceipt })
    assert.equal(sent[1].parentId, sent[0].parentId)
    assert.equal(sent[1].split, sent[0].split)
    assert.deepEqual(f.files[0].metadata, { keep: 'unchanged' })
    assert.equal(f.files.length, 2)
  } finally { globalThis.fetch = originalFetch; await f.cleanup() }
})

test('caller fails closed on expired or unavailable receipts and malformed responses', async () => {
  const f = await fixture()
  const originalFetch = globalThis.fetch
  const originalNow = Date.now
  try {
    let now = originalNow()
    Date.now = () => now
    const caller = usePDFParser()
    globalThis.fetch = async (_url, init) => {
      const result = await saveParsedFiles(JSON.parse(init.body), f.service, { storagePath: f.storage, roots: f.roots })
      return { ok: true, async json() { return result } }
    }
    f.failNextMetadata()
    const request = { parentId: 'kb-id', split: true, results: [{ ...parsed, description: 'retained' }] }
    const first = await caller.retrySaveParsedFiles(request)
    const [pending] = createParsedSaveRecoveries(request, first)
    now += 60 * 60 * 1000 + 1
    const expired = await caller.retrySaveParsedFiles(pending)
    assert.equal(expired.savedCount, 0)
    assert.match(expired.items[0].error, /receipt/i)
    assert.equal(createParsedSaveRecoveries(pending, expired).length, 0)
    assert.equal(f.updates, 1)
    const unavailable = await caller.retrySaveParsedFiles({ ...pending, results: [{ ...pending.results[0], recoveryReceipt: 'unknown-after-restart' }] })
    assert.match(unavailable.items[0].error, /receipt/i)
    assert.equal(f.updates, 1)
    assert.throws(() => createParsedSaveRecoveries(request, { ...first, items: [] }), /incomplete/i)
    assert.throws(() => createParsedSaveRecoveries(request, { ...first, savedCount: 9 }), /incomplete/i)
  } finally { Date.now = originalNow; globalThis.fetch = originalFetch; await f.cleanup() }
})

test('caller recovery builder retains the exact request fields and opaque receipt only for the failed item', () => {
  const request = {
    parentId: 'kb-id', split: true, agentPlan: { mode: 'fixed' },
    results: [
      { filename: 'first.pdf', success: true, markdown: 'one', description: 'first' },
      { filename: 'second.pdf', success: true, markdown: 'two', description: 'second', images_dir: 'output/images' },
    ],
  }
  const response = {
    success: false, savedCount: 1, files: [{ id: '1' }], partialCount: 0, partialFiles: [], existingCount: 0, existingFiles: [], failedCount: 1,
    items: [
      { index: 0, filename: 'first.pdf', success: true, files: [{ id: '1' }], createdImages: [] },
      { index: 1, filename: 'second.pdf', success: false, files: [{ id: '2' }], createdImages: [], error: 'metadata failed', recoveryReceipt: 'opaque-secret' },
    ],
  }
  const pending = createParsedSaveRecoveries(request, response)
  assert.equal(pending.length, 1)
  assert.deepEqual(pending[0], {
    parentId: 'kb-id', split: true, agentPlan: { mode: 'fixed' },
    results: [{ filename: 'second.pdf', success: true, markdown: 'two', description: 'second', images_dir: 'output/images', recoveryReceipt: 'opaque-secret' }],
  })
  assert.equal(JSON.stringify(pending).includes('first.pdf'), false)
})

test('metadata failure returns receipt and retry completes the same document', async () => {
  const f = await fixture()
  try {
    await writeFile(join(f.source, 'fig.png'), 'figure')
    const input = { ...parsed, images_dir: f.source }
    f.failNextMetadata()
    const first = await f.save(input)
    assert.equal(first.success, false)
    assert.equal(first.savedCount, 0)
    assert.equal(first.partialCount, 1)
    assert.equal(first.items[0].success, false)
    assert.match(first.items[0].error, /metadata failure/)
    const receipt = first.items[0].recoveryReceipt
    assert.match(receipt, /^[0-9a-f-]{36}$/)
    assert.equal(first.items[0].files[0].id, '1')
    assert.equal(f.files.length, 1)

    const plainRetry = await f.save(input)
    assert.equal(plainRetry.success, false)
    assert.equal(plainRetry.items[0].recoveryReceipt, undefined)
    assert.equal(f.updates, 1)

    const recovered = await f.save({ ...input, recoveryReceipt: receipt })
    assert.equal(recovered.success, true)
    assert.equal(recovered.items[0].success, true)
    assert.equal(recovered.files[0].id, '1')
    assert.equal(recovered.files[0].deduped, undefined)
    assert.deepEqual(f.files[0].metadata.imagePaths, ['images/fig.png'])
    assert.equal(await readFile(join(f.storage, 'kb', 'images', 'fig.png'), 'utf8'), 'figure')
    assert.equal(f.files.length, 1)
    const replay = await f.save({ ...input, recoveryReceipt: receipt })
    assert.equal(replay.success, false)
    assert.match(replay.items[0].error, /receipt/i)
  } finally { await f.cleanup() }
})

test('metadata error after persistence recovers JSON-normalized metadata', async () => {
  const f = await fixture()
  try {
    f.failNextMetadataAfterWrite()
    const first = await f.save(parsed)
    assert.equal(first.success, false)
    assert.match(first.items[0].error, /outcome uncertain/)
    assert.equal(f.files[0].metadata.sourcePdf, 'paper.pdf')
    const retry = await f.save({ ...parsed, recoveryReceipt: first.items[0].recoveryReceipt })
    assert.equal(retry.success, true)
    assert.equal(retry.files[0].id, '1')
    assert.equal(f.files.length, 1)
  } finally { await f.cleanup() }
})

test('image failure after a partial copy can be retried with the receipt', async () => {
  const f = await fixture()
  try {
    await writeFile(join(f.source, 'a.png'), 'first')
    await writeFile(join(f.source, 'z.png'), 'second')
    const images = join(f.storage, 'kb', 'images')
    await mkdir(images)
    await writeFile(join(images, 'z.png'), 'other')
    const input = { ...parsed, images_dir: f.source }
    const first = await f.save(input)
    assert.equal(first.success, false)
    assert.match(first.items[0].error, /collision/i)
    assert.equal(first.items[0].createdImages.length, 1)
    assert.equal(f.updates, 0)
    // Resolve the external collision; no file owned by the endpoint is removed.
    await rm(join(images, 'z.png'))
    const retry = await f.save({ ...input, recoveryReceipt: first.items[0].recoveryReceipt })
    assert.equal(retry.success, true)
    assert.equal(retry.files[0].id, '1')
    assert.deepEqual(f.files[0].metadata.imagePaths, ['images/a.png', 'images/z.png'])
    assert.equal(await readFile(join(images, 'a.png'), 'utf8'), 'first')
    assert.equal(await readFile(join(images, 'z.png'), 'utf8'), 'second')
    assert.equal(f.files.length, 1)
  } finally { await f.cleanup() }
})

test('ordinary dedup remains unmodified with or without images and has no receipt', async () => {
  const f = await fixture()
  try {
    await f.service.uploadFile('kb-id', Buffer.from(parsed.markdown), 'existing.md')
    f.files[0].metadata = { keep: 'untouched' }
    await writeFile(join(f.source, 'fig.png'), 'figure')
    for (const input of [parsed, { ...parsed, images_dir: f.source }]) {
      const result = await f.save(input)
      assert.equal(result.success, false)
      assert.equal(result.items[0].success, false)
      assert.equal(result.items[0].files[0].deduped, true)
      assert.equal(result.items[0].recoveryReceipt, undefined)
      assert.deepEqual(f.files[0].metadata, { keep: 'untouched' })
      assert.equal(f.updates, 0)
    }
    await assert.rejects(readFile(join(f.storage, 'kb', 'images', 'fig.png')))
  } finally { await f.cleanup() }
})

test('split recovery resumes owned parts and refuses a changed plan', async t => {
  const large = getLargeDocConfig()
  if (!large.autoSplit || large.maxChars > 1000000) return t.skip('automatic splitting unavailable in local test config')
  const f = await fixture()
  const oldFetch = globalThis.$fetch
  try {
    const plan = {
      success: true, split: true, source_chars: large.maxChars + 1, max_chars: large.maxChars,
      parts: [
        { part_index: 1, part_count: 2, content: 'first part', description: 'first' },
        { part_index: 2, part_count: 2, content: 'second part', description: 'second' },
      ],
    }
    globalThis.$fetch = async () => structuredClone(plan)
    const input = { filename: 'large.pdf', success: true, markdown: 'x'.repeat(large.maxChars + 1) }
    const save = result => saveParsedFiles({ parentId: 'kb-id', split: true, results: [result] }, f.service, { storagePath: f.storage, roots: f.roots })
    f.failNextMetadata()
    const first = await save(input)
    assert.equal(first.success, false)
    assert.equal(f.files.length, 1)
    const receipt = first.items[0].recoveryReceipt
    plan.parts[0].content = 'different plan'
    const changed = await save({ ...input, recoveryReceipt: receipt })
    assert.equal(changed.success, false)
    assert.match(changed.items[0].error, /split plan changed/i)
    plan.parts[0].content = 'first part'
    const retry = await save({ ...input, recoveryReceipt: receipt })
    assert.equal(retry.success, true)
    assert.equal(f.files.length, 2)
    assert.deepEqual(retry.files.map(file => file.id), ['1', '2'])
    assert.equal(f.files[0].metadata.largeDocSplit.part_index, 1)
    assert.equal(f.files[1].metadata.largeDocSplit.part_index, 2)
  } finally { globalThis.$fetch = oldFetch; await f.cleanup() }
})

test('unsafe source names fail before upload or image copying', async () => {
  const f = await fixture()
  try {
    for (const filename of ['../escape.pdf', 'CON.pdf', 'folder\\\\escape.pdf']) {
      const result = await f.save({ ...parsed, filename, images_dir: f.source })
      assert.equal(result.success, false)
      assert.match(result.items[0].error, /filename/i)
    }
    assert.equal(f.files.length, 0)
    assert.equal(f.updates, 0)
  } finally { await f.cleanup() }
})

test('image filenames are validated before document upload', async () => {
  const f = await fixture()
  try {
    await writeFile(join(f.source, 'good.png'), 'figure')
    await writeFile(join(f.source, 'CON.png'), 'bad')
    const result = await f.save({ ...parsed, images_dir: f.source })
    assert.equal(result.success, false)
    assert.match(result.items[0].error, /filename/i)
    assert.equal(f.files.length, 0)
  } finally { await f.cleanup() }
})

test('recovery rejects a moved destination and a changed document body', async () => {
  const f = await fixture()
  try {
    f.failNextMetadata()
    const first = await f.save(parsed)
    const receipt = first.items[0].recoveryReceipt
    f.service.metadata.folders[0].path = 'moved'
    const moved = await f.save({ ...parsed, recoveryReceipt: receipt })
    assert.equal(moved.success, false)
    assert.match(moved.items[0].error, /destination changed/i)
    f.service.metadata.folders[0].path = 'kb'
    await writeFile(join(f.storage, f.files[0].path), 'modified')
    const changed = await f.save({ ...parsed, recoveryReceipt: receipt })
    assert.equal(changed.success, false)
    assert.match(changed.items[0].error, /content changed/i)
    assert.equal(f.updates, 1)
  } finally { await f.cleanup() }
})

test('receipts reject changed requests, changed targets and different parents', async () => {
  const f = await fixture()
  try {
    f.failNextMetadata()
    const first = await f.save(parsed)
    const receipt = first.items[0].recoveryReceipt
    for (const [input, parent] of [
      [{ ...parsed, markdown: 'different', recoveryReceipt: receipt }, 'kb-id'],
      [{ ...parsed, recoveryReceipt: receipt }, 'other'],
      [{ ...parsed, recoveryReceipt: 'invented' }, 'kb-id'],
    ]) {
      const result = await f.save(input, parent)
      assert.equal(result.success, false)
      assert.match(result.items[0].error, /receipt/i)
    }
    f.files[0].metadata = { changed: true }
    const changed = await f.save({ ...parsed, recoveryReceipt: receipt })
    assert.equal(changed.success, false)
    assert.match(changed.items[0].error, /target changed/i)
    assert.deepEqual(f.files[0].metadata, { changed: true })
    assert.equal(f.updates, 1)
  } finally { await f.cleanup() }
})

test('real TreeFileSystemService reports YAML persistence failure without consuming recovery or indexing', async () => {
  const base = await mkdtemp(join(tmpdir(), 'parse-real-tree-yaml-'))
  const service = new TreeFileSystemService(base)
  let indexCalls = 0
  service.indexDocument = async () => { indexCalls++ }
  const roots = { project: base, output: join(base, 'output'), storage: base }
  await mkdir(roots.output, { recursive: true })
  try {
    await service.initialize()
    const folder = await service.createFolder({ name: 'kb', isKnowledgeBase: true })
    const addDocument = service.yamlService.addDocument.bind(service.yamlService)
    let failYamlWrite = true
    service.yamlService.addDocument = async (knowledgeBaseId, fileInfo) => {
      if (failYamlWrite && fileInfo?.metadata?.sourcePdf) {
        failYamlWrite = false
        throw new Error('mock YAML write failure')
      }
      return addDocument(knowledgeBaseId, fileInfo)
    }

    const request = { parentId: folder.id, results: [{ ...parsed, description: 'YAML failure' }] }
    const failed = await saveParsedFiles(request, service, { storagePath: base, roots })
    assert.equal(failed.success, false)
    assert.equal(failed.savedCount, 0)
    assert.equal(failed.partialCount, 1)
    assert.equal(failed.files.length, 0)
    assert.equal(failed.items[0].success, false)
    assert.match(failed.items[0].error, /YAML|metadata persistence/i)
    const receipt = failed.items[0].recoveryReceipt
    assert.match(receipt, /^[0-9a-f-]{36}$/)
    assert.equal(indexCalls, 0)

    // The document was physically uploaded, but the failed update is not a save.
    assert.equal(await service.getFileCount(), 1)
    assert.equal((await service.yamlService.read('kb')).documents.length, 0)

    service.yamlService.addDocument = addDocument
    const recovered = await saveParsedFiles({ ...request, results: [{ ...request.results[0], recoveryReceipt: receipt }] }, service, { storagePath: base, roots })
    assert.equal(recovered.success, true, JSON.stringify(recovered))
    assert.equal(recovered.savedCount, 1)
    assert.equal(recovered.items[0].success, true)
    assert.equal(indexCalls, 0)

    const replay = await saveParsedFiles({ ...request, results: [{ ...request.results[0], recoveryReceipt: receipt }] }, service, { storagePath: base, roots })
    assert.equal(replay.success, false)
    assert.match(replay.items[0].error, /receipt/i)
  } finally {
    await rm(base, { recursive: true, force: true })
  }
})

test('real TreeFileSystemService reports tree disk persistence failure and retries partial save', async () => {
  const base = await mkdtemp(join(tmpdir(), 'parse-real-tree-disk-'))
  const service = new TreeFileSystemService(base)
  let indexCalls = 0
  service.indexDocument = async () => { indexCalls++ }
  const roots = { project: base, output: join(base, 'output'), storage: base }
  await mkdir(roots.output, { recursive: true })
  try {
    await service.initialize()
    const folder = await service.createFolder({ name: 'kb', isKnowledgeBase: true })
    const saveMetadata = service.saveMetadata.bind(service)
    let metadataWrites = 0
    service.saveMetadata = async () => {
      metadataWrites++
      if (metadataWrites === 2) throw new Error('mock tree metadata disk failure')
      await saveMetadata()
    }

    const request = { parentId: folder.id, results: [{ ...parsed, description: 'tree failure' }] }
    const failed = await saveParsedFiles(request, service, { storagePath: base, roots })
    assert.equal(failed.success, false)
    assert.equal(failed.savedCount, 0)
    assert.equal(failed.partialCount, 1)
    assert.equal(failed.files.length, 0)
    assert.match(failed.items[0].error, /tree metadata|disk failure/i)
    const receipt = failed.items[0].recoveryReceipt
    assert.match(receipt, /^[0-9a-f-]{36}$/)
    assert.equal(indexCalls, 0)

    // YAML was written, but the tree write failed; the response must remain partial.
    assert.equal((await service.yamlService.read('kb')).documents.length, 1)
    const persistedTreeBeforeRetry = JSON.parse(await readFile(join(base, '.tree-fs.json'), 'utf8'))
    assert.equal(persistedTreeBeforeRetry.files.length, 1)

    const recovered = await saveParsedFiles({ ...request, results: [{ ...request.results[0], recoveryReceipt: receipt }] }, service, { storagePath: base, roots })
    assert.equal(recovered.success, true)
    assert.equal(recovered.savedCount, 1)
    assert.equal(recovered.items[0].success, true)
    assert.equal(indexCalls, 0)

    const persistedTree = JSON.parse(await readFile(join(base, '.tree-fs.json'), 'utf8'))
    assert.equal(persistedTree.files.length, 1)
    const persistedYaml = await service.yamlService.read('kb')
    assert.equal(persistedYaml.documents.length, 1)
    assert.equal(persistedYaml.documents[0].metadata.sourcePdf, 'paper.pdf')
  } finally {
    await rm(base, { recursive: true, force: true })
  }
})
