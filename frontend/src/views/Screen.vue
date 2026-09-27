<template>
  <div class="screen">
    <!-- 顶部标题栏 -->
    <header class="screen-header">
      <div class="header-left">
        <div class="logo">AI</div>
        <div class="title-group">
          <h1>AIOps 智能运维中心</h1>
          <span class="subtitle">Kubernetes Cluster Monitor</span>
        </div>
      </div>
      <div class="header-center">
        <div class="health-score">
          <div class="score-value" :style="{ color: healthColor }">{{ healthScore }}</div>
          <div class="score-label">全局健康分</div>
        </div>
      </div>
      <div class="header-right">
        <div class="clock">
          <div class="time">{{ currentTime }}</div>
          <div class="date">{{ currentDate }}</div>
        </div>
        <div class="header-actions">
          <el-tooltip content="全屏显示 / 退出全屏（F）" placement="bottom">
            <el-icon class="action-btn" @click="toggleFullscreen"><FullScreen /></el-icon>
          </el-tooltip>
          <el-tooltip content="返回工作台（Esc）" placement="bottom">
            <el-icon class="action-btn" @click="exitScreen"><Close /></el-icon>
          </el-tooltip>
        </div>
      </div>
    </header>

    <!-- 主体：三栏布局 -->
    <main class="screen-body">
      <!-- 左侧栏 -->
      <aside class="panel-left">
        <!-- 量化指标 -->
        <div class="panel">
          <div class="panel-title">
            <i></i><span>告警治理</span>
          </div>
          <div class="metrics-grid">
            <div class="metric-item">
              <div class="metric-value">{{ metrics.total_raw || 0 }}</div>
              <div class="metric-label">原始告警</div>
            </div>
            <div class="metric-item">
              <div class="metric-value accent">{{ metrics.compression_rate || 0 }}x</div>
              <div class="metric-label">压缩率</div>
            </div>
            <div class="metric-item">
              <div class="metric-value warning">{{ metrics.false_positive_rate || 0 }}%</div>
              <div class="metric-label">误报率</div>
            </div>
            <div class="metric-item">
              <div class="metric-value success">{{ formatDuration(metrics.mttr_seconds) }}</div>
              <div class="metric-label">MTTR</div>
            </div>
          </div>
        </div>

        <!-- 节点列表 -->
        <div class="panel panel-flex">
          <div class="panel-title">
            <i></i><span>节点状态</span>
          </div>
          <div class="node-list">
            <div v-for="node in nodes" :key="node.name" class="node-item">
              <div class="node-info">
                <div class="node-name">{{ node.name }}</div>
                <div class="node-stats">
                  <span>CPU {{ node.cpu || 0 }}%</span>
                  <span>内存 {{ node.memory || 0 }}%</span>
                </div>
              </div>
              <div class="node-bars">
                <div class="bar">
                  <div class="bar-fill" :style="{ width: (node.cpu || 0) + '%', background: getBarColor(node.cpu) }"></div>
                </div>
                <div class="bar">
                  <div class="bar-fill" :style="{ width: (node.memory || 0) + '%', background: getBarColor(node.memory) }"></div>
                </div>
              </div>
            </div>
            <div v-if="nodes.length === 0" class="empty-tip">暂无节点数据</div>
          </div>
        </div>
      </aside>

      <!-- 中间主区域 -->
      <section class="panel-center">
        <!-- CPU 趋势 -->
        <div class="panel">
          <div class="panel-title">
            <i></i><span>CPU 使用率趋势（最近 1 小时）</span>
          </div>
          <div ref="cpuChartRef" class="chart"></div>
        </div>

        <!-- 内存趋势 -->
        <div class="panel">
          <div class="panel-title">
            <i></i><span>内存使用率趋势（最近 1 小时）</span>
          </div>
          <div ref="memChartRef" class="chart"></div>
        </div>

        <!-- 磁盘趋势 -->
        <div class="panel">
          <div class="panel-title">
            <i></i><span>磁盘使用率趋势（最近 1 小时）</span>
          </div>
          <div ref="diskChartRef" class="chart"></div>
        </div>
      </section>

      <!-- 右侧栏 -->
      <aside class="panel-right">
        <!-- 实时告警 -->
        <div class="panel panel-flex">
          <div class="panel-title">
            <i class="pulse"></i><span>实时告警</span>
          </div>
          <div class="alert-list">
            <div v-for="a in alerts" :key="a.id" class="alert-item">
              <div class="alert-dot" :class="a.status === 'OPEN' ? 'danger' : 'info'"></div>
              <div class="alert-body">
                <div class="alert-line1">
                  <span class="alert-node">{{ a.node }}</span>
                  <span class="alert-resource">{{ a.resource }}</span>
                </div>
                <div class="alert-line2">
                  <span>{{ a.value }}% / 阈值 {{ a.threshold }}%</span>
                  <span class="alert-time">{{ a.triggered_at?.slice(11, 19) }}</span>
                </div>
              </div>
            </div>
            <div v-if="alerts.length === 0" class="empty-tip">暂无告警</div>
          </div>
        </div>

        <!-- 服务拓扑概览 -->
        <div class="panel panel-flex">
          <div class="panel-title">
            <i></i><span>服务概览</span>
          </div>
          <div class="topology-stats">
            <div class="topo-item" v-for="(count, type) in topoStats" :key="type">
              <div class="topo-count">{{ count }}</div>
              <div class="topo-type">{{ type }}</div>
            </div>
          </div>
        </div>
      </aside>
    </main>

    <!-- 底部滚动条 -->
    <footer class="screen-footer">
      <div class="scroll-text">
        <span>{{ scrollText }}</span>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { getNodes, getCpu, getMemory, getDisk } from '@/api/metrics'
