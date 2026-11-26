import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchStatus } from './api'

describe('request 超时', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('请求挂起时按超时中止，不会无限等待', async () => {
    vi.useFakeTimers()
    let signal: AbortSignal | undefined
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init?: RequestInit) => {
        signal = init?.signal ?? undefined
        return new Promise<Response>((_resolve, reject) => {
          signal?.addEventListener('abort', () =>
            reject(new DOMException('Aborted', 'AbortError'))
          )
        })
      })
    )

    const pending = fetchStatus()
    const assertion = expect(pending).rejects.toMatchObject({ name: 'AbortError' })
    await vi.advanceTimersByTimeAsync(15_000)
    await assertion
    expect(signal).toBeInstanceOf(AbortSignal)
  })
})
