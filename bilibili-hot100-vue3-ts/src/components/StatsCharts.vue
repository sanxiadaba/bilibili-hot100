<template>
  <div class="stats-charts" :class="{ dark: themeStore.isDark }">
    <n-grid :cols="4" :x-gap="16" :y-gap="16" responsive="screen">
      <!-- 总播放量 -->
      <n-gi>
        <n-card class="stat-card">
          <div class="stat-value" :style="{ color: '#fb7299' }">
            {{ formatNumber(stats.totalViews) }}
          </div>
          <div class="stat-label">总播放量</div>
        </n-card>
      </n-gi>

      <!-- 总点赞 -->
      <n-gi>
        <n-card class="stat-card">
          <div class="stat-value" :style="{ color: '#ff8eb4' }">
            {{ formatNumber(stats.totalLikes) }}
          </div>
          <div class="stat-label">总点赞</div>
        </n-card>
      </n-gi>

      <!-- 总投币 -->
      <n-gi>
        <n-card class="stat-card">
          <div class="stat-value" :style="{ color: '#ffd700' }">
            {{ formatNumber(stats.totalCoins) }}
          </div>
          <div class="stat-label">总投币</div>
        </n-card>
      </n-gi>

      <!-- 总收藏 -->
      <n-gi>
        <n-card class="stat-card">
          <div class="stat-value" :style="{ color: '#3a7bd5' }">
            {{ formatNumber(stats.totalFavorites) }}
          </div>
          <div class="stat-label">总收藏</div>
        </n-card>
      </n-gi>
    </n-grid>

    <n-grid :cols="2" :x-gap="16" :y-gap="16" style="margin-top: 16px;" responsive="screen">
      <!-- 分类分布饼图 -->
      <n-gi>
        <n-card title="视频分类分布" class="chart-card">
          <div ref="categoryChartRef" class="chart-container"></div>
        </n-card>
      </n-gi>

      <!-- 分类播放量柱状图 -->
      <n-gi>
        <n-card title="分类播放量对比" class="chart-card">
          <div ref="viewsChartRef" class="chart-container"></div>
        </n-card>
      </n-gi>

      <!-- 播放量TOP10 -->
      <n-gi :span="2">
        <n-card title="播放量 TOP 10" class="chart-card">
          <div ref="topVideosChartRef" class="chart-container" style="height: 400px;"></div>
        </n-card>
      </n-gi>
    </n-grid>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { NCard, NGrid, NGi } from 'naive-ui'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { graphic, init, use, type ECharts } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { useThemeStore } from '@/stores/theme'
import { formatNumber } from '@/utils/format'
import type { StatsData } from '@/types'

const props = defineProps<{
  stats: StatsData
}>()

use([BarChart, PieChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const themeStore = useThemeStore()

const categoryChartRef = ref<HTMLDivElement | null>(null)
const viewsChartRef = ref<HTMLDivElement | null>(null)
const topVideosChartRef = ref<HTMLDivElement | null>(null)

let categoryChart: ECharts | null = null
let viewsChart: ECharts | null = null
let topVideosChart: ECharts | null = null

const initCharts = () => {
  if (categoryChartRef.value) {
    categoryChart = init(categoryChartRef.value)
  }
  if (viewsChartRef.value) {
    viewsChart = init(viewsChartRef.value)
  }
  if (topVideosChartRef.value) {
    topVideosChart = init(topVideosChartRef.value)
  }
  updateCharts()
}

const updateCharts = () => {
  const isDark = themeStore.isDark
  const textColor = isDark ? '#e0e0e0' : '#333'
  const axisColor = isDark ? '#555' : '#ccc'

  // 分类分布饼图
  if (categoryChart) {
    const categoryData = Object.entries(props.stats.categoryStats)
      .map(([name, stat]) => ({ name, value: stat.count }))
      .sort((a, b) => b.value - a.value)

    categoryChart.setOption({
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
        textStyle: { color: textColor }
      },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: isDark ? '#1a1a2e' : '#fff',
          borderWidth: 2
        },
        label: {
          show: false
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          }
        },
        data: categoryData
      }]
    })
  }

  // 分类播放量柱状图
  if (viewsChart) {
    const sortedCategories = Object.entries(props.stats.categoryStats)
      .sort((a, b) => b[1].views - a[1].views)
      .slice(0, 8)

    viewsChart.setOption({
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: sortedCategories.map(([name]) => name),
        axisLabel: { color: textColor, rotate: 30 },
        axisLine: { lineStyle: { color: axisColor } }
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          color: textColor,
          formatter: (value: number) => formatNumber(value)
        },
        axisLine: { lineStyle: { color: axisColor } },
        splitLine: { lineStyle: { color: isDark ? '#333' : '#eee' } }
      },
      series: [{
        type: 'bar',
        data: sortedCategories.map(([, stat]) => stat.views),
        itemStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#fb7299' },
            { offset: 1, color: '#ff8eb4' }
          ]),
          borderRadius: [6, 6, 0, 0]
        }
      }]
    })
  }

  // 播放量TOP10横向柱状图
  if (topVideosChart) {
    const top10 = props.stats.topVideos.slice(0, 10).reverse()

    topVideosChart.setOption({
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: any) => {
          const data = params[0]
          return `${data.name}<br/>播放量: ${formatNumber(data.value)}`
        }
      },
      grid: {
        left: '3%',
        right: '8%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'value',
        axisLabel: {
          color: textColor,
          formatter: (value: number) => formatNumber(value)
        },
        axisLine: { lineStyle: { color: axisColor } },
        splitLine: { lineStyle: { color: isDark ? '#333' : '#eee' } }
      },
      yAxis: {
        type: 'category',
        data: top10.map(v => v.title.slice(0, 20) + (v.title.length > 20 ? '...' : '')),
        axisLabel: { color: textColor },
        axisLine: { lineStyle: { color: axisColor } }
      },
      series: [{
        type: 'bar',
        data: top10.map(v => v.stat?.view || 0),
        itemStyle: {
          color: new graphic.LinearGradient(1, 0, 0, 0, [
            { offset: 0, color: '#3a7bd5' },
            { offset: 1, color: '#00d2ff' }
          ]),
          borderRadius: [0, 6, 6, 0]
        },
        label: {
          show: true,
          position: 'right',
          formatter: (params: any) => formatNumber(params.value),
          color: textColor
        }
      }]
    })
  }
}

const handleResize = () => {
  categoryChart?.resize()
  viewsChart?.resize()
  topVideosChart?.resize()
}

onMounted(() => {
  nextTick(() => {
    initCharts()
    window.addEventListener('resize', handleResize)
  })
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  categoryChart?.dispose()
  viewsChart?.dispose()
  topVideosChart?.dispose()
})

watch(() => props.stats, () => {
  updateCharts()
}, { deep: true })

watch(() => themeStore.isDark, () => {
  updateCharts()
})
</script>

<style scoped>
.stats-charts {
  padding: 16px 0;
}

.stat-card {
  text-align: center;
}

.stat-value {
  font-size: 1.8rem;
  font-weight: 700;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 0.9rem;
  color: #888;
}

.chart-card {
  min-height: 350px;
}

.chart-container {
  height: 300px;
  width: 100%;
}

.stats-charts.dark .stat-label {
  color: #a0a0a0;
}
</style>
