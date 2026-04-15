<template>
  <div class="stats-view" :class="{ dark: themeStore.isDark }">
    <!-- 详情弹窗 -->
    <n-modal
      v-model:show="showDetailModal"
      :title="detailTitle"
      preset="card"
      style="width: 900px; max-width: 95vw"
      :segmented="{ content: true }"
    >
      <div class="detail-content">
        <div v-if="detailVideos.length > 0" class="detail-grid">
          <div
            v-for="(video, index) in detailVideos"
            :key="video.bvid"
            class="detail-item"
            @click="openVideo(video.bvid)"
          >
            <div class="detail-rank">{{ index + 1 }}</div>
            <div class="detail-cover">
              <img
                :src="getImageUrl(video.pic || 'https://i0.hdslb.com/bfs/archive/7e6c4623b846e5a01b326f608c2c98e14c5b3c3c.jpg')"
                class="detail-img"
                loading="lazy"
                @error="$event.target.src = 'https://i0.hdslb.com/bfs/archive/7e6c4623b846e5a01b326f608c2c98e14c5b3c3c.jpg'"
              />
            </div>
            <div class="detail-info">
              <div class="detail-title">{{ video.title }}</div>
              <div class="detail-up">
                <n-avatar round :size="16" :src="video.owner?.face" />
                <span>{{ video.owner?.name }}</span>
              </div>
              <div class="detail-stat">
                <n-tag type="error" size="tiny">{{ formatNumber(getVideoStat(video, detailType)) }} {{ getStatLabel(detailType) }}</n-tag>
              </div>
            </div>
          </div>
        </div>
        <n-empty v-else description="暂无数据" />
      </div>
    </n-modal>

    <n-card title="数据概览" class="stats-overview">
      <n-grid :cols="4" :x-gap="24" :y-gap="24" responsive="screen">
        <n-gi>
          <div class="overview-item" @click="showDetail('views')">
            <div class="overview-icon" style="background: linear-gradient(135deg, #fb7299, #ff8eb4);">
              <n-icon :component="EyeOutline" :size="28" color="#fff" />
            </div>
            <div class="overview-content">
              <div class="overview-value">{{ formatNumber(stats.totalViews) }}</div>
              <div class="overview-label">总播放量</div>
            </div>
            <div class="overview-arrow">
              <n-icon :component="ChevronForwardOutline" :size="20" />
            </div>
          </div>
        </n-gi>

        <n-gi>
          <div class="overview-item" @click="showDetail('likes')">
            <div class="overview-icon" style="background: linear-gradient(135deg, #ffd700, #ffaa00);">
              <n-icon :component="ThumbsUpOutline" :size="28" color="#fff" />
            </div>
            <div class="overview-content">
              <div class="overview-value">{{ formatNumber(stats.totalLikes) }}</div>
              <div class="overview-label">总点赞</div>
            </div>
            <div class="overview-arrow">
              <n-icon :component="ChevronForwardOutline" :size="20" />
            </div>
          </div>
        </n-gi>

        <n-gi>
          <div class="overview-item" @click="showDetail('favorites')">
            <div class="overview-icon" style="background: linear-gradient(135deg, #3a7bd5, #00d2ff);">
              <n-icon :component="HeartOutline" :size="28" color="#fff" />
            </div>
            <div class="overview-content">
              <div class="overview-value">{{ formatNumber(stats.totalFavorites) }}</div>
              <div class="overview-label">总收藏</div>
            </div>
            <div class="overview-arrow">
              <n-icon :component="ChevronForwardOutline" :size="20" />
            </div>
          </div>
        </n-gi>

        <n-gi>
          <div class="overview-item" @click="showDetail('coins')">
            <div class="overview-icon" style="background: linear-gradient(135deg, #9c27b0, #e91e63);">
              <n-icon :component="CashOutline" :size="28" color="#fff" />
            </div>
            <div class="overview-content">
              <div class="overview-value">{{ formatNumber(stats.totalCoins) }}</div>
              <div class="overview-label">总投币</div>
            </div>
            <div class="overview-arrow">
              <n-icon :component="ChevronForwardOutline" :size="20" />
            </div>
          </div>
        </n-gi>
      </n-grid>

      <n-divider />

      <n-grid :cols="4" :x-gap="24" :y-gap="24" responsive="screen">
        <n-gi>
          <div class="sub-stat" @click="showDetail('danmaku')">
            <div class="sub-stat-icon">
              <n-icon :component="ChatbubbleOutline" :size="20" />
            </div>
            <div class="sub-stat-value">{{ formatNumber(stats.totalDanmaku) }}</div>
            <div class="sub-stat-label">弹幕总数</div>
          </div>
        </n-gi>
        <n-gi>
          <div class="sub-stat" @click="showDetail('reply')">
            <div class="sub-stat-icon">
              <n-icon :component="ChatboxOutline" :size="20" />
            </div>
            <div class="sub-stat-value">{{ formatNumber(stats.totalReply) }}</div>
            <div class="sub-stat-label">评论总数</div>
          </div>
        </n-gi>
        <n-gi>
          <div class="sub-stat" @click="showDetail('share')">
            <div class="sub-stat-icon">
              <n-icon :component="ShareSocialOutline" :size="20" />
            </div>
            <div class="sub-stat-value">{{ formatNumber(stats.totalShare) }}</div>
            <div class="sub-stat-label">分享总数</div>
          </div>
        </n-gi>
        <n-gi>
          <div class="sub-stat" @click="showDetail('avgViews')">
            <div class="sub-stat-icon">
              <n-icon :component="TrendingUpOutline" :size="20" />
            </div>
            <div class="sub-stat-value">{{ formatNumber(stats.avgViews) }}</div>
            <div class="sub-stat-label">平均播放量</div>
          </div>
        </n-gi>
      </n-grid>
    </n-card>

    <StatsCharts :stats="stats" />

    <n-card title="点赞最多 TOP 5" class="top-liked">
      <div class="top-liked-grid">
        <div 
          v-for="(video, index) in stats.mostLiked" 
          :key="video.bvid"
          class="top-liked-item"
          @click="openVideo(video.bvid)"
        >
          <div class="top-liked-cover">
            <img
              :src="getImageUrl(video.pic || 'https://i0.hdslb.com/bfs/archive/7e6c4623b846e5a01b326f608c2c98e14c5b3c3c.jpg')"
              class="top-liked-img"
              loading="lazy"
              @error="$event.target.src = 'https://i0.hdslb.com/bfs/archive/7e6c4623b846e5a01b326f608c2c98e14c5b3c3c.jpg'"
            />
            <div class="top-liked-rank" :class="`rank-${index + 1}`">
              <template v-if="index === 0">
                <n-icon :component="ThumbsUpOutline" :size="16" />
              </template>
              <template v-else-if="index === 1">
                <n-icon :component="ThumbsUpOutline" :size="14" />
              </template>
              <template v-else-if="index === 2">
                <n-icon :component="ThumbsUpOutline" :size="12" />
              </template>
              <template v-else>
                {{ index + 1 }}
              </template>
            </div>
          </div>
          <div class="top-liked-info">
            <div class="top-liked-title">{{ video.title }}</div>
            <div class="top-liked-meta">
              <n-avatar round :size="20" :src="video.owner?.face" />
              <span class="top-liked-up">{{ video.owner?.name }}</span>
            </div>
            <div class="top-liked-stats">
              <n-tag type="error" size="small">{{ formatNumber(video.stat?.like || 0) }} 赞</n-tag>
              <span class="top-liked-views">{{ formatNumber(video.stat?.view || 0) }} 播放</span>
            </div>
          </div>
        </div>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  NCard,
  NGrid,
  NGi,
  NIcon,
  NText,
  NTag,
  NAvatar,
  NSpace,
  NDivider,
  NList,
  NListItem,
  NThing,
  NImage,
  NModal,
  NEmpty,
  useMessage
} from 'naive-ui'
import {
  EyeOutline,
  ThumbsUpOutline,
  HeartOutline,
  CashOutline,
  ChevronForwardOutline,
  ChatbubbleOutline,
  ChatboxOutline,
  ShareSocialOutline,
  TrendingUpOutline,
  LinkOutline
} from '@vicons/ionicons5'
import { useThemeStore } from '@/stores/theme'
import { formatNumber } from '@/utils/format'
import { getImageUrl } from '@/api/backend'
import StatsCharts from './StatsCharts.vue'
import type { StatsData } from '@/types'

