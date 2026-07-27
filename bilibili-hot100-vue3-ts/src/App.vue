<template>
  <n-config-provider :theme="themeStore.isDark ? darkTheme : null" :theme-overrides="themeStore.theme">
    <n-message-provider>
      <n-dialog-provider>
        <div class="app" :class="{ dark: themeStore.isDark }">
          <AppHeader
            :show-stats-view="showStatsView"
            @refresh="handleRefresh"
            @show-logs="showLogViewer = true"
            @toggle-stats="toggleStatsView"
          />

          <main class="main-content">
            <n-alert
              v-if="videoStore.error"
              type="error"
              closable
              class="error-alert"
              @close="videoStore.clearError"
            >
              {{ videoStore.error }}
            </n-alert>
            <n-spin :show="videoStore.loading && !videoStore.videos.length" size="large">
              <template #description>
                加载中...
              </template>

              <StatsView
                v-if="showStatsView && videoStore.stats"
                :stats="videoStore.stats"
              />

              <VideoList
                v-else
                :videos="videoStore.filteredVideos"
                :loading="videoStore.loading"
                @refresh="handleRefresh"
              />
            </n-spin>
          </main>

          <LogViewer v-model:show="showLogViewer" />

          <n-back-top :right="24" :bottom="24" />
        </div>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { defineAsyncComponent, onMounted, ref } from 'vue'
import {
  NConfigProvider,
  NMessageProvider,
  NDialogProvider,
  NSpin,
  NBackTop,
  NAlert,
  darkTheme
} from 'naive-ui'
import { useThemeStore } from '@/stores/theme'
import { useVideoStore } from '@/stores/videos'
import AppHeader from '@/components/AppHeader.vue'
import VideoList from '@/components/VideoList.vue'

const StatsView = defineAsyncComponent(() => import('@/components/StatsView.vue'))
const LogViewer = defineAsyncComponent(() => import('@/components/LogViewer.vue'))

const themeStore = useThemeStore()
const videoStore = useVideoStore()

const showStatsView = ref(false)
const showLogViewer = ref(false)

const handleRefresh = async () => {
  await videoStore.refreshVideos()
}

const toggleStatsView = () => {
  showStatsView.value = !showStatsView.value
}

onMounted(() => {
  videoStore.loadVideos()
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app {
  min-height: 100vh;
  background: #f5f5f5;
  transition: background-color 0.3s;
}

.app.dark {
  background: #0f0f1e;
}

.main-content {
  max-width: 1800px;
  margin: 0 auto;
  padding: 16px 24px;
}

.error-alert {
  margin-bottom: 16px;
}

@media (max-width: 768px) {
  .main-content {
    padding: 12px 16px;
  }
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #c0c0c0;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a0a0a0;
}

.app.dark ::-webkit-scrollbar-thumb {
  background: #444;
}

.app.dark ::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>
