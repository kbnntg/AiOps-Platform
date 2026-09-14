import {
  MAX_GIF_ANIMATION_SIZE,
  MAX_IMAGE_SIDE,
  MAX_STORED_SIZE,
} from '@/config/appearance'

/** 把文件读成 data URL */
export function readAsDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(reader.error || new Error('读取文件失败'))
    reader.readAsDataURL(file)
  })
}

/** 加载图片（用于取原始尺寸） */
export function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('图片解析失败'))
    img.src = src
  })
}

/** data URL 的近似字节大小 */
export function dataUrlSize(dataUrl: string): number {
  const idx = dataUrl.indexOf(',')
  const body = idx >= 0 ? dataUrl.slice(idx + 1) : dataUrl
  // base64 为 4/3 膨胀
  return Math.floor((body.length * 3) / 4)
}

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

interface DecodedImage {
  source: CanvasImageSource
  width: number
  height: number
  release: () => void
}

/**
 * 解码图片，优先使用 createImageBitmap：
 * - 直接解析 File，不需要先转成 base64（大图可省下上百 MB 的临时字符串）
 * - 按 EXIF 方向解码，手机竖拍的照片不会横过来
 * 失败时依次回退到 object URL 与 data URL。
 */
async function decodeImage(file: File): Promise<DecodedImage> {
  if (typeof createImageBitmap === 'function') {
    try {
      const bitmap = await createImageBitmap(file, {
        imageOrientation: 'from-image',
      } as ImageBitmapOptions)
      return {
        source: bitmap,
        width: bitmap.width,
        height: bitmap.height,
        release: () => bitmap.close?.(),
      }
    } catch {
      /* 回退到下一种方式 */
    }
  }

  let objectUrl = ''
  try {
    objectUrl = URL.createObjectURL(file)
    const img = await loadImage(objectUrl)
    return {
      source: img,
      width: img.naturalWidth || img.width,
      height: img.naturalHeight || img.height,
      release: () => URL.revokeObjectURL(objectUrl),
    }
  } catch {
    if (objectUrl) URL.revokeObjectURL(objectUrl)
  }

  const raw = await readAsDataURL(file)
  const img = await loadImage(raw)
  return {
    source: img,
    width: img.naturalWidth || img.width,
    height: img.naturalHeight || img.height,
    release: () => {},
  }
}

/**
 * 压缩图片为 data URL，降低 localStorage 压力。
 * - 超过 MAX_IMAGE_SIDE 时等比缩放（工作面板最大也就 1920px 宽）
 * - 逐步降低 JPEG 质量直到小于 MAX_STORED_SIZE
 * - 小体积 GIF 保留动图原图；无法解码时回退为原图 data URL
 */
export async function compressImage(file: File): Promise<string> {
  const isGif = file.type === 'image/gif'
  if (isGif && file.size <= MAX_GIF_ANIMATION_SIZE) return readAsDataURL(file)

  let decoded: DecodedImage
  try {
    decoded = await decodeImage(file)
  } catch {
    return readAsDataURL(file)
  }

  try {
    const { source, width, height } = decoded
    if (!width || !height) return await readAsDataURL(file)

    const scale = Math.min(1, MAX_IMAGE_SIDE / Math.max(width, height))
    const targetWidth = Math.max(1, Math.round(width * scale))
    const targetHeight = Math.max(1, Math.round(height * scale))

    const canvas = document.createElement('canvas')
    canvas.width = targetWidth
    canvas.height = targetHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return await readAsDataURL(file)

    // JPEG 不支持透明通道，先铺白底避免透明区域变黑
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, targetWidth, targetHeight)
    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = 'high'
    ctx.drawImage(source, 0, 0, targetWidth, targetHeight)

    const qualities = [0.86, 0.78, 0.68, 0.55, 0.45]
    let best = ''
    for (const quality of qualities) {
      best = canvas.toDataURL('image/jpeg', quality)
      if (dataUrlSize(best) <= MAX_STORED_SIZE) return best
    }
    // 仍超出软上限时返回最小的那一版（写入时若超出 localStorage 配额会再提示）
    return best
  } finally {
    decoded.release()
  }
}
