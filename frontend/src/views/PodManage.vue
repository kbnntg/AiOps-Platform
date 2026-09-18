<template>
  <div class="pod-manage">
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <el-select v-model="ns" style="width:200px" @change="loadPods">
          <el-option v-for="n in namespaces" :key="n" :label="n" :value="n" />
        </el-select>
        <el-input v-model="kw" placeholder="搜索 Pod" clearable style="width:250px" />
        <el-button type="primary" @click="loadPods">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </el-card>

    <el-card shadow="never" class="mt-4">
      <el-table :data="filtered" border stripe v-loading="loading" empty-text="暂无 Pod">
        <el-table-column prop="name" label="Pod 名称" min-width="240" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="node" label="节点" width="150" />
        <el-table-column prop="ip" label="IP" width="130" />
        <el-table-column label="重启" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.restarts > 0" type="warning" size="small">{{ row.restarts }}</el-tag>
            <span v-else>0</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="360" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="warning" @click="diagnose(row)">
              <el-icon><MagicStick /></el-icon> 诊断
            </el-button>
            <el-button size="small" @click="openLogs(row)">日志</el-button>
            <el-button size="small" type="info" @click="openEvents(row)">事件</el-button>
            <el-button size="small" type="danger" @click="confirmDelete(row)"
                       :disabled="authStore.role !== 'admin'">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 日志弹窗 -->
    <el-dialog v-model="logVisible" :title="`日志: ${logPod}`" width="1000px" top="3vh"
               @close="closeLogs">
      <div class="log-toolbar">
        <el-input-number v-model="tailLines" :min="10" :max="5000" :step="100" size="small" />
        <el-button size="small" @click="loadLogs">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>

        <div class="log-toolbar-right">
          <el-tag :type="wsConnected ? 'success' : 'info'" size="small" effect="dark">
            <el-icon><component :is="wsConnected ? 'VideoPlay' : 'VideoPause'" /></el-icon>
            {{ wsConnected ? '实时接收中' : '已停止' }}
          </el-tag>
          <el-button size="small" type="success" @click="analyzeLogs" :loading="analyzing">
            <el-icon><MagicStick /></el-icon> AI 分析
          </el-button>
          <el-button size="small" type="primary" @click="exportLogs" :disabled="!logs">
            <el-icon><Download /></el-icon> 导出日志
          </el-button>
        </div>
      </div>

      <div class="log-viewer-wrapper">
        <div class="log-viewer" ref="logViewerRef" @scroll="onLogScroll">
          <pre v-if="logs">{{ logs }}</pre>
          <el-empty v-else description="暂无日志" />
        </div>

        <transition name="fade">
          <el-button
            v-show="!autoScroll && logs"
            class="jump-bottom-btn"
            type="primary"
            circle
            @click="jumpToBottom"
          >
            <el-icon><ArrowDown /></el-icon>
          </el-button>
        </transition>
      </div>
    </el-dialog>

    <!-- AI 日志分析结果弹窗 -->
    <el-dialog v-model="aiVisible" title="🤖 AI 日志分析" width="850px" top="5vh">
      <div v-loading="analyzing" element-loading-text="AI 正在分析日志，请稍候..." class="ai-analysis">
        <div v-if="aiAnalysis" v-html="renderMarkdown(aiAnalysis)"></div>
        <el-empty v-else description="暂无分析结果" />
      </div>
      <template #footer>
        <el-button @click="aiVisible = false">关闭</el-button>
        <el-button type="primary" @click="copyAnalysis" :disabled="!aiAnalysis">
          <el-icon><CopyDocument /></el-icon> 复制结果
        </el-button>
      </template>
    </el-dialog>

    <!-- 多信号融合诊断弹窗 -->
    <el-dialog v-model="diagnoseVisible" title="🔬 多信号融合根因诊断" width="900px" top="5vh">
      <div class="signal-bar" v-if="diagnoseSignals">
        <div class="signal-item">
          <span class="signal-label">指标</span>
          <span class="signal-value" :class="diagnoseSignals.metrics === '✓' ? 'ok' : 'fail'">
            {{ diagnoseSignals.metrics }}
          </span>
        </div>
        <div class="signal-item">
          <span class="signal-label">日志</span>
          <span class="signal-value" :class="diagnoseSignals.logs === '✓' ? 'ok' : 'fail'">
            {{ diagnoseSignals.logs }}
          </span>
        </div>
        <div class="signal-item">
          <span class="signal-label">事件</span>
          <span class="signal-value ok">{{ diagnoseSignals.events }} 条</span>
        </div>
        <div class="signal-item">
          <span class="signal-label">告警</span>
          <span class="signal-value ok">{{ diagnoseSignals.alerts }} 条</span>
        </div>
      </div>

      <div v-loading="diagnosing" element-loading-text="AI 正在融合分析四类信号..." class="ai-analysis">
        <div v-if="diagnoseResult" v-html="renderMarkdown(diagnoseResult)"></div>
        <el-empty v-else description="暂无诊断结果" />
      </div>

      <template #footer>
        <el-button @click="diagnoseVisible = false">关闭</el-button>
        <el-button type="primary" @click="copyDiagnose" :disabled="!diagnoseResult">
          <el-icon><CopyDocument /></el-icon> 复制结果
        </el-button>
      </template>
    </el-dialog>

    <!-- 事件弹窗 -->
    <el-dialog v-model="eventVisible" :title="`事件: ${eventPod}`" width="700px">
      <el-timeline>
        <el-timeline-item v-for="(e,i) in events" :key="i"
                          :type="e.type==='Warning'?'danger':'success'" :timestamp="e.time">
          <strong>{{ e.reason }}</strong> — {{ e.message }}
        </el-timeline-item>
      </el-timeline>
      <el-empty v-if="events.length===0" description="暂无事件" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getPods, getPodLogs, getPodEvents, deletePod,
  analyzePodLogs, diagnosePod,
} from '@/api/pods'
import { getNamespaces } from '@/api/metrics'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const ns = ref('privatization')
const namespaces = ref<string[]>([])
const pods = ref<any[]>([])
const kw = ref('')
const loading = ref(false)

