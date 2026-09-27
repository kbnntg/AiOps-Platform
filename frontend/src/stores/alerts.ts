import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import router from '@/router'
import { getAlerts } from '@/api/alerts'

/** 轮询间隔（毫秒） */
const POLL_INTERVAL = 30_000
/** 单轮最多弹出的通知条数，避免告警风暴刷屏 */
const MAX_NOTIFY = 3
/** 提醒开关的本地存储键 */
const NOTIFY_KEY = 'alertNotifyEnabled'

/**
 * 全局告警状态：侧边栏 / 顶栏未处理角标 + 新告警桌面提醒。
 *
 * 数据来源是后端已有的 GET /api/alerts?status=OPEN，未改动后端。
 */
export const useAlertStore = defineStore('alerts', () => {
  /** 未处理告警列表（已剔除误报） */
  const openAlerts = ref<any[]>([])
  /** 最近一次拉取成功的时间戳 */
  const lastUpdated = ref(0)
  /** 最近一次拉取的错误信息（后端不可用时的降级提示） */
  const lastError = ref('')
  /** 是否轮询中 */
  const polling = ref(false)

  const notifyEnabled = ref(localStorage.getItem(NOTIFY_KEY) !== '0')

  const unhandledCount = computed(() => openAlerts.value.length)
  /** 是否处于「后端不可达」状态（顶栏显示为灰色而非红色角标） */
  const degraded = computed(() => !!lastError.value && openAlerts.value.length === 0)

  /** 已见过的告警 id，用于判断"新告警"；null 表示尚未建立基线 */
  let knownIds: Set<number> | null = null
  let timer: number | undefined
  let inFlight = false

  function idOf(alert: any): number {
    return Number(alert?.id)
  }

  function isFalsePositive(alert: any): boolean {
    return alert?.is_false_positive === 1 || alert?.is_false_positive === true
  }

  function notifyNewAlerts(fresh: any[]): void {
    const goToAlerts = () => router.push('/alerts')

    fresh.slice(0, MAX_NOTIFY).forEach((alert) => {
      const value = Number(alert.value)
      const threshold = Number(alert.threshold)
      const over = Number.isFinite(value) && Number.isFinite(threshold) && value >= threshold
      ElNotification({
        title: `新告警 · ${alert.node || '未知节点'}`,
        message: `${alert.resource || '资源'} ${alert.value ?? '-'}% / 阈值 ${alert.threshold ?? '-'}%`,
        type: over ? 'error' : 'warning',
        duration: 8000,
        position: 'bottom-right',
        onClick: goToAlerts,
      })
    })

    if (fresh.length > MAX_NOTIFY) {
      ElNotification({
        title: '新告警',
        message: `另有 ${fresh.length - MAX_NOTIFY} 条新告警，点击查看全部`,
        type: 'warning',
        duration: 8000,
        position: 'bottom-right',
        onClick: goToAlerts,
      })
    }
  }

  /**
   * 拉取一次未处理告警
   * @param notify 是否允许对"新增"告警弹提醒（首次调用只建立基线，不提醒）
   */
  async function fetchOnce(notify = true): Promise<void> {
    if (inFlight) return
    inFlight = true
    try {
      const data: any = await getAlerts(200, 'OPEN', true)
      const list = (Array.isArray(data) ? data : []).filter((a) => !isFalsePositive(a))

      openAlerts.value = list
      lastUpdated.value = Date.now()
      lastError.value = ''

      const ids = new Set<number>(list.map(idOf))
      if (knownIds === null) {
        // 首次：只记录基线，历史告警不提醒
        knownIds = ids
      } else {
        const fresh = list.filter((a) => !knownIds!.has(idOf(a)))
        knownIds = ids
        if (
          fresh.length > 0 &&
          notify &&
          notifyEnabled.value &&
          typeof document !== 'undefined' &&
          document.visibilityState === 'visible'
        ) {
          notifyNewAlerts(fresh)
        }
      }
    } catch (e: any) {
      // 静默失败：只在顶栏做降级展示，不打断用户
      lastError.value = e?.response?.data?.detail || e?.message || '无法获取告警数据'
    } finally {
      inFlight = false
    }
  }

  function onVisibilityChange(): void {
    // 页面重新可见时立即刷新一次，避免切回来角标是旧的
    if (document.visibilityState === 'visible') fetchOnce(true)
  }

  /** 开始轮询（进入工作台时调用） */
  function start(): void {
    if (timer !== undefined) return
    polling.value = true
    fetchOnce(false)
    timer = window.setInterval(() => {
      if (document.visibilityState === 'hidden') return
      fetchOnce(true)
    }, POLL_INTERVAL)
    document.addEventListener('visibilitychange', onVisibilityChange)
  }

  /** 停止轮询（离开工作台 / 退出登录时调用） */
  function stop(): void {
    if (timer !== undefined) {
      clearInterval(timer)
      timer = undefined
    }
    polling.value = false
    document.removeEventListener('visibilitychange', onVisibilityChange)
  }

  /** 清空状态（退出登录时调用，避免下一个用户看到上一个用户的角标） */
  function reset(): void {
    stop()
    knownIds = null
    openAlerts.value = []
    lastUpdated.value = 0
    lastError.value = ''
  }

  /** 手动刷新（页面内的操作会调用它，比如标记解决后）：只更新角标，不弹提醒 */
  async function refresh(): Promise<void> {
    await fetchOnce(false)
  }

  function setNotifyEnabled(enabled: boolean): void {
    notifyEnabled.value = enabled
    localStorage.setItem(NOTIFY_KEY, enabled ? '1' : '0')
    ElMessage.success(enabled ? '已开启新告警提醒' : '已关闭新告警提醒')
  }

  return {
    openAlerts,
    unhandledCount,
    notifyEnabled,
    polling,
    lastUpdated,
    lastError,
    degraded,
    start,
    stop,
    reset,
    refresh,
    fetchOnce,
    setNotifyEnabled,
  }
})
