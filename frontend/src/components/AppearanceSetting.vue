<template>
  <el-drawer
    v-model="visible"
    title="外观设置"
    :size="drawerSize"
    append-to-body
    class="appearance-drawer"
  >
    <div class="setting-body">
      <!-- 背景模式 -->
      <section class="block">
        <h4 class="block-title">背景模式</h4>
        <el-radio-group v-model="mode" class="mode-group">
          <el-radio-button value="default">默认</el-radio-button>
          <el-radio-button value="gradient">渐变预设</el-radio-button>
          <el-radio-button value="image">自定义图片</el-radio-button>
        </el-radio-group>
      </section>

      <!-- 渐变预设 -->
      <section v-if="mode === 'gradient'" class="block">
        <h4 class="block-title">选择一个预设</h4>
        <div class="preset-grid">
          <div
            v-for="p in GRADIENT_PRESETS"
            :key="p.id"
            class="preset"
            :class="{ active: config.gradientId === p.id }"
            :style="{ background: p.css }"
            @click="store.setGradient(p.id)"
          >
            <span class="preset-name">{{ p.name }}</span>
            <el-icon v-if="config.gradientId === p.id" class="preset-check"><Check /></el-icon>
          </div>
        </div>
      </section>

      <!-- 自定义图片 -->
      <section v-if="mode === 'image'" class="block">
        <h4 class="block-title">上传本地图片</h4>
        <el-upload
          ref="uploadRef"
          class="uploader"
          drag
          :auto-upload="false"
          :show-file-list="false"
          :accept="IMAGE_ACCEPT"
          :on-change="onFileChange"
        >
          <el-icon class="uploader-icon"><UploadFilled /></el-icon>
          <div class="uploader-text">将图片拖到此处，或<em>点击选择</em></div>
          <div class="uploader-hint">支持 JPG / PNG / WebP / GIF / BMP，单张不超过 100MB</div>
        </el-upload>

        <div v-loading="processing" element-loading-text="正在处理图片…" class="url-row-wrap">
          <div class="url-row">
            <el-input
              v-model="urlInput"
              placeholder="或粘贴图片网络地址 https://…"
              clearable
              @keyup.enter="applyUrl"
            />
            <el-button type="primary" :disabled="!urlInput.trim()" @click="applyUrl">使用</el-button>
          </div>
        </div>

        <p class="hint">
          超大图片（几十 MB）会先自动压缩到 1920px 以内再使用，处理需要几秒；图片仅保存在本机浏览器（localStorage），不会上传到服务器。
          若压缩后仍超出浏览器本地存储上限（约 5MB），背景只在本次会话生效。
        </p>

        <div v-if="store.isImage" class="current-image">
          <img class="current-thumb" :src="config.image" alt="当前背景" />
          <div class="current-meta">
            <div class="current-title">当前背景</div>
            <div class="current-size">{{ imageSizeText }}</div>
            <div class="current-ops">
              <el-button link type="primary" @click="pickFile">更换</el-button>
              <el-button link type="danger" @click="clearImage">移除</el-button>
            </div>
          </div>
        </div>
        <input ref="fileRef" type="file" class="hidden-input" :accept="IMAGE_ACCEPT" @change="onNativePick" />
      </section>

      <!-- 效果调整 -->
      <section v-if="mode !== 'default'" class="block">
        <h4 class="block-title">效果调整</h4>

        <div class="field">
          <span class="field-label">遮罩浓度</span>
          <el-slider v-model="overlay" :min="0" :max="95" :show-tooltip="false" class="field-control" />
          <span class="field-value">{{ overlay }}%</span>
        </div>

        <div class="field">
          <span class="field-label">背景模糊</span>
          <el-slider v-model="blur" :min="0" :max="24" :show-tooltip="false" class="field-control" />
          <span class="field-value">{{ blur }}px</span>
        </div>

        <div v-if="mode === 'image'" class="field">
          <span class="field-label">填充方式</span>
          <el-radio-group v-model="fit" size="small" class="field-control">
            <el-radio-button value="cover">铺满</el-radio-button>
            <el-radio-button value="contain">完整显示</el-radio-button>
            <el-radio-button value="repeat">平铺</el-radio-button>
          </el-radio-group>
        </div>

        <div class="field">
          <span class="field-label">遮罩色调</span>
          <el-radio-group v-model="tone" size="small" class="field-control">
            <el-radio-button value="light">浅色</el-radio-button>
            <el-radio-button value="dark">深色</el-radio-button>
          </el-radio-group>
        </div>

        <p class="hint">遮罩越浓、背景越柔和，卡片与图表文字越清晰。</p>
      </section>

      <!-- 实时预览 -->
      <section class="block">
        <h4 class="block-title">实时预览</h4>
        <div class="preview" :class="{ 'is-default': !store.hasBackground }">
          <div v-if="store.hasBackground" class="preview-bg" :style="store.backgroundStyle"></div>
          <div v-if="store.hasBackground" class="preview-mask" :style="store.overlayStyle"></div>
          <div class="preview-card">
            <div class="preview-title">资源总览</div>
            <div class="preview-line w80"></div>
            <div class="preview-line w55"></div>
            <div class="preview-bar"><span></span></div>
          </div>
        </div>
      </section>

      <el-alert
        v-if="store.storageError"
        class="storage-alert"
        type="warning"
        :closable="false"
        show-icon
        :title="store.storageError"
      />

      <div class="actions">
        <el-button @click="handleReset">恢复默认背景</el-button>
        <el-button type="primary" @click="visible = false">完成</el-button>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { storeToRefs } from 'pinia'