const props = defineProps<{
  stats: StatsData
}>()

const themeStore = useThemeStore()
const message = useMessage()

// 详情弹窗状态
const showDetailModal = ref(false)
const detailType = ref('')
const detailTitle = computed(() => {
  const labels: Record<string, string> = {
    views: '播放量 TOP 10',
    likes: '点赞 TOP 10',
    favorites: '收藏 TOP 10',
    coins: '投币 TOP 10',
    danmaku: '弹幕 TOP 10',
    reply: '评论 TOP 10',
    share: '分享 TOP 10',
    avgViews: '播放量 TOP 10'
  }
  return labels[detailType.value] || '详情'
})

const detailVideos = computed(() => {
  if (!props.stats) return []
  
  const videos = [...props.stats.topVideos]
  
  switch (detailType.value) {
    case 'views':
    case 'avgViews':
      return videos.sort((a, b) => (b.stat?.view || 0) - (a.stat?.view || 0)).slice(0, 10)
    case 'likes':
      return videos.sort((a, b) => (b.stat?.like || 0) - (a.stat?.like || 0)).slice(0, 10)
    case 'favorites':
      return videos.sort((a, b) => (b.stat?.favorite || 0) - (a.stat?.favorite || 0)).slice(0, 10)
    case 'coins':
      return videos.sort((a, b) => (b.stat?.coin || 0) - (a.stat?.coin || 0)).slice(0, 10)
    case 'danmaku':
      return videos.sort((a, b) => (b.stat?.danmaku || 0) - (a.stat?.danmaku || 0)).slice(0, 10)
    case 'reply':
      return videos.sort((a, b) => (b.stat?.reply || 0) - (a.stat?.reply || 0)).slice(0, 10)
    case 'share':
      return videos.sort((a, b) => (b.stat?.share || 0) - (a.stat?.share || 0)).slice(0, 10)
    default:
      return videos.slice(0, 10)
  }
})

