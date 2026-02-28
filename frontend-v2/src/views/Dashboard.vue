<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Message, Modal } from '@arco-design/web-vue'
import { api, type CertResult, type DomainItem, type Webhook } from '../api'
import { useUserStore } from '../store/user'

const router = useRouter()
const store = useUserStore()
const loading = ref(false)
const checking = ref(false)
const isDark = ref(document.body.getAttribute('arco-theme') === 'dark')

const domains = ref<DomainItem[]>([])
const results = ref<CertResult[]>([])
const webhooks = ref<Webhook[]>([])
const expandedCard = ref<number | null>(null)

// 过滤器状态
const filterMode = ref<'all' | 'expiring' | 'expired' | 'error'>('all')

// 历史色块数据: "domain:port" -> [{checked_at, days_left, is_expired, is_expiring_soon, error}]
type HistPoint = { checked_at: string; days_left: number | null; is_expired: boolean; is_expiring_soon: boolean; error: string | null }
const historyData = ref<Record<string, HistPoint[]>>({})

// 添加域名
const addForm = ref({ name: '', domain: '', port: 443, note: '', tags: [] as string[] })
const addVisible = ref(false)
// 添加时的 webhook 配置: webhook_id -> { enabled, threshold_days }
const addFormWh = ref<Record<number, { enabled: boolean; threshold_days: string }>>({});

function openAddModal() {
  addForm.value = { name: '', domain: '', port: 443, note: '', tags: [] as string[] }
  addFormWh.value = Object.fromEntries(
    webhooks.value.map((wh) => [wh.id, { enabled: false, threshold_days: '' }])
  )
  addVisible.value = true
}
const addLoading = ref(false)

// 修改密码
const changePwdVisible = ref(false)
const pwdForm = ref({ old_password: '', new_password: '' })
const pwdLoading = ref(false)

// 批量导入
const batchVisible = ref(false)
const batchText = ref('')
const batchLoading = ref(false)

// 单行刷新
const checkingRow = ref<string | null>(null)  // "domain:port"

// 域名级 Webhook 配置
const domainWhVisible = ref(false)
const domainWhTarget = ref<DomainItem | null>(null)
// 编辑中的绑定状态：webhook_id -> { enabled, threshold_days }
const domainWhEdit = ref<Record<number, { enabled: boolean; threshold_days: string }>>({}) 
const domainWhLoading = ref(false)
const domainWhSaving = ref(false)

// 编辑域名
const editVisible = ref(false)
const editLoading = ref(false)
const editTarget = ref<DomainItem | null>(null)
const editForm = ref({ name: '', note: '', tags: [] as string[] })

// Webhook 管理
const whVisible = ref(false)
const whForm = ref({ name: '', type: 'wecom', url: '', enabled: true, threshold_days: 30 })
const whEditId = ref<number | null>(null)
const whLoading = ref(false)
const whTestingId = ref<number | null>(null)

// 批量处理管理
const selectedDomainIds = ref<number[]>([])
const allSelected = computed(() => tableData.value.length > 0 && selectedDomainIds.value.length === tableData.value.length)
const isBatchWh = ref(false) // 是否处于批量告警配置模式
const batchProcessing = ref(false) // 批量删除/检测的 loading 状态

function toggleAll(val: boolean) {
  if (val) {
    selectedDomainIds.value = tableData.value.map(d => d.id)
  } else {
    selectedDomainIds.value = []
  }
}

function handleSelectionChange(id: number) {
  const index = selectedDomainIds.value.indexOf(id)
  if (index > -1) {
    selectedDomainIds.value.splice(index, 1)
  } else {
    selectedDomainIds.value.push(id)
  }
}

// 合并 + 排序：错误/已过期 → 即将过期 → 正常（days_left 升序） → 未检测
function urgencyOrder(row: any): number {
  const r = row.result
  if (!r) return 9999
  if (r.error) return 5000
  if (r.is_expired) return 0
  if (r.is_expiring_soon) return r.days_left ?? 1000
  return (r.days_left ?? 9000) + 100
}

const selectedTag = ref<string | null>(null) // 选中的项目标签过滤

// 所有现存的不同标签
const allTags = computed(() => {
  const set = new Set<string>()
  domains.value.forEach(d => {
    if (d.tags) d.tags.forEach(t => set.add(t))
  })
  return Array.from(set)
})

const tableData = computed(() => {
  const rows = domains.value.map((d) => ({
    ...d,
    result: results.value.find((r) => r.domain === d.domain && r.port === d.port),
  }))
  let filtered = rows;
  // 按照统计状态过滤
  if (filterMode.value === 'expiring') {
    filtered = filtered.filter(r => r.result?.is_expiring_soon && !r.result?.is_expired);
  } else if (filterMode.value === 'expired') {
    filtered = filtered.filter(r => r.result?.is_expired);
  } else if (filterMode.value === 'error') {
    filtered = filtered.filter(r => r.result?.error);
  }
  
  // 按照选择的项目标签过滤
  if (selectedTag.value) {
    filtered = filtered.filter(r => r.tags && r.tags.includes(selectedTag.value!))
  }
  
  return filtered.sort((a, b) => urgencyOrder(a) - urgencyOrder(b))
})

onMounted(async () => {
  await Promise.all([loadDomains(), loadResults(), loadWebhooks(), loadHistory()])
})