import { getAlerts, getAlertMetrics } from '@/api/alerts'
import { getTopology } from '@/api/topology'

const router = useRouter()

const nodes = ref<any[]>([])
const alerts = ref<any[]>([])
const metrics = ref<any>({})
const topoStats = ref<Record<string, number>>({})

const currentTime = ref('')
const currentDate = ref('')

const cpuChartRef = ref<HTMLDivElement>()
const memChartRef = ref<HTMLDivElement>()
const diskChartRef = ref<HTMLDivElement>()
let cpuChart: echarts.ECharts | null = null
let memChart: echarts.ECharts | null = null
let diskChart: echarts.ECharts | null = null

let timer: any = null
let clockTimer: any = null

// ========== 计算属性 ==========
const healthScore = computed(() => {
  if (!nodes.value.length) return 100
  const avgCpu = nodes.value.reduce((s, n) => s + (n.cpu || 0), 0) / nodes.value.length
  const avgMem = nodes.value.reduce((s, n) => s + (n.memory || 0), 0) / nodes.value.length
  const score = Math.max(0, 100 - Math.round((avgCpu + avgMem) / 2))
  return score
})

const healthColor = computed(() => {
  if (healthScore.value >= 80) return '#10b981'
  if (healthScore.value >= 60) return '#f59e0b'
  return '#ef4444'
})

const scrollText = computed(() => {
  const parts = [
    `节点总数：${nodes.value.length}`,
    `告警总数：${metrics.value.total_alerts || 0}`,
    `未处理告警：${alerts.value.filter((a) => a.status === 'OPEN').length}`,
    `系统状态：${healthScore.value >= 80 ? '正常' : healthScore.value >= 60 ? '注意' : '告警'}`,
  ]
  return parts.join('    ·    ')
})

// ========== 工具函数 ==========
function getBarColor(v: number): string {
  if (v > 80) return '#ef4444'
  if (v > 60) return '#f59e0b'
  return '#10b981'
}

function formatDuration(seconds: number): string {
  if (!seconds) return '—'
  if (seconds < 60) return seconds + 's'
  if (seconds < 3600) return Math.round(seconds / 60) + 'min'
  return (seconds / 3600).toFixed(1) + 'h'
}

// ========== 时钟 ==========
function updateClock() {
  const now = new Date()
  currentTime.value = now.toTimeString().slice(0, 8)
  currentDate.value = now.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    weekday: 'short',
  })
}

// ========== 加载数据 ==========
async function loadAll() {
  try {
    const [n, m, a, t] = await Promise.all([
      getNodes(),
      getAlertMetrics(),
      getAlerts(20),
      getTopology('privatization'),
    ])
    nodes.value = n as any
    metrics.value = m
    alerts.value = a as any

    // 统计拓扑节点类型
    const stats: Record<string, number> = {}
    for (const node of (t as any).nodes || []) {
      stats[node.type] = (stats[node.type] || 0) + 1
    }
    topoStats.value = stats

    // 刷新图表
    const [cpu, mem, disk] = await Promise.all([getCpu(1), getMemory(1), getDisk(1)])
    renderChart(cpuChart, cpu as any, '#6366f1')
    renderChart(memChart, mem as any, '#a855f7')
    renderChart(diskChart, disk as any, '#f59e0b')
  } catch (e) {
    console.error('加载大屏数据失败', e)
  }
}

