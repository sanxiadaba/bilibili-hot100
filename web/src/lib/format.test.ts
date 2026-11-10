import { describe, expect, it } from 'vitest'
import { formatDuration, formatNumber } from './format'

describe('formatNumber', () => {
  it('按万 / 亿取一位小数并去掉多余的 .0', () => {
    expect(formatNumber(9999)).toBe('9999')
    expect(formatNumber(12345)).toBe('1.2万')
    expect(formatNumber(120000)).toBe('12万')
    expect(formatNumber(123456789)).toBe('1.2亿')
  })

  it('空值和 0 都显示 0', () => {
    expect(formatNumber(0)).toBe('0')
    expect(formatNumber(undefined)).toBe('0')
    expect(formatNumber(null)).toBe('0')
  })
})

describe('formatDuration', () => {
  it('输出 mm:ss 或 h:mm:ss', () => {
    expect(formatDuration(0)).toBe('0:00')
    expect(formatDuration(65)).toBe('1:05')
    expect(formatDuration(3661)).toBe('1:01:01')
  })

  it('空值安全', () => {
    expect(formatDuration(undefined)).toBe('0:00')
    expect(formatDuration(-1)).toBe('0:00')
  })
})