async function loadDomains() {
  const r = await api.getDomains()
  domains.value = r.data
}
async function loadResults() {
  const r = await api.getResults()
  results.value = r.data
}
async function loadWebhooks() {
  const r = await api.getWebhooks()
  webhooks.value = r.data
}
async function loadHistory() {
  const r = await api.getHistory()
  historyData.value = r.data
}

async function checkNow() {
  checking.value = true
  try {
    const r = await api.checkNow()
    results.value = r.data
    await loadHistory()
    Message.success('检测完成')
  } catch (e: any) {
    Message.error(e.response?.data?.detail || '检测失败')
  } finally {
    checking.value = false
  }
}

async function doAddDomain() {
  if (!addForm.value.domain.trim()) return
  addLoading.value = true
  try {
    const r = await api.addDomain(addForm.value.name?.trim() || '', addForm.value.domain.trim(), addForm.value.port, addForm.value.note || undefined, addForm.value.tags)
    // 若有勾选 webhook，自动绑定
    const whBindings = webhooks.value
      .filter((wh) => addFormWh.value[wh.id]?.enabled)
      .map((wh) => ({
        webhook_id: wh.id,
        enabled: true,
        threshold_days: addFormWh.value[wh.id].threshold_days
          ? parseInt(addFormWh.value[wh.id].threshold_days)
          : null,
      }))
    if (whBindings.length > 0) {
      await api.setDomainWebhooks(r.data.id, whBindings)
    }
    addVisible.value = false
    addForm.value = { name: '', domain: '', port: 443, note: '', tags: [] as string[] }
    await loadDomains()
    Message.success('添加成功')
  } catch (e: any) {
    Message.error(e.response?.data?.detail || '添加失败')
  } finally {
    addLoading.value = false
  }
}

async function doBatchImport() {
  if (!batchText.value.trim()) return
  batchLoading.value = true
  try {
    const r = await api.batchImport(batchText.value)
    const { added, skipped, failed } = r.data
    batchVisible.value = false
    batchText.value = ''
    await loadDomains()
    Message.success(`导入完成：新增 ${added}，跳过 ${skipped}，失败 ${failed}`)
  } catch (e: any) {
    Message.error(e.response?.data?.detail || '导入失败')
  } finally {
    batchLoading.value = false
  }
}

async function checkOneRow(row: any) {
  const key = `${row.domain}:${row.port}`
  checkingRow.value = key
  try {
    const r = await api.checkOne(row.domain, row.port)
    const idx = results.value.findIndex((x) => x.domain === row.domain && x.port === row.port)
    if (idx >= 0) results.value[idx] = r.data
    else results.value.push(r.data)
    await loadHistory()
    Message.success(`${row.domain} 检测完成`)
  } catch (e: any) {
    Message.error('检测失败')
  } finally {
    checkingRow.value = null
  }
}

async function openDomainWh(row: DomainItem) {
  isBatchWh.value = false
  domainWhTarget.value = row
  domainWhEdit.value = {}
  // 先初始化空的编辑状态，避免表格渲染时访问 undefined 导致崩溃
  for (const wh of webhooks.value) {
    domainWhEdit.value[wh.id] = { enabled: false, threshold_days: '' }
  }
  
  domainWhVisible.value = true
  domainWhLoading.value = true
  try {
    const bindRes = await api.getDomainWebhooks(row.id)
    for (const wh of webhooks.value) {
      const existing = bindRes.data.find((b) => b.webhook_id === wh.id)
      if (existing) {
        domainWhEdit.value[wh.id].enabled = existing.enabled
        domainWhEdit.value[wh.id].threshold_days = existing.threshold_days != null ? String(existing.threshold_days) : ''
      }
    }
  } catch (e: any) {
    Message.error('获取域名告警配置失败')
  } finally {
    domainWhLoading.value = false
  }
}

async function saveDomainWh() {
  domainWhSaving.value = true
  try {
    const bindings = webhooks.value
      .filter((wh) => domainWhEdit.value[wh.id]?.enabled)
      .map((wh) => ({
        webhook_id: wh.id,
        enabled: true,
        threshold_days: domainWhEdit.value[wh.id].threshold_days
          ? parseInt(domainWhEdit.value[wh.id].threshold_days)
          : null,
      }))
      
    if (isBatchWh.value) {
      if (selectedDomainIds.value.length === 0) return
      await api.setBatchDomainWebhooks(selectedDomainIds.value, bindings)
      Message.success(`批量配置告警成功（${selectedDomainIds.value.length} 个域名）`)
    } else {
      if (!domainWhTarget.value) return
      await api.setDomainWebhooks(domainWhTarget.value.id, bindings)
      Message.success('域名告警配置成功')
    }
    
    domainWhVisible.value = false
  } catch (e: any) {
    Message.error('域名告警配置失败')
  } finally {
    domainWhSaving.value = false
  }
}

// ============== 批量操作处理函数 ==============

async function handleBatchCheck() {
  if (selectedDomainIds.value.length === 0) return
  batchProcessing.value = true
  try {
    const r = await api.checkBatch(selectedDomainIds.value)
    // 更新本地 results
    for (const data of r.data) {
      const idx = results.value.findIndex((x) => x.domain === data.domain && x.port === data.port)
      if (idx >= 0) results.value[idx] = data
      else results.value.push(data)
    }
    await loadHistory()
    selectedDomainIds.value = []
    Message.success('批量检测完成')
  } catch (e: any) {
    Message.error('批量检测失败')
  } finally {
    batchProcessing.value = false
  }
}

