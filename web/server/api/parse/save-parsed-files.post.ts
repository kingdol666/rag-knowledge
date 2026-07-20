import { defineEventHandler, readBody, createError } from 'h3'
import { basename, join, dirname } from 'path'
import { readFile, stat, readdir, copyFile, mkdir } from 'fs/promises'
import { existsSync } from 'fs'
import { getTreeFileSystemService } from '~/server/utils/tree-service'
import { getTreeStorageAbsolutePath, resolveProjectPath } from '~/server/utils/runtime-paths'
import { resolveWithinAnyRoot } from '~/server/utils/safe-paths'
import type { BatchParsePDFFileVTItem } from '~/types/pdf-parse'

interface ParsedFileResult extends BatchParsePDFFileVTItem {
  description?: string
}

interface SaveParsedFilesRequest {
  parentId: string
  results: ParsedFileResult[]
}

/**
 * The markdown_path / images_dir from the client POST body are external inputs;
 * they must be restricted to within the backend output root or tree storage root
 * to prevent path traversal reading arbitrary files.
 */
const BACKEND_OUTPUT_ROOT = resolveProjectPath('./backend/output')
const TREE_STORAGE_ROOT = getTreeStorageAbsolutePath()
const ALLOWED_EXTERNAL_ROOTS = [BACKEND_OUTPUT_ROOT, TREE_STORAGE_ROOT]

/**
 * Copy all images from the parse output's images_dir to the KB's images/ folder.
 * Returns the list of relative image paths (relative to KB root) for metadata.
 */
async function copyImagesToKb(
  imagesDir: string | undefined,
  kbFolderPath: string,
  docFileName: string,
): Promise<string[]> {
  if (!imagesDir || !existsSync(imagesDir)) {
    return []
  }

  // Target: {kbRoot}/{kbFolderPath}/images/  (flat, no subdirectories, matches markdown relative paths)
  const targetDir = join(getTreeStorageAbsolutePath(), kbFolderPath, 'images')

  let imageFiles: string[] = []
  try {
    const entries = await readdir(imagesDir, { withFileTypes: true })
    imageFiles = entries
      .filter(e => e.isFile() && /\.(jpg|jpeg|png|gif|bmp|webp|svg|tif|tiff)$/i.test(e.name))
      .map(e => e.name)
  } catch {
    return []
  }

  if (imageFiles.length === 0) {
    return []
  }

  // Create target directory
  await mkdir(targetDir, { recursive: true })

  // Copy each image
  const relativePaths: string[] = []
  for (const imgName of imageFiles) {
    const srcPath = join(imagesDir, imgName)
    const dstPath = join(targetDir, imgName)
    try {
      await copyFile(srcPath, dstPath)
      // Relative path from KB root: images/{imgName} (consistent with markdown ![](images/xxx.jpg))
      relativePaths.push(`images/${imgName}`)
    } catch (err) {
      console.warn(`Failed to copy image ${imgName}:`, err)
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
 * Does NOT index (vector/graph).
 * Callers should chain: save → index (POST /api/v1/search/index-document) if needed.
 */
export default defineEventHandler(async (event) => {
  try {
    const body = await readBody<SaveParsedFilesRequest>(event)

    if (!body.parentId || !body.results || !Array.isArray(body.results)) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Invalid request: parentId and results are required',
      })
    }

    const service = await getTreeFileSystemService()
    await service.reloadMetadata()

    const savedFiles = []

    for (const result of body.results) {
      if (!result.success) {
        continue
      }

      // Prefer already-back-filled markdown content; otherwise read the .md
      // file the backend wrote (markdown_path).
      let markdownBuffer: Buffer | null = null
      let fileName = ''
      let fileSize = 0

      if (result.markdown) {
        markdownBuffer = Buffer.from(result.markdown, 'utf-8')
        fileSize = markdownBuffer.length
        const stem = (result.source_filename || result.filename || 'document').replace(/\.(pdf|png|jpg|jpeg|docx|xlsx)$/i, '')
        fileName = `${stem}.md`
      } else if (result.markdown_path) {
        // markdown_path comes from client POST body, must be within allowed roots to block path traversal
        const safeMdPath = resolveWithinAnyRoot(result.markdown_path, ALLOWED_EXTERNAL_ROOTS)
        if (!safeMdPath) {
          console.warn(`markdown_path outside allowed roots, skipping: ${result.markdown_path}`)
          continue
        }
        try {
          markdownBuffer = await readFile(safeMdPath)
          fileName = basename(safeMdPath)
          try {
            fileSize = (await stat(safeMdPath)).size
          } catch {
            fileSize = markdownBuffer.length
          }
        } catch (readErr) {
          console.warn(`Could not read markdown at ${safeMdPath}:`, readErr)
        }
      }

      if (!markdownBuffer) {
        console.warn(`No markdown content for ${result.filename}; skipping`)
        continue
      }

      try {
        // uploadFile() handles: disk write + .tree-fs.json + .knowledge-base.yml (with file ID)
        const fileRecord = await service.uploadFile(
          body.parentId,
          markdownBuffer,
          fileName,
          result.description,
        )

        // Determine the KB folder path for image copying
        const norm = (p: string) => p.replace(/\\/g, '/').toLowerCase()
        const parentFolder = (service as any).metadata.folders.find(
          (f: any) => f.id === body.parentId || norm(f.path) === norm(body.parentId)
        )
        const kbFolderPath = parentFolder?.path || ''

        // Copy images to KB's images/ folder
        // images_dir also comes from client POST body, only allow if within allowed roots
        const rawImagesDir = result.images_dir || result.image_dir
        const safeImagesDir = rawImagesDir
          ? resolveWithinAnyRoot(rawImagesDir, ALLOWED_EXTERNAL_ROOTS)
          : null
        if (rawImagesDir && !safeImagesDir) {
          console.warn(`images_dir outside allowed roots, skipping images: ${rawImagesDir}`)
        }
        const imagePaths = await copyImagesToKb(safeImagesDir ?? undefined, kbFolderPath, fileName)

        // Add parse metadata (sourcePdf, parseMethod, image paths, etc.)
        const metadata = {
          ...fileRecord.metadata,
          sourcePdf: result.source_filename || result.filename,
          parseMethod: result.parse_method,
          imageDir: safeImagesDir ?? rawImagesDir,
          markdownPath: result.markdown_path,
          imageCount: imagePaths.length || result.image_count || 0,
          imagePaths, // Relative paths from KB root: images/{docStem}/{imgName}
          parsedAt: new Date().toISOString(),
        }

        const updatedFile = await service.updateFile(fileRecord.id, {
          metadata,
        })

        savedFiles.push({
          ...updatedFile,
          fileSize,
          imageCount: imagePaths.length,
        })
      } catch (error) {
        console.error(`Failed to save parsed file for ${result.filename}:`, error)
      }
    }

    return {
      success: true,
      savedCount: savedFiles.length,
      files: savedFiles,
    }
  } catch (error: any) {
    console.error('Save parsed files error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: error.message || 'Failed to save parsed files',
    })
  }
})
