import assert from 'node:assert/strict'
import test from 'node:test'
import { mkdtemp, mkdir, writeFile, readFile, readdir, symlink, realpath, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createJiti } from 'jiti'

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const jiti = createJiti(import.meta.url, { alias: { '~': webRoot } })
const { PDFParseService, resolveParseArtifact, readParseArtifact } = await jiti.import('../server/services/pdf-parse-service.ts')
const { copyImagesToKb, saveParsedFiles } = await jiti.import('../server/api/parse/save-parsed-files.post.ts')

const rootsFor = (project, output, storage) => ({ project, output, storage })

test('batch form uses default_output while single uses output_dir', async () => {
  const originalFetch = globalThis.fetch
  const requests = []
  globalThis.fetch = async (url, options) => {
    requests.push({ url, form: options.body })
    return new Response(JSON.stringify(url.endsWith('/parse/file/vt') && !url.includes('/batch/')
      ? { success: false }
      : { total: 1, successful: 1, failed: 0, results: [] }), { status: 200 })
  }
  try {
    const service = new PDFParseService()
    await service.parseFileVT(Buffer.from('pdf'), 'a.pdf', { output_dir: 'backend/output/test' })
    await service.batchParseFilesVT([{ buffer: Buffer.from('pdf'), filename: 'a.pdf' }], { output_dir: 'backend/output/test' })
    await service.batchParseFilesVTStream([{ buffer: Buffer.from('pdf'), filename: 'a.pdf' }], { output_dir: 'backend/output/test' })
    assert.equal(requests[0].form.get('output_dir'), 'backend/output/test')
    assert.equal(requests[0].form.get('default_output'), null)
    assert.equal(requests[1].form.get('default_output'), 'backend/output/test')
    assert.equal(requests[1].form.get('output_dir'), null)
    assert.equal(requests[2].form.get('default_output'), 'backend/output/test')
    assert.equal(requests[2].form.get('output_dir'), null)
  } finally { globalThis.fetch = originalFetch }
})

test('artifact paths allow backend output and explicitly configured external storage only', async t => {
  const base = await mkdtemp(join(tmpdir(), 'parse-path-'))
  try {
    const project = join(base, 'project')
    const output = join(project, 'backend', 'output')
    const externalStorage = join(base, 'configured-tree-storage')
    const outside = join(base, 'untrusted')
    await Promise.all([mkdir(output, { recursive: true }), mkdir(externalStorage), mkdir(outside)])
    const allowed = join(output, 'test.md')
    const external = join(externalStorage, 'configured.md')
    const secret = join(outside, 'secret.md')
    await Promise.all([
      writeFile(allowed, 'allowed'), writeFile(external, 'configured'), writeFile(secret, 'secret'),
    ])
    const paths = rootsFor(project, output, externalStorage)
    assert.equal(await resolveParseArtifact(allowed, paths), await realpath(allowed))
    assert.equal(await resolveParseArtifact(external, paths), await realpath(external))
    assert.equal(await resolveParseArtifact(secret, paths), null)
    assert.equal(await resolveParseArtifact(join(base, 'configured-tree-storage-sibling', 'secret.md'), paths), null)
    assert.equal(await resolveParseArtifact('test.md', paths), null)
    assert.equal(await resolveParseArtifact(join(project, 'other.md'), paths), null)
    assert.equal(await resolveParseArtifact(join(output, '..', 'escape.md'), paths), null)

    const link = join(output, 'escape')
    try { await symlink(outside, link, 'junction') } catch (err) {
      if (['EPERM', 'EACCES', 'ENOSYS'].includes(err.code)) return t.diagnostic('symlinks unavailable')
      throw err
    }
    assert.equal(await resolveParseArtifact(join(link, 'secret.md'), paths), null)
  } finally { await rm(base, { recursive: true, force: true }) }
})