import { useAppearanceStore } from '@/stores/appearance'
import {
  GRADIENT_PRESETS,
  IMAGE_ACCEPT,
  MAX_UPLOAD_SIZE,
  type BackgroundFit,
  type BackgroundType,
  type MaskTone,
} from '@/config/appearance'
import { compressImage, dataUrlSize, formatSize } from '@/utils/imageFile'

const store = useAppearanceStore()
const { config } = storeToRefs(store)

const { drawerVisible: visible } = storeToRefs(store)

const uploadRef = ref()
const fileRef = ref<HTMLInputElement>()
const urlInput = ref('')
const processing = ref(false)
const drawerSize = ref(window.innerWidth < 768 ? '100%' : '440px')

function syncDrawerSize() {
  drawerSize.value = window.innerWidth < 768 ? '100%' : '440px'
}

onMounted(() => window.addEventListener('resize', syncDrawerSize))
onBeforeUnmount(() => window.removeEventListener('resize', syncDrawerSize))

const mode = computed<BackgroundType>({
  get: () => config.value.type,
  set: (v) => {
    // 选图片但还没有图片时，先停在图片面板等待用户选择
    if (v === 'image' && !config.value.image) {
      store.update({ type: 'image' }, false)
      return
    }
    store.setType(v)
  },
})

const overlay = computed({
  get: () => Math.round(config.value.overlay),
  set: (v: number) => store.setOverlay(v),
})

const blur = computed({
  get: () => Math.round(config.value.blur),
  set: (v: number) => store.setBlur(v),
})

const fit = computed<BackgroundFit>({
  get: () => config.value.fit,
  set: (v) => store.setFit(v),
})

const tone = computed<MaskTone>({
  get: () => config.value.tone,
  set: (v) => store.setTone(v),
})

const imageSizeText = computed(() => {
  const img = config.value.image
  if (!img) return ''
  if (img.startsWith('data:')) return `约 ${formatSize(dataUrlSize(img))}`
  return '网络图片地址'
})

function pickFile() {
  fileRef.value?.click()
}

function onNativePick(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) handleFile(file)
  input.value = ''
}

function onFileChange(uploadFile: any) {
  const raw: File | undefined = uploadFile?.raw
  uploadRef.value?.clearFiles?.()
  if (raw) handleFile(raw)
}

async function handleFile(file: File) {
  if (!file.type.startsWith('image/')) {
    ElMessage.error('请选择图片文件')
    return
  }
  if (file.size > MAX_UPLOAD_SIZE) {
    ElMessage.error(`图片过大（${formatSize(file.size)}），请选择小于 ${formatSize(MAX_UPLOAD_SIZE)} 的图片`)
    return
  }
  processing.value = true
  const started = Date.now()
  try {
    const dataUrl = await compressImage(file)
    store.setImage(dataUrl)
    if (store.storageError) {
      // 压缩后仍放不进 localStorage：本次会话可正常预览
      ElMessage.warning(store.storageError)
      return
    }
    const cost = ((Date.now() - started) / 1000).toFixed(1)
    ElMessage.success(
      `背景已更新：${formatSize(file.size)} → ${formatSize(dataUrlSize(dataUrl))}（耗时 ${cost}s）`
    )
  } catch (e) {
    ElMessage.error('图片处理失败，请换一张图片试试')
  } finally {
    processing.value = false
  }
}

