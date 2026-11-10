function trim(value: number): string {
  return value.toFixed(1).replace(/\.0$/, '')
}

export function formatNumber(value: number | null | undefined): string {
  if (!value || value <= 0) return '0'
  if (value >= 100_000_000) return `${trim(value / 100_000_000)}亿`
  if (value >= 10_000) return `${trim(value / 10_000)}万`
  return String(value)
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || seconds < 0) return '0:00'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const rest = seconds % 60
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
  }
  return `${minutes}:${String(rest).padStart(2, '0')}`
}

export function formatTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}
