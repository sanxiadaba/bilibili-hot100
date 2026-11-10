import { ref } from 'vue'

const STORAGE_KEY = 'bilibili-theme'
const dark = ref(false)

function apply(): void {
  document.documentElement.dataset.theme = dark.value ? 'dark' : 'light'
}

export function initTheme(): void {
  const stored = localStorage.getItem(STORAGE_KEY)
  dark.value = stored
    ? stored === 'dark'
    : window.matchMedia('(prefers-color-scheme: dark)').matches
  apply()
}

export function toggleTheme(): void {
  dark.value = !dark.value
  localStorage.setItem(STORAGE_KEY, dark.value ? 'dark' : 'light')
  apply()
}

export function useTheme() {
  return { dark, toggleTheme }
}
