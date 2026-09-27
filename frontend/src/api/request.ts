import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { clearAuthStorage } from '@/utils/authStorage'

declare module 'axios' {
  export interface AxiosRequestConfig {
    /** 静默请求：失败时不弹全局错误提示（用于轮询、自动刷新等后台请求） */
    silent?: boolean
  }
}

const request = axios.create({ baseURL: '/api', timeout: 30000 })

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // 静默请求（自动刷新/轮询）不打扰用户，交给调用方自行处理
    const silent = (error.config as any)?.silent === true

    if (error.response?.status === 401) {
      // 登录过期无论是否静默都要回到登录页，但静默请求不弹提示避免刷屏
      clearAuthStorage()
      router.push('/login')
      if (!silent) ElMessage.error('登录已过期')
    } else if (silent) {
      // 忽略
    } else if (error.response?.status === 403) {
      ElMessage.error('没有权限执行此操作')
    } else {
      ElMessage.error(error.response?.data?.detail || '请求失败')
    }
    return Promise.reject(error)
  },
)

export default request
