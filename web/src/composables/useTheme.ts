import { ref } from 'vue'

const STORAGE_KEY = 'bilibili-theme'
const dark = ref(false)

function apply(): void {
  document.documentElement.dataset.theme = dark.value ? 'dark' : 'light'
}

function readStoredTheme(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    // 隐私模式/策略禁用存储时按系统主题走，别让整个应用挂载失败。
    return null
  }
}

export function initTheme(): void {
  const stored = readStoredTheme()
  dark.value = stored
    ? stored === 'dark'
    : window.matchMedia('(prefers-color-scheme: dark)').matches
  apply()
}

export function toggleTheme(): void {
  dark.value = !dark.value
  apply()
  try {
    localStorage.setItem(STORAGE_KEY, dark.value ? 'dark' : 'light')
  } catch {
    // 存不下就只在本页生效，切换本身不能失败。
  }
}

export function useTheme() {
  return { dark, toggleTheme }
}
