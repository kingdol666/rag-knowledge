import { defineEventHandler, readBody, createError, setResponseHeader } from 'h3'
import { constants } from 'fs'
import { createHash, randomUUID } from 'crypto'
import { isDeepStrictEqual } from 'util'
import { basename, extname, isAbsolute, join, relative, resolve, sep } from 'path'
import { lstat, mkdir, open, readdir, realpath, link, unlink } from 'fs/promises'
import { getTreeFileSystemService } from '~/server/utils/tree-service'
import { getTreeStorageAbsolutePath } from '~/server/utils/runtime-paths'
import { readParseArtifact, resolveParseArtifact } from '~/server/services/pdf-parse-service'
import type { ParseArtifactRoots } from '~/server/services/pdf-parse-service'
import { getLargeDocConfig, buildPartDescription, requestSplitPlan } from '~/server/utils/large-doc-split'
import type { BatchParsePDFFileVTItem } from '~/types/pdf-parse'
import { assertSafeFilename } from '~/server/utils/safe-filename'

// Recovery receipts are deliberately opaque and process-local. Losing one (or
// restarting the server) fails closed instead of guessing ownership from a hash.
type RecoveryFile = { key: string; hash: string; id: string; path: string; name: string; parentId: string | null; initialMetadata: unknown; intendedMetadata?: any }
type Recovery = { fingerprint: string; files: RecoveryFile[]; expires: number; busy: boolean; folderId?: string; folderPath?: string; splitPlanHash?: string }
const recoveries = new Map<string, Recovery>()
const recoveryTtl = 60 * 60 * 1000

function recoveryFingerprint(parentId: string, result: ParsedFileResult, split: boolean, agentPlan: unknown, storagePath: string): string {
  const { recoveryReceipt: _receipt, ...original } = result
  return createHash('sha256').update(JSON.stringify([parentId, original, split, agentPlan, resolve(storagePath)])).digest('hex')
}

function persistedMetadata(value: unknown): unknown {
  // Tree metadata is persisted as JSON; undefined fields disappear on reload.
  return value === undefined ? undefined : JSON.parse(JSON.stringify(value))
}

function sameValue(a: unknown, b: unknown): boolean {
  return isDeepStrictEqual(persistedMetadata(a), persistedMetadata(b))
}

function pruneRecoveries(): void {
  for (const [token, recovery] of recoveries) {
    if (!recovery.busy && recovery.expires < Date.now()) recoveries.delete(token)
  }
  while (recoveries.size >= 1000) {
    const oldest = [...recoveries].find(([, recovery]) => !recovery.busy)
    if (!oldest) throw new Error('Recovery receipt capacity exhausted')
    recoveries.delete(oldest[0])
  }
}

interface ParsedFileResult extends BatchParsePDFFileVTItem {
  description?: string
  /** Opaque receipt from a failed save of this exact parse result. */
  recoveryReceipt?: string
}

interface SaveParsedFilesRequest {
  parentId: string
  results: ParsedFileResult[]
  split?: boolean
  agentPlan?: Record<string, unknown>
}

function within(path: string, root: string): boolean {
  const rel = relative(root, path)
  return rel === '' || (rel !== '..' && !rel.startsWith(`..${sep}`) && !isAbsolute(rel))
}

function sameIdentity(a: { dev: number; ino: number }, b: { dev: number; ino: number }): boolean {
  return a.dev === b.dev && a.ino === b.ino
}

async function validateImageFilenames(imagesDir: string | undefined, roots?: ParseArtifactRoots): Promise<void> {
  if (!imagesDir) return
  const sourceDir = await resolveParseArtifact(imagesDir, roots)
  if (!sourceDir) throw new Error('Image source directory is invalid or has changed')
  const info = await lstat(sourceDir)
  if (!info.isDirectory() || info.isSymbolicLink()) throw new Error('Invalid image source directory')
  const imageName = /\.(jpg|jpeg|png|gif|bmp|webp|svg|tif|tiff)$/i
  const entries = await readdir(sourceDir, { withFileTypes: true })
  for (const entry of entries) {
    if (!imageName.test(entry.name)) continue
    if (!entry.isFile()) throw new Error('Image source contains a link or non-file')
    assertSafeFilename(entry.name)
  }
}