test('a missing parse root does not disable the independent configured storage root', async () => {
  const base = await mkdtemp(join(tmpdir(), 'parse-missing-root-'))
  try {
    const project = join(base, 'project')
    const storage = join(base, 'external-storage')
    await Promise.all([mkdir(project), mkdir(storage)])
    const external = join(storage, 'doc.md')
    await writeFile(external, 'stored')
    assert.equal(await resolveParseArtifact(external, rootsFor(project, join(project, 'missing-output'), storage)), await realpath(external))
  } finally { await rm(base, { recursive: true, force: true }) }
})

test('artifact read rejects a source mutated between validation and opening', async () => {
  const base = await mkdtemp(join(tmpdir(), 'parse-mutation-'))
  try {
    const project = join(base, 'project')
    const output = join(project, 'backend', 'output')
    const storage = join(base, 'external-storage')
    await Promise.all([mkdir(output, { recursive: true }), mkdir(storage)])
    const artifactPath = join(output, 'test.md')
    const roots = rootsFor(project, output, storage)
    await writeFile(artifactPath, 'original')
    let invoked = false
    const artifact = await readParseArtifact(artifactPath, roots, {
      beforeOpen: async path => {
        invoked = true
        await writeFile(path, 'replacement-content')
      },
    })
    assert.equal(invoked, true)
    assert.equal(artifact, null)
  } finally { await rm(base, { recursive: true, force: true }) }
})

test('image copy refuses a swapped destination junction', async t => {
  const base = await mkdtemp(join(tmpdir(), 'parse-copy-'))
  try {
    const project = join(base, 'project')
    const output = join(project, 'backend', 'output')
    const storage = join(base, 'configured-storage')
    const imageDir = join(output, 'images-src')
    const victim = join(base, 'outside-target')
    await Promise.all([mkdir(imageDir, { recursive: true }), mkdir(storage), mkdir(victim)])
    await writeFile(join(imageDir, 'fig.png'), 'image-bytes')
    const roots = rootsFor(project, output, storage)
    let swapped = false
    let symlinkUnavailable = false
    let copyError
    try {
      await copyImagesToKb(imageDir, 'kb', 'doc.md', storage, roots, {
        beforeDestinationOpen: async () => {
        if (swapped) return
        swapped = true
        await rm(join(storage, 'kb', 'images'), { recursive: true, force: true })
        try { await symlink(victim, join(storage, 'kb', 'images'), 'junction') } catch (err) {
          if (['EPERM', 'EACCES', 'ENOSYS'].includes(err.code)) {
            symlinkUnavailable = true
            return
          }
          throw err
        }
        },
      })
    } catch (err) { copyError = err }
    if (symlinkUnavailable) return t.skip('symlinks unavailable')
    assert.equal(swapped, true)
    assert.equal(copyError?.statusCode, 422)
    assert.deepEqual(await readdir(victim), [])
  } finally { await rm(base, { recursive: true, force: true }) }
})

test('image copy exclusively creates safe targets and will not overwrite existing files', async () => {
  const base = await mkdtemp(join(tmpdir(), 'parse-copy-safe-'))
  try {
    const project = join(base, 'project')
    const output = join(project, 'backend', 'output')
    const storage = join(base, 'configured-storage')
    const imageDir = join(output, 'images-src')
    await Promise.all([mkdir(imageDir, { recursive: true }), mkdir(storage)])
    await writeFile(join(imageDir, 'fig.png'), 'image-bytes')
    const roots = rootsFor(project, output, storage)
    assert.deepEqual(await copyImagesToKb(imageDir, 'kb', 'doc.md', storage, roots), ['images/fig.png'])
    assert.equal(await readFile(join(storage, 'kb', 'images', 'fig.png'), 'utf8'), 'image-bytes')
    const differentSource = join(output, 'other-images')
    await mkdir(differentSource)
    await writeFile(join(differentSource, 'fig.png'), 'different-bytes')
    await assert.rejects(
      copyImagesToKb(differentSource, 'kb', 'doc.md', storage, roots),
      err => err?.statusCode === 409,
    )
    assert.equal(await readFile(join(storage, 'kb', 'images', 'fig.png'), 'utf8'), 'image-bytes')
  } finally { await rm(base, { recursive: true, force: true }) }
})

