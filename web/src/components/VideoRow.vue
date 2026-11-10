<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { formatDuration, formatNumber } from '@/lib/format'
import { FALLBACK_AVATAR, FALLBACK_COVER } from '@/lib/placeholder'
import type { VideoItem } from '@/lib/types'

const props = defineProps<{ video: VideoItem }>()

const coverFailed = ref(false)
const avatarFailed = ref(false)

const cover = computed(() => {
  if (coverFailed.value) return FALLBACK_COVER
  return props.video.pic || FALLBACK_COVER
})

const avatar = computed(() => {
  if (avatarFailed.value) return FALLBACK_AVATAR
  return props.video.owner.face || FALLBACK_AVATAR
})

const rankClass = computed(() => (props.video.rank <= 3 ? 'top' : ''))

const url = computed(() => `https://www.bilibili.com/video/${props.video.bvid}`)

function onCoverError(): void {
  coverFailed.value = true
}

function onAvatarError(): void {
  avatarFailed.value = true
}

// 刷新后可能从远程图换成刚下载好的本地图，给一次重新加载的机会。
watch(
  () => props.video.pic,
  () => {
    coverFailed.value = false
  }
)
watch(
  () => props.video.owner.face,
  () => {
    avatarFailed.value = false
  }
)
</script>

<template>
  <a class="row" :href="url" target="_blank" rel="noopener noreferrer">
    <span :class="['rank', rankClass]">{{ video.rank }}</span>

    <span class="cover">
      <img
        :src="cover"
        alt=""
        width="160"
        height="90"
        loading="lazy"
        decoding="async"
        @error="onCoverError"
      />
      <span class="duration">{{ formatDuration(video.duration) }}</span>
      <span v-if="video.rcmd_reason?.content" class="rcmd">{{ video.rcmd_reason.content }}</span>
    </span>

    <span class="body">
      <span class="title">{{ video.title }}</span>
      <span class="sub">
        <img class="avatar" :src="avatar" alt="" width="20" height="20" loading="lazy" @error="onAvatarError" />
        <span class="up">{{ video.owner.name }}</span>
        <span class="dot">·</span>
        <span class="category">{{ video.tname }}</span>
      </span>
    </span>

    <span class="stats">
      <span><b>{{ formatNumber(video.stat.view) }}</b>播放</span>
      <span><b>{{ formatNumber(video.stat.like) }}</b>点赞</span>
      <span><b>{{ formatNumber(video.stat.coin) }}</b>投币</span>
      <span><b>{{ formatNumber(video.stat.danmaku) }}</b>弹幕</span>
    </span>
  </a>
</template>

<style scoped>
.row {
  display: grid;
  grid-template-columns: 28px 160px minmax(0, 1fr) 300px;
  align-items: center;
  gap: 14px;
  padding: 10px 16px;
  color: inherit;
  text-decoration: none;
  border-top: 1px solid var(--line);
}

li:first-child .row {
  border-top: 0;
}

.row:hover {
  background: var(--panel-2);
}

.rank {
  font-size: 15px;
  font-weight: 700;
  color: var(--muted);
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.rank.top {
  color: var(--accent);
}

.cover {
  position: relative;
  display: block;
  width: 160px;
  height: 90px;
  border-radius: 6px;
  overflow: hidden;
  background: var(--panel-2);
}

.cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.duration {
  position: absolute;
  right: 4px;
  bottom: 4px;
  padding: 1px 4px;
  border-radius: 3px;
  background: rgba(0, 0, 0, 0.68);
  color: #fff;
  font-size: 11px;
  line-height: 1.5;
}

.rcmd {
  position: absolute;
  left: 4px;
  top: 4px;
  padding: 1px 5px;
  border-radius: 3px;
  background: rgba(251, 114, 153, 0.9);
  color: #fff;
  font-size: 11px;
  line-height: 1.5;
}

.body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.title {
  font-size: 14px;
  font-weight: 600;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.row:hover .title {
  color: var(--accent);
}

.sub {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-size: 12px;
  color: var(--muted);
}

.avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.up {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dot {
  opacity: 0.6;
}

.category {
  flex-shrink: 0;
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 0 5px;
  font-size: 11px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  text-align: right;
  font-size: 12px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.stats b {
  display: block;
  color: var(--text);
  font-size: 13px;
  font-weight: 600;
}

@media (max-width: 980px) {
  .row {
    grid-template-columns: 28px 160px minmax(0, 1fr);
  }

  .stats {
    display: none;
  }
}

@media (max-width: 620px) {
  .row {
    grid-template-columns: 24px 112px minmax(0, 1fr);
    gap: 10px;
    padding: 8px 10px;
  }

  .cover {
    width: 112px;
    height: 63px;
  }

  .title {
    font-size: 13px;
    -webkit-line-clamp: 3;
  }

  .category,
  .dot {
    display: none;
  }
}
</style>