const logVisible = ref(false)
const logPod = ref('')
const logs = ref('')
const tailLines = ref(200)
const logViewerRef = ref<HTMLDivElement>()
const wsConnected = ref(false)
const autoScroll = ref(true)

const eventVisible = ref(false)
const eventPod = ref('')
const events = ref<any[]>([])

// AI 日志分析
const analyzing = ref(false)
const aiVisible = ref(false)
const aiAnalysis = ref('')

// 多信号诊断
const diagnosing = ref(false)
const diagnoseVisible = ref(false)
const diagnoseResult = ref('')
const diagnoseSignals = ref<any>(null)

let ws: WebSocket | null = null

const filtered = computed(() =>
  kw.value ? pods.value.filter(p => p.name.includes(kw.value)) : pods.value
)

async function loadNamespaces() { namespaces.value = await getNamespaces() as any }

async function loadPods() {
  loading.value = true
  try { pods.value = await getPods(ns.value) as any }
  catch (e) { pods.value = [] }
  finally { loading.value = false }
}

// ========== 日志 ==========
async function loadLogs() {
  try {
    const d: any = await getPodLogs(ns.value, logPod.value, tailLines.value)
    logs.value = d.logs || ''
    autoScroll.value = true
    scrollToBottom()
  } catch (e) {
    logs.value = '获取日志失败'
  }
}

async function openLogs(row: any) {
  logPod.value = row.name
  logs.value = ''
  autoScroll.value = true
  logVisible.value = true
  await loadLogs()
  connectWs()
}

function connectWs() {
  const token = localStorage.getItem('token')
  if (!token) return

  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const url = `${proto}://${location.host}/api/ws/pods/${ns.value}/${logPod.value}/logs?token=${token}&tail_lines=50`

  ws = new WebSocket(url)

  ws.onopen = () => {
    wsConnected.value = true
    logs.value += '\n--- 实时日志流已连接 ---\n'
  }

  ws.onmessage = (event) => {
    logs.value += event.data
    scrollToBottom()
  }

  ws.onerror = () => {
    logs.value += '\n[ERROR] WebSocket 连接失败\n'
  }

  ws.onclose = () => {
    wsConnected.value = false
    logs.value += '\n--- 实时日志流已断开 ---\n'
  }
}

function closeLogs() {
  if (ws) {
    ws.close()
    ws = null
  }
  wsConnected.value = false
}

// ========== 自动滚动 ==========
function onLogScroll() {
  if (!logViewerRef.value) return
  const el = logViewerRef.value
  const threshold = 30
  autoScroll.value = el.scrollTop + el.clientHeight >= el.scrollHeight - threshold
}

function scrollToBottom() {
  if (!autoScroll.value) return
  nextTick(() => {
    if (logViewerRef.value) {
      logViewerRef.value.scrollTop = logViewerRef.value.scrollHeight
    }
  })
}

function jumpToBottom() {
  if (logViewerRef.value) {
    logViewerRef.value.scrollTop = logViewerRef.value.scrollHeight
    autoScroll.value = true
  }
}

