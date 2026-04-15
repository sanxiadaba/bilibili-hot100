import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { darkTheme, type GlobalTheme } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'

const lightThemeOverrides: GlobalThemeOverrides = {
  common: {
    bodyColor: '#f5f7fa',
    cardColor: '#ffffff',
    modalColor: '#ffffff',
    popoverColor: '#ffffff',
    tableColor: '#ffffff',
    textColorBase: '#1f2937',
    textColor1: '#1f2937',
    textColor2: '#4b5563',
    textColor3: '#9ca3af',
    borderColor: '#e5e7eb',
    dividerColor: '#e5e7eb'
  }
}

const darkThemeOverrides: GlobalThemeOverrides = {
  common: {
    bodyColor: '#0d0d1a',
    cardColor: 'rgba(255,255,255,0.04)',
    modalColor: '#1a1a2e',
    popoverColor: '#1a1a2e',
    tableColor: 'rgba(255,255,255,0.04)',
    textColorBase: '#e0e0e0',
    textColor1: '#e8e8e8',
    textColor2: '#a0a0a0',
    textColor3: '#6b7280',
    borderColor: 'rgba(255,255,255,0.1)',
    dividerColor: 'rgba(255,255,255,0.1)'
  },
  Card: {
    color: 'rgba(255,255,255,0.04)',
    colorModal: '#1a1a2e',
    colorPopover: '#1a1a2e',
    borderColor: 'rgba(255,255,255,0.06)'
  }
}

export const useThemeStore = defineStore('theme', () => {
  const isDark = ref<boolean>(localStorage.getItem('bilibili-theme') === 'dark')

  const theme = computed<GlobalThemeOverrides>(() => ({
    common: {
      primaryColor: '#00d2ff',
      primaryColorHover: '#33dbff',
      primaryColorPressed: '#00a8cc',
      primaryColorSuppl: '#00d2ff',
      infoColor: '#3a7bd5',
      successColor: '#18a058',
      warningColor: '#f0a020',
      errorColor: '#d03050',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif',
      fontSize: '14px',
      borderRadius: '12px',
      lineHeight: '1.6'
    },
    ...(isDark.value ? darkThemeOverrides : lightThemeOverrides)
  }))

  const toggleTheme = (): void => {
    isDark.value = !isDark.value
    localStorage.setItem('bilibili-theme', isDark.value ? 'dark' : 'light')
  }

  const setTheme = (dark: boolean): void => {
    isDark.value = dark
    localStorage.setItem('bilibili-theme', dark ? 'dark' : 'light')
  }

  const naiveTheme = computed<GlobalTheme | null>(() => isDark.value ? darkTheme : null)

  watch(isDark, (val) => {
    document.documentElement.classList.toggle('dark', val)
  }, { immediate: true })

  return {
    isDark,
    theme,
    naiveTheme,
    toggleTheme,
    setTheme
  }
})
