<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    title="后台日志"
    :style="{ width: '900px', maxWidth: '95vw' }"
    :mask-closable="false"
  >
    <template #header-extra>
      <n-space>
        <n-tag :type="connectionStatus.type" size="small">
          {{ connectionStatus.text }}
        </n-tag>
        <n-button size="small" @click="clearLogs" :disabled="logs.length === 0">
          清空日志
        </n-button>
        <n-button size="small" @click="close">关闭</n-button>
      </n-space>
    </template>

    <div ref="logContainer" class="log-container" :class="{ dark: themeStore.isDark }">
      <div v-if="logs.length === 0" class="empty-logs">
        <n-empty description="暂无日志" size="small" />
      </div>
      <div
        v-for="(log, index) in logs"
        :key="index"
        class="log-entry"
        :class="`level-${log.level.toLowerCase()}`"
      >
        <span class="log-time">{{ log.time }}</span>
        <span class="log-level">{{ log.level }}</span>
        <span class="log-message">{{ log.message }}</span>
      </div>
    </div>

    <template #footer>
      <n-space justify="space-between" align="center" style="width: 100%">
        <n-text depth="3" style="font-size: 12px;">
          共 {{ logs.length }} 条日志
        </n-text>
        <n-space>
          <n-checkbox v-model:checked="autoScroll" size="small">
            自动滚动
          </n-checkbox>
          <n-button size="small" type="primary" @click="reconnect" :loading="isConnecting">
            重新连接
          </n-button>
        </n-space>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'
import {
  NModal,
  NCard,
  NSpace,
  NButton,
  NTag,
  NEmpty,
  NText,
  NCheckbox
} from 'naive-ui'
import { useThemeStore } from '@/stores/theme'
import type { LogEntry } from '@/types'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void
}>()

const themeStore = useThemeStore()
const visible = computed({
  get: () => props.show,
  set: (val) => emit('update:show', val)
})

const logs = ref<LogEntry[]>([])
const logContainer = ref<HTMLDivElement | null>(null)
const autoScroll = ref(true)
const isConnecting = ref(false)
const connectionState = ref<'connected' | 'disconnected' | 'connecting'>('disconnected')

let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

const connectionStatus = computed(() => {
  switch (connectionState.value) {
    case 'connected':
      return { type: 'success' as const, text: '已连接' }
    case 'connecting':
      return { type: 'warning' as const, text: '连接中...' }
    default:
      return { type: 'error' as const, text: '未连接' }
  }
})

const connectWebSocket = () => {
  if (ws?.readyState === WebSocket.OPEN) return

  connectionState.value = 'connecting'
  isConnecting.value = true

  const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/logs/ws'

  try {
    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      connectionState.value = 'connected'
      isConnecting.value = false
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'log' && data.data) {
          logs.value.push(data.data)
          if (logs.value.length > 500) {
            logs.value = logs.value.slice(-500)
          }
          if (autoScroll.value) {
            scrollToBottom()
          }
        } else if (data.type === 'cleared') {
          logs.value = []
        }
      } catch (err) {
        console.error('解析日志消息失败:', err)
      }
    }

    ws.onclose = () => {
      connectionState.value = 'disconnected'
      isConnecting.value = false
      // 自动重连
      if (visible.value) {
        reconnectTimer = setTimeout(() => {
          connectWebSocket()
        }, 3000)
      }
    }

    ws.onerror = () => {
      connectionState.value = 'disconnected'
      isConnecting.value = false
    }
  } catch (err) {
    connectionState.value = 'disconnected'
    isConnecting.value = false
  }
}

const disconnectWebSocket = () => {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (ws) {
    ws.close()
    ws = null
  }
  connectionState.value = 'disconnected'
}

const scrollToBottom = () => {
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

const clearLogs = () => {
  logs.value = []
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: 'clear' }))
  }
}

const close = () => {
  visible.value = false
}

const reconnect = () => {
  disconnectWebSocket()
  logs.value = []
  setTimeout(() => connectWebSocket(), 100)
}

watch(visible, (val) => {
  if (val) {
    logs.value = []
    connectWebSocket()
  } else {
    disconnectWebSocket()
  }
})

onUnmounted(() => {
  disconnectWebSocket()
})
</script>

<style scoped>
.log-container {
  height: 500px;
  overflow-y: auto;
  background: #f8f9fa;
  border-radius: 8px;
  padding: 12px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.log-container.dark {
  background: #1a1a2e;
}

.empty-logs {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.log-entry {
  display: flex;
  gap: 12px;
  padding: 4px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.log-container.dark .log-entry {
  border-bottom-color: rgba(255, 255, 255, 0.05);
}

.log-time {
  color: #888;
  flex-shrink: 0;
  min-width: 80px;
}

.log-level {
  flex-shrink: 0;
  min-width: 60px;
  font-weight: 600;
  text-align: center;
  padding: 0 6px;
  border-radius: 4px;
  font-size: 11px;
}

.level-info .log-level {
  background: #e3f2fd;
  color: #1976d2;
}

.level-success .log-level {
  background: #e8f5e9;
  color: #388e3c;
}

.level-warning .log-level {
  background: #fff3e0;
  color: #f57c00;
}

.level-error .log-level {
  background: #ffebee;
  color: #d32f2f;
}

.level-debug .log-level {
  background: #f3e5f5;
  color: #7b1fa2;
}

.log-container.dark .level-info .log-level {
  background: rgba(25, 118, 210, 0.2);
  color: #64b5f6;
}

.log-container.dark .level-success .log-level {
  background: rgba(56, 142, 60, 0.2);
  color: #81c784;
}

.log-container.dark .level-warning .log-level {
  background: rgba(245, 124, 0, 0.2);
  color: #ffb74d;
}

.log-container.dark .level-error .log-level {
  background: rgba(211, 47, 47, 0.2);
  color: #e57373;
}

.log-container.dark .level-debug .log-level {
  background: rgba(123, 31, 162, 0.2);
  color: #ba68c8;
}

.log-message {
  flex: 1;
  word-break: break-all;
  color: #333;
}

.log-container.dark .log-message {
  color: #e0e0e0;
}

.log-container.dark .log-time {
  color: #888;
}
</style>
