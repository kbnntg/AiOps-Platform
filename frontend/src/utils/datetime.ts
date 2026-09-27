/**
 * 时间处理小工具
 *
 * 后端返回的是 MySQL DATETIME 字符串（形如 "2024-05-05 12:00:00"），
 * 各浏览器对它的解析行为不一致，统一在这里做兼容处理。
 */

/** 把后端时间字符串解析成毫秒时间戳，无法解析时返回 0 */
export function parseTime(value?: string | null): number {
  if (!value) return 0
  const normalized = String(value).trim().replace(' ', 'T')
  const t = Date.parse(normalized)
  return Number.isNaN(t) ? 0 : t
}

function pad(n: number): string {
  return n < 10 ? `0${n}` : String(n)
}

/** 格式化为 YYYY-MM-DD HH:mm:ss */
export function formatDateTime(value?: string | number | Date | null): string {
  if (value === null || value === undefined || value === '') return ''
  const date =
    value instanceof Date
      ? value
      : typeof value === 'number'
        ? new Date(value)
        : new Date(parseTime(String(value)))
  if (Number.isNaN(date.getTime())) return String(value)
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  )
}

/** 相对时间描述，例如「3 分钟前」 */
export function fromNow(value?: string | null): string {
  const t = parseTime(value)
  if (!t) return ''
  const diff = Date.now() - t
  if (diff < 0) return formatDateTime(value)
  const sec = Math.floor(diff / 1000)
  if (sec < 60) return '刚刚'
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min} 分钟前`
  const hour = Math.floor(min / 60)
  if (hour < 24) return `${hour} 小时前`
  const day = Math.floor(hour / 24)
  if (day < 30) return `${day} 天前`
  return formatDateTime(value)
}
