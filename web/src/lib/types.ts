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
  rcmd_reason?: { content?: string } | null
}

export interface Hot100Response {
  data: VideoItem[]
  update_time: string
  is_partial: boolean
  source: string
  is_stale: boolean
  is_updating: boolean
}

export interface StatusResponse {
  total: number
  update_time: string | null
  is_updating: boolean
  is_partial: boolean
  source: string | null
  last_error: string | null
  stale: boolean
  cached_images: number
  data_dir: string
  cache_ttl_seconds: number
}

export interface LogEntry {
  time: string
  level: 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR'
  message: string
}

export type SortKey = 'rank' | 'view' | 'like' | 'coin' | 'favorite' | 'danmaku'
export type StatKey = 'view' | 'like' | 'coin' | 'favorite' | 'danmaku'
