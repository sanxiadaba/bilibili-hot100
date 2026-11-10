<script setup lang="ts">
import { formatTime } from '@/lib/format'
import { SORT_OPTIONS } from '@/lib/videos'
import { useTheme } from '@/composables/useTheme'
import { useVideos } from '@/composables/useVideos'
import type { SortKey } from '@/lib/types'

const props = defineProps<{ view: 'list' | 'stats' }>()

const emit = defineEmits<{
  'update:view': [value: 'list' | 'stats']
  'open-logs': []
}>()

const { state, categories, refresh } = useVideos()
const { dark, toggleTheme } = useTheme()

function toggleView(): void {
  emit('update:view', props.view === 'stats' ? 'list' : 'stats')
}

function onSort(event: Event): void {
  state.sort = (event.target as HTMLSelectElement).value as SortKey
}
</script>

<template>
  <header class="header">
    <div class="bar">
      <div class="brand">
        <img src="/bilibili-icon.svg" alt="" width="28" height="28" />
        <h1>B站热门</h1>
        <span class="badge">TOP 100</span>
      </div>

      <div class="actions">
        <input
          v-model="state.query"
          class="search"
          type="search"
          placeholder="搜索标题或 UP 主"
          aria-label="搜索视频或UP主"
        />
        <button
          class="btn primary"
          type="button"
          :disabled="state.refreshing || state.updating"
          aria-label="刷新数据"
          @click="refresh"
        >
          {{ state.refreshing || state.updating ? '抓取中…' : '刷新' }}
        </button>
        <a class="btn" href="/api/export" download aria-label="导出当前数据">导出</a>
        <button
          class="btn"
          type="button"
          :aria-label="view === 'stats' ? '返回列表' : '打开数据分析'"
          @click="toggleView"
        >
          {{ view === 'stats' ? '列表' : '统计' }}
        </button>
        <button class="btn" type="button" aria-label="查看日志" @click="emit('open-logs')">
          日志
        </button>
        <button
          class="btn icon"
          type="button"
          :aria-label="dark ? '切换到浅色模式' : '切换到深色模式'"
          @click="toggleTheme"
        >
          {{ dark ? '☀' : '☾' }}
        </button>
      </div>
    </div>

    <div class="meta">
      <span v-if="state.updateTime">更新于 {{ formatTime(state.updateTime) }}</span>
      <span v-if="state.preparing" class="tag">抓取中…</span>
      <span v-else-if="state.updating" class="tag">后台刷新中…</span>
      <span v-if="state.isPartial" class="tag warn">数据不完整</span>
      <span v-if="state.source === 'snapshot'" class="tag">本地快照</span>
      <span class="count">共 {{ state.videos.length }} 条</span>
    </div>

    <div v-if="view === 'list'" class="filters">
      <div class="chips" role="group" aria-label="按分类筛选">
        <button
          type="button"
          :class="['chip', { active: state.category === 'all' }]"
          :aria-pressed="state.category === 'all'"
          @click="state.category = 'all'"
        >
          全部 {{ state.videos.length }}
        </button>
        <button
          v-for="cat in categories"
          :key="cat.name"
          type="button"
          :class="['chip', { active: state.category === cat.name }]"
          :aria-pressed="state.category === cat.name"
          @click="state.category = cat.name"
        >
          {{ cat.name }} {{ cat.count }}
        </button>
      </div>
      <label class="sort">
        排序
        <select :value="state.sort" aria-label="排序方式" @change="onSort">
          <option v-for="option in SORT_OPTIONS" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>
    </div>
  </header>
</template>

<style scoped>
.header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--bg);
  background: color-mix(in srgb, var(--bg) 88%, transparent);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--line);
}

.bar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  padding: 12px 24px 8px;
  max-width: 1200px;
  margin: 0 auto;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.brand h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.badge {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-weak);
  border-radius: 4px;
  padding: 2px 6px;
}

.actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-left: auto;
}

.search {
  width: 220px;
}

.meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px 8px;
  color: var(--muted);
  font-size: 12px;
}

.meta .count {
  margin-left: auto;
}

.filters {
  display: flex;
  align-items: center;
  gap: 16px;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px 10px;
}

.chips {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
  scrollbar-width: thin;
}

.chip {
  flex-shrink: 0;
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--muted);
  border-radius: 999px;
  padding: 5px 12px;
  font-size: 13px;
  cursor: pointer;
}

.chip:hover {
  color: var(--text);
  border-color: var(--muted);
}

.chip.active {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-weak);
}

.sort {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  font-size: 13px;
  color: var(--muted);
}

.sort select {
  width: 104px;
}

@media (max-width: 760px) {
  .bar {
    padding: 10px 16px 6px;
    gap: 10px;
  }

  .actions {
    width: 100%;
    margin-left: 0;
  }

  .search {
    flex: 1 0 100%;
    width: 100%;
    min-width: 0;
  }

  .meta,
  .filters {
    padding-left: 16px;
    padding-right: 16px;
  }

  .filters {
    align-items: flex-start;
    flex-direction: column-reverse;
    gap: 8px;
  }

  .chips {
    width: 100%;
  }
}
</style>
