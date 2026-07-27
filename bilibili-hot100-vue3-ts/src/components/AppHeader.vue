<template>
  <header class="app-header" :class="{ dark: themeStore.isDark }">
    <div class="header-content">
      <div class="logo-section">
        <div class="logo">
          <n-icon :component="LogoYoutube" :size="32" color="#fb7299" />
          <h1 class="title">B站热门视频</h1>
        </div>
        <n-tag type="info" size="small" class="count-tag">
          TOP 100
        </n-tag>
      </div>

      <div class="search-section">
        <n-input
          v-model:value="videoStore.searchQuery"
          placeholder="搜索视频或UP主..."
          clearable
          @update:value="onSearch"
        >
          <template #prefix>
            <n-icon :component="SearchOutline" />
          </template>
        </n-input>
      </div>

      <div class="actions-section">
        <n-space>
          <n-tooltip>
            <template #trigger>
              <n-button
                circle
                size="large"
                :loading="videoStore.refreshing"
                aria-label="刷新数据"
                @click="onRefresh"
                class="action-button"
              >
                <template #icon>
                  <n-icon :component="RefreshOutline" :size="20" />
                </template>
              </n-button>
            </template>
            刷新数据
          </n-tooltip>

          <n-tooltip>
            <template #trigger>
              <n-button circle size="large" aria-label="查看日志" @click="showLogs" class="action-button">
                <template #icon>
                  <n-icon :component="DocumentTextOutline" :size="20" />
                </template>
              </n-button>
            </template>
            查看日志
          </n-tooltip>

          <n-tooltip>
            <template #trigger>
              <n-button
                circle
                size="large"
                :aria-label="showStatsView ? '返回视频列表' : '打开数据分析'"
                @click="toggleStats"
                class="action-button"
              >
                <template #icon>
                  <n-icon :component="StatsChartOutline" :size="20" />
                </template>
              </n-button>
            </template>
            {{ showStatsView ? '返回列表' : '数据分析' }}
          </n-tooltip>

          <ThemeToggle />
        </n-space>
      </div>
    </div>

    <div v-if="!showStatsView" class="filter-section">
      <CategoryFilter
        :categories="videoStore.categories"
        :selected="videoStore.selectedCategory"
        @select="onCategorySelect"
      />

      <n-space align="center" class="sort-section">
        <n-text depth="3" style="font-size: 13px;">排序:</n-text>
        <n-select
          v-model:value="videoStore.sortBy"
          :options="sortOptions"
          size="small"
          style="width: 120px"
          @update:value="onSortChange"
        />
      </n-space>
    </div>

    <div v-if="videoStore.lastUpdateTime" class="update-info">
      <n-text depth="3" style="font-size: 12px;">
        更新时间: {{ formatUpdateTime(videoStore.lastUpdateTime) }}
        <n-tag
          v-if="videoStore.fromCache"
          size="tiny"
          type="warning"
          style="margin-left: 8px"
        >
          缓存
        </n-tag>
      </n-text>
    </div>
  </header>
</template>

<script setup lang="ts">
import {
  NIcon,
  NInput,
  NButton,
  NSpace,
  NTag,
  NTooltip,
  NSelect,
  NText
} from 'naive-ui'
import {
  LogoYoutube,
  SearchOutline,
  RefreshOutline,
  DocumentTextOutline,
  BarChartOutline as StatsChartOutline
} from '@vicons/ionicons5'
import { useThemeStore } from '@/stores/theme'
import { useVideoStore } from '@/stores/videos'
import ThemeToggle from './ThemeToggle.vue'
import CategoryFilter from './CategoryFilter.vue'
import type { SortType } from '@/types'

const props = defineProps<{
  showStatsView: boolean
}>()

const emit = defineEmits<{
  (e: 'refresh'): void
  (e: 'show-logs'): void
  (e: 'toggle-stats'): void
}>()

const themeStore = useThemeStore()
const videoStore = useVideoStore()

const sortOptions: Array<{ label: string; value: SortType }> = [
  { label: '默认排名', value: 'rank' },
  { label: '播放量', value: 'view' },
  { label: '点赞数', value: 'like' },
  { label: '投币数', value: 'coin' },
  { label: '收藏数', value: 'favorite' },
  { label: '弹幕数', value: 'danmaku' }
]

const onSearch = (value: string) => {
  videoStore.setSearch(value)
}

const onRefresh = () => {
  emit('refresh')
}

const showLogs = () => {
  emit('show-logs')
}

const toggleStats = () => {
  emit('toggle-stats')
}

const onCategorySelect = (category: string) => {
  videoStore.setCategory(category)
}

const onSortChange = (value: SortType) => {
  videoStore.setSort(value)
}

const formatUpdateTime = (time: string): string => {
  const date = new Date(time)
  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.app-header {
  background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%);
  border-bottom: 1px solid #e8e8e8;
  padding: 16px 24px;
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(10px);
}

.app-header.dark {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-bottom-color: #333;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(135deg, #fb7299, #ff8eb4);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.count-tag {
  font-weight: 600;
}

.search-section {
  flex: 1;
  max-width: 400px;
  min-width: 200px;
}

.actions-section {
  flex-shrink: 0;
}

.action-button {
  transition: all 0.3s ease;
  border-radius: 50%;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.action-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.action-button:active {
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.filter-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e8e8e8;
  gap: 16px;
  flex-wrap: wrap;
}

.app-header.dark .filter-section {
  border-top-color: #333;
}

.sort-section {
  flex-shrink: 0;
}

.update-info {
  margin-top: 12px;
  text-align: right;
}

@media (max-width: 768px) {
  .header-content {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: 12px;
  }

  .search-section {
    max-width: none;
    min-width: 0;
    grid-column: 1 / -1;
  }

  .actions-section {
    justify-self: end;
  }

  .filter-section {
    margin-top: 10px;
    padding-top: 10px;
    gap: 8px;
  }

  .sort-section {
    justify-content: flex-start;
  }

  .update-info {
    margin-top: 6px;
  }
}
</style>
