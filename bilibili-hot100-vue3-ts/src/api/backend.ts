import axios from 'axios'
import type { Hot100Response, LogEntry } from '@/types'

const backend = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

export const fetchHot100 = async (forceRefresh = false): Promise<{
  videos: Hot100Response['data']
  fromCache: boolean
  updateTime: string
}> => {
  const response = await backend.get<Hot100Response>('/hot100', {
    params: { force_refresh: forceRefresh }
  })
  if (response.data.code === 0) {
    return {
      videos: response.data.data,
      fromCache: response.data.from_cache,
      updateTime: response.data.update_time
    }
  }
  throw new Error(response.data.message)
}

export const refreshData = async (): Promise<{ code: number; message: string }> => {
  const response = await backend.post('/refresh')
  return response.data
}

export const getStatus = async (): Promise<{
  total_videos: number
  update_time: string | null
  is_updating: boolean
  cached_images: number
  cached_urls: number
}> => {
  const response = await backend.get('/status')
  return response.data.data
}

export const getImageUrl = (url: string): string => {
  if (!url) return ''
  if (url.startsWith('/api/images/')) {
    return url
  }
  // 对于外部图片 URL，直接返回
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }
  // 对于其他情况，返回默认图片
  return 'https://i0.hdslb.com/bfs/archive/7e6c4623b846e5a01b326f608c2c98e14c5b3c3c.jpg'
}

export const getLogs = async (): Promise<LogEntry[]> => {
  const response = await backend.get('/logs')
  return response.data.data
}

export const clearLogs = async (): Promise<void> => {
  await backend.delete('/logs')
}

export default backend
