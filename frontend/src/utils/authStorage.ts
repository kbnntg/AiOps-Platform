export const AUTH_KEYS = ['token', 'username', 'role'] as const

/**
 * 仅清除登录态，保留 appearance:* 等本地偏好设置。
 * （原先使用的 localStorage.clear() 会连带删除用户自定义背景）
 */
export function clearAuthStorage() {
  for (const key of AUTH_KEYS) localStorage.removeItem(key)
}
