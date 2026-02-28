import { createApp } from 'vue'
import ArcoVue from '@arco-design/web-vue'
import ArcoVueIcon from '@arco-design/web-vue/es/icon'
import '@arco-design/web-vue/dist/arco.css'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

// 初始化主题：优先 localStorage，其次跟系统
const savedTheme = localStorage.getItem('theme')
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
  document.body.setAttribute('arco-theme', 'dark')
}

const app = createApp(App)
app.use(ArcoVue)
app.use(ArcoVueIcon)
app.use(createPinia())
app.use(router)
app.mount('#app')