async function handleBatchDelete() {
  if (selectedDomainIds.value.length === 0) return
  Modal.warning({
    title: '批量删除确认',
    content: `确定要删除选中的 ${selectedDomainIds.value.length} 个域名吗？删除后其历史监控记录也会一并删除！`,
    okButtonProps: { status: 'danger' },
    onOk: async () => {
      batchProcessing.value = true
      try {
        await api.deleteBatch(selectedDomainIds.value)
        await loadDomains()
        selectedDomainIds.value = []
        Message.success('批量删除成功')
      } catch (e: any) {
        Message.error('批量删除失败')
      } finally {
        batchProcessing.value = false
      }
    }
  })
}

function openBatchWhCreate() {
  if (selectedDomainIds.value.length === 0) return
  isBatchWh.value = true
  domainWhTarget.value = null
  domainWhEdit.value = {}
  for (const wh of webhooks.value) {
    domainWhEdit.value[wh.id] = { enabled: false, threshold_days: '' }
  }
  domainWhVisible.value = true
}

// ===========================================

function confirmDelete(row: DomainItem) {
  Modal.confirm({
    title: '确认删除',
    content: `删除 ${row.domain}:${row.port} ？`,
    onOk: async () => {
      await api.deleteDomain(row.domain, row.port)
      await loadDomains()
      results.value = results.value.filter((r) => !(r.domain === row.domain && r.port === row.port))
      Message.success('已删除')
    },
  })
}

function openEditModal(row: DomainItem) {
  editTarget.value = row
  editForm.value = {
    name: row.name || '',
    note: row.note || '',
    tags: row.tags ? [...row.tags] : []
  }
  editVisible.value = true
}

async function doEditDomain() {
  if (!editTarget.value) return
  editLoading.value = true
  try {
    await api.updateDomain(editTarget.value.id, {
      name: editForm.value.name,
      domain: editTarget.value.domain,
      port: editTarget.value.port,
      note: editForm.value.note,
      tags: editForm.value.tags,
    })
    editVisible.value = false
    await loadDomains()
    Message.success('修改成功')
  } catch (e: any) {
    Message.error(e.response?.data?.detail || '修改失败')
  } finally {
    editLoading.value = false
  }
}

async function doChangePwd() {
  pwdLoading.value = true
  try {
    await api.changePassword(pwdForm.value.old_password, pwdForm.value.new_password)
    changePwdVisible.value = false
    pwdForm.value = { old_password: '', new_password: '' }
    Message.success('密码已更新')
  } catch (e: any) {
    Message.error(e.response?.data?.detail || '修改失败')
  } finally {
    pwdLoading.value = false
  }
}

async function logout() {
  await api.logout()
  store.logout()
  router.replace('/login')
}

// ---------- 暗色模式 ----------
function toggleDark() {
  isDark.value = !isDark.value
  document.body.setAttribute('arco-theme', isDark.value ? 'dark' : '')
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
}

// ---------- Webhook ----------
function openWhCreate() {
  whEditId.value = null
  whForm.value = { name: '', type: 'wecom', url: '', enabled: true, threshold_days: 30 }
  whVisible.value = true
}

function openWhEdit(wh: Webhook) {
  whEditId.value = wh.id
  whForm.value = { name: wh.name, type: wh.type, url: wh.url, enabled: wh.enabled, threshold_days: wh.threshold_days }
  whVisible.value = true
}

async function doSaveWebhook() {
  if (!whForm.value.name || !whForm.value.url) {
    Message.warning('名称和 URL 必填')
    return
  }
  whLoading.value = true
  try {
    if (whEditId.value) {
      await api.updateWebhook(whEditId.value, whForm.value)
    } else {
      await api.createWebhook(whForm.value)
    }
    whVisible.value = false
    await loadWebhooks()
    Message.success('保存成功')
  } catch (e: any) {
    Message.error(e.response?.data?.detail || '保存失败')
  } finally {
    whLoading.value = false
  }
}

function confirmDeleteWh(wh: Webhook) {
  Modal.confirm({
    title: '删除 Webhook',
    content: `确认删除「${wh.name}」？`,
    onOk: async () => {
      await api.deleteWebhook(wh.id)
      await loadWebhooks()
      Message.success('已删除')
    },
  })
}

async function testWebhook(wh: Webhook) {
  whTestingId.value = wh.id
  try {
    const r = await api.testWebhook(wh.id)
    if (r.data.ok) Message.success('发送成功')
    else Message.error('发送失败：' + r.data.error)
  } catch (e: any) {
    Message.error('请求失败')
  } finally {
    whTestingId.value = null
  }
}

// ---------- 工具函数 ----------
function daysColor(row: any) {
  if (!row.result) return 'gray'
  if (row.result.error) return 'red'
  if (row.result.is_expired) return 'red'
  if (row.result.is_expiring_soon) return 'orangered'
  return 'green'
}

function daysText(row: any) {
  if (!row.result) return '未检测'
  if (row.result.error) return '错误'
  if (row.result.days_left === null) return '未知'
  return `${row.result.days_left} 天`
}

const whTypeLabel: Record<string, string> = {
  wecom: '企业微信',
  dingtalk: '钉钉',
  custom: '自定义',
}

function statusKey(row: any): string {
  if (!row.result) return 'gray'
  if (row.result.error) return 'red'
  if (row.result.is_expired) return 'red'
  if (row.result.is_expiring_soon) return 'orange'
  return 'green'
}

