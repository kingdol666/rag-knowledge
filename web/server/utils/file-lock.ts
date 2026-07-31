/**
 * 跨进程文件锁 —— 修复 .knowledge-base.yml 跨进程读改写竞争。
 *
 * 与 backend/app/utils/file_lock.py 同协议（O_EXCL 锁文件 + 时间戳 + 过期抢占）：
 * - web(Nitro) 与 backend(FastAPI) 都会对同一 YAML 做 read-modify-write；
 * - 进程内锁（withKbLock）无法互斥跨进程，必须用文件锁串行化；
 * - 锁路径 = `<yaml>.lock`，获取后执行 fn，finally 删除锁文件。
 */

import { open, rm, stat } from 'fs/promises'

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export interface FileLockOptions {
  /** 获取锁超时（毫秒），默认 15000 */
  timeoutMs?: number
  /** 锁文件视为崩溃残留的年龄（毫秒），默认 30000 */
  staleMs?: number
  /** 重试间隔（毫秒），默认 20 */
  retryMs?: number
}

/**
 * 在 lockPath 上获取跨进程互斥锁，执行 fn，释放锁。
 * 与 Python 端 file_lock 同协议，两进程互斥生效。
 */
export async function withFileLock<T>(
  lockPath: string,
  fn: () => Promise<T>,
  opts: FileLockOptions = {},
): Promise<T> {
  const timeoutMs = opts.timeoutMs ?? 15000
  const staleMs = opts.staleMs ?? 30000
  const retryMs = opts.retryMs ?? 20
  const deadline = Date.now() + timeoutMs

  for (;;) {
    let acquired = false
    try {
      const fh = await open(lockPath, 'wx')
      acquired = true
      await fh.writeFile(`${process.pid} ${Date.now()}\n`)
      await fh.close()
      return await fn()
    } catch (err: any) {
      if (err?.code !== 'EEXIST') throw err
      // 持有者崩溃后锁文件残留：超龄即抢占
      try {
        const st = await stat(lockPath)
        if (Date.now() - st.mtimeMs > staleMs) {
          await rm(lockPath, { force: true }).catch(() => {})
          continue
        }
      } catch {
        continue // 锁文件恰好消失，立即重试
      }
      if (Date.now() >= deadline) {
        throw new Error(`Timed out acquiring lock: ${lockPath}`)
      }
      await sleep(retryMs)
    } finally {
      if (acquired) {
        await rm(lockPath, { force: true }).catch(() => {})
      }
    }
  }
}

/** YAML 文件对应的锁文件路径（同目录，.lock 后缀）。 */
export function yamlLockPath(ymlPath: string): string {
  return `${ymlPath}.lock`
}