function samePath(a: string, b: string): boolean {
  return process.platform === 'win32' ? a.toLowerCase() === b.toLowerCase() : a === b
}

/** Reject links/junctions in the destination path, not just escapes after realpath. */
async function checkedDestinationDirectory(storagePath: string, folderPath: string): Promise<string> {
  if (isAbsolute(folderPath) || folderPath.includes('\0') || folderPath.split(/[\\/]/).includes('..')) throw new Error('Invalid destination folder')
  const root = await realpath(storagePath)
  const target = resolve(root, folderPath, 'images')
  if (!within(target, root)) throw new Error('Destination outside storage root')
  let current = root
  for (const segment of relative(root, target).split(sep).filter(Boolean)) {
    current = join(current, segment)
    try {
      await mkdir(current)
    } catch (error: any) {
      if (error.code !== 'EEXIST') throw error
    }
    const info = await lstat(current)
    if (info.isSymbolicLink() || !info.isDirectory() || !samePath(await realpath(current), current)) {
      throw new Error('Destination directory is a link or has changed')
    }
  }
  return target
}

/** Copy from verified descriptors into exclusively created destination files.
 * Existing files are deliberately never overwritten, including symlinks and hardlinks.
 * Node does not expose a portable Windows directory-handle-relative create API,
 * so a hostile parent junction swap between final recheck and create is an
 * unavoidable narrow TOCTOU window; exclusive create and descriptor-based write
 * ensure the final component itself is never followed or replaced.
 */
export async function copyImagesToKb(
  imagesDir: string | undefined,
  kbFolderPath: string,
  _docFileName: string,
  storagePath = getTreeStorageAbsolutePath(),
  roots?: ParseArtifactRoots,
  hooks: {
    beforeDestinationOpen?: (path: string) => Promise<void>
    onImage?: (path: string, identity: { dev: number; ino: number }) => void
  } = {},
): Promise<string[]> {
  if (!imagesDir) return []
  const sourceDir = await resolveParseArtifact(imagesDir, roots)
  if (!sourceDir) throw createError({ statusCode: 422, statusMessage: 'Invalid or changed image source directory' })
  let imageFiles: string[]
  try {
    const sourceInfo = await lstat(sourceDir)
    if (!sourceInfo.isDirectory() || sourceInfo.isSymbolicLink()) throw new Error('Invalid image source directory')
    const entries = await readdir(sourceDir, { withFileTypes: true })
    if (!samePath(await realpath(sourceDir), sourceDir) || !sameIdentity(sourceInfo, await lstat(sourceDir))) throw new Error('Image source directory changed')
    const imageName = /\.(jpg|jpeg|png|gif|bmp|webp|svg|tif|tiff)$/i
    if (entries.some(e => imageName.test(e.name) && !e.isFile())) throw new Error('Image source contains a link or non-file')
    imageFiles = entries
      .filter(e => e.isFile() && imageName.test(e.name))
      .map(e => {
        assertSafeFilename(e.name)
        return e.name
      })
  } catch (err: any) {
    throw createError({ statusCode: 422, statusMessage: `Failed to read image source directory: ${err?.message || err}` })
  }
  if (!imageFiles.length) return []

  const relativePaths: string[] = []
  for (const imgName of imageFiles) {
    try {
      // Validate every source image independently, including its current parents.
      const artifact = await readParseArtifact(join(sourceDir, imgName), roots)
      if (!artifact || !samePath(artifact.path, join(sourceDir, imgName))) throw new Error('Image source changed or is unsafe')
      const targetDir = await checkedDestinationDirectory(storagePath, kbFolderPath)
      const dirInfo = await lstat(targetDir)
      // Revalidate immediately before creating, and again before writing. O_EXCL
      // prevents following an existing final-component link (including on Windows).
      if (!samePath(await checkedDestinationDirectory(storagePath, kbFolderPath), targetDir)
          || !sameIdentity(dirInfo, await lstat(targetDir))) throw new Error('Image destination changed')
      const dstPath = join(targetDir, imgName)
      const temporaryPath = join(targetDir, `.parse-image-${randomUUID()}.tmp`)
      await hooks.beforeDestinationOpen?.(dstPath)
      if (!samePath(await checkedDestinationDirectory(storagePath, kbFolderPath), targetDir)
          || !sameIdentity(dirInfo, await lstat(targetDir))
          || !await resolveParseArtifact(join(sourceDir, imgName), roots)) throw new Error('Image paths changed')

      // Prepare a complete private file before publishing its name. Hard-linking
      // is an atomic no-replace operation, so another save never sees partial data.
      const handle = await open(temporaryPath, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL, 0o600)
      let tempIdentity: { dev: number; ino: number } | undefined
      try {
        const created = await handle.stat()
        const current = await lstat(temporaryPath)
        tempIdentity = created
        if (!created.isFile() || current.isSymbolicLink() || !sameIdentity(created, current)
            || !samePath(await realpath(targetDir), targetDir)
            || !sameIdentity(dirInfo, await lstat(targetDir))) throw new Error('Image destination changed')
        await handle.writeFile(artifact.buffer)
        await handle.close()
        if (!samePath(await checkedDestinationDirectory(storagePath, kbFolderPath), targetDir)
            || !sameIdentity(dirInfo, await lstat(targetDir))
            || !sameIdentity(created, await lstat(temporaryPath))) throw new Error('Image destination changed')
        let published = false
        try {
          await link(temporaryPath, dstPath)
          published = true
        } catch (error: any) {
          if (error?.code !== 'EEXIST') throw error
          const existing = await readParseArtifact(dstPath, roots)
          if (!existing || !samePath(existing.path, dstPath) || !existing.buffer.equals(artifact.buffer)
              || !samePath(await checkedDestinationDirectory(storagePath, kbFolderPath), targetDir)
              || !sameIdentity(dirInfo, await lstat(targetDir))) {
            throw createError({ statusCode: 409, statusMessage: `Image name collision or unsafe destination: ${imgName}` })
          }
        }
        if (published) hooks.onImage?.(dstPath, { dev: created.dev, ino: created.ino })
        relativePaths.push(`images/${imgName}`)
      } finally {
        await handle.close().catch(() => undefined)
        // Only unlink the exact temporary file we created, and only while the
        // directory is still the one that was validated.
        try {
          if (tempIdentity && samePath(await realpath(targetDir), targetDir)
              && sameIdentity(dirInfo, await lstat(targetDir))
              && sameIdentity(tempIdentity, await lstat(temporaryPath))) await unlink(temporaryPath)
        } catch { /* changed or already removed; do not unlink an untrusted path */ }
      }
    } catch (err: any) {
      if (err?.statusCode) throw err
      throw createError({ statusCode: 422, statusMessage: `Failed to safely copy image ${imgName}: ${err?.message || err}` })
    }
  }
  return relativePaths
}