function daysBarStyle(row: any) {
  if (!row.result || row.result.error || row.result.days_left == null) return { width: '0%' }
  const pct = Math.min(100, Math.max(0, (row.result.days_left / 365) * 100))
  const color = row.result.days_left <= 7 ? '#f53f3f' : row.result.days_left <= 30 ? '#ff7d00' : '#00b42a'
  return { width: `${pct}%`, background: color }
}

function histBlockClass(h: HistPoint): string {
  if (h.error) return 'hist-red'
  if (h.is_expired) return 'hist-red'
  if (h.is_expiring_soon) return 'hist-orange'
  return 'hist-green'
}
</script>

<template>
  <a-layout style="min-height: 100vh; background: transparent;">
    <!-- 顶栏 -->
    <a-layout-header class="header">
      <div class="header-left">
        <div class="logo-wrap">
          <icon-safe class="logo-icon" />
        </div>
        <div class="title-group">
          <span class="site-title">SSL 证书监控</span>
          <span class="site-sub">{{ domains.length }} 个域名·实时跟踪证书状态</span>
        </div>
      </div>
      <div class="header-right">
        <a-tooltip :content="isDark ? '切换亮色' : '切换暗色'">
          <a-button type="text" shape="circle" class="hdr-btn" @click="toggleDark">
            <template #icon>
              <icon-moon-fill v-if="!isDark" />
              <icon-sun-fill v-else />
            </template>
          </a-button>
        </a-tooltip>
        <a-tooltip v-if="store.user?.is_admin" content="管理后台">
          <a-button type="text" shape="circle" class="hdr-btn" @click="router.push('/admin')">
            <template #icon><icon-settings /></template>
          </a-button>
        </a-tooltip>
        <a-dropdown>
          <a-tooltip :content="store.user?.email">
            <div class="avatar">
              {{ (store.user?.email || '?')[0].toUpperCase() }}
            </div>
          </a-tooltip>
          <template #content>
            <a-doption v-if="store.user?.auth_method === 'password'" @click="changePwdVisible = true">
              <template #icon><icon-lock /></template>
              修改密码
            </a-doption>
            <a-doption @click="logout">
              <template #icon><icon-export /></template>
              退出登录
            </a-doption>
          </template>
        </a-dropdown>
      </div>
    </a-layout-header>

    <a-layout-content class="content">
      <!-- 统计卡片 -->
      <a-row :gutter="20" class="stat-row">
        <a-col :span="6">
          <div :class="['stat-card', filterMode === 'all' ? 'stat-active' : '']" @click="filterMode = 'all'">
            <div class="stat-content">
              <div class="stat-title">总监控站点</div>
              <div class="stat-value">{{ domains.length }}</div>
            </div>
            <div class="stat-icon-wrap bg-blue-light">
              <icon-bar-chart class="text-blue" />
            </div>
          </div>
        </a-col>
        <a-col :span="6">
          <div :class="['stat-card', filterMode === 'expiring' ? 'stat-active' : '']" @click="filterMode = 'expiring'">
            <div class="stat-content">
              <div class="stat-title">即将过期</div>
              <div class="stat-value">{{ results.filter(r => r.is_expiring_soon && !r.is_expired).length }}</div>
            </div>
            <div class="stat-icon-wrap bg-orange-light">
              <icon-exclamation-circle class="text-orange" />
            </div>
          </div>
        </a-col>
        <a-col :span="6">
          <div :class="['stat-card', filterMode === 'expired' ? 'stat-active' : '']" @click="filterMode = 'expired'">
            <div class="stat-content">
              <div class="stat-title">已过期</div>
              <div class="stat-value">{{ results.filter(r => r.is_expired).length }}</div>
            </div>
            <div class="stat-icon-wrap bg-red-light">
              <icon-close-circle class="text-red" />
            </div>
          </div>
        </a-col>
        <a-col :span="6">
          <div :class="['stat-card', filterMode === 'error' ? 'stat-active' : '']" @click="filterMode = 'error'">
            <div class="stat-content">
              <div class="stat-title">检测错误</div>
              <div class="stat-value">{{ results.filter(r => r.error).length }}</div>
            </div>
            <div class="stat-icon-wrap bg-gray-light">
              <icon-info-circle class="text-gray" />
            </div>
          </div>
        </a-col>
      </a-row>

      <!-- 操作栏 -->
      <div class="toolbar">
        <a-button type="primary" @click="openAddModal">
          <template #icon><icon-plus /></template>
          添加域名
        </a-button>
        <a-button :loading="checking" @click="checkNow">
          <template #icon><icon-refresh /></template>
          立即检测
        </a-button>
        <a-button @click="batchVisible = true">
          <template #icon><icon-import /></template>
          批量导入
        </a-button>
        <a-button @click="openWhCreate">
          <template #icon><icon-notification /></template>
          告警配置
          <a-badge v-if="webhooks.length" :count="webhooks.length" :max-count="99"
            style="margin-left: 4px" />
        </a-button>
      </div>

      <!-- 批量操作栏 -->
      <transition name="fade">
        <div v-if="selectedDomainIds.length > 0" class="batch-toolbar">
          <a-checkbox :model-value="allSelected" @change="toggleAll">全选 (已选 {{ selectedDomainIds.length }} 项)</a-checkbox>
          <div class="batch-actions">
            <a-button :loading="batchProcessing" type="primary" status="success" size="small" @click="handleBatchCheck">
              <template #icon><icon-sync /></template>快速检测
            </a-button>
            <a-button :loading="batchProcessing" type="outline" size="small" @click="openBatchWhCreate">
              <template #icon><icon-notification /></template>配置告警
            </a-button>
            <a-button :loading="batchProcessing" type="outline" status="danger" size="small" @click="handleBatchDelete">
              <template #icon><icon-delete /></template>批量删除
            </a-button>
          </div>
        </div>
      </transition>

      <!-- 标签过滤栏 -->
      <div v-if="allTags.length > 0" class="tag-filter-bar">
        <span class="tag-filter-label"><icon-tags /> 项目标签：</span>
        <a-tag 
          v-for="tag in allTags" 
          :key="tag" 
          :color="selectedTag === tag ? 'arcoblue' : 'gray'"
          class="filter-tag"
          checkable
          :checked="selectedTag === tag"
          @check="selectedTag = selectedTag === tag ? null : tag"
        >
          {{ tag }}
        </a-tag>
      </div>

      <!-- 域名卡片列表 -->
      <a-spin :loading="loading">
        <a-empty
          v-if="tableData.length === 0"
          description="暂无域名，点击「添加域名」开始监控"
          style="padding: 60px 0"
        />
        <div
          v-for="row in tableData"
          :key="row.id"
          class="domain-card"
          :class="{'card-selected': selectedDomainIds.includes(row.id)}"
          @click="expandedCard = expandedCard === row.id ? null : row.id"
        >
          <div class="card-body">
            <div class="card-row1">
              <div class="card-checkbox-inline" @click.stop>
                <a-checkbox :model-value="selectedDomainIds.includes(row.id)" @change="handleSelectionChange(row.id)" />
              </div>
              <div class="status-indicator">
                <div :class="['status-ping', `bg-${statusKey(row)}`]"></div>
                <div :class="['status-dot', `bg-${statusKey(row)}`]"></div>
              </div>
              <div class="card-name-group">
                <span class="domain-name">{{ row.name || row.domain }}</span>
                <span v-if="row.name" style="font-size: 13px; color: var(--color-text-3); margin-left: 6px">{{ row.domain }}</span>
                <a-tag v-if="row.port !== 443" size="small" style="margin-left: 4px">:{{ row.port }}</a-tag>
                <a-tag v-for="tag in (row.tags || [])" :key="tag" size="small" class="domain-badge-tag">{{ tag }}</a-tag>
                <span v-if="row.note" class="card-note">{{ row.note }}</span>
              </div>
              <div class="card-meta">
                <span v-if="row.result?.not_after">到期 {{ row.result.not_after }}</span>
                <span v-if="row.result?.issuer_cn">{{ row.result.issuer_cn }}</span>
                <span v-if="row.result">检测 {{ new Date(row.result.checked_at).toLocaleString() }}</span>
              </div>
              <div class="card-actions" @click.stop>
                <a-tooltip content="重新检测">
                  <a-button
                    type="text" size="small"
                    :loading="checkingRow === `${row.domain}:${row.port}`"
                    @click="checkOneRow(row)"
                  >
                    <template #icon><icon-sync /></template>
                  </a-button>
                </a-tooltip>
                <a-tooltip content="编辑域名信息">
                  <a-button type="text" size="small" @click="openEditModal(row)">
                    <template #icon><icon-edit /></template>
                  </a-button>
                </a-tooltip>
                <a-tooltip content="域名告警配置">
                  <a-button type="text" size="small" @click="openDomainWh(row)">
                    <template #icon><icon-notification /></template>
                  </a-button>
                </a-tooltip>
                <a-button type="text" status="danger" size="small" @click="confirmDelete(row)">
                  <template #icon><icon-delete /></template>
                </a-button>
              </div>
            </div>
            <div class="card-row2">
              <div class="days-info">
                <a-tooltip :content="row.result?.error || ''" :disabled="!row.result?.error">
                  <span :class="['days-label', `days-${statusKey(row)}`]">{{ daysText(row) }}</span>
                </a-tooltip>
                <div class="days-progress-bar">
                  <div class="days-bar-inner" :style="daysBarStyle(row)"></div>
                </div>
              </div>
              <div class="history-blocks">
                <a-tooltip
                  v-for="(h, i) in (historyData[`${row.domain}:${row.port}`] || []).slice().reverse()"
                  :key="i"
                  :content="`${new Date(h.checked_at).toLocaleDateString()} \u00b7 ${h.error ? '错误' : h.is_expired ? '已过期' : h.is_expiring_soon ? '即将过期' : h.days_left + '天'}`"
                  mini
                >
                  <div :class="['hist-block', histBlockClass(h)]"></div>
                </a-tooltip>
              </div>
            </div>
            <!-- 展开证书详情 -->
            <div v-if="expandedCard === row.id" class="card-detail" @click.stop>
              <template v-if="row.result?.error">
                <a-alert type="error" :message="row.result.error" />
              </template>
              <template v-else-if="row.result">
                <a-descriptions :column="3" size="small" bordered>
                  <a-descriptions-item label="Subject CN">{{ row.result.subject_cn || '-' }}</a-descriptions-item>
                  <a-descriptions-item label="颁发机构">{{ row.result.issuer_cn || '-' }}</a-descriptions-item>
                  <a-descriptions-item label="颁发组织">{{ row.result.issuer_org || '-' }}</a-descriptions-item>
                  <a-descriptions-item label="SAN 列表" :span="3">
                    <template v-if="row.result.san?.length">
                      <a-tag v-for="s in row.result.san" :key="s" size="small" style="margin: 2px">{{ s }}</a-tag>
                    </template>
                    <span v-else>-</span>
                  </a-descriptions-item>
                </a-descriptions>
              </template>
              <template v-else>
                <a-empty description="暂无检测数据" />
              </template>
            </div>
          </div>
        </div>
      </a-spin>
    </a-layout-content>
  </a-layout>

  <!-- 添加域名 -->
  <a-modal v-model:visible="addVisible" title="添加域名" @ok="doAddDomain" :ok-loading="addLoading" :width="520">
    <a-form :model="addForm" layout="vertical">
      <a-form-item label="站点名称（可选）">
        <a-input v-model="addForm.name" placeholder="例如：公司官网，不填则默认显示域名" @keyup.enter="doAddDomain" />
      </a-form-item>
      <a-form-item label="域名" required>
        <a-input v-model="addForm.domain" placeholder="example.com" @keyup.enter="doAddDomain" />
      </a-form-item>
      <a-form-item label="端口">
        <a-input-number v-model="addForm.port" :min="1" :max="65535" />
      </a-form-item>
      <a-form-item label="项目标签" tooltip="输入项目或环境名称，可搜索已有标签或创建新标签">
        <a-select v-model="addForm.tags" multiple allow-create allow-search placeholder="搜索或输入新标签后回车">
          <a-option v-for="tag in allTags" :key="tag" :value="tag">{{ tag }}</a-option>
        </a-select>
      </a-form-item>
      <a-form-item label="备注">
        <a-input v-model="addForm.note" placeholder="可选" />
      </a-form-item>
    </a-form>
    <!-- Webhook 告警配置 -->
    <template v-if="webhooks.length > 0">
      <a-divider style="margin: 12px 0" />
      <p style="font-size: 13px; font-weight: 500; margin-bottom: 10px; color: var(--color-text-1)">告警配置（可选）</p>
      <p style="font-size: 12px; color: var(--color-text-3); margin-bottom: 12px">
        留空则使用全局 Webhook 配置，勾选后仅对该域名生效
      </p>
      <a-table :data="webhooks" :pagination="false" :bordered="false" size="small" row-key="id">
        <template #columns>
          <a-table-column title="启用" :width="60">
            <template #cell="{ record }">
              <a-checkbox v-if="addFormWh[record.id]" v-model="addFormWh[record.id].enabled" />
            </template>
          </a-table-column>
          <a-table-column title="名称" data-index="name" />
          <a-table-column title="类型" :width="80">
            <template #cell="{ record }">
              <a-tag size="small">{{ whTypeLabel[record.type] }}</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="告警阈值（天）" :width="146">
            <template #cell="{ record }">
              <a-input-number
                v-if="addFormWh[record.id]"
                v-model="addFormWh[record.id].threshold_days"
                :disabled="!addFormWh[record.id]?.enabled"
                placeholder="默认"
                :min="1" :max="365"
                :style="{ width: '90px' }"
                allow-clear
              />
              <span style="color: var(--color-text-3); font-size: 12px; margin-left: 4px">
                默认 {{ record.threshold_days }}
              </span>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
  </a-modal>

  <!-- 编辑域名 -->
  <a-modal v-model:visible="editVisible" title="编辑域名信息" @ok="doEditDomain" :ok-loading="editLoading" :width="480">
    <a-form :model="editForm" layout="vertical">
      <a-form-item label="站点名称">
        <a-input v-model="editForm.name" placeholder="例如：公司官网" />
      </a-form-item>
      <a-form-item label="域名">
        <a-input :model-value="editTarget?.domain" disabled />
      </a-form-item>
      <a-form-item label="项目标签">
        <a-select v-model="editForm.tags" multiple allow-create allow-search placeholder="搜索或输入新标签后回车">
          <a-option v-for="tag in allTags" :key="tag" :value="tag">{{ tag }}</a-option>
        </a-select>
      </a-form-item>
      <a-form-item label="备注">
        <a-input v-model="editForm.note" placeholder="可选" />
      </a-form-item>
    </a-form>
  </a-modal>

  <!-- 域名级 Webhook 配置 -->
  <a-modal
    v-model:visible="domainWhVisible"
    :title="`告警配置：${domainWhTarget?.domain}`"
    :ok-loading="domainWhSaving"
    ok-text="保存"
    @ok="saveDomainWh"
    :width="520"
  >
    <a-spin :loading="domainWhLoading" style="width: 100%">
      <template v-if="webhooks.length === 0">
        <a-empty description="请先在「告警配置」中添加全局 Webhook" />
      </template>
      <template v-else>
        <p style="color: var(--color-text-3); font-size: 13px; margin-bottom: 16px">
          勾选后，该域名只使用以下 Webhook 告警（不再使用全局配置）；留空则回退到全局配置。
        </p>
        <a-table
          :data="webhooks"
          :pagination="false"
          :bordered="false"
          size="small"
          row-key="id"
        >
          <template #columns>
            <a-table-column title="启用" :width="60">
              <template #cell="{ record }">
                <a-checkbox v-if="domainWhEdit[record.id]" v-model="domainWhEdit[record.id].enabled" />
              </template>
            </a-table-column>
            <a-table-column title="名称" data-index="name" />
            <a-table-column title="类型" :width="80">
              <template #cell="{ record }">
                <a-tag size="small">{{ whTypeLabel[record.type] }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="告警阈值（天）" :width="146">
              <template #cell="{ record }">
                <a-input-number
                  v-if="domainWhEdit[record.id]"
                  v-model="domainWhEdit[record.id].threshold_days"
                  :disabled="!domainWhEdit[record.id]?.enabled"
                  placeholder="默认"
                  :min="1" :max="365"
                  :style="{ width: '90px' }"
                  allow-clear
                />
                <span style="color: var(--color-text-3); font-size: 12px; margin-left: 4px">
                  默认 {{ record.threshold_days }}
                </span>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </template>
    </a-spin>
  </a-modal>

  <!-- 批量导入 -->
  <a-modal
    v-model:visible="batchVisible"
    title="批量导入域名"
    @ok="doBatchImport"
    :ok-loading="batchLoading"
    ok-text="导入"
    :width="480"
  >
    <p style="margin-bottom: 8px; color: var(--color-text-3); font-size: 13px;">
      每行一个域名，支持格式：<br>
      <code>example.com</code>　　（默认 443 端口）<br>
      <code>example.com:8443</code>　　（自定义端口）<br>
      <code>example.com:443 备注文字</code>　　（可选备注）<br>
      以 <code>#</code> 开头的行会被跳过
    </p>
    <a-textarea
      v-model="batchText"
      :auto-size="{ minRows: 6, maxRows: 16 }"
      placeholder="example.com&#10;api.example.com:8443&#10;internal.corp:443 内网"
      allow-clear
    />
  </a-modal>

  <!-- 修改密码 -->
  <a-modal v-model:visible="changePwdVisible" title="修改密码" @ok="doChangePwd" :ok-loading="pwdLoading">
    <a-form :model="pwdForm" layout="vertical">
      <a-form-item label="旧密码">
        <a-input-password v-model="pwdForm.old_password" />
      </a-form-item>
      <a-form-item label="新密码">
        <a-input-password v-model="pwdForm.new_password" />
      </a-form-item>
    </a-form>
  </a-modal>

  <!-- Webhook 管理抽屉 -->
  <a-drawer
    v-model:visible="whVisible"
    title="告警 Webhook 配置"
    :width="520"
    :footer="false"
  >
    <div class="wh-section">
      <!-- 已有 Webhook 列表 -->
      <a-list v-if="webhooks.length" :bordered="false" style="margin-bottom: 16px">
        <a-list-item v-for="wh in webhooks" :key="wh.id">
          <a-list-item-meta>
            <template #title>
              <span>{{ wh.name }}</span>
              <a-tag size="small" style="margin-left: 8px">{{ whTypeLabel[wh.type] }}</a-tag>
              <a-tag v-if="!wh.enabled" size="small" color="gray" style="margin-left: 4px">已禁用</a-tag>
            </template>
            <template #description>
              阈值 {{ wh.threshold_days }} 天 · {{ wh.url.slice(0, 40) }}{{ wh.url.length > 40 ? '...' : '' }}
            </template>
          </a-list-item-meta>
          <template #actions>
            <a-button size="small" :loading="whTestingId === wh.id" @click="testWebhook(wh)">测试</a-button>
            <a-button size="small" @click="openWhEdit(wh)">编辑</a-button>
            <a-button size="small" status="danger" @click="confirmDeleteWh(wh)">删除</a-button>
          </template>
        </a-list-item>
      </a-list>
      <a-empty v-else description="暂无 Webhook" style="margin: 24px 0" />

      <!-- 添加/编辑表单 -->
      <a-divider>{{ whEditId ? '编辑 Webhook' : '添加 Webhook' }}</a-divider>
      <a-form :model="whForm" layout="vertical">
        <a-form-item label="名称">
          <a-input v-model="whForm.name" placeholder="企业微信告警" />
        </a-form-item>
        <a-form-item label="类型">
          <a-radio-group v-model="whForm.type" type="button">
            <a-radio value="wecom">企业微信</a-radio>
            <a-radio value="dingtalk">钉钉</a-radio>
            <a-radio value="custom">自定义</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="Webhook URL">
          <a-input v-model="whForm.url" placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..." />
        </a-form-item>
        <a-form-item label="告警阈值（剩余天数 ≤ 时触发）">
          <a-input-number v-model="whForm.threshold_days" :min="1" :max="365" style="width: 120px" />
        </a-form-item>
        <a-form-item label="状态">
          <a-switch v-model="whForm.enabled" checked-text="启用" unchecked-text="禁用" />
        </a-form-item>
        <a-space>
          <a-button type="primary" :loading="whLoading" @click="doSaveWebhook">
            {{ whEditId ? '保存修改' : '添加' }}
          </a-button>
          <a-button v-if="whEditId" @click="openWhCreate">取消编辑</a-button>
        </a-space>
      </a-form>
    </div>
  </a-drawer>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  height: 64px;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--color-border);
  box-shadow: 0 1px 12px rgba(0,0,0,.04);
  position: sticky;
  top: 0;
  z-index: 1000;
}
body[arco-theme='dark'] .header {
  background: rgba(20, 24, 36, 0.8);
}
.header-left { display: flex; align-items: center; gap: 14px; }
.logo-wrap {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--color-primary-light-1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.logo-icon {
  font-size: 22px;
  color: rgb(var(--primary-6));
}
.title-group {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.site-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text-1);
  line-height: 1.3;
}
.site-sub {
  font-size: 12px;
  color: var(--color-text-3);
  line-height: 1.3;
}
.header-right { display: flex; align-items: center; gap: 4px; }
.hdr-btn {
  color: var(--color-text-2) !important;
}
.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgb(var(--primary-6));
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  margin-left: 4px;
  user-select: none;
  transition: opacity 0.2s;
}
.avatar:hover { opacity: 0.85; }
.content {
  padding: 32px 24px;
  max-width: 1280px;
  margin: 0 auto;
  width: 100%;
}
.stat-row { margin-bottom: 24px; }
.stat-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--color-bg-2);
  padding: 24px;
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.02);
  border: 1px solid var(--color-border);
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: pointer;
  position: relative;
  overflow: hidden;
}
.stat-card:hover { box-shadow: 0 8px 24px rgba(0,0,0,0.06); transform: translateY(-4px); border-color: transparent;}
.stat-active {
  border-color: rgb(var(--primary-6));
  box-shadow: 0 8px 24px rgba(0,0,0,0.08); /* highlight activated stat card */
}
.stat-active::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  border-radius: 16px;
  box-shadow: inset 0 0 0 2px rgb(var(--primary-6));
  pointer-events: none;
}
.stat-content { display: flex; flex-direction: column; }
.stat-title {
  color: var(--color-text-3);
  font-size: 13px;
  margin-bottom: 6px;
  font-weight: 500;
}
.stat-value {
  color: var(--color-text-1);
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
}
.stat-icon-wrap {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}
.bg-blue-light { background: rgba(22, 93, 255, 0.1); }
.text-blue { color: rgb(var(--primary-6)); }
.bg-orange-light { background: rgba(255, 125, 0, 0.1); }
.text-orange { color: rgb(255, 125, 0); }
.bg-red-light { background: rgba(245, 63, 63, 0.1); }
.text-red { color: rgb(245, 63, 63); }
.bg-gray-light { background: rgba(134, 144, 156, 0.1); }
.text-gray { color: rgb(134, 144, 156); }