const getVideoStat = (video: any, type: string): number => {
  switch (type) {
    case 'views':
    case 'avgViews':
      return video.stat?.view || 0
    case 'likes':
      return video.stat?.like || 0
    case 'favorites':
      return video.stat?.favorite || 0
    case 'coins':
      return video.stat?.coin || 0
    case 'danmaku':
      return video.stat?.danmaku || 0
    case 'reply':
      return video.stat?.reply || 0
    case 'share':
      return video.stat?.share || 0
    default:
      return 0
  }
}

const getStatLabel = (type: string): string => {
  const labels: Record<string, string> = {
    views: '播放',
    likes: '点赞',
    favorites: '收藏',
    coins: '投币',
    danmaku: '弹幕',
    reply: '评论',
    share: '分享',
    avgViews: '播放'
  }
  return labels[type] || ''
}

const showDetail = (type: string) => {
  detailType.value = type
  showDetailModal.value = true
}

const openVideo = (bvid: string) => {
  window.open(`https://www.bilibili.com/video/${bvid}`, '_blank')
}
</script>

<style scoped>
.stats-view {
  padding: 24px 0;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.stats-overview {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
}

.stats-overview:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.overview-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: 12px;
  background: #fff;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.overview-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.6s ease;
}

.overview-item:hover::before {
  left: 100%;
}

.overview-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
}

.overview-icon {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
}

.overview-item:hover .overview-icon {
  transform: scale(1.05);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
}

.overview-content {
  flex: 1;
}

.overview-value {
  font-size: 1.6rem;
  font-weight: 700;
  color: #333;
  line-height: 1.2;
  margin-bottom: 4px;
  transition: color 0.3s ease;
}

.overview-item:hover .overview-value {
  color: #fb7299;
}

.overview-label {
  font-size: 0.9rem;
  color: #888;
  margin-top: 2px;
  transition: color 0.3s ease;
}

