import { writeFile, rename, unlink } from 'fs/promises'
import { writeFileSync, renameSync, existsSync, unlinkSync } from 'fs'
import { dirname, join, basename } from 'path'
import { randomBytes } from 'crypto'

/**
 * Atomic write -- Phase 0 (P0 #2 #3) Data Integrity Foundation.
 *
 * Strategy: temp file (same directory) -> write -> atomic rename to replace target.
 *   - Same-directory rename is atomic on both Windows (NTFS) and POSIX;
 *   - Crash at any time, the target is either old or new content, never truncated/empty;
 *   - Temp file uses .prefix + pid + random, avoiding concurrent collisions, and can be cleaned by orphan scan.
 *
 * Backward compatible: Fully transparent to callers (same writeFile signature). Flag storage.atomic_write
 * can downgrade in extreme cases, enabled by default.
 */

function tmpPath(target: string): string {
  const rand = randomBytes(6).toString('hex')
  return join(dirname(target), `.${basename(target)}.${process.pid}.${rand}.tmp`)
}

/**
 * Cross-platform rename to existing target, with short retries.
 * On Windows, when the target was just replaced by another process/thread (handle not fully released), rename may throw
 * EPERM/EACCES (Sharing violation) -- a transient conflict that short retry resolves. Finally fallback unlink+rename
 * handles read-only target and similar stubborn cases.
 */
async function renameOverride(from: string, to: string): Promise<void> {
  const retries = 6
  const baseDelay = 30
  let lastErr: unknown = null
  for (let i = 0; i < retries; i++) {
    try {
      await rename(from, to)
      return
    } catch (err: any) {
      lastErr = err
      if (err && (err.code === 'EPERM' || err.code === 'EACCES')) {
        await new Promise((r) => setTimeout(r, baseDelay * (i + 1)))
        continue
      }
      throw err
    }
  }
  // Fallback: delete target then rename (read-only / stubborn target)
  if (existsSync(to)) {
    try {
      await unlink(to)
    } catch {
      /* ignore */
    }
    try {
      await rename(from, to)
      return
    } catch (err) {
      lastErr = err
    }
  }
  throw lastErr
}

export async function writeTextAtomic(filePath: string, data: string): Promise<void> {
  const tmp = tmpPath(filePath)
  try {
    await writeFile(tmp, data, { encoding: 'utf-8', mode: 0o644 })
    await renameOverride(tmp, filePath)
  } catch (err) {
    try {
      await unlink(tmp)
    } catch {
      /* ignore: temp may not have been created */
    }
    throw err
  }
}

export async function writeJsonAtomic(
  filePath: string,
  data: unknown,
  pretty = true,
): Promise<void> {
  const text = JSON.stringify(data, null, pretty ? 2 : 0)
  await writeTextAtomic(filePath, text)
}

/** Sync version, for startup critical sections and similar rare scenarios. */
export function writeTextAtomicSync(filePath: string, data: string): void {
  const tmp = tmpPath(filePath)
  try {
    writeFileSync(tmp, data, { encoding: 'utf-8', mode: 0o644 })
    try {
      renameSync(tmp, filePath)
    } catch (err: any) {
      if (
        err &&
        (err.code === 'EPERM' || err.code === 'EACCES') &&
        existsSync(filePath)
      ) {
        try {
          unlinkSync(filePath)
        } catch {
          /* ignore */
        }
        renameSync(tmp, filePath)
      } else {
        throw err
      }
    }
  } catch (err) {
    try {
      if (existsSync(tmp)) unlinkSync(tmp)
    } catch {
      /* ignore */
    }
    throw err
  }
}
