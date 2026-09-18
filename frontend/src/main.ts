import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as Icons from '@element-plus/icons-vue'
import './styles.css'
import App from './App.vue'
import router from './router'
import { useAppearanceStore } from './stores/appearance'

const app = createApp(App)
for (const [key, comp] of Object.entries(Icons)) app.component(key, comp)

const pinia = createPinia()
app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// 首屏就恢复当前用户的自定义背景，避免出现背景闪烁
useAppearanceStore(pinia).init(localStorage.getItem('username') || '')

app.mount('#app')