.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  align-items: center;
}
.batch-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: var(--color-bg-2);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  margin-bottom: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}
.batch-actions {
  display: flex;
  gap: 12px;
}
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
.tag-filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: var(--color-bg-2);
  border-radius: 12px;
  border: 1px solid var(--color-border);
}
.tag-filter-label {
  font-size: 13px;
  color: var(--color-text-3);
  margin-right: 4px;
}
.filter-tag {
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
}
.domain-badge-tag {
  margin-left: 6px;
  border-radius: 4px;
  background: rgba(22, 93, 255, 0.08);
  color: rgb(var(--primary-6));
  border: none;
}
body[arco-theme='dark'] .domain-badge-tag {
  background: rgba(22, 93, 255, 0.15);
}
.wh-section { padding: 0 4px; }

/* 域名卡片 */
.domain-card {
  display: flex;
  align-items: stretch;
  background: var(--color-bg-2);
  border-radius: 16px;
  margin-bottom: 16px;
  border: 1px solid var(--color-border);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
}
.card-selected {
  border-color: rgb(var(--primary-6));
  box-shadow: 0 4px 16px rgba(var(--primary-6), 0.15);
}
.domain-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(var(--primary-6), 0.08); /* 悬浮时带一点主色发光 */
  border-color: rgba(var(--primary-6), 0.3);
}
.card-checkbox-inline {
  margin-right: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.domain-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08); /* 更柔和且大面积的悬浮阴影 */
  border-color: transparent;
}
.status-indicator {
  position: relative;
  width: 12px;
  height: 12px;
  margin-right: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  position: relative;
  z-index: 2;
}
.status-ping {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  opacity: 0.4;
  animation: bg-ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;
}
@keyframes bg-ping {
  75%, 100% { transform: scale(3); opacity: 0; }
}

