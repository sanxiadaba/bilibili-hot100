import type { Hot100Response, LogEntry, StatusResponse } from './types'

const REQUEST_TIMEOUT_MS = 15_000

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // 本机服务也可能卡住（事件循环被占、进程被挂起）；没有超时会让调用方永远 await。
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    const response = await fetch(path, {
      ...init,
      signal: init?.signal ?? controller.signal,
      headers: { Accept: 'application/json', ...init?.headers }
    })
    if (!response.ok) {
      let detail = `请求失败 (${response.status})`
      try {
        const body = (await response.json()) as { detail?: string }
        if (body?.detail) detail = body.detail
      } catch {
        // 响应不是 JSON 时保留默认提示
      }
      throw new ApiError(detail, response.status)
    }
    return (await response.json()) as T
  } finally {
    clearTimeout(timer)
  }
}

export const fetchHot100 = (): Promise<Hot100Response> => request<Hot100Response>('/api/hot100')

export const fetchStatus = (): Promise<StatusResponse> => request<StatusResponse>('/api/status')

export const startRefresh = (): Promise<{ started: boolean }> =>
  request<{ started: boolean }>('/api/refresh', { method: 'POST' })

export const fetchLogs = (): Promise<{ data: LogEntry[] }> =>
  request<{ data: LogEntry[] }>('/api/logs')

export const clearLogs = (): Promise<{ ok: boolean }> =>
  request<{ ok: boolean }>('/api/logs', { method: 'DELETE' })

export function logsSocketUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/logs/ws`
}
