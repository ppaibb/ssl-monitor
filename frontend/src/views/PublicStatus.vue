<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { api, type PublicStatusItem } from '../api'
import { Message } from '@arco-design/web-vue'
import { IconMoonFill, IconSunFill, IconSafe, IconGithub } from '@arco-design/web-vue/es/icon'

const domains = ref<PublicStatusItem[]>([])
const loading = ref(true)
const lastUpdate = ref<Date>(new Date())
const isDark = ref(false)

// Auto refresh interval
let intervalId: ReturnType<typeof setInterval>

async function fetchData() {
  loading.value = true
  try {
    const r = await api.getPublicStatus()
    domains.value = r.data
    lastUpdate.value = new Date()
  } catch (e: any) {
    console.error('Failed to fetch public status:', e)
    Message.error('无法连接到监控服务器')
  } finally {
    loading.value = false
  }
}

function toggleDark() {
  isDark.value = !isDark.value
  if (isDark.value) {
    document.body.setAttribute('arco-theme', 'dark')
  } else {
    document.body.removeAttribute('arco-theme')
  }
}

function openGitHub() {
  window.open('https://github.com/ppaibb/ssl-monitor', '_blank')
}

onMounted(() => {
  // 默认为亮色，或者跟随系统
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    isDark.value = true
    document.body.setAttribute('arco-theme', 'dark')
  }
  
  fetchData()
  intervalId = setInterval(fetchData, 60000) // 60s
})

onUnmounted(() => {
  clearInterval(intervalId)
  document.body.removeAttribute('arco-theme')
})

function statusColor(row: PublicStatusItem): string {
  if (row.error) return '#86909c' // gray
  if (row.is_expired) return '#f53f3f' // red
  if (row.is_expiring_soon) return '#ff7d00' // orange
  if (row.days_left === null) return '#86909c' // gray
  return '#00b42a' // green
}

function statusText(row: PublicStatusItem): string {
  if (row.error) return '异常/错误'
  if (row.is_expired) return '已过期'
  if (row.days_left === null) return '未检测'
  return `${row.days_left} 天`
}

const columns = [
  { title: '当前状态', dataIndex: 'status', slotName: 'status', align: 'center', width: 100 },
  { title: '站点名称', dataIndex: 'name', slotName: 'name', width: 200 },
  { title: '监测地址 (脱敏)', dataIndex: 'masked_domain', slotName: 'domain' },
  { title: '端口', dataIndex: 'port', width: 100 },
  { title: '剩余天数', dataIndex: 'days_left', slotName: 'days' },
  { title: '最后监测时间', dataIndex: 'checked_at', slotName: 'time' },
] as const;

const selectedTag = ref<string | null>(null)
const daysFilter = ref<number | null>(null) // 7, 15, 30 或 null（全部）

const allTags = computed(() => {
  const set = new Set<string>()
  domains.value.forEach(d => {
    if (d.tags) d.tags.forEach(t => set.add(t))
  })
  return Array.from(set)
})

const filteredDomains = computed(() => {
  let list = domains.value
  // 按标签筛选
  if (selectedTag.value) {
    list = list.filter(d => d.tags && d.tags.includes(selectedTag.value!))
  }
  // 按到期天数筛选
  if (daysFilter.value !== null) {
    list = list.filter(d => d.days_left !== null && d.days_left <= daysFilter.value!)
  }
  return list
})

</script>

