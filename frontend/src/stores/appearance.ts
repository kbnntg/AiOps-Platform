import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  DEFAULT_APPEARANCE,
  getGradientCss,
  type AppearanceConfig,
  type BackgroundFit,
  type BackgroundType,
  type MaskTone,
} from '@/config/appearance'
import { dataUrlSize, formatSize } from '@/utils/imageFile'

const STORAGE_PREFIX = 'appearance:'
const HTML_CLASS = 'has-custom-bg'

function storageKey(user: string) {
  return STORAGE_PREFIX + (user || 'guest')
}

function sanitize(raw: any): AppearanceConfig {
  const base: AppearanceConfig = { ...DEFAULT_APPEARANCE }
  if (!raw || typeof raw !== 'object') return base

  if (raw.type === 'gradient' || raw.type === 'image' || raw.type === 'default') base.type = raw.type
  if (typeof raw.gradientId === 'string' && raw.gradientId) base.gradientId = raw.gradientId
  if (typeof raw.image === 'string') base.image = raw.image
  if (typeof raw.overlay === 'number' && isFinite(raw.overlay)) base.overlay = clamp(raw.overlay, 0, 95)
  if (typeof raw.blur === 'number' && isFinite(raw.blur)) base.blur = clamp(raw.blur, 0, 24)
  if (raw.fit === 'cover' || raw.fit === 'contain' || raw.fit === 'repeat') base.fit = raw.fit
  if (raw.tone === 'light' || raw.tone === 'dark') base.tone = raw.tone

  // 说明：图片模式下尚未选择图片时保留 type，方便用户停留在上传面板；
  // 是否真正显示背景由 hasBackground 判定（无图片即不生效）。
  return base
}

function clamp(v: number, min: number, max: number) {
  return Math.min(max, Math.max(min, v))
}

