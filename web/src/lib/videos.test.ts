import { describe, expect, it } from 'vitest'
import { categoryCounts, selectVideos, statOf, summarize, topBy } from './videos'
import type { VideoItem } from './types'

function makeVideo(rank: number, overrides: Partial<VideoItem> = {}): VideoItem {
  return {
    aid: rank,
    bvid: `BV${rank}`,
    title: `视频 ${rank}`,
    pic: '/img/a.jpg',
    duration: 60,
    pubdate: 1_700_000_000,
    owner: { mid: rank, name: `UP ${rank}`, face: '/img/b.jpg' },
    stat: {
      view: rank * 100,
      danmaku: rank,
      reply: rank,
      favorite: rank,
      coin: rank,
      share: rank,
      like: rank * 10
    },
    tname: rank % 2 === 0 ? '日常' : '游戏',
    rank,
    ...overrides
  }
}

const videos = [makeVideo(1), makeVideo(2), makeVideo(3)]

describe('categoryCounts', () => {
  it('按数量倒序统计分类', () => {
    expect(categoryCounts(videos)).toEqual([
      { name: '游戏', count: 2 },
      { name: '日常', count: 1 }
    ])
  })
})

describe('selectVideos', () => {
  it('按分类和关键词筛选，不修改原数组', () => {
    const filtered = selectVideos(videos, '游戏', 'UP 3', 'rank')
    expect(filtered.map(video => video.rank)).toEqual([3])
    expect(videos.map(video => video.rank)).toEqual([1, 2, 3])
  })

  it('按播放量倒序', () => {
    expect(selectVideos(videos, 'all', '', 'view').map(video => video.rank)).toEqual([3, 2, 1])
  })
})

describe('summarize', () => {
  it('汇总总量和均值', () => {
    const summary = summarize(videos)
    expect(summary.total).toBe(3)
    expect(summary.views).toBe(600)
    expect(summary.likes).toBe(60)
    expect(summary.averageViews).toBe(200)
    expect(summary.categories[0]).toEqual({ name: '游戏', count: 2 })
  })

  it('空列表不会除零', () => {
    expect(summarize([]).averageViews).toBe(0)
  })
})

describe('topBy', () => {
  it('按指标取前 N 个', () => {
    expect(topBy(videos, 'like', 2).map(video => video.rank)).toEqual([3, 2])
    expect(statOf(videos[0], 'view')).toBe(100)
  })
})
