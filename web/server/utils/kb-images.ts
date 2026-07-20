import { join } from 'path'
import { readdir, stat, mkdir, copyFile } from 'fs/promises'
import { existsSync } from 'fs'

/**
 * Recursively copy a source images directory into a target folder, so that the
 * markdown's relative `images/xxx.jpg` references resolve after the doc is
 * archived into a knowledge base.
 *
 * @param srcImagesDir  absolute path of the images dir the backend produced
 *                      (MineruParseResult.images_dir). May be missing.
 * @param targetKbDir   absolute path of the knowledge-base folder where the
 *                      parsed .md was written. Images are copied next to it
 *                      under `images/`.
 * @returns             number of image files copied.
 */
export async function copyImagesToKb(
  srcImagesDir: string | undefined | null,
  targetKbDir: string,
): Promise<number> {
  if (!srcImagesDir || !existsSync(srcImagesDir)) return 0
  try {
    const srcStat = await stat(srcImagesDir)
    if (!srcStat.isDirectory()) return 0
  } catch {
    return 0
  }

  const dstImagesDir = join(targetKbDir, 'images')
  await mkdir(dstImagesDir, { recursive: true })

  let count = 0
  async function walk(src: string, dst: string): Promise<void> {
    const entries = await readdir(src, { withFileTypes: true })
    await mkdir(dst, { recursive: true })
    for (const entry of entries) {
      const s = join(src, entry.name)
      const d = join(dst, entry.name)
      if (entry.isDirectory()) {
        await walk(s, d)
      } else if (entry.isFile()) {
        if (!existsSync(d)) {
          await copyFile(s, d)
        }
        count++
      }
    }
  }

  await walk(srcImagesDir, dstImagesDir)
  return count
}