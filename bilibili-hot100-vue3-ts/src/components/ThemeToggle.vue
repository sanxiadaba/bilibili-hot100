<template>
  <n-button
    circle
    quaternary
    class="theme-toggle"
    @click="themeStore.toggleTheme"
    :title="themeStore.isDark ? '切换到浅色模式' : '切换到深色模式'"
    :aria-label="themeStore.isDark ? '切换到浅色模式' : '切换到深色模式'"
  >
    <template #icon>
      <n-icon :size="20">
        <SunnyOutline v-if="themeStore.isDark" />
        <MoonOutline v-else />
      </n-icon>
    </template>
  </n-button>
</template>

<script setup lang="ts">
import { NButton, NIcon } from 'naive-ui'
import { SunnyOutline, MoonOutline } from '@vicons/ionicons5'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()
</script>
