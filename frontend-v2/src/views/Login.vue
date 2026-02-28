<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { api } from '../api'
import { useUserStore } from '../store/user'

const router = useRouter()
const route = useRoute()
const store = useUserStore()
const loading = ref(false)
const isRegister = ref(false)
const form = ref({ email: '', password: '' })

// 处理 GitHub OAuth 回调
onMounted(async () => {
  const code = route.query.github_code as string
  if (code) {
    try {
      const res = await fetch(`/api/auth/github/exchange?code=${code}`)
      const data = await res.json()
      if (data.token) {
        store.setToken(data.token, data.user)
        router.replace('/')
      } else {
        Message.error('GitHub 登录失败：' + (data.detail || '未知错误'))
      }
    } catch (e: any) {
      Message.error('GitHub 登录失败')
    }
  }
})

async function submit() {
  loading.value = true
  try {
    const r = isRegister.value
      ? await api.register(form.value.email, form.value.password)
      : await api.login(form.value.email, form.value.password)
    store.setToken(r.data.token, r.data.user)
    router.replace('/')
  } catch (e: any) {
    Message.error(e.response?.data?.detail || '操作失败')
  } finally {
    loading.value = false
  }
}

function githubLogin() {
  location.href = '/api/auth/github'
}
</script>

<template>
  <div class="login-container">
    <a-card class="login-card">
      <div class="logo">
        <icon-safe style="font-size: 32px; color: var(--color-primary)" />
        <span class="title">SSL 证书监控</span>
      </div>

      <a-form :model="form" layout="vertical">
        <a-form-item label="邮箱">
          <a-input v-model="form.email" placeholder="your@email.com" allow-clear />
        </a-form-item>
        <a-form-item label="密码">
          <a-input-password v-model="form.password" placeholder="密码" @keyup.enter="submit" />
        </a-form-item>
        <a-button type="primary" long :loading="loading" @click="submit">
          {{ isRegister ? '注册' : '登录' }}
        </a-button>
      </a-form>

      <div class="divider">
        <a-divider>或</a-divider>
        <a-button long @click="githubLogin">
          <template #icon><icon-github /></template>
          GitHub 登录
        </a-button>
      </div>

      <div class="switch-mode">
        <a-link @click="isRegister = !isRegister">
          {{ isRegister ? '已有账号？去登录' : '没有账号？去注册' }}
        </a-link>
      </div>
    </a-card>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: transparent;
}
.login-card {
  width: 400px;
  padding: 16px 8px;
  border-radius: 16px;
  background: color-mix(in srgb, var(--color-bg-2) 70%, transparent);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.06);
  border: 1px solid var(--color-border-2);
  position: relative;
  z-index: 10;
}
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 28px;
}
.title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-1);
}
.divider {
  margin-top: 16px;
}
.switch-mode {
  margin-top: 16px;
  text-align: center;
}
</style>
