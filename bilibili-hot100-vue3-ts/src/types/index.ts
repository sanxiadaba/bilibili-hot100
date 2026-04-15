export interface VideoStat {
  view: number
  danmaku: number
  reply: number
  favorite: number
  coin: number
  share: number
  like: number
}

export interface VideoOwner {
  mid: number
  name: string
  face: string
}

export interface VideoItem {
  aid: number
  bvid: string
  title: string
  pic: string
  duration: number
  pubdate: number
  owner: VideoOwner
  stat: VideoStat
  tname: string
  rank: number
  rcmd_reason?: {
    content?: string
  }
}

export interface Hot100Response {
  code: number
  message: string
  data: VideoItem[]
  update_time: string
  from_cache: boolean
}

export interface CategoryStat {
  count: number
  views: number
  likes: number
}

export interface StatsData {
  total: number
  totalViews: number
  totalLikes: number
  totalCoins: number
  totalFavorites: number
  totalDanmaku: number
  totalReply: number
  totalShare: number
  avgViews: number
  avgLikes: number
  categoryStats: Record<string, CategoryStat>
  topVideos: VideoItem[]
  mostLiked: VideoItem[]
}

export interface LogEntry {
  time: string
  level: 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR' | 'DEBUG'
  message: string
}

export type SortType = 'rank' | 'view' | 'like' | 'coin' | 'favorite' | 'danmaku'

export interface SelectOption {
  label: string
  value: string
}
