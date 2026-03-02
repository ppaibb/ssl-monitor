import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../store/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('../views/Login.vue') },
    {
      path: '/',
      component: () => import('../views/Dashboard.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/status',
      name: 'PublicStatus',
      component: () => import('../views/PublicStatus.vue')
    },
    {
      path: '/admin',
      name: 'Admin',
      component: () => import('../views/Admin.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
  ],
})

router.beforeEach(async (to) => {
  const store = useUserStore()
  if (to.meta.requiresAuth) {
    if (!store.token) {
      // 保留 github_code 参数，让 Login 页面能处理 OAuth 回调
      if (to.query.github_code) {
        return { path: '/login', query: { github_code: to.query.github_code } }
      }
      return '/login'
    }
    if (!store.user) await store.fetchMe()
    if (!store.user) return '/login'
    if (to.meta.requiresAdmin && !store.user.is_admin) return '/'
  }
})

export default router