.overview-item:hover .overview-label {
  color: #666;
}

.overview-arrow {
  opacity: 0.5;
  transition: all 0.3s ease;
}

.overview-item:hover .overview-arrow {
  opacity: 1;
  transform: translateX(4px);
}

.sub-stat {
  text-align: center;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.sub-stat::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.6s ease;
}

.sub-stat:hover::before {
  left: 100%;
}

.sub-stat:hover {
  transform: translateY(-4px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
  background: #f0f0f0;
}

.sub-stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(251, 114, 153, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
  transition: all 0.3s ease;
}

.sub-stat:hover .sub-stat-icon {
  background: rgba(251, 114, 153, 0.2);
  transform: scale(1.1);
}

.sub-stat-value {
  font-size: 1.3rem;
  font-weight: 600;
  color: #333;
  line-height: 1.2;
  transition: color 0.3s ease;
}

.sub-stat:hover .sub-stat-value {
  color: #fb7299;
}

.sub-stat-label {
  font-size: 0.85rem;
  color: #888;
  margin-top: 4px;
  transition: color 0.3s ease;
}

.sub-stat:hover .sub-stat-label {
  color: #666;
}

.top-liked {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
}

.top-liked:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.top-item {
  cursor: pointer;
  transition: all 0.3s ease;
  border-radius: 8px;
  margin: 0 8px;
}

.top-item:hover {
  background: rgba(251, 114, 153, 0.05);
  transform: translateX(8px);
}

.top-thing {
  transition: all 0.3s ease;
}

.rank-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1rem;
  background: #e0e0e0;
  color: #666;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
}

