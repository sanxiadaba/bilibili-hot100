export const formatNumber = (num: number | undefined): string => {
  if (num === undefined || num === null) return '0'
  if (num >= 100000000) {
    return (num / 100000000).toFixed(1) + '亿'
  } else if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toString()
}

export const formatDuration = (seconds: number | undefined): string => {
  if (!seconds && seconds !== 0) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  const h = Math.floor(m / 60)
  if (h > 0) {
    return `${h}:${(m % 60).toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }
  return `${m}:${s.toString().padStart(2, '0')}`
}

export const getRankClass = (rank: number): string => {
  if (rank <= 3) return 'top3'
  if (rank <= 10) return 'top10'
  return ''
}
