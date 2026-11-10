import { computed, reactive } from 'vue'
import { ApiError, fetchHot100, fetchStatus, startRefresh } from '@/lib/api'
import { categoryCounts, selectVideos, summarize } from '@/lib/videos'
import type { Hot100Response, SortKey, VideoItem } from '@/lib/types'

interface State {
  videos: VideoItem[]
  loading: boolean
  refreshing: boolean
  updating: boolean
  preparing: boolean
  error: string
  updateTime: string
  isPartial: boolean
  source: string
  stale: boolean
  query: string
  category: string
  sort: SortKey
}

const state = reactive<State>({
  videos: [],
  loading: false,
  refreshing: false,
  updating: false,
  preparing: false,
  error: '',
  updateTime: '',
  isPartial: false,
  source: '',
  stale: false,
  query: '',
  category: 'all',
  sort: 'rank'
})

let pollPromise: Promise<void> | null = null

function describe(error: unknown): string {
  return error instanceof Error ? error.message : '请求失败'
}

function apply(data: Hot100Response): void {
  state.videos = data.data
  state.updateTime = data.update_time
  state.isPartial = data.is_partial
  state.source = data.source
  state.stale = data.is_stale
  state.updating = data.is_updating
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function pollUntilDone(): Promise<void> {
  state.updating = true
  const deadline = Date.now() + 150_000
  try {
    while (Date.now() < deadline) {
      const status = await fetchStatus()
      state.updating = status.is_updating
      if (!status.is_updating) {
        if (status.last_error) throw new Error(status.last_error)
        if (!status.total) throw new Error('刷新结束但没有数据，请查看日志')
        return
      }
      await sleep(700)
    }
    throw new Error('刷新超时，请查看日志')
  } finally {
    state.updating = false
  }
}

function waitForRefresh(): Promise<void> {
  if (!pollPromise) {
    pollPromise = pollUntilDone().finally(() => {
      pollPromise = null
    })
  }
  return pollPromise
}

async function load(): Promise<void> {
  if (state.loading) return
  state.loading = true
  state.error = ''
  try {
    let data: Hot100Response
    try {
      data = await fetchHot100()
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 503) throw error
      // 后端刚启动、还没抓到第一份数据：催一次并等它完成。
      state.preparing = true
      await startRefresh().catch(() => undefined)
      await waitForRefresh()
      data = await fetchHot100()
    }
    apply(data)
    if (data.is_stale || data.is_updating) {
      // 旧数据先展示，后台刷完再替换。
      void waitForRefresh()
        .then(async () => apply(await fetchHot100()))
        .catch(error => {
          state.error = describe(error)
        })
    }
  } catch (error) {
    state.error = describe(error)
  } finally {
    state.loading = false
    state.preparing = false
  }
}

async function refresh(): Promise<void> {
  if (state.refreshing) return
  state.refreshing = true
  state.error = ''
  try {
    await startRefresh()
    await waitForRefresh()
    apply(await fetchHot100())
  } catch (error) {
    state.error = describe(error)
  } finally {
    state.refreshing = false
  }
}

const categories = computed(() => categoryCounts(state.videos))
const visibleVideos = computed(() =>
  selectVideos(state.videos, state.category, state.query, state.sort)
)
const summary = computed(() => summarize(state.videos))

export function useVideos() {
  return {
    state,
    categories,
    visibleVideos,
    summary,
    load,
    refresh
  }
}