test('concurrent same-name images with different bytes have exactly one successful publisher', async () => {
  const base = await mkdtemp(join(tmpdir(), 'parse-copy-race-'))
  try {
    const project = join(base, 'project')
    const output = join(project, 'backend', 'output')
    const storage = join(base, 'storage')
    const sourceA = join(output, 'a')
    const sourceB = join(output, 'b')
    await Promise.all([mkdir(sourceA, { recursive: true }), mkdir(sourceB, { recursive: true }), mkdir(storage)])
    await Promise.all([writeFile(join(sourceA, 'fig.png'), 'first-image'), writeFile(join(sourceB, 'fig.png'), 'second-image')])
    const roots = rootsFor(project, output, storage)
    let arrivals = 0
    let release
    const gate = new Promise(resolve => { release = resolve })
    const hooks = { beforeDestinationOpen: async () => { if (++arrivals === 2) release(); await gate } }
    const results = await Promise.allSettled([
      copyImagesToKb(sourceA, 'kb', 'a.md', storage, roots, hooks),
      copyImagesToKb(sourceB, 'kb', 'b.md', storage, roots, hooks),
    ])
    assert.equal(results.filter(r => r.status === 'fulfilled').length, 1)
    const failed = results.find(r => r.status === 'rejected')
    assert.equal(failed?.reason?.statusCode, 409)
    const winner = results[0].status === 'fulfilled' ? 'first-image' : 'second-image'
    assert.equal(await readFile(join(storage, 'kb', 'images', 'fig.png'), 'utf8'), winner)
    assert.deepEqual(await readdir(join(storage, 'kb', 'images')), ['fig.png'])
  } finally { await rm(base, { recursive: true, force: true }) }
})

test('default output links are rejected even when the target is configured storage', async t => {
  const base = await mkdtemp(join(tmpdir(), 'parse-root-link-'))
  try {
    const project = join(base, 'project')
    const backend = join(project, 'backend')
    const output = join(backend, 'output')
    const storage = join(base, 'storage')
    await Promise.all([mkdir(backend, { recursive: true }), mkdir(storage)])
    await writeFile(join(storage, 'doc.md'), 'external')
    try { await symlink(storage, output, 'junction') } catch (error) {
      if (['EPERM', 'EACCES', 'ENOSYS'].includes(error.code)) return t.skip('symlinks unavailable')
      throw error
    }
    const roots = rootsFor(project, output, storage)
    assert.equal(await resolveParseArtifact(join(output, 'doc.md'), roots), null)
    assert.equal(await resolveParseArtifact(join(storage, 'doc.md'), roots), await realpath(join(storage, 'doc.md')))
    await rm(output)
    const internal = join(project, 'other')
    await mkdir(internal)
    await writeFile(join(internal, 'doc.md'), 'internal')
    await symlink(internal, output, 'junction')
    assert.equal(await resolveParseArtifact(join(output, 'doc.md'), roots), null)
  } finally { await rm(base, { recursive: true, force: true }) }
})

