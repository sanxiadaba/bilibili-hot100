import { describe, expect, it } from 'vitest'
import { formatDuration, formatNumber, getRankClass } from './format'

describe('formatNumber', () => {
  it('formats 万 and 亿 magnitudes', () => {
    expect(formatNumber(9999)).toBe('9999')
    expect(formatNumber(12345)).toBe('1.2万')
    expect(formatNumber(123_456_789)).toBe('1.2亿')
  })

  it('handles missing values', () => {
    expect(formatNumber(undefined)).toBe('0')
    expect(formatNumber(null as unknown as number)).toBe('0')
  })
})

describe('formatDuration', () => {
  it('formats mm:ss and h:mm:ss', () => {
    expect(formatDuration(0)).toBe('0:00')
    expect(formatDuration(65)).toBe('1:05')
    expect(formatDuration(3661)).toBe('1:01:01')
  })

  it('handles undefined', () => {
    expect(formatDuration(undefined)).toBe('0:00')
  })
})

describe('getRankClass', () => {
  it('maps the top ranks to badge classes', () => {
    expect(getRankClass(1)).toBe('top3')
    expect(getRankClass(3)).toBe('top3')
    expect(getRankClass(4)).toBe('top10')
    expect(getRankClass(10)).toBe('top10')
    expect(getRankClass(11)).toBe('')
  })
})
