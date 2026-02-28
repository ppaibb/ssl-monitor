<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { api } from '../api'

const router = useRouter()
const users = ref<any[]>([])
const allDomains = ref<any[]>([])
const checkLoading = ref(false)

onMounted(async () => {
  await Promise.all([loadUsers(), loadDomains()])
})

async function loadUsers() {
  const r = await api.adminUsers()
  users.value = r.data
}

async function loadDomains() {
  const r = await api.adminDomains()
  allDomains.value = r.data
}

async function checkAll() {
  checkLoading.value = true
  try {
    const r = await api.adminCheckAll()
    Message.success(`检测完成，共 ${r.data.checked} 个域名`)
  } catch (e: any) {
    Message.error('检测失败')
  } finally {
    checkLoading.value = false
  }
}
</script>

<template>
  <a-layout style="min-height: 100vh; background: var(--color-bg-1)">
    <a-layout-header class="header">
      <div class="header-left">
        <a-button type="text" @click="router.push('/')">
          <template #icon><icon-arrow-left /></template>
        </a-button>
        <span class="site-title">管理后台</span>
      </div>
      <a-button :loading="checkLoading" @click="checkAll">
        <template #icon><icon-refresh /></template>
        全量检测
      </a-button>
    </a-layout-header>

    <a-layout-content class="content">
      <a-typography-title :heading="6">用户列表</a-typography-title>
      <a-table :data="users" :pagination="false" row-key="id" style="margin-bottom: 32px">
        <template #columns>
          <a-table-column title="ID" data-index="id" :width="60" />
          <a-table-column title="邮箱" data-index="email" />
          <a-table-column title="登录方式" data-index="auth_method" />
          <a-table-column title="管理员">
            <template #cell="{ record }">
              <a-tag v-if="record.is_admin" color="arcoblue">是</a-tag>
              <span v-else>-</span>
            </template>
          </a-table-column>
          <a-table-column title="域名数" data-index="domain_count" />
          <a-table-column title="注册时间">
            <template #cell="{ record }">
              {{ new Date(record.created_at).toLocaleString() }}
            </template>
          </a-table-column>
        </template>
      </a-table>

      <a-typography-title :heading="6">全部域名</a-typography-title>
      <a-table :data="allDomains" :pagination="{ pageSize: 20 }" row-key="id">
        <template #columns>
          <a-table-column title="用户 ID" data-index="user_id" :width="80" />
          <a-table-column title="域名" data-index="domain" />
          <a-table-column title="端口" data-index="port" :width="80" />
          <a-table-column title="备注" data-index="note" />
          <a-table-column title="添加时间">
            <template #cell="{ record }">
              {{ new Date(record.added_at).toLocaleString() }}
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-layout-content>
  </a-layout>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: var(--color-bg-2);
  border-bottom: 1px solid var(--color-border);
}
.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.site-title {
  font-size: 16px;
  font-weight: 600;
}
.content {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}
</style>