test('batch save reports prior successes, partial images, failed uploads and metadata errors', async () => {
  const base = await mkdtemp(join(tmpdir(), 'parse-save-batch-'))
  try {
    const project = join(base, 'project')
    const output = join(project, 'backend', 'output')
    const storage = join(base, 'storage')
    const source = join(output, 'images')
    const dest = join(storage, 'kb', 'images')
    await Promise.all([mkdir(source, { recursive: true }), mkdir(dest, { recursive: true })])
    await Promise.all([
      writeFile(join(source, 'a.png'), 'new'),
      writeFile(join(source, 'z.png'), 'conflicting'),
      writeFile(join(dest, 'z.png'), 'preexisting'),
    ])
    let nextId = 0
    const service = {
      metadata: { folders: [{ id: 'kb-id', path: 'kb' }] },
      async uploadFile(parent, data, name) {
        if (name === 'upload.md') throw new Error('upload error')
        return { id: String(++nextId), name, metadata: {} }
      },
      async updateFile(id, { metadata }) {
        if (id === '3') throw new Error('metadata error')
        return { id, name: 'ok.md', metadata, persistence: { tree: true, yaml: true } }
      },
    }
    const result = await saveParsedFiles({ parentId: 'kb-id', results: [
      { filename: 'ok.pdf', success: true, markdown: 'one' },
      { filename: 'collision.pdf', success: true, markdown: 'two', images_dir: source },
      { filename: 'meta.pdf', success: true, markdown: 'three' },
      { filename: 'upload.pdf', success: true, markdown: 'four' },
      { filename: 'absent.pdf', success: true },
      { filename: 'parse.pdf', success: false, error: 'parse error' },
      { filename: 'last.pdf', success: true, markdown: 'five' },
    ] }, service, { storagePath: storage, roots: rootsFor(project, output, storage) })
    assert.equal(result.success, false)
    assert.equal(result.savedCount, 2)
    assert.equal(result.partialCount, 2)
    assert.equal(result.existingCount, 0)
    assert.deepEqual(result.files.map(file => file.id), ['1', '4'])
    assert.deepEqual(result.partialFiles.map(file => file.id), ['2', '3'])
    assert.equal(result.failedCount, 5)
    assert.deepEqual(result.items.map(i => i.success), [true, false, false, false, false, false, true])
    assert.match(result.items[1].error, /collision/i)
    assert.deepEqual(result.items[1].createdImages.map(i => i.path), [join(dest, 'a.png')])
    assert.ok(result.items[1].createdImages[0].identity.ino)
    assert.equal(await readFile(join(dest, 'z.png'), 'utf8'), 'preexisting')
    assert.equal(await readFile(join(dest, 'a.png'), 'utf8'), 'new')
    assert.equal(result.items[1].files[0].id, '2')
    assert.equal(result.items[2].files[0].id, '3')
    assert.match(result.items[2].error, /metadata error/)
    assert.match(result.items[3].error, /uncertain/)
    assert.match(result.items[4].error, /markdown/i)
    assert.equal(result.items[5].error, 'parse error')
  } finally { await rm(base, { recursive: true, force: true }) }
})

test('content-deduplicated documents are reported as incomplete without modifying existing metadata', async () => {
  let updates = 0
  const service = {
    metadata: { folders: [{ id: 'kb-id', path: 'kb' }] },
    async uploadFile() { return { id: 'existing', name: 'existing.md', metadata: { keep: true }, deduped: true } },
    async updateFile() { updates++; throw new Error('must not update') },
  }
  const result = await saveParsedFiles({ parentId: 'kb-id', results: [{ filename: 'a.pdf', success: true, markdown: 'same' }] }, service)
  assert.equal(result.success, false)
  assert.equal(result.failedCount, 1)
  assert.equal(result.items[0].success, false)
  assert.match(result.items[0].error, /deduplicated|completeness/i)
  assert.equal(result.savedCount, 0)
  assert.equal(result.existingCount, 1)
  assert.equal(result.existingFiles[0].id, 'existing')
  assert.equal(result.existingFiles[0].deduped, true)
  assert.equal(updates, 0)
})

test('artifact read uses the validated descriptor for stable content', async () => {
  const base = await mkdtemp(join(tmpdir(), 'parse-read-'))
  try {
    const project = join(base, 'project')
    const output = join(project, 'backend', 'output')
    const storage = join(base, 'external-storage')
    await Promise.all([mkdir(output, { recursive: true }), mkdir(storage)])
    const artifactPath = join(output, 'test.md')
    await writeFile(artifactPath, 'safe markdown')
    const result = await readParseArtifact(artifactPath, rootsFor(project, output, storage))
    assert.equal(result?.path, await realpath(artifactPath))
    assert.equal(result?.buffer.toString('utf8'), 'safe markdown')
  } finally { await rm(base, { recursive: true, force: true }) }
})
