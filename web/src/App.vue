<script setup lang="ts">
import { onMounted, ref } from 'vue'
import AppHeader from '@/components/AppHeader.vue'
import VideoList from '@/components/VideoList.vue'
import StatsView from '@/components/StatsView.vue'
import LogPanel from '@/components/LogPanel.vue'
import { useVideos } from '@/composables/useVideos'
import { initTheme } from '@/composables/useTheme'

const { state, load } = useVideos()
const view = ref<'list' | 'stats'>('list')
const showLogs = ref(false)

initTheme()
onMounted(() => {
  void load()
})
</script>

<template>
  <div class="app">
    <AppHeader v-model:view="view" @open-logs="showLogs = true" />

    <main class="main">
      <p v-if="state.error" class="error" role="alert">
        <span>{{ state.error }}</span>
        <button type="button" aria-label="关闭提示" @click="state.error = ''">×</button>
      </p>

      <p v-if="state.loading && !state.videos.length" class="placeholder">
        正在抓取第一屏数据…
      </p>
      <StatsView v-else-if="view === 'stats'" />
      <VideoList v-else />
    </main>

    <LogPanel v-model:open="showLogs" />
  </div>
</template>
