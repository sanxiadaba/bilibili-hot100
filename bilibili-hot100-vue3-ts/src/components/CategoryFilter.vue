<template>
  <div class="category-filter">
    <div class="filter-scroll">
      <n-space align="center" wrap>
        <n-tag
          :type="videoStore.selectedCategory === 'all' ? 'primary' : 'default'"
          :bordered="videoStore.selectedCategory !== 'all'"
          @click="selectCategory('all')"
          class="filter-tag"
        >
          <template #icon>
            <n-icon :component="GridOutline" />
          </template>
          全部 ({{ videoStore.videos.length }})
        </n-tag>
        
        <n-tag
          v-for="cat in filteredCategories"
          :key="cat.name"
          :type="videoStore.selectedCategory === cat.name ? 'primary' : 'default'"
          :bordered="videoStore.selectedCategory !== cat.name"
          @click="selectCategory(cat.name)"
          class="filter-tag"
        >
          {{ cat.name }} ({{ cat.count }})
        </n-tag>
        
        <n-tag
          v-if="videoStore.categories.length > maxCategories"
          type="default"
          bordered
          @click="showAllCategories = !showAllCategories"
          class="filter-tag more-tag"
        >
          {{ showAllCategories ? '收起' : `更多 (${videoStore.categories.length - maxCategories})` }}
        </n-tag>
      </n-space>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { NSpace, NTag, NIcon } from 'naive-ui'
import { GridOutline, ChevronDownOutline, ChevronUpOutline } from '@vicons/ionicons5'
import { useVideoStore } from '@/stores/videos'

const videoStore = useVideoStore()
const showAllCategories = ref(false)
const maxCategories = 6

const filteredCategories = computed(() => {
  if (showAllCategories.value) {
    return videoStore.categories
  }
  return videoStore.categories.slice(0, maxCategories)
})

const selectCategory = (cat: string) => {
  videoStore.setCategory(cat)
}
</script>

<style scoped>
.category-filter {
  padding: 12px 0;
}

.filter-scroll {
  overflow-x: auto;
  padding-bottom: 8px;
  scrollbar-width: thin;
  scrollbar-color: #c0c0c0 transparent;
}

.filter-scroll::-webkit-scrollbar {
  height: 4px;
}

.filter-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.filter-scroll::-webkit-scrollbar-thumb {
  background: #c0c0c0;
  border-radius: 2px;
}

.filter-scroll::-webkit-scrollbar-thumb:hover {
  background: #a0a0a0;
}

.filter-tag {
  cursor: pointer;
  margin-right: 8px;
  margin-bottom: 8px;
  transition: all 0.3s ease;
  font-size: 14px;
  padding: 6px 12px;
  border-radius: 16px;
}

.filter-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.more-tag {
  font-weight: 500;
  color: #666;
}

.more-tag:hover {
  color: #fb7299;
  border-color: #fb7299;
}
</style>
