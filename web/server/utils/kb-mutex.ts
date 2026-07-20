/**
 * In-process Concurrency Lock -- Phase 0 Emergency Hemostasis (P0 #1) Concurrent RMW Protection.
 *
 * Design: module-level Map<string, Promise>, calls with the same key are chained and queued (promise chaining).
 *   - Calls with the same key execute serially, preventing read-modify-write cross-update loss;
 *   - Different keys don't block each other (parallel by KB dimension);
 *   - fn errors don't affect subsequent queued calls (store swallow-rejection version in Map).
 *
 * Non-reentrant: fn must not acquire the same key internally (promise chain would deadlock).
 * Only effective within process (Nuxt single-process server), not cross-process.
 */

const locks = new Map<string, Promise<unknown>>()

/**
 * Execute fn serially by kbKey. Same key queues, different keys parallel.
 * fn rejection doesn't block subsequent same-key calls.
 */
export function withKbLock<T>(kbKey: string, fn: () => Promise<T>): Promise<T> {
  const prev = locks.get(kbKey) ?? Promise.resolve()
  // Execute fn after prev settles regardless of success or failure (chain doesn't break on previous failure)
  const next = prev.then(fn, fn)
  // Store swallow-rejection version, preventing fn failure from rejecting the entire chain
  locks.set(
    kbKey,
    next.then(
      () => {},
      () => {},
    ),
  )
  return next
}

/** Global tree lock key (.tree-fs.json single file, writes must be globally serialized). */
const TREE_LOCK_KEY = '__tree_fs__'

/**
 * Global tree lock: all .tree-fs.json writes are serialized.
 * Different key space from withKbLock, both don't interfere with each other.
 */
export function withTreeLock<T>(fn: () => Promise<T>): Promise<T> {
  return withKbLock(TREE_LOCK_KEY, fn)
}
