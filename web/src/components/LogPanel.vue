<script setup lang="ts">
import { onUnmounted, ref, watch, nextTick } from 'vue'
import { clearLogs, logsSocketUrl } from '@/lib/api'
import type { LogEntry } from '@/lib/types'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [value: boolean] }>()

const logs = ref<LogEntry[]>([])
const listRef = ref<HTMLDivElement | null>(null)
const autoScroll = ref(true)
const connection = ref<'offline' | 'connecting' | 'online'>('offline')

let socket: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

function close(): void {
  emit('update:open', false)
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') close()
}

function scrollToBottom(): void {
  nextTick(() => {
    const element = listRef.value
    if (element) element.scrollTop = element.scrollHeight
  })
}

function push(entry: LogEntry): void {
  logs.value.push(entry)
  if (logs.value.length > 500) logs.value.splice(0, logs.value.length - 500)
  if (autoScroll.value) scrollToBottom()
}

function disconnect(): void {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  const current = socket
  socket = null
  current?.close()
  connection.value = 'offline'
}

function connect(): void {
  disconnect()
  connection.value = 'connecting'
  const current = new WebSocket(logsSocketUrl())
  socket = current

  current.onopen = () => {
    if (socket === current) connection.value = 'online'
  }

  current.onmessage = event => {
    try {
      const message = JSON.parse(event.data) as { type?: string; data?: LogEntry }
      if (message.type === 'log' && message.data) push(message.data)
    } catch {
      // 忽略无法解析的帧
    }
  }

  current.onclose = () => {
    if (socket !== current) return
    socket = null
    connection.value = 'offline'
    if (props.open) reconnectTimer = setTimeout(connect, 2000)
  }

  current.onerror = () => {
    if (socket === current) connection.value = 'offline'
  }
}

async function clear(): Promise<void> {
  logs.value = []
  await clearLogs().catch(() => undefined)
}

watch(
  () => props.open,
  open => {
    if (open) {
      logs.value = []
      connection.value = 'connecting'
      document.addEventListener('keydown', onKeydown)
      connect()
    } else {
      document.removeEventListener('keydown', onKeydown)
      disconnect()
    }
  }
)

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  disconnect()
})
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="overlay" @click.self="close">
      <section class="panel" role="dialog" aria-modal="true" aria-label="后台日志">
        <header class="panel-head">
          <strong>后台日志</strong>
          <span :class="['status', connection]">
            {{ connection === 'online' ? '已连接' : connection === 'connecting' ? '连接中…' : '未连接' }}
          </span>
          <button class="btn" type="button" :disabled="!logs.length" @click="clear">清空</button>
          <button class="btn icon" type="button" aria-label="关闭日志" @click="close">×</button>
        </header>

        <div ref="listRef" class="log-list">
          <p v-if="!logs.length" class="empty">暂无日志</p>
          <div
            v-for="(entry, index) in logs"
            :key="index"
            :class="['log', `level-${entry.level.toLowerCase()}`]"
          >
            <span class="time">{{ entry.time }}</span>
            <span class="level">{{ entry.level }}</span>
            <span class="message">{{ entry.message }}</span>
          </div>
        </div>

        <footer class="panel-foot">
          <span>共 {{ logs.length }} 条，最多保留 500 条</span>
          <label>
            <input v-model="autoScroll" type="checkbox" />
            自动滚动
          </label>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(8, 10, 16, 0.5);
}

.panel {
  display: flex;
  flex-direction: column;
  width: min(920px, 100%);
  height: min(640px, 80vh);
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.28);
  overflow: hidden;
}

.panel-head,
.panel-foot {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
}

.panel-foot {
  border-bottom: 0;
  border-top: 1px solid var(--line);
  justify-content: space-between;
  color: var(--muted);
  font-size: 12px;
}

.panel-head strong {
  margin-right: auto;
  font-size: 14px;
}

.status {
  font-size: 12px;
  color: var(--muted);
}

.status.online {
  color: var(--accent);
}

.log-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 14px;
  font-family: Consolas, 'Cascadia Mono', Menlo, monospace;
  font-size: 12px;
  line-height: 1.7;
}

.empty {
  padding: 32px 0;
  text-align: center;
  color: var(--muted);
}

.log {
  display: grid;
  grid-template-columns: 84px 64px minmax(0, 1fr);
  gap: 8px;
  padding: 2px 0;
}

.time {
  color: var(--muted);
}

.level {
  font-weight: 600;
}

.message {
  word-break: break-word;
}

.level-success .level {
  color: #18a058;
}

.level-warning .level {
  color: #d98b00;
}

.level-error .level {
  color: #d03050;
}

.level-info .level {
  color: #3a7bd5;
}
</style>
