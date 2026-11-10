<script setup lang="ts">
import { computed, ref } from 'vue'
import { formatNumber } from '@/lib/format'
import { METRICS, statOf, topBy } from '@/lib/videos'
import { useVideos } from '@/composables/useVideos'
import type { StatKey } from '@/lib/types'

const { state, summary } = useVideos()
const metric = ref<StatKey>('view')

const topVideos = computed(() => topBy(state.videos, metric.value, 10))
const maxTop = computed(() =>
  topVideos.value.length ? statOf(topVideos.value[0], metric.value) : 1
)
const topCategories = computed(() => summary.value.categories.slice(0, 12))
const restCategories = computed(() => summary.value.categories.slice(12))
const restCount = computed(() =>
  restCategories.value.reduce((total, category) => total + category.count, 0)
)
const maxCategory = computed(() => summary.value.categories[0]?.count ?? 1)
const metricLabel = computed(
  () => METRICS.find(item => item.value === metric.value)?.label ?? '播放'
)

function percent(value: number, max: number): string {
  if (!max) return '2%'
  return `${Math.max(2, Math.round((value / max) * 100))}%`
}

function categoryPercent(count: number): number {
  return summary.value.total ? Math.round((count / summary.value.total) * 100) : 0
}

function videoUrl(bvid: string): string {
  return `https://www.bilibili.com/video/${bvid}`
}
</script>

<template>
  <section class="stats-view" aria-label="数据分析">
    <div class="cards">
      <div class="card">
        <span class="label">总播放</span>
        <strong>{{ formatNumber(summary.views) }}</strong>
      </div>
      <div class="card">
        <span class="label">总点赞</span>
        <strong>{{ formatNumber(summary.likes) }}</strong>
      </div>
      <div class="card">
        <span class="label">总收藏</span>
        <strong>{{ formatNumber(summary.favorites) }}</strong>
      </div>
      <div class="card">
        <span class="label">总投币</span>
        <strong>{{ formatNumber(summary.coins) }}</strong>
      </div>
    </div>

    <div class="minis">
      <div><span>弹幕</span><b>{{ formatNumber(summary.danmaku) }}</b></div>
      <div><span>评论</span><b>{{ formatNumber(summary.reply) }}</b></div>
      <div><span>分享</span><b>{{ formatNumber(summary.share) }}</b></div>
      <div><span>平均播放</span><b>{{ formatNumber(summary.averageViews) }}</b></div>
    </div>

    <div class="panels">
      <section class="block">
        <h2>分类分布</h2>
        <div class="cat-list">
          <div v-for="cat in topCategories" :key="cat.name" class="cat-row">
            <span class="cat-name" :title="cat.name">{{ cat.name }}</span>
            <span class="meter"><i :style="{ width: percent(cat.count, maxCategory) }"></i></span>
            <span class="cat-count">{{ cat.count }}</span>
            <span class="cat-pct">{{ categoryPercent(cat.count) }}%</span>
          </div>
          <div v-if="restCategories.length" class="cat-rest">
            其余 {{ restCategories.length }} 个分类共 {{ restCount }} 条（{{ categoryPercent(restCount) }}%）
          </div>
          <p v-if="!summary.categories.length" class="empty">暂无数据</p>
        </div>
      </section>

      <section class="block">
        <div class="block-head">
          <h2>{{ metricLabel }} TOP 10</h2>
          <div class="tabs" role="tablist" aria-label="排行指标">
            <button
              v-for="item in METRICS"
              :key="item.value"
              type="button"
              role="tab"
              :aria-selected="metric === item.value"
              :class="{ active: metric === item.value }"
              @click="metric = item.value"
            >
              {{ item.label }}
            </button>
          </div>
        </div>

        <ol class="top-list">
          <li v-for="(video, index) in topVideos" :key="video.bvid">
            <span :class="['top-rank', { lead: index < 3 }]">{{ index + 1 }}</span>
            <span class="top-main">
              <span class="top-line">
                <a :href="videoUrl(video.bvid)" target="_blank" rel="noopener noreferrer">
                  {{ video.title }}
                </a>
                <b>{{ formatNumber(statOf(video, metric)) }}</b>
              </span>
              <span class="meter"><i :style="{ width: percent(statOf(video, metric), maxTop) }"></i></span>
              <span class="top-up">{{ video.owner.name }} · {{ video.tname }}</span>
            </span>
          </li>
          <p v-if="!topVideos.length" class="empty">暂无数据</p>
        </ol>
      </section>
    </div>
  </section>
</template>

<style scoped>
.stats-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 16px;
}

.cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card .label {
  color: var(--muted);
  font-size: 12px;
}

.card strong {
  font-size: 26px;
  font-weight: 700;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

.minis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px 18px;
}

.minis div {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.minis span {
  color: var(--muted);
  font-size: 12px;
}

.minis b {
  font-size: 16px;
  font-variant-numeric: tabular-nums;
}

.panels {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  align-items: start;
}

.block {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 16px 18px 18px;
}

.block h2 {
  margin: 0 0 12px;
  font-size: 15px;
  font-weight: 600;
}

.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.block-head h2 {
  margin: 0;
}

.cat-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cat-row {
  display: grid;
  grid-template-columns: 104px minmax(0, 1fr) 40px 44px;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}

.cat-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--muted);
}

.cat-count,
.cat-pct {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.cat-pct {
  color: var(--muted);
}

.cat-rest {
  margin-top: 2px;
  padding-top: 8px;
  border-top: 1px dashed var(--line);
  color: var(--muted);
  font-size: 12px;
}

.meter {
  display: block;
  height: 8px;
  border-radius: 4px;
  background: var(--panel-2);
  overflow: hidden;
}

.meter i {
  display: block;
  height: 100%;
  border-radius: 4px;
  background: var(--accent);
  opacity: 0.75;
}

.tabs {
  display: flex;
  gap: 4px;
  background: var(--panel-2);
  border-radius: 8px;
  padding: 3px;
}

.tabs button {
  border: 0;
  background: transparent;
  color: var(--muted);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}

.tabs button.active {
  background: var(--panel);
  color: var(--accent);
  box-shadow: var(--shadow);
}

.top-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.top-list li {
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr);
  gap: 10px;
}

.top-rank {
  font-size: 14px;
  font-weight: 700;
  text-align: center;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.top-rank.lead {
  color: var(--accent);
}

.top-main {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.top-line {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
}

.top-line a {
  color: inherit;
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.top-line a:hover {
  color: var(--accent);
}

.top-line b {
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}

.top-up {
  font-size: 12px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty {
  margin: 8px 0;
  color: var(--muted);
  font-size: 13px;
}

@media (max-width: 1000px) {
  .panels {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 760px) {
  .cards,
  .minis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .card strong {
    font-size: 22px;
  }

  .cat-row {
    grid-template-columns: 72px minmax(0, 1fr) 32px 38px;
    font-size: 12px;
  }
}
</style>
