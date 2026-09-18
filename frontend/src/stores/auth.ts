import { defineStore } from 'pinia'
import { ref } from 'vue'
import { clearAuthStorage } from '@/utils/authStorage'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')
  const role = ref(localStorage.getItem('role') || '')

  function setAuth(t: string, u: string, r: string) {
    token.value = t; username.value = u; role.value = r
    localStorage.setItem('token', t)
    localStorage.setItem('username', u)
    localStorage.setItem('role', r)
  }
  function clearAuth() {
    token.value = ''; username.value = ''; role.value = ''
    // 只清理登录态，保留外观（自定义背景）等用户本地偏好
    clearAuthStorage()
  }
  return { token, username, role, setAuth, clearAuth }
})