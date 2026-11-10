<script setup lang="ts">
import { useVideos } from '@/composables/useVideos'
import VideoRow from './VideoRow.vue'

const { state, visibleVideos } = useVideos()
</script>

<template>
  <section class="video-list" aria-label="视频列表">
    <p v-if="!state.videos.length" class="empty">还没有数据，点右上角“刷新”抓一次。</p>

    <template v-else>
      <ol class="rows">
        <li v-for="video in visibleVideos" :key="video.bvid">
          <VideoRow :video="video" />
        </li>
      </ol>
      <p v-if="visibleVideos.length !== state.videos.length" class="footer">
        筛选出 {{ visibleVideos.length }} 条，共 {{ state.videos.length }} 条
      </p>
    </template>
  </section>
</template>

<style scoped>
.rows {
  list-style: none;
  margin: 0;
  padding: 0;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
}

.empty {
  padding: 64px 0;
  text-align: center;
  color: var(--muted);
}

.footer {
  padding: 14px 4px 0;
  color: var(--muted);
  font-size: 12px;
}
</style>