// ========== 渲染图表 ==========
function renderChart(chart: echarts.ECharts | null, data: any[], color: string) {
  if (!chart) return
  const list = Array.isArray(data) ? data : []
  const series = list.map((item: any) => ({
    name: item.metric?.instance || 'unknown',
    type: 'line',
    smooth: true,
    showSymbol: false,
    lineStyle: { color, width: 2 },
    areaStyle: {
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: color + '66' },
        { offset: 1, color: color + '00' },
      ]),
    },
    data: (item.values || []).map((v: any) => [Number(v[0]) * 1000, Number(v[1])]),
  }))

  chart.setOption({
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(15,23,42,0.9)', borderColor: '#334155', textStyle: { color: '#e2e8f0' } },
    xAxis: {
      type: 'time',
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { color: '#94a3b8', fontSize: 11, formatter: '{value}%' },
      splitLine: { lineStyle: { color: 'rgba(51,65,85,0.3)' } },
    },
    series,
  })
}

// ========== 交互：全屏 / 返回 ==========
async function toggleFullscreen() {
  try {
    if (!document.fullscreenElement) {
      await document.documentElement.requestFullscreen()
    } else {
      await document.exitFullscreen()
    }
  } catch (e) {
    ElMessage.warning('当前浏览器不允许进入全屏')
  }
}

async function exitScreen() {
  if (document.fullscreenElement) {
    try {
      await document.exitFullscreen()
    } catch (e) {
      /* 忽略 */
    }
  }
  router.push('/dashboard')
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    // 浏览器全屏时 Esc 已被浏览器占用，这里只在非全屏时兜底返回
    if (!document.fullscreenElement) exitScreen()
  } else if (e.key === 'f' || e.key === 'F') {
    toggleFullscreen()
  }
}

// ========== 生命周期 ==========
onMounted(async () => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)

  await nextTick()
  if (cpuChartRef.value) cpuChart = echarts.init(cpuChartRef.value)
  if (memChartRef.value) memChart = echarts.init(memChartRef.value)
  if (diskChartRef.value) diskChart = echarts.init(diskChartRef.value)

  await loadAll()
  timer = setInterval(loadAll, 10000)  // 每 10 秒刷新

  window.addEventListener('resize', onResize)
  window.addEventListener('keydown', onKeydown)
})

function onResize() {
  cpuChart?.resize()
  memChart?.resize()
  diskChart?.resize()
}

onUnmounted(() => {
  clearInterval(timer)
  clearInterval(clockTimer)
  window.removeEventListener('resize', onResize)
  window.removeEventListener('keydown', onKeydown)
  cpuChart?.dispose()
  memChart?.dispose()
  diskChart?.dispose()
})
</script>