export const useAppearanceStore = defineStore('appearance', () => {
  const config = ref<AppearanceConfig>({ ...DEFAULT_APPEARANCE })
  const user = ref('guest')
  const drawerVisible = ref(false)
  /** localStorage 写入失败（配额不足）时的提示，供界面展示 */
  const storageError = ref('')

  /** 是否启用了自定义背景（渐变或图片） */
  const hasBackground = computed(
    () => config.value.type !== 'default' && (config.value.type === 'gradient' || !!config.value.image)
  )

  const isImage = computed(() => config.value.type === 'image' && !!config.value.image)

  /** 背景图层样式 */
  const backgroundStyle = computed(() => {
    const c = config.value
    const style: Record<string, string> = {}
    if (!hasBackground.value) return style

    if (c.type === 'gradient') {
      style.backgroundImage = getGradientCss(c.gradientId)
      style.backgroundSize = 'cover'
      style.backgroundPosition = 'center'
      style.backgroundRepeat = 'no-repeat'
    } else {
      style.backgroundImage = `url("${c.image}")`
      if (c.fit === 'repeat') {
        style.backgroundSize = 'auto'
        style.backgroundRepeat = 'repeat'
        style.backgroundPosition = 'top left'
      } else {
        style.backgroundSize = c.fit
        style.backgroundRepeat = 'no-repeat'
        style.backgroundPosition = 'center'
      }
    }

    if (c.blur > 0) {
      style.filter = `blur(${c.blur}px)`
      // 模糊会在边缘产生透明描边，放大一点盖住
      style.transform = `scale(${1 + c.blur / 60})`
    }
    return style
  })

  /** 遮罩层样式 */
  const overlayStyle = computed(() => {
    const ratio = clamp(config.value.overlay, 0, 95) / 100
    const rgb = config.value.tone === 'dark' ? '15, 23, 42' : '248, 250, 252'
    return { background: `rgba(${rgb}, ${ratio})` }
  })

  /** 卡片背景变量：跟随遮罩浓度，图片越清晰卡片越实，保证文字可读 */
  const cardBg = computed(() => {
    const tone = config.value.tone
    const solid = tone === 'dark' ? 0.9 : 0.86
    return `rgba(255, 255, 255, ${solid})`
  })

  const cardBgSolid = computed(() => 'rgba(255, 255, 255, 0.95)')

  function applyToDocument() {
    if (typeof document === 'undefined') return
    const root = document.documentElement
    root.classList.toggle(HTML_CLASS, hasBackground.value)
    root.style.setProperty('--app-card-bg', cardBg.value)
    root.style.setProperty('--app-card-bg-solid', cardBgSolid.value)
  }

  function persist() {
    storageError.value = ''
    try {
      localStorage.setItem(storageKey(user.value), JSON.stringify(config.value))
    } catch (e) {
      const size = config.value.image && config.value.image.startsWith('data:')
        ? dataUrlSize(config.value.image)
        : 0
      storageError.value = size
        ? `背景图片压缩后仍约 ${formatSize(size)}，超出浏览器本地存储上限，本次会话仍正常显示，但刷新后需重新选择图片`
        : '浏览器本地存储空间不足，外观设置仅本次会话生效'
      // 退而求其次：只保存外观参数，省略图片数据，避免下次读取时解析失败
      try {
        localStorage.setItem(
          storageKey(user.value),
          JSON.stringify({ ...config.value, image: '', type: config.value.type === 'image' ? 'default' : config.value.type })
        )
      } catch {
        /* ignore */
      }
    }
  }

  /** 连续拖动滑块时合并写入，避免每次都序列化整张背景图 */
  let saveTimer: number | undefined

  function persistSoon() {
    if (saveTimer !== undefined) clearTimeout(saveTimer)
    saveTimer = window.setTimeout(() => {
      saveTimer = undefined
      persist()
    }, 300)
  }

  function persistNow() {
    if (saveTimer !== undefined) {
      clearTimeout(saveTimer)
      saveTimer = undefined
    }
    persist()
  }

  /** 离开工作面板时移除全局副作用（配置仍保留在本地存储中） */
  function clearDocumentEffect() {
    if (saveTimer !== undefined) persistNow()
    if (typeof document === 'undefined') return
    const root = document.documentElement
    root.classList.remove(HTML_CLASS)
    root.style.removeProperty('--app-card-bg')
    root.style.removeProperty('--app-card-bg-solid')
  }

  /** 切换用户 / 启动时载入配置 */
  function init(name: string) {
    user.value = name || 'guest'
    try {
      const raw = localStorage.getItem(storageKey(user.value))
      config.value = raw ? sanitize(JSON.parse(raw)) : { ...DEFAULT_APPEARANCE }
    } catch {
      config.value = { ...DEFAULT_APPEARANCE }
    }
    applyToDocument()
  }

  function update(patch: Partial<AppearanceConfig>, save: boolean | 'now' = true) {
    config.value = sanitize({ ...config.value, ...patch })
    applyToDocument()
    if (save === 'now') persistNow()
    else if (save) persistSoon()
  }

  function setType(type: BackgroundType) {
    update({ type })
  }

  function setGradient(gradientId: string) {
    update({ gradientId, type: 'gradient' }, 'now')
  }

  function setImage(image: string) {
    update({ image, type: image ? 'image' : 'default' }, 'now')
  }

  function setOverlay(overlay: number) {
    update({ overlay })
  }

  function setBlur(blur: number) {
    update({ blur })
  }

  function setFit(fit: BackgroundFit) {
    update({ fit })
  }

  function setTone(tone: MaskTone) {
    update({ tone })
  }

  function reset() {
    config.value = { ...DEFAULT_APPEARANCE }
    applyToDocument()
    persistNow()
  }

  function openDrawer() {
    drawerVisible.value = true
  }

  function closeDrawer() {
    drawerVisible.value = false
  }

  return {
    config,
    user,
    drawerVisible,
    storageError,
    hasBackground,
    isImage,
    backgroundStyle,
    overlayStyle,
    cardBg,
    cardBgSolid,
    init,
    update,
    setType,
    setGradient,
    setImage,
    setOverlay,
    setBlur,
    setFit,
    setTone,
    reset,
    applyToDocument,
    clearDocumentEffect,
    openDrawer,
    closeDrawer,
  }
})
