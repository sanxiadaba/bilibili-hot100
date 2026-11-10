import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useVideoStore } from './videos'
import { fetchHot100 } from '@/api/backend'
import type { VideoItem } from '@/types'

vi.mock('@/api/backend', () => ({
  fetchHot100: vi.fn(),
  getStatus: vi.fn(),
  refreshData: vi.fn()
}))

const makeVideo = (rank: number, overrides: Partial<VideoItem> = {}): VideoItem => ({
  aid: rank,
  bvid: `BV${rank}`,
  title: `video ${rank}`,
  pic: 'https://example.test/cover.jpg',
  duration: 60,
  pubdate: 1_700_000_000,
  owner: { mid: rank, name: `owner ${rank}`, face: 'https://example.test/face.jpg' },
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
})

const videos = [makeVideo(1), makeVideo(2), makeVideo(3)]

describe('useVideoStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads videos and derives categories and stats', async () => {
    vi.mocked(fetchHot100).mockResolvedValue({
      videos,
      fromCache: true,
      updateTime: '2026-11-10T09:00:00+08:00',
      isPartial: false
    })
    const store = useVideoStore()
    await store.loadVideos()

    expect(store.videos).toHaveLength(3)
    expect(store.fromCache).toBe(true)
    expect(store.isPartial).toBe(false)
    expect(store.categories).toEqual([
      { name: '游戏', count: 2 },
      { name: '日常', count: 1 }
    ])
    expect(store.stats?.total).toBe(3)
    expect(store.stats?.totalViews).toBe(600)
    expect(store.stats?.topVideos[0].rank).toBe(3)
  })

  it('flags partial data coming from the backend', async () => {
    vi.mocked(fetchHot100).mockResolvedValue({
      videos,
      fromCache: false,
      updateTime: '2026-11-10T09:00:00+08:00',
      isPartial: true
    })
    const store = useVideoStore()
    await store.loadVideos()
    expect(store.isPartial).toBe(true)
  })

  it('filters by category and search, and sorts by views', async () => {
    vi.mocked(fetchHot100).mockResolvedValue({
      videos,
      fromCache: false,
      updateTime: '2026-11-10T09:00:00+08:00',
      isPartial: false
    })
    const store = useVideoStore()
    await store.loadVideos()

    store.setCategory('游戏')
    expect(store.filteredVideos.map(v => v.rank)).toEqual([1, 3])

    store.setCategory('all')
    store.setSearch('owner 2')
    expect(store.filteredVideos.map(v => v.rank)).toEqual([2])

    store.setSearch('')
    store.setSort('view')
    expect(store.filteredVideos.map(v => v.rank)).toEqual([3, 2, 1])
  })

  it('surfaces backend failures as an error message', async () => {
    vi.mocked(fetchHot100).mockRejectedValue(new Error('数据尚未就绪'))
    const store = useVideoStore()
    await store.loadVideos()
    expect(store.error).toBe('数据尚未就绪')
    expect(store.loading).toBe(false)
  })
})
