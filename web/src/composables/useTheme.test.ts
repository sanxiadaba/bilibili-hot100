import { afterEach, describe, expect, it, vi } from 'vitest'
import { initTheme, toggleTheme, useTheme } from './useTheme'

describe('useTheme', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('存储不可用时仍能初始化并切换主题', () => {
    const dataset: Record<string, string> = {}
    vi.stubGlobal('document', { documentElement: { dataset } })
    vi.stubGlobal('localStorage', {
      getItem: () => {
        throw new Error('SecurityError')
      },
      setItem: () => {
        throw new Error('SecurityError')
      }
    })
    vi.stubGlobal('window', { matchMedia: () => ({ matches: false }) })

    expect(() => initTheme()).not.toThrow()
    expect(() => toggleTheme()).not.toThrow()
    expect(dataset.theme).toBe('dark')
    expect(useTheme().dark.value).toBe(true)
  })
})
