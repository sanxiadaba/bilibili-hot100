import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchHot100, refreshData } from '@/api/backend'
import type { VideoItem, CategoryStat, StatsData, SortType } from '@/types'

export const useVideoStore = defineStore('videos', () => {
  const videos = ref<VideoItem[]>([])
  const loading = ref(false)
  const refreshing = ref(false)
  const error = ref<string | null>(null)
  const selectedCategory = ref<string>('all')
  const searchQuery = ref('')
  const sortBy = ref<SortType>('rank')
  const lastUpdateTime = ref<string | null>(null)
  const fromCache = ref(false)

  const categories = computed(() => {
    const cats = new Map<string, number>()
    videos.value.forEach(v => {
      const name = v.tname || '未分类'
      cats.set(name, (cats.get(name) || 0) + 1)
    })
    return Array.from(cats.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([name, count]) => ({ name, count }))
  })

  const filteredVideos = computed(() => {
    let result = [...videos.value]

    if (selectedCategory.value !== 'all') {
      result = result.filter(v => v.tname === selectedCategory.value)
    }

    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      result = result.filter(v =>
        v.title?.toLowerCase().includes(query) ||
        v.owner?.name?.toLowerCase().includes(query)
      )
    }

    switch (sortBy.value) {
      case 'view':
        result.sort((a, b) => (b.stat?.view || 0) - (a.stat?.view || 0))
        break
      case 'like':
        result.sort((a, b) => (b.stat?.like || 0) - (a.stat?.like || 0))
        break
      case 'coin':
        result.sort((a, b) => (b.stat?.coin || 0) - (a.stat?.coin || 0))
        break
      case 'favorite':
        result.sort((a, b) => (b.stat?.favorite || 0) - (a.stat?.favorite || 0))
        break
      case 'danmaku':
        result.sort((a, b) => (b.stat?.danmaku || 0) - (a.stat?.danmaku || 0))
        break
      default:
        result.sort((a, b) => (a.rank || 0) - (b.rank || 0))
    }

    return result
  })

  const stats = computed<StatsData | null>(() => {
    if (!videos.value.length) return null

    const totalViews = videos.value.reduce((sum, v) => sum + (v.stat?.view || 0), 0)
    const totalLikes = videos.value.reduce((sum, v) => sum + (v.stat?.like || 0), 0)
    const totalCoins = videos.value.reduce((sum, v) => sum + (v.stat?.coin || 0), 0)
    const totalFavorites = videos.value.reduce((sum, v) => sum + (v.stat?.favorite || 0), 0)
    const totalDanmaku = videos.value.reduce((sum, v) => sum + (v.stat?.danmaku || 0), 0)
    const totalReply = videos.value.reduce((sum, v) => sum + (v.stat?.reply || 0), 0)
    const totalShare = videos.value.reduce((sum, v) => sum + (v.stat?.share || 0), 0)

    const categoryStats: Record<string, CategoryStat> = {}
    videos.value.forEach(v => {
      const cat = v.tname || '未分类'
      if (!categoryStats[cat]) {
        categoryStats[cat] = { count: 0, views: 0, likes: 0 }
      }
      categoryStats[cat].count++
      categoryStats[cat].views += v.stat?.view || 0
      categoryStats[cat].likes += v.stat?.like || 0
    })

    const topVideos = [...videos.value]
      .sort((a, b) => (b.stat?.view || 0) - (a.stat?.view || 0))
      .slice(0, 10)

    const mostLiked = [...videos.value]
      .sort((a, b) => (b.stat?.like || 0) - (a.stat?.like || 0))
      .slice(0, 5)

    return {
      total: videos.value.length,
      totalViews,
      totalLikes,
      totalCoins,
      totalFavorites,
      totalDanmaku,
      totalReply,
      totalShare,
      avgViews: Math.round(totalViews / videos.value.length),
      avgLikes: Math.round(totalLikes / videos.value.length),
      categoryStats,
      topVideos,
      mostLiked
    }
  })

  const loadVideos = async (forceRefresh = false): Promise<void> => {
    loading.value = true
    error.value = null
    try {
      const result = await fetchHot100(forceRefresh)
      videos.value = result.videos
      lastUpdateTime.value = result.updateTime
      fromCache.value = result.fromCache
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  const refreshVideos = async (): Promise<boolean> => {
    refreshing.value = true
    error.value = null
    try {
      await refreshData()
      await new Promise(resolve => setTimeout(resolve, 2000))
      const result = await fetchHot100(true)
      videos.value = result.videos
      lastUpdateTime.value = result.updateTime
      fromCache.value = result.fromCache
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : '刷新失败'
      return false
    } finally {
      refreshing.value = false
    }
  }

  const setCategory = (cat: string): void => {
    selectedCategory.value = cat
  }

  const setSearch = (query: string): void => {
    searchQuery.value = query
  }

  const setSort = (sort: SortType): void => {
    sortBy.value = sort
  }

  return {
    videos,
    loading,
    refreshing,
    error,
    selectedCategory,
    searchQuery,
    sortBy,
    lastUpdateTime,
    fromCache,
    categories,
    filteredVideos,
    stats,
    loadVideos,
    refreshVideos,
    setCategory,
    setSearch,
    setSort
  }
})