<style scoped>
/* ========== 全屏深色布局 ========== */
.screen {
  position: fixed;
  inset: 0;
  background: radial-gradient(ellipse at top, #1e293b 0%, #0f172a 50%, #020617 100%);
  color: #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* ========== 顶部 ========== */
.screen-header {
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  background: linear-gradient(180deg, rgba(30, 41, 59, 0.8) 0%, transparent 100%);
  border-bottom: 1px solid rgba(99, 102, 241, 0.2);
  flex-shrink: 0;
}

.header-left { display: flex; align-items: center; gap: 16px; }

.logo {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: linear-gradient(135deg, #6366f1, #a855f7);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  box-shadow: 0 0 24px rgba(99, 102, 241, 0.5);
}

.title-group h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 2px;
  background: linear-gradient(90deg, #e2e8f0, #a855f7, #6366f1);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.subtitle {
  font-size: 11px;
  color: #64748b;
  letter-spacing: 3px;
  text-transform: uppercase;
}

.header-center { display: flex; align-items: center; }
.health-score { text-align: center; }
.score-value {
  font-size: 40px;
  font-weight: 700;
  line-height: 1;
  text-shadow: 0 0 20px currentColor;
}
.score-label {
  font-size: 11px;
  color: #64748b;
  letter-spacing: 2px;
  margin-top: 4px;
}

.header-right { display: flex; align-items: center; gap: 16px; }
.clock { text-align: right; }
.header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  padding-left: 16px;
  border-left: 1px solid rgba(99, 102, 241, 0.25);
}
.action-btn {
  font-size: 18px;
  color: #64748b;
  cursor: pointer;
  padding: 6px;
  border-radius: 8px;
  transition: all 0.2s;
}
.action-btn:hover {
  color: #a855f7;
  background: rgba(99, 102, 241, 0.15);
}
.time {
  font-size: 28px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  letter-spacing: 2px;
  color: #e2e8f0;
}
.date { font-size: 12px; color: #64748b; margin-top: 2px; }

/* ========== 主体三栏 ========== */
.screen-body {
  flex: 1;
  display: grid;
  grid-template-columns: 340px 1fr 340px;
  gap: 16px;
  padding: 16px 24px;
  overflow: hidden;
}

.panel-left,
.panel-right {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}
.panel-center {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}

/* ========== 面板通用 ========== */
.panel {
  background: linear-gradient(180deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.4) 100%);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(8px);
}
.panel::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, #6366f1, transparent);
}

.panel-flex { flex: 1; min-height: 0; }

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #94a3b8;
  letter-spacing: 1px;
  margin-bottom: 12px;
  flex-shrink: 0;
}
.panel-title i {
  width: 3px;
  height: 14px;
  background: #6366f1;
  border-radius: 2px;
  box-shadow: 0 0 8px #6366f1;
}
.panel-title i.pulse {
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* ========== 量化指标 ========== */
.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.metric-item { text-align: center; padding: 8px 0; }
.metric-value {
  font-size: 26px;
  font-weight: 700;
  color: #e2e8f0;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}
.metric-value.accent { color: #6366f1; }
.metric-value.warning { color: #f59e0b; }
.metric-value.success { color: #10b981; }
.metric-label { font-size: 11px; color: #64748b; margin-top: 4px; }

/* ========== 节点列表 ========== */
.node-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.node-item {
  padding: 10px 12px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 8px;
  border-left: 3px solid #6366f1;
}
.node-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.node-name {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
  font-family: Consolas, monospace;
}
.node-stats {
  display: flex;
  gap: 10px;
  font-size: 11px;
  color: #94a3b8;
}
.node-bars { display: flex; flex-direction: column; gap: 4px; }
.bar {
  height: 3px;
  background: rgba(51, 65, 85, 0.5);
  border-radius: 2px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  transition: width 0.5s ease;
  border-radius: 2px;
}

/* ========== 图表 ========== */
.chart {
  flex: 1;
  min-height: 160px;
  width: 100%;
}

/* ========== 告警列表 ========== */
.alert-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.alert-item {
  display: flex;
  gap: 10px;
  padding: 8px 10px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 6px;
  animation: slideIn 0.3s ease;
}
@keyframes slideIn {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}
.alert-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}
.alert-dot.danger {
  background: #ef4444;
  box-shadow: 0 0 8px #ef4444;
  animation: pulse 1.5s ease-in-out infinite;
}
.alert-dot.info { background: #10b981; }
.alert-body { flex: 1; min-width: 0; }
.alert-line1 {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 2px;
}
.alert-node {
  color: #e2e8f0;
  font-weight: 600;
  font-family: Consolas, monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.alert-resource { color: #f59e0b; font-size: 11px; }
.alert-line2 {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #64748b;
}

/* ========== 拓扑统计 ========== */
.topology-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.topo-item {
  padding: 12px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 8px;
  text-align: center;
}
.topo-count {
  font-size: 24px;
  font-weight: 700;
  color: #6366f1;
  line-height: 1;
}
.topo-type {
  font-size: 11px;
  color: #64748b;
  margin-top: 4px;
  letter-spacing: 1px;
}

/* ========== 底部滚动条 ========== */
.screen-footer {
  height: 32px;
  background: rgba(15, 23, 42, 0.8);
  border-top: 1px solid rgba(99, 102, 241, 0.2);
  overflow: hidden;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.scroll-text {
  white-space: nowrap;
  font-size: 12px;
  color: #64748b;
  animation: scroll 30s linear infinite;
  padding-left: 100%;
}
@keyframes scroll {
  from { transform: translateX(0); }
  to { transform: translateX(-100%); }
}

/* ========== 空状态 ========== */
.empty-tip {
  text-align: center;
  color: #475569;
  font-size: 12px;
  padding: 20px 0;
}

/* ========== 滚动条美化 ========== */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: rgba(99, 102, 241, 0.3);
  border-radius: 2px;
}
::-webkit-scrollbar-thumb:hover { background: rgba(99, 102, 241, 0.5); }
</style>