<template>
  <div class="public-layout">
    <!-- Header -->
    <header class="public-header">
      <div class="header-left">
        <icon-safe class="logo" />
        <span class="title">SSL 证书运行状态监测</span>
      </div>
      <div class="header-right">
        <a-button type="text" shape="circle" @click="openGitHub">
          <template #icon><icon-github /></template>
        </a-button>
        <a-button type="text" shape="circle" @click="toggleDark">
          <template #icon>
            <icon-moon-fill v-if="!isDark" />
            <icon-sun-fill v-else />
          </template>
        </a-button>
      </div>
    </header>

    <!-- Content -->
    <main class="public-content">
      <a-card class="status-card" :bordered="false">
        <template #title>
          <div class="card-title">
            <span>站点监控列表</span>
            <span class="refresh-text" v-if="!loading">最后刷新于 {{ lastUpdate.toLocaleTimeString() }}</span>
            <span class="refresh-text" v-else>正在刷新...</span>
          </div>
        </template>
        
        <!-- 筛选栏 -->
        <div class="tag-filter">
          <a-button 
            :type="!selectedTag ? 'primary' : 'secondary'" 
            size="small" 
            @click="selectedTag = null"
          >全部</a-button>
          <a-button
            v-for="tag in allTags"
            :key="tag"
            :type="selectedTag === tag ? 'primary' : 'secondary'"
            size="small"
            @click="selectedTag = selectedTag === tag ? null : tag"
          >{{ tag }}</a-button>

          <a-divider direction="vertical" v-if="allTags.length > 0" />

          <a-button
            :type="daysFilter === null ? 'primary' : 'secondary'"
            size="small"
            @click="daysFilter = null"
          >不限</a-button>
          <a-button
            :type="daysFilter === 7 ? 'primary' : 'secondary'"
            size="small"
            status="danger"
            @click="daysFilter = daysFilter === 7 ? null : 7"
          >≤ 7天</a-button>
          <a-button
            :type="daysFilter === 15 ? 'primary' : 'secondary'"
            size="small"
            status="warning"
            @click="daysFilter = daysFilter === 15 ? null : 15"
          >≤ 15天</a-button>
          <a-button
            :type="daysFilter === 30 ? 'primary' : 'secondary'"
            size="small"
            @click="daysFilter = daysFilter === 30 ? null : 30"
          >≤ 30天</a-button>
        </div>

        <a-table 
          :data="filteredDomains" 
          :columns="columns" 
          :pagination="false"
          :loading="loading"
          class="custom-table"
        >
          <template #status="{ record }">
            <div class="status-dot-wrap">
              <div class="status-dot" :style="{ backgroundColor: statusColor(record) }">
                <div class="status-ping" :style="{ backgroundColor: statusColor(record) }"></div>
              </div>
            </div>
          </template>
          
          <template #name="{ record }">
            <span class="site-name">{{ record.name || '-' }}</span>
          </template>
          
          <template #domain="{ record }">
            <span class="domain-text">{{ record.masked_domain }}</span>
          </template>

          <template #days="{ record }">
            <span :style="{ color: statusColor(record), fontWeight: 600 }">
              {{ statusText(record) }}
            </span>
          </template>

          <template #time="{ record }">
            <span class="time-text" v-if="record.checked_at">{{ new Date(record.checked_at).toLocaleString() }}</span>
            <span class="time-text text-gray" v-else>-</span>
          </template>
        </a-table>

        <!-- Legend -->
        <div class="legend">
          <div class="legend-item">
            <div class="status-dot static" style="background-color: #00b42a;"></div>
            <span>正常</span>
          </div>
          <div class="legend-item">
            <div class="status-dot static" style="background-color: #ff7d00;"></div>
            <span>即将过期</span>
          </div>
          <div class="legend-item">
            <div class="status-dot static" style="background-color: #f53f3f;"></div>
            <span>异常/过期</span>
          </div>
        </div>
      </a-card>
    </main>
  </div>
</template>

<style scoped>
.public-layout {
  min-height: 100vh;
  background-color: var(--color-fill-2);
  transition: background-color 0.3s;
}

.public-header {
  height: 60px;
  background-color: var(--color-bg-2);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 100;
}

body[arco-theme='dark'] .public-header {
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.5);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  font-size: 28px;
  color: rgb(var(--primary-6));
}

.title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-1);
}

.public-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 24px;
}

.status-card {
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}
body[arco-theme='dark'] .status-card {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

.card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 16px;
  font-weight: 600;
}

.refresh-text {
  font-size: 13px;
  color: var(--color-text-3);
  font-weight: normal;
}

.tag-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.custom-table :deep(.arco-table-cell) {
  font-size: 16px;
  padding: 16px 16px;
}

.custom-table :deep(.arco-table-th) {
  background-color: var(--color-fill-2);
  font-weight: 600;
  font-size: 16px;
}

.site-name {
  font-weight: 600;
  color: var(--color-text-1);
}

.domain-text {
  font-family: monospace;
  font-size: 15px;
  color: var(--color-text-2);
  background: var(--color-fill-2);
  padding: 4px 8px;
  border-radius: 6px;
}

.time-text {
  color: var(--color-text-3);
  font-size: 15px;
}

.status-dot-wrap {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 24px;
}

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  position: relative;
  z-index: 2;
}

.status-ping {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  opacity: 0.4;
  animation: bg-ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;
}

.static {
  width: 10px;
  height: 10px;
}
.static .status-ping {
  display: none;
}

@keyframes bg-ping {
  75%, 100% { transform: scale(2.5); opacity: 0; }
}

.legend {
  display: flex;
  gap: 20px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-text-2);
}
</style>
