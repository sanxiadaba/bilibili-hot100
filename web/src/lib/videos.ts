import type { SortKey, StatKey, VideoItem } from './types'

export interface CategoryCount {
  name: string
  count: number
}

export interface Summary {
  total: number
  views: number
  likes: number
  coins: number
  favorites: number
  danmaku: number
  reply: number
  share: number
  averageViews: number
  categories: CategoryCount[]
}

export const SORT_OPTIONS: Array<{ value: SortKey; label: string }> = [
  { value: 'rank', label: '默认排名' },
  { value: 'view', label: '播放量' },
  { value: 'like', label: '点赞数' },
  { value: 'coin', label: '投币数' },
  { value: 'favorite', label: '收藏数' },
  { value: 'danmaku', label: '弹幕数' }
]

export const METRICS: Array<{ value: StatKey; label: string }> = [
  { value: 'view', label: '播放' },
  { value: 'like', label: '点赞' },
  { value: 'coin', label: '投币' },
  { value: 'favorite', label: '收藏' },
  { value: 'danmaku', label: '弹幕' }
]

export function statOf(video: VideoItem, key: StatKey): number {
  return video.stat?.[key] ?? 0
}

export function categoryCounts(videos: VideoItem[]): CategoryCount[] {
  const counts = new Map<string, number>()
  for (const video of videos) {
    const name = video.tname || '未分类'
    counts.set(name, (counts.get(name) ?? 0) + 1)
  }
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((left, right) => right.count - left.count || left.name.localeCompare(right.name))
}

export function selectVideos(
  videos: VideoItem[],
  category: string,
  query: string,
  sort: SortKey
): VideoItem[] {
  const keyword = query.trim().toLowerCase()
  const result = videos.filter(video => {
    if (category !== 'all' && video.tname !== category) return false
    if (!keyword) return true
    return (
      video.title.toLowerCase().includes(keyword) ||
      video.owner.name.toLowerCase().includes(keyword)
    )
  })

  if (sort === 'rank') {
    return result.sort((left, right) => left.rank - right.rank)
  }
  return result.sort((left, right) => statOf(right, sort) - statOf(left, sort))
}

export function summarize(videos: VideoItem[]): Summary {
  const summary: Summary = {
    total: videos.length,
    views: 0,
    likes: 0,
    coins: 0,
    favorites: 0,
    danmaku: 0,
    reply: 0,
    share: 0,
    averageViews: 0,
    categories: categoryCounts(videos)
  }
  for (const video of videos) {
    summary.views += video.stat?.view ?? 0
    summary.likes += video.stat?.like ?? 0
    summary.coins += video.stat?.coin ?? 0
    summary.favorites += video.stat?.favorite ?? 0
    summary.danmaku += video.stat?.danmaku ?? 0
    summary.reply += video.stat?.reply ?? 0
    summary.share += video.stat?.share ?? 0
  }
  summary.averageViews = videos.length ? Math.round(summary.views / videos.length) : 0
  return summary
}

export function topBy(videos: VideoItem[], key: StatKey, limit = 10): VideoItem[] {
  return [...videos].sort((left, right) => statOf(right, key) - statOf(left, key)).slice(0, limit)
}