// ========== 导出日志 ==========
function exportLogs() {
  if (!logs.value) {
    ElMessage.warning('没有日志可导出')
    return
  }
  const blob = new Blob([logs.value], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  a.download = `${ns.value}-${logPod.value}-${ts}.log`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success('日志已导出')
}

// ========== AI 日志分析 ==========
async function analyzeLogs() {
  if (!logPod.value) return
  analyzing.value = true
  aiVisible.value = true
  aiAnalysis.value = ''
  try {
    const res: any = await analyzePodLogs(ns.value, logPod.value, 500)
    aiAnalysis.value = res.analysis || '分析结果为空'
  } catch (e) {
    aiAnalysis.value = '分析失败，请重试'
  } finally {
    analyzing.value = false
  }
}

function copyAnalysis() {
  navigator.clipboard.writeText(aiAnalysis.value).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

// ========== 多信号融合诊断 ==========
async function diagnose(row: any) {
  diagnosing.value = true
  diagnoseVisible.value = true
  diagnoseResult.value = ''
  diagnoseSignals.value = null
  try {
    const res: any = await diagnosePod(ns.value, row.name)
    diagnoseResult.value = res.analysis || '诊断结果为空'
    diagnoseSignals.value = res.signals || null
  } catch (e) {
    diagnoseResult.value = '诊断失败，请重试'
  } finally {
    diagnosing.value = false
  }
}

function copyDiagnose() {
  navigator.clipboard.writeText(diagnoseResult.value).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

// ========== Markdown 渲染 ==========
function renderMarkdown(text: string): string {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
    .replace(/^## (.*$)/gm, '<h2>$1</h2>')
    .replace(/^# (.*$)/gm, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/^- (.*$)/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br/>')
}

// ========== 事件 ==========
async function openEvents(row: any) {
  eventPod.value = row.name
  events.value = await getPodEvents(ns.value, row.name) as any
  eventVisible.value = true
}

// ========== 删除 ==========
function confirmDelete(row: any) {
  ElMessageBox.confirm(`确定删除 Pod "${row.name}" 吗？`, '危险操作', { type: 'warning' })
    .then(async () => {
      await deletePod(ns.value, row.name)
      ElMessage.success('已删除')
      loadPods()
    }).catch(() => {})
}

function statusType(s: string): string {
  const m: Record<string, string> = {
    Running: 'success', Pending: 'warning', Failed: 'danger',
    Succeeded: 'info', Terminating: 'danger'
  }
  return m[s] || 'info'
}

onMounted(() => { loadNamespaces(); loadPods() })
onUnmounted(() => closeLogs())
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; align-items: center; }
.mt-4 { margin-top: 16px; }

.log-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}
.log-toolbar-right { margin-left: auto; display: flex; gap: 12px; align-items: center; }

.log-viewer-wrapper { position: relative; }

.log-viewer {
  background: #0f172a;
  color: #cbd5e1;
  border-radius: 8px;
  padding: 16px;
  height: 500px;
  overflow: auto;
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
}
.log-viewer pre { margin: 0; white-space: pre-wrap; word-break: break-all; }

.jump-bottom-btn {
  position: absolute;
  bottom: 24px;
  right: 24px;
  z-index: 10;
  width: 40px;
  height: 40px;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.5);
  transition: all 0.25s;
}
.jump-bottom-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.7);
}

/* ========== AI 分析结果 ========== */
.ai-analysis {
  min-height: 200px;
  max-height: 65vh;
  overflow-y: auto;
  padding: 8px 16px;
  line-height: 1.8;
  color: #1e293b;
}
.ai-analysis :deep(h1),
.ai-analysis :deep(h2),
.ai-analysis :deep(h3) {
  color: #4f46e5;
  margin: 16px 0 8px;
  border-left: 4px solid #6366f1;
  padding-left: 10px;
}
.ai-analysis :deep(code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: Consolas, monospace;
  color: #e11d48;
}
.ai-analysis :deep(ul) { padding-left: 24px; }
.ai-analysis :deep(li) { margin: 6px 0; }
.ai-analysis :deep(strong) { color: #6366f1; }

/* ========== 信号状态栏 ========== */
.signal-bar {
  display: flex;
  gap: 24px;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 8px;
  margin-bottom: 16px;
}
.signal-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}
.signal-label { color: #64748b; }
.signal-value { font-weight: 600; }
.signal-value.ok { color: #10b981; }
.signal-value.fail { color: #ef4444; }

/* 淡入淡出 */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s, transform 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(10px); }
</style>
