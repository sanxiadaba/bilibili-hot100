<template>
  <n-card
    :class="['video-card', { 'dark': themeStore.isDark }]"
    hoverable
    @click="openVideo"
  >
    <div class="card-content">
      <div class="rank-badge" :class="rankClass">
        {{ video.rank }}
      </div>
      
      <div class="thumbnail-wrapper">
        <img
          :src="thumbnailUrl"
          :alt="video.title"
          class="thumbnail"
          loading="lazy"
          @error="onImageError"
        />
        <span class="duration">{{ formatDuration(video.duration) }}</span>
        <n-tag
          v-if="video.rcmd_reason?.content"
          size="small"
          type="error"
          class="rcmd-tag"
        >
          {{ video.rcmd_reason.content }}
        </n-tag>
      </div>

      <div class="info">
        <h3 class="title" :title="video.title">{{ video.title }}</h3>
        
        <div class="meta">
          <div class="up">
            <img
              :src="ownerFace"
              class="avatar"
              alt=""
              loading="lazy"
              @error="onAvatarError"
            />
            <n-ellipsis class="up-name">{{ video.owner?.name || '未知UP主' }}</n-ellipsis>
          </div>
          <n-tag size="small" class="category-tag">{{ video.tname || '其他' }}</n-tag>
        </div>

        <div class="stats">
          <span v-for="stat in statsList" :key="stat.key" class="stat-item" :title="stat.label">
            <n-icon :component="stat.icon" :size="14" />
            {{ stat.value }}
          </span>
        </div>
      </div>
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { NCard, NTag, NEllipsis, NIcon } from 'naive-ui'
import { PlayCircleOutline, ChatbubbleOutline, ThumbsUpOutline } from '@vicons/ionicons5'
import { useThemeStore } from '@/stores/theme'
import { getImageUrl } from '@/api/backend'
import { formatNumber, formatDuration, getRankClass } from '@/utils/format'
import type { VideoItem } from '@/types'

const props = defineProps<{
  video: VideoItem
}>()

const themeStore = useThemeStore()
const imageError = ref(false)
const avatarError = ref(false)

const thumbnailUrl = computed(() => {
  if (imageError.value) return ''
  return getImageUrl(props.video.pic || 'https://i0.hdslb.com/bfs/archive/7e6c4623b846e5a01b326f608c2c98e14c5b3c3c.jpg')
})

const ownerFace = computed(() => {
  if (avatarError.value) return 'https://i0.hdslb.com/bfs/face/member/noface.jpg'
  return getImageUrl(props.video.owner?.face || '')
})

const rankClass = computed(() => getRankClass(props.video.rank))

const statsList = computed(() => [
  { key: 'view', label: '播放', icon: PlayCircleOutline, value: formatNumber(props.video.stat?.view) },
  { key: 'danmaku', label: '弹幕', icon: ChatbubbleOutline, value: formatNumber(props.video.stat?.danmaku) },
  { key: 'like', label: '点赞', icon: ThumbsUpOutline, value: formatNumber(props.video.stat?.like) }
])

const onImageError = () => {
  imageError.value = true
}

const onAvatarError = () => {
  avatarError.value = true
}

const openVideo = () => {
  window.open(`https://www.bilibili.com/video/${props.video.bvid}`, '_blank')
}
</script>

<style scoped>
.video-card {
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.video-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.video-card :deep(.n-card__content) {
  padding: 0;
}

.card-content {
  position: relative;
}

.rank-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 10;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.85em;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(12px);
  color: #e0e0e0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
}

.rank-badge:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.rank-badge.top3 {
  background: linear-gradient(135deg, #ff6b6b, #ee5a24);
  color: #fff;
  box-shadow: 0 4px 12px rgba(238, 90, 36, 0.4);
}

.rank-badge.top3:hover {
  box-shadow: 0 6px 16px rgba(238, 90, 36, 0.6);
}

.rank-badge.top10 {
  background: linear-gradient(135deg, #3a7bd5, #00d2ff);
  color: #fff;
  box-shadow: 0 4px 12px rgba(0, 210, 255, 0.3);
}

.rank-badge.top10:hover {
  box-shadow: 0 6px 16px rgba(0, 210, 255, 0.5);
}

.thumbnail-wrapper {
  position: relative;
  width: 100%;
  padding-top: 56.25%;
  overflow: hidden;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border-radius: 16px 16px 0 0;
}

.thumbnail {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 16px 16px 0 0;
}

.video-card:hover .thumbnail {
  transform: scale(1.1);
}

.duration {
  position: absolute;
  bottom: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.85);
  color: #fff;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 0.8em;
  font-weight: 600;
  backdrop-filter: blur(8px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
}

.rcmd-tag {
  position: absolute;
  top: 10px;
  right: 10px;
  font-weight: 700;
  font-size: 0.75em;
  border-radius: 6px;
  padding: 2px 8px;
  box-shadow: 0 2px 6px rgba(255, 69, 0, 0.3);
  transition: all 0.3s ease;
}

.rcmd-tag:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 10px rgba(255, 69, 0, 0.5);
}

.info {
  padding: 16px;
  background: #fff;
  border-radius: 0 0 16px 16px;
}

.title {
  font-size: 1em;
  font-weight: 600;
  line-height: 1.5;
  margin: 0 0 12px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 3em;
  color: #333;
  transition: color 0.3s ease;
}

.video-card:hover .title {
  color: #fb7299;
}

.meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 12px;
}

.up {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid #f0f0f0;
  transition: all 0.3s ease;
}

.video-card:hover .avatar {
  border-color: #fb7299;
  transform: scale(1.05);
}

.up-name {
  font-size: 0.85em;
  flex: 1;
  color: #666;
  transition: color 0.3s ease;
}

.video-card:hover .up-name {
  color: #fb7299;
}

.category-tag {
  flex-shrink: 0;
  font-size: 0.75em;
  border-radius: 6px;
  padding: 2px 8px;
  transition: all 0.3s ease;
}

.video-card:hover .category-tag {
  transform: scale(1.05);
}

.stats {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8em;
  opacity: 0.7;
  color: #888;
  transition: all 0.3s ease;
}

.video-card:hover .stat-item {
  opacity: 1;
  color: #666;
}

/* 深色模式样式 */
.video-card.dark {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.video-card.dark:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}

.video-card.dark .thumbnail-wrapper {
  background: linear-gradient(135deg, #1a1a2e, #16213e);
}

.video-card.dark .info {
  background: #1e1e2f;
}

.video-card.dark .title {
  color: #e8e8e8;
}

.video-card.dark:hover .title {
  color: #ff8eb4;
}

.video-card.dark .up-name {
  color: #a0a0a0;
}

.video-card.dark:hover .up-name {
  color: #ff8eb4;
}

.video-card.dark .stat-item {
  color: #888;
}

.video-card.dark:hover .stat-item {
  color: #a0a0a0;
}

.video-card.dark .avatar {
  border-color: rgba(255, 255, 255, 0.2);
}

.video-card.dark:hover .avatar {
  border-color: #ff8eb4;
}

.video-card.dark .stats {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}
</style>
