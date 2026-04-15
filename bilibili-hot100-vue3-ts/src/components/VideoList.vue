<template>
  <div class="video-list" :class="{ dark: themeStore.isDark }">
    <n-empty
      v-if="!loading && videos.length === 0"
      description="暂无视频数据"
      size="large"
      class="empty-state"
    >
      <template #extra>
        <n-button @click="onRefresh">刷新数据</n-button>
      </template>
    </n-empty>

    <div v-else class="video-grid">
      <VideoCard
        v-for="video in videos"
        :key="video.bvid"
        :video="video"
      />
    </div>

    <div v-if="!loading && videos.length > 0" class="list-footer">
      <n-text depth="3">
        共 {{ videos.length }} 个视频
      </n-text>
    </div>
  </div>
</template>

<script setup lang="ts">
import { NEmpty, NButton, NSpin, NText } from 'naive-ui'
import { useThemeStore } from '@/stores/theme'
import VideoCard from './VideoCard.vue'
import type { VideoItem } from '@/types'

const props = defineProps<{
  videos: VideoItem[]
}>()

const emit = defineEmits<{
  (e: 'refresh'): void
}>()

const themeStore = useThemeStore()

const onRefresh = () => {
  emit('refresh')
}
</script>

<style scoped>
.video-list {
  padding: 24px 0;
}

.empty-state {
  padding: 100px 0;
}

/* 3列网格布局 */
.video-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

/* 响应式布局调整 */
@media (max-width: 1200px) {
  .video-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
  }
}

@media (max-width: 768px) {
  .video-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

.loading-more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px;
  color: #888;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 12px;
  margin: 24px 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.loading-more:hover {
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);
}

.loading-text {
  font-size: 16px;
  font-weight: 500;
}

.list-footer {
  text-align: center;
  padding: 32px;
  border-top: 1px solid #e8e8e8;
  margin-top: 24px;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 12px;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.list-footer:hover {
  box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.08);
}

.video-list.dark .list-footer {
  border-top-color: #333;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}

.video-list.dark .loading-more {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.video-list.dark .loading-more:hover {
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
}

.video-list.dark .list-footer:hover {
  box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.3);
}
</style>
