import axios from 'axios'
import type { BackendStatus, Hot100Response, LogEntry, RefreshResponse } from '@/types'
import { FALLBACK_COVER } from '@/utils/placeholder'

const backend = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

export const fetchHot100 = async (): Promise<{
  videos: Hot100Response['data']
  fromCache: boolean
  updateTime: string
  isPartial: boolean
}> => {
  const response = await backend.get<Hot100Response>('/hot100')
  if (response.data.code === 0) {
    return {
      videos: response.data.data,
      fromCache: response.data.from_cache,
      updateTime: response.data.update_time,
      isPartial: response.data.is_partial ?? false
    }
  }
  throw new Error(response.data.message)
}

export const refreshData = async (): Promise<RefreshResponse> => {
  const response = await backend.post<RefreshResponse>('/refresh')
  return response.data
}

export const getStatus = async (): Promise<BackendStatus> => {
  const response = await backend.get('/status')
  return response.data.data
}

export const getImageUrl = (url: string): string => {
  if (!url) return ''
  // Cached images are already served from this origin; external URLs are kept
  // as-is so a missing cache entry degrades to the original CDN image.
  if (url.startsWith('/api/') || url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }
  return FALLBACK_COVER
}

export const getLogs = async (): Promise<LogEntry[]> => {
  const response = await backend.get('/logs')
  return response.data.data
}

export const clearLogs = async (): Promise<void> => {
  await backend.delete('/logs')
}

export default backend