function applyUrl() {
  const url = urlInput.value.trim()
  if (!/^(https?:)?\/\//i.test(url) && !url.startsWith('data:image/')) {
    ElMessage.error('请输入以 http(s):// 开头的图片地址')
    return
  }
  store.setImage(url)
  ElMessage.success('背景已更新')
}

function clearImage() {
  urlInput.value = ''
  store.setImage('')
  store.update({ type: 'default' })
}

function handleReset() {
  store.reset()
  urlInput.value = ''
  ElMessage.success('已恢复默认背景')
}
</script>

<style scoped>
.setting-body {
  padding: 0 4px 24px;
}

.block {
  margin-bottom: 22px;
}

.block-title {
  margin: 0 0 12px;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  letter-spacing: 0.3px;
}

.mode-group {
  width: 100%;
  display: flex;
}
.mode-group :deep(.el-radio-button) { flex: 1; }
.mode-group :deep(.el-radio-button__inner) { width: 100%; }

/* ===== 预设网格 ===== */
.preset-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.preset {
  position: relative;
  height: 62px;
  border-radius: 10px;
  cursor: pointer;
  overflow: hidden;
  display: flex;
  align-items: flex-end;
  padding: 6px 8px;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.25);
  transition: transform 0.2s, box-shadow 0.2s;
}
.preset:hover { transform: translateY(-2px); }
.preset.active {
  box-shadow: 0 0 0 2px #6366f1, 0 6px 16px rgba(99, 102, 241, 0.35);
}
.preset-name {
  font-size: 11px;
  color: #fff;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.55);
}
.preset-check {
  position: absolute;
  top: 4px;
  right: 4px;
  color: #fff;
  font-size: 14px;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.6);
}

/* ===== 上传 ===== */
.uploader { width: 100%; }
.uploader :deep(.el-upload) { width: 100%; }
.uploader :deep(.el-upload-dragger) {
  width: 100%;
  padding: 22px 12px;
  border-radius: 12px;
}
.uploader-icon {
  font-size: 34px;
  color: #a5b4fc;
  margin-bottom: 6px;
}
.uploader-text {
  font-size: 13px;
  color: #64748b;
}
.uploader-text em {
  color: var(--primary);
  font-style: normal;
  font-weight: 600;
}
.uploader-hint {
  margin-top: 4px;
  font-size: 11px;
  color: #94a3b8;
}

.url-row-wrap { margin-top: 12px; }
.url-row { display: flex; gap: 8px; }

.hint {
  margin: 10px 0 0;
  font-size: 11px;
  line-height: 1.6;
  color: #94a3b8;
}

/* ===== 当前图片 ===== */
.current-image {
  margin-top: 14px;
  display: flex;
  gap: 12px;
  padding: 10px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}
.current-thumb {
  width: 92px;
  height: 60px;
  object-fit: cover;
  border-radius: 8px;
  flex-shrink: 0;
}
.current-meta { flex: 1; min-width: 0; }
.current-title { font-size: 13px; font-weight: 600; color: #1e293b; }
.current-size { font-size: 11px; color: #94a3b8; margin-top: 2px; }
.current-ops { margin-top: 2px; }
.hidden-input { display: none; }

/* ===== 参数调节 ===== */
.field {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.field-label {
  width: 64px;
  flex-shrink: 0;
  font-size: 12px;
  color: #64748b;
}
.field-control { flex: 1; min-width: 0; }
.field-value {
  width: 44px;
  text-align: right;
  font-size: 12px;
  color: #1e293b;
  font-variant-numeric: tabular-nums;
}

/* ===== 预览 ===== */
.preview {
  position: relative;
  height: 150px;
  border-radius: 12px;
  overflow: hidden;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}
.preview-bg {
  position: absolute;
  inset: 0;
  background-position: center;
  background-repeat: no-repeat;
  background-size: cover;
}
.preview-mask { position: absolute; inset: 0; }
.preview-card {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 12px;
  padding: 12px;
  border-radius: 10px;
  background: var(--app-card-bg, rgba(255, 255, 255, 0.86));
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.12);
}
.preview-title {
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 8px;
}
.preview-line {
  height: 6px;
  border-radius: 3px;
  background: rgba(148, 163, 184, 0.35);
  margin-bottom: 6px;
}
.preview-line.w80 { width: 80%; }
.preview-line.w55 { width: 55%; }
.preview-bar {
  height: 6px;
  border-radius: 3px;
  background: rgba(99, 102, 241, 0.18);
  overflow: hidden;
}
.preview-bar span {
  display: block;
  width: 62%;
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #a855f7);
}

.storage-alert { margin-bottom: 14px; }

.actions {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding-top: 4px;
}
</style>
