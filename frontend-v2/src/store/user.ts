import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, type User } from '../api'

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('token'))

  async function fetchMe() {
    try {
      const r = await api.me()
      user.value = r.data
    } catch {
      logout()
    }
  }

  function setToken(t: string, u: User) {
    token.value = t
    user.value = u
    localStorage.setItem('token', t)
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return { user, token, fetchMe, setToken, logout }
})