.bg-green  { background: #00b42a; border: 1px solid rgba(0,180,42,0.2); }
.bg-orange { background: #ff7d00; border: 1px solid rgba(255,125,0,0.2); }
.bg-red    { background: #f53f3f; border: 1px solid rgba(245,63,63,0.2); }
.bg-gray   { background: #c9cdd4; border: 1px solid rgba(201,205,212,0.2); }

.card-body {
  flex: 1;
  padding: 16px 24px;
  min-width: 0;
}
.card-row1 {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.card-name-group {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}
.domain-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.card-note {
  font-size: 12px;
  color: var(--color-text-3);
  margin-left: 6px;
  white-space: nowrap;
}
.card-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--color-text-3);
  white-space: nowrap;
  flex-shrink: 0;
}
.card-actions { display: flex; gap: 0; flex-shrink: 0; }

.card-row2 {
  display: flex;
  align-items: center;
  gap: 16px;
}
.days-info {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 220px;
  flex-shrink: 0;
}
.days-label {
  font-size: 13px;
  font-weight: 600;
  width: 64px;
  flex-shrink: 0;
}
.days-green  { color: #00b42a; }
.days-orange { color: #ff7d00; }
.days-red    { color: #f53f3f; }
.days-gray   { color: #86909c; }
.days-progress-bar {
  flex: 1;
  height: 6px;
  background: var(--color-fill-3);
  border-radius: 9999px;
  overflow: hidden;
}
.days-bar-inner {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.4s ease, background-color 0.4s ease;
}
.history-blocks {
  flex: 1;
  display: flex;
  gap: 3px;
  align-items: center;
  overflow: hidden;
}
.hist-block {
  width: 8px;
  height: 18px;
  border-radius: 4px;
  flex-shrink: 0;
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  transform-origin: center;
}
.hist-block:hover {
  transform: scaleY(1.3) scaleX(1.1);
}
.hist-green  { background: #00b42a; }
.hist-orange { background: #ff7d00; }
.hist-red    { background: #f53f3f; }
.card-detail {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-2);
}
</style>
