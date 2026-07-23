/**
 * Async message queue — converts callback-driven producers into async iterables.
 *
 * Producer calls push(msg); consumer iterates with for-await.
 * A sentinel (null) signals completion and ends iteration.
 *
 * Standard single-producer/single-consumer queue with a pending resolver
 * for backpressure-free streaming.
 */
export class AsyncQueue<T> {
  private buffer: T[] = []
  private done = false
  private waiter: ((value: IteratorResult<T>) => void) | null = null

  push(item: T): void {
    if (this.done) return
    if (this.waiter) {
      const w = this.waiter
      this.waiter = null
      w({ value: item, done: false })
    } else {
      this.buffer.push(item)
    }
  }

  /** Signal end of stream — subsequent next() calls return done. */
  close(): void {
    if (this.done) return
    this.done = true
    if (this.waiter) {
      const w = this.waiter
      this.waiter = null
      w({ value: undefined as any, done: true })
    }
  }

  async next(): Promise<IteratorResult<T>> {
    if (this.buffer.length > 0) {
      return { value: this.buffer.shift()!, done: false }
    }
    if (this.done) {
      return { value: undefined as any, done: true }
    }
    // Wait for next push or close
    const { promise, resolve } = Promise.withResolvers<IteratorResult<T>>()
    this.waiter = resolve
    return promise
  }

  [Symbol.asyncIterator](): AsyncIterator<T> {
    return {
      next: () => this.next(),
    }
  }
}