.top-item:hover .rank-avatar {
  transform: scale(1.1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.rank-1 {
  background: linear-gradient(135deg, #ffd700, #ffaa00);
  color: #fff;
  box-shadow: 0 4px 12px rgba(255, 215, 0, 0.4);
}

.rank-2 {
  background: linear-gradient(135deg, #c0c0c0, #a0a0a0);
  color: #fff;
  box-shadow: 0 4px 12px rgba(192, 192, 192, 0.4);
}

.rank-3 {
  background: linear-gradient(135deg, #cd7f32, #b87333);
  color: #fff;
  box-shadow: 0 4px 12px rgba(205, 127, 50, 0.4);
}

.video-title {
  font-size: 1rem;
  line-height: 1.4;
  transition: color 0.3s ease;
}

.top-item:hover .video-title {
  color: #fb7299;
}

.like-tag {
  font-weight: 600;
  transition: all 0.3s ease;
}

.top-item:hover .like-tag {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(255, 69, 0, 0.3);
}

.owner-avatar {
  transition: all 0.3s ease;
}

.top-item:hover .owner-avatar {
  transform: scale(1.1);
  border: 2px solid #fb7299;
}

.top-liked-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}

.top-liked-item {
  cursor: pointer;
  transition: all 0.3s ease;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.top-liked-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.top-liked-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  overflow: hidden;
}

.top-liked-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.3s ease;
}

.top-liked-item:hover .top-liked-img {
  transform: scale(1.05);
}

.top-liked-rank {
  position: absolute;
  top: 8px;
  left: 8px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.top-liked-rank.rank-1 {
  background: linear-gradient(135deg, #ffd700, #ffaa00);
  color: #fff;
}

.top-liked-rank.rank-2 {
  background: linear-gradient(135deg, #c0c0c0, #a0a0a0);
  color: #fff;
}

.top-liked-rank.rank-3 {
  background: linear-gradient(135deg, #cd7f32, #b87333);
  color: #fff;
}

.top-liked-info {
  padding: 12px;
}

.top-liked-title {
  font-size: 14px;
  font-weight: 600;
  line-height: 1.4;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  color: #333;
}

.top-liked-item:hover .top-liked-title {
  color: #fb7299;
}

.top-liked-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.top-liked-up {
  font-size: 13px;
  color: #666;
}

.top-liked-stats {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.top-liked-views {
  font-size: 12px;
  color: #888;
}

@media (max-width: 1200px) {
  .top-liked-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .top-liked-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Dark mode styles for new layout */
.stats-view.dark .top-liked-item {
  background: #1e1e2f;
}

.stats-view.dark .top-liked-title {
  color: #e8e8e8;
}

.stats-view.dark .top-liked-item:hover .top-liked-title {
  color: #ff8eb4;
}

.stats-view.dark .top-liked-up {
  color: #a0a0a0;
}

.stats-view.dark .top-liked-views {
  color: #888;
}

/* Dark mode styles */
.stats-view.dark .overview-item {
  background: #1e1e2f;
}

.stats-view.dark .overview-value {
  color: #e8e8e8;
}

.stats-view.dark .overview-item:hover .overview-value {
  color: #ff8eb4;
}

.stats-view.dark .overview-label {
  color: #a0a0a0;
}

.stats-view.dark .overview-item:hover .overview-label {
  color: #c0c0c0;
}

.stats-view.dark .sub-stat {
  background: #252542;
}

.stats-view.dark .sub-stat:hover {
  background: #2a2a4a;
}

.stats-view.dark .sub-stat-value {
  color: #e8e8e8;
}

.stats-view.dark .sub-stat:hover .sub-stat-value {
  color: #ff8eb4;
}

.stats-view.dark .sub-stat-label {
  color: #a0a0a0;
}

.stats-view.dark .sub-stat:hover .sub-stat-label {
  color: #c0c0c0;
}

.stats-view.dark .sub-stat-icon {
  background: rgba(255, 142, 180, 0.1);
}

.stats-view.dark .sub-stat:hover .sub-stat-icon {
  background: rgba(255, 142, 180, 0.2);
}

.stats-view.dark .top-item:hover {
  background: rgba(255, 142, 180, 0.1);
}

.stats-view.dark .video-title {
  color: #e8e8e8;
}

.stats-view.dark .top-item:hover .video-title {
  color: #ff8eb4;
}

@media (max-width: 768px) {
  .overview-item {
    flex-direction: column;
    text-align: center;
    padding: 16px;
  }
  
  .overview-arrow {
    display: none;
  }
  
  .sub-stat {
    padding: 16px;
  }
  
  .top-item:hover {
    transform: none;
  }
}

/* 详情弹窗样式 */
.detail-content {
  max-height: 70vh;
  overflow-y: auto;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  background: #f8f9fa;
  cursor: pointer;
  transition: all 0.3s ease;
}

.detail-item:hover {
  background: #f0f0f0;
  transform: translateX(4px);
}

.detail-rank {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 13px;
  background: #e0e0e0;
  color: #666;
  flex-shrink: 0;
}

.detail-item:nth-child(1) .detail-rank {
  background: linear-gradient(135deg, #ffd700, #ffaa00);
  color: #fff;
}

.detail-item:nth-child(2) .detail-rank {
  background: linear-gradient(135deg, #c0c0c0, #a0a0a0);
  color: #fff;
}

.detail-item:nth-child(3) .detail-rank {
  background: linear-gradient(135deg, #cd7f32, #b87333);
  color: #fff;
}

.detail-cover {
  width: 100px;
  height: 56px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.detail-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.3s ease;
}

.detail-item:hover .detail-img {
  transform: scale(1.05);
}

.detail-info {
  flex: 1;
  min-width: 0;
}

.detail-title {
  font-size: 14px;
  font-weight: 600;
  line-height: 1.4;
  margin-bottom: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  color: #333;
}

.detail-item:hover .detail-title {
  color: #fb7299;
}

.detail-up {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.detail-stat {
  font-size: 12px;
}

@media (max-width: 768px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
  
  .detail-cover {
    width: 80px;
    height: 45px;
  }
}

/* Dark mode for detail modal */
.stats-view.dark .detail-item {
  background: #252542;
}

.stats-view.dark .detail-item:hover {
  background: #2a2a4a;
}

.stats-view.dark .detail-title {
  color: #e8e8e8;
}

.stats-view.dark .detail-item:hover .detail-title {
  color: #ff8eb4;
}

.stats-view.dark .detail-up {
  color: #a0a0a0;
}

.stats-view.dark .detail-rank {
  background: #333;
  color: #ccc;
}
</style>