/**
 * POST /api/parse/save-parsed-files
 *
 * Saves parsed markdown files into the file system tree, copies associated
 * images to the KB's images/ folder, and writes metadata
 * (.tree-fs.json + .knowledge-base.yml with file ID + image paths).
 *
 * On a partial failure, items[].recoveryReceipt is an opaque, scoped bearer
 * capability. Retry the identical result with result.recoveryReceipt set; it is
 * valid for one hour in the same server process and is consumed on success. Ordinary dedup is reported as
 * incomplete because it cannot prove that metadata/images were saved. A lost
 * or expired receipt requires manual inspection, not an automatic overwrite.
 *
 * Does NOT index (vector/graph).
 * Callers should chain: save → index (POST /api/v1/search/index-document) if needed.
 */
export async function saveParsedFiles(
  body: SaveParsedFilesRequest,
  service: Awaited<ReturnType<typeof getTreeFileSystemService>>,
  options: { storagePath?: string; roots?: ParseArtifactRoots } = {},
) {
    type CreatedImage = { path: string; identity: { dev: number; ino: number } }
    const items: Array<{ index: number; filename: string; success: boolean; files: any[]; createdImages: CreatedImage[]; error?: string; recoveryReceipt?: string }> = []

    for (const [index, result] of body.results.entries()) {
      const item: { index: number; filename: string; success: boolean; files: any[]; createdImages: CreatedImage[]; error?: string; recoveryReceipt?: string } = { index, filename: result?.filename || `#${index + 1}`, success: false, files: [], createdImages: [] }
      items.push(item)
      let uploading = false
      let recovery: Recovery | undefined
      let token: string | undefined
      try {
      if (!result?.success) throw new Error(result?.error || 'Parse failed; document not saved')
      const resultForReceipt = { ...result }
      delete resultForReceipt.recoveryReceipt
      const fingerprint = recoveryFingerprint(body.parentId, resultForReceipt, body.split === true, body.agentPlan, options.storagePath || getTreeStorageAbsolutePath())
      if (result.recoveryReceipt !== undefined) {
        if (typeof result.recoveryReceipt !== 'string') throw new Error('Invalid recovery receipt')
        token = result.recoveryReceipt
        recovery = recoveries.get(token)
        if (!recovery || recovery.expires < Date.now() || recovery.fingerprint !== fingerprint || recovery.busy) {
          recovery = undefined
          token = undefined
          throw new Error('Recovery receipt is invalid, expired, in use, or does not match this request')
        }
        recovery.busy = true
      } else {
        pruneRecoveries()
        token = randomUUID()
        recovery = { fingerprint, files: [], expires: Date.now() + recoveryTtl, busy: true }
        recoveries.set(token, recovery)
      }

      // Prefer already-back-filled markdown content; otherwise read the .md
      // file the backend wrote (markdown_path).
      let markdownBuffer: Buffer | null = null
      let fileName = ''

      const selectedSourceName = result.source_filename || result.filename
      if (selectedSourceName) assertSafeFilename(selectedSourceName)
      if (result.markdown) {
        markdownBuffer = Buffer.from(result.markdown, 'utf-8')
        // Strip KNOWN parse-source extensions; .md/.txt sources keep their stem too
        // (otherwise a "x.md" source would become "x.md.md" on disk).
        const sourceName = result.source_filename || result.filename || 'document'
        assertSafeFilename(sourceName)
        const stem = sourceName.replace(/\.(pdf|png|jpg|jpeg|docx|xlsx|md|markdown|txt)$/i, '')
        fileName = `${stem}.md`
      } else if (result.markdown_path) {
        // markdown_path comes from client POST body, must be within allowed roots to block path traversal
        const artifact = await readParseArtifact(result.markdown_path, options.roots)
        if (!artifact) throw new Error('Markdown path is invalid or has changed')
        markdownBuffer = artifact.buffer
        fileName = basename(artifact.path)
      }

      if (!markdownBuffer) throw new Error('No markdown content is available')
      assertSafeFilename(fileName)

      // Validate image sources now, but publish only after the document is
      // accounted for in the per-item response. Copy failures may leave a
      // partial document and images, which are explicitly reported below.
      const norm = (p: string) => p.replace(/\\/g, '/').toLowerCase()
      const parentFolder = (service as any).metadata.folders.find(
        (f: any) => f.id === body.parentId || norm(f.path) === norm(body.parentId)
      )
      if (!parentFolder) throw new Error(`Parent folder not found: ${body.parentId}`)
      const kbFolderPath = parentFolder.path
      if (recovery!.folderId !== undefined && (recovery!.folderId !== parentFolder.id || recovery!.folderPath !== kbFolderPath)) {
        throw new Error('Recovery destination changed; inspect it manually')
      }
      recovery!.folderId = parentFolder.id
      recovery!.folderPath = kbFolderPath
      const rawImagesDir = result.images_dir || result.image_dir
      const safeImagesDir = rawImagesDir ? await resolveParseArtifact(rawImagesDir, options.roots) : null
      if (rawImagesDir && !safeImagesDir) throw new Error('Image source directory is invalid or has changed')
      await validateImageFilenames(safeImagesDir ?? undefined, options.roots)
      let imagePaths: string[] = []
      const copyImages = () => copyImagesToKb(safeImagesDir ?? undefined, kbFolderPath, fileName, options.storagePath, options.roots, {
        onImage: (path, identity) => {
          item.createdImages.push({ path, identity })
        },
      })

      // Only files created by this operation are eligible for recovery. Recheck
      // their identity, parent, contents and metadata before touching images or
      // metadata: an ordinary content duplicate is never proof of ownership.
      const acquireFile = async (key: string, data: Buffer, name: string, description?: string) => {
        assertSafeFilename(name)
        const hash = createHash('sha256').update(data).digest('hex')
        let owned = recovery!.files.find(file => file.key === key)
        let fileRecord: any
        if (owned) {
          if (hash !== owned.hash) throw new Error('Recovery source content changed; inspect it manually')
          const currentFolder = (service as any).metadata.folders.find((folder: any) => folder.id === parentFolder.id)
          if (!currentFolder || currentFolder.path !== kbFolderPath) throw new Error('Recovery destination changed; inspect it manually')
          fileRecord = await service.getFileById(owned.id)
          if (!fileRecord || fileRecord.path !== owned.path || fileRecord.name !== owned.name
              || fileRecord.parentId !== owned.parentId
              || (!sameValue(fileRecord.metadata, owned.initialMetadata)
                  && !sameValue(fileRecord.metadata, owned.intendedMetadata))) {
            throw new Error('Recovery target changed; inspect it manually')
          }
          const storage = options.storagePath || getTreeStorageAbsolutePath()
          const target = resolve(storage, owned.path)
          if (!within(target, resolve(storage))) throw new Error('Recovery target outside storage')
          const artifact = await readParseArtifact(target, options.roots)
          if (!artifact || !samePath(artifact.path, target) || !artifact.buffer.equals(data)) throw new Error('Recovery target content changed; inspect it manually')
        } else {
          uploading = true
          fileRecord = await service.uploadFile(body.parentId, data, name, description)
          uploading = false
          if (!fileRecord.deduped) {
            owned = { key, hash, id: fileRecord.id, path: fileRecord.path, name: fileRecord.name,
              parentId: fileRecord.parentId, initialMetadata: structuredClone(fileRecord.metadata) }
            recovery!.files.push(owned)
          }
        }
        const saved = { ...fileRecord, fileSize: data.length, imageCount: imagePaths.length }
        item.files.push(saved)
        if (!owned) throw new Error('Existing deduplicated document was not changed; save completeness is unknown')
        // A recovered document is a new save for downstream indexing, not an
        // ordinary dedup. Never inherit a deduped flag from the upload path.
        delete saved.deduped
        return { fileRecord, saved, owned }
      }
      const finishFile = async (fileRecord: any, saved: any, owned: RecoveryFile, metadata: any) => {
        owned.intendedMetadata = structuredClone(metadata)
        const updatedFile = await service.updateFile(fileRecord.id, { metadata })
        if (updatedFile?.persistence?.tree !== true || updatedFile?.persistence?.yaml !== true) {
          throw new Error('Metadata persistence was not verified; document save is incomplete')
        }
        Object.assign(saved, updatedFile)
      }

      // ── 大文档拆分入库 (2026-09-18, opt-in) ─────────────────────────
      // 拆分仅在请求显式携带 `split: true` 时执行（web 解析保存 UI 传入）。
      // 默认整篇保存：本端点同时被批量入库管线用作**中转暂存**（如 benchmark
      // Papers-Inbox → 按内容分类路由），暂存态必须保持整篇，拆分属于
      // 最终入库动作（A2.5 门禁脚本 / documents/create 的大文档拆分层）。
      const markdownText = markdownBuffer.toString('utf-8')
      const largeDoc = getLargeDocConfig()
      if ((body as any).split === true && largeDoc.autoSplit
          && Array.from(markdownText).length > largeDoc.maxChars) {
        try {
          const plan = await requestSplitPlan(fileName, markdownText, true, body.agentPlan)
          const validParts = plan?.success && plan.split && Array.isArray(plan.parts)
            && plan.parts.length >= 1
            && plan.parts.every((part) => String(part.content || '').length > 0)
          if (!validParts) {
            throw createError({
              statusCode: 422,
              statusMessage: 'Parsed oversized document requires a valid structure-aware split plan; raw content was not stored',
            })
          }
          if (recovery!.files.some(file => file.key === 'document')) throw new Error('Recovery split configuration changed; inspect it manually')
          const planHash = createHash('sha256').update(JSON.stringify(plan)).digest('hex')
          if (recovery!.splitPlanHash && recovery!.splitPlanHash !== planHash) {
            throw new Error('Recovery split plan changed; inspect it manually')
          }
          recovery!.splitPlanHash = planHash
          {
            const base = basename(fileName, extname(fileName) || '.md')
            let imagesCopied = false
            for (const part of plan.parts) {
              const partName = `${base} (part ${part.part_index} of ${part.part_count}).md`
              const partDesc = buildPartDescription(result.description, part)
              const partBuffer = Buffer.from(String(part.content), 'utf-8')
              const { fileRecord, saved, owned } = await acquireFile(partName, partBuffer, partName, partDesc)
              if (!imagesCopied) {
                imagePaths = await copyImages()
                imagesCopied = true
              }
              saved.imageCount = imagePaths.length
              const metadata = {
                ...fileRecord.metadata,
                sourcePdf: result.source_filename || result.filename,
                parseMethod: result.parse_method,
                imageDir: safeImagesDir ?? rawImagesDir,
                markdownPath: result.markdown_path,
                imageCount: imagePaths.length || result.image_count || 0,
                imagePaths,
                parsedAt: new Date().toISOString(),
                largeDocSplit: {
                  part_index: part.part_index,
                  part_count: part.part_count,
                  source_chars: plan.source_chars ?? Array.from(markdownText).length,
                  max_chars: plan.max_chars ?? largeDoc.maxChars,
                  strategy: plan.strategy,
                  planner: plan.planner,
                  source_start: part.source_start ?? part.start_char,
                  source_end: part.source_end ?? part.end_char,
                  section_range: part.section_range,
                  warnings: part.warnings,
                },
              }
              await finishFile(fileRecord, saved, owned, metadata)
            }
            item.success = true
            continue
          }
        } catch (splitErr: any) {
          throw splitErr
        }
      }

      if (recovery!.splitPlanHash) throw new Error('Recovery split configuration changed; inspect it manually')
      // An unproven dedup may itself be an earlier partial. Do not claim it is
      // complete or modify it without the matching recovery receipt.
      const { fileRecord, saved, owned } = await acquireFile('document', markdownBuffer, fileName, result.description)
      if (owned) {
        imagePaths = await copyImages()
        saved.imageCount = imagePaths.length
        const metadata = {
          ...fileRecord.metadata,
          sourcePdf: result.source_filename || result.filename,
          parseMethod: result.parse_method,
          imageDir: safeImagesDir ?? rawImagesDir,
          markdownPath: result.markdown_path,
          imageCount: imagePaths.length || result.image_count || 0,
          imagePaths,
          parsedAt: new Date().toISOString(),
        }
        await finishFile(fileRecord, saved, owned, metadata)
      }
      item.success = true
      } catch (error: any) {
        item.error = error?.statusMessage || error?.message || String(error)
        if (uploading) item.error += ' (upload outcome uncertain; inspect the target folder before retrying)'
      } finally {
        if (recovery && token) {
          recovery.busy = false
          if (item.success || !recovery.files.length) recoveries.delete(token)
          else item.recoveryReceipt = token
        }
      }
    }

    // A split item is confirmed only once every part and its metadata succeeded.
    // Keep incomplete and pre-existing records available for inspection, but
    // never advertise them as saved or as safe downstream indexing candidates.
    const savedFiles = items.filter(item => item.success).flatMap(item => item.files)
    const partialFiles = items.filter(item => !item.success).flatMap(item => item.files.filter(file => !file.deduped))
    const existingFiles = items.filter(item => !item.success).flatMap(item => item.files.filter(file => file.deduped))
    return {
      success: items.every(item => item.success),
      savedCount: savedFiles.length,
      partialCount: partialFiles.length,
      existingCount: existingFiles.length,
      failedCount: items.filter(item => !item.success).length,
      files: savedFiles,
      partialFiles,
      existingFiles,
      items,
    }
}

export default defineEventHandler(async (event) => {
  // Responses may contain bearer receipts and must not be cached by proxies.
  setResponseHeader(event, 'Cache-Control', 'no-store')
  const body = await readBody<SaveParsedFilesRequest>(event)
  if (!body?.parentId || !Array.isArray(body.results)) {
    throw createError({ statusCode: 400, statusMessage: 'Invalid request: parentId and results are required' })
  }
  const service = await getTreeFileSystemService()
  await service.reloadMetadata()
  return saveParsedFiles(body, service)
})
