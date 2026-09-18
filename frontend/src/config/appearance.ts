/**
 * 工作面板外观（背景）相关配置
 */

/** 背景类型 */
export type BackgroundType = 'default' | 'gradient' | 'image'

/** 图片填充方式 */
export type BackgroundFit = 'cover' | 'contain' | 'repeat'

/** 遮罩色调 */
export type MaskTone = 'light' | 'dark'

/** 外观配置 */
export interface AppearanceConfig {
  type: BackgroundType
  /** 渐变预设 id */
  gradientId: string
  /** 自定义图片（data URL 或网络地址） */
  image: string
  /** 遮罩浓度 0 - 95 */
  overlay: number
  /** 背景模糊半径(px) 0 - 24 */
  blur: number
  /** 图片填充方式 */
  fit: BackgroundFit
  /** 遮罩色调 */
  tone: MaskTone
}

/** 渐变 / 纯色预设背景 */
export interface BackgroundPreset {
  id: string
  name: string
  /** 缩略图预览用的 css background */
  css: string
}

export const GRADIENT_PRESETS: BackgroundPreset[] = [
  { id: 'aurora', name: '极光', css: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' },
  { id: 'dawn', name: '晨曦', css: 'linear-gradient(135deg, #f6d365 0%, #fda085 100%)' },
  { id: 'ocean', name: '深海', css: 'linear-gradient(135deg, #2b5876 0%, #4e4376 100%)' },
  { id: 'mint', name: '薄荷', css: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)' },
  { id: 'sakura', name: '樱花', css: 'linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)' },
  { id: 'night', name: '夜空', css: 'linear-gradient(135deg, #0f172a 0%, #312e81 50%, #4c1d95 100%)' },
  { id: 'sunset', name: '落日', css: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)' },
  { id: 'sky', name: '晴空', css: 'linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 100%)' },
  { id: 'forest', name: '森野', css: 'linear-gradient(135deg, #134e5e 0%, #71b280 100%)' },
  { id: 'steel', name: '钢铁', css: 'linear-gradient(135deg, #e0eafc 0%, #cfdef3 100%)' },
  { id: 'violet', name: '紫罗兰', css: 'radial-gradient(circle at 20% 20%, #8b5cf6 0%, #1e1b4b 60%)' },
  { id: 'slate', name: '石墨', css: 'linear-gradient(135deg, #232526 0%, #414345 100%)' },
]

export const DEFAULT_APPEARANCE: AppearanceConfig = {
  type: 'default',
  gradientId: GRADIENT_PRESETS[0].id,
  image: '',
  overlay: 60,
  blur: 0,
  fit: 'cover',
  tone: 'light',
}

/** 单张图片上传上限（原始文件） */
export const MAX_UPLOAD_SIZE = 100 * 1024 * 1024
/** 压缩后写入 localStorage 的软上限，超过则继续降质量（localStorage 配额约 5MB） */
export const MAX_STORED_SIZE = 2.2 * 1024 * 1024
/** GIF 小于该体积时保留原图（动图），超出则压缩为静态帧 */
export const MAX_GIF_ANIMATION_SIZE = 8 * 1024 * 1024
/** 压缩后的最大边长 */
export const MAX_IMAGE_SIDE = 1920

export const IMAGE_ACCEPT = 'image/png,image/jpeg,image/webp,image/gif,image/bmp,image/avif'

/** 取得预设背景的 css，未知 id 回退到默认预设 */
export function getGradientCss(id: string): string {
  return (GRADIENT_PRESETS.find(p => p.id === id) || GRADIENT_PRESETS[0]).css
}
