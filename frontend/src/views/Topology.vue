<template>
  <div class="topology-page">
    <!-- 工具栏 -->
    <div class="toolbar-card">
      <div class="toolbar">
        <el-select v-model="namespace" style="width:200px" @change="loadTopology" clearable placeholder="全部命名空间">
          <el-option v-for="n in namespaces" :key="n" :label="n" :value="n" />
        </el-select>
        <el-button type="primary" @click="loadTopology">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
        <div class="toolbar-right">
          <el-checkbox-group v-model="visibleTypes" size="small">
            <el-checkbox-button value="Deployment">Deployment</el-checkbox-button>
            <el-checkbox-button value="Pod">Pod</el-checkbox-button>
            <el-checkbox-button value="Service">Service</el-checkbox-button>
            <el-checkbox-button value="Ingress">Ingress</el-checkbox-button>
          </el-checkbox-group>
        </div>
      </div>

      <!-- 图例 -->
      <div class="legend">
        <span class="legend-item"><i class="dot healthy"></i>健康</span>
        <span class="legend-item"><i class="dot warning"></i>警告</span>
        <span class="legend-item"><i class="dot error"></i>异常</span>
        <span class="legend-item"><i class="line solid"></i>拥有关系</span>
        <span class="legend-item"><i class="line dashed"></i>选中/路由</span>
        <span class="legend-item" style="margin-left: 16px; color: #94a3b8">
          D=Deployment · P=Pod · S=Service · I=Ingress
        </span>
      </div>
    </div>

    <!-- 图表 -->
    <div class="graph-container" v-loading="loading" element-loading-text="正在推导拓扑...">
      <div ref="chartRef" class="graph"></div>

      <!-- 空状态 -->
      <div v-if="!loading && (!topology.nodes || topology.nodes.length === 0)" class="empty">
        <el-empty description="暂无拓扑数据" />
      </div>
    </div>

    <!-- 节点详情弹窗 -->
    <el-drawer v-model="drawerVisible" :title="selectedNode?.name" size="420px">
      <div v-if="selectedNode" class="node-detail">
        <div class="detail-row">
          <span class="label">类型</span>
          <el-tag :type="typeTagColor(selectedNode.type)" size="small">{{ selectedNode.type }}</el-tag>
        </div>
        <div class="detail-row">
          <span class="label">命名空间</span>
          <span>{{ selectedNode.namespace }}</span>
        </div>
        <div class="detail-row">
          <span class="label">健康度</span>
          <el-tag :type="healthTagColor(selectedNode.health)" size="small">
            {{ healthText(selectedNode.health) }}
          </el-tag>
        </div>

        <el-divider />

        <div v-if="selectedNode.detail">
          <div v-for="(v, k) in selectedNode.detail" :key="k" class="detail-row">
            <span class="label">{{ k }}</span>
            <span class="value">{{ formatValue(v) }}</span>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { getTopology } from '@/api/topology'
import { getNamespaces } from '@/api/metrics'

const chartRef = ref<HTMLDivElement>()
const namespace = ref('privatization')
const namespaces = ref<string[]>([])
const loading = ref(false)
const topology = ref<any>({ nodes: [], edges: [] })
const visibleTypes = ref(['Deployment', 'Pod', 'Service', 'Ingress'])
const drawerVisible = ref(false)
const selectedNode = ref<any>(null)

let chart: echarts.ECharts | null = null

// 节点颜色
const TYPE_COLORS: Record<string, string> = {
  Deployment: '#6366f1',
  Pod: '#10b981',
  Service: '#f59e0b',
  Ingress: '#a855f7',
}

// 健康度颜色（边框）
const HEALTH_COLORS: Record<string, string> = {
  healthy: '#10b981',
  warning: '#f59e0b',
  error: '#ef4444',
}

// 过滤后的节点和边
const filteredData = computed(() => {
  const types = new Set(visibleTypes.value)
  const nodes = topology.value.nodes.filter((n: any) => types.has(n.type))
  const nodeIds = new Set(nodes.map((n: any) => n.id))
  const edges = topology.value.edges.filter(
    (e: any) => nodeIds.has(e.source) && nodeIds.has(e.target)
  )
  return { nodes, edges }
})

function healthText(h: string): string {
  return { healthy: '健康', warning: '警告', error: '异常' }[h] || '未知'
}
function healthTagColor(h: string): string {
  return { healthy: 'success', warning: 'warning', error: 'danger' }[h] || 'info'
}
function typeTagColor(t: string): string {
  return { Deployment: '', Pod: 'success', Service: 'warning', Ingress: 'danger' }[t] || 'info'
}
function formatValue(v: any): string {
  if (Array.isArray(v)) return v.join(', ')
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

async function loadNamespaces() {
  namespaces.value = await getNamespaces() as any
}

async function loadTopology() {
  loading.value = true
  try {
    const data: any = await getTopology(namespace.value || undefined)
    if (data.detail) {
      console.error('拓扑接口出错:', data.detail)
      topology.value = { nodes: [], edges: [] }
    } else {
      topology.value = data
    }
    renderChart()
  } finally {
    loading.value = false
  }
}

function renderChart() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)

  const { nodes, edges } = filteredData.value

  if (nodes.length === 0) {
    chart.clear()
    return
  }

  // 节点数据
  const chartNodes = nodes.map((n: any) => ({
    id: n.id,
    name: n.name,
    symbolSize: n.type === 'Pod' ? 42 : 52,
    itemStyle: {
      color: TYPE_COLORS[n.type] || '#94a3b8',
      borderColor: HEALTH_COLORS[n.health] || '#94a3b8',
      borderWidth: 3,
      shadowBlur: 12,
      shadowColor: 'rgba(99, 102, 241, 0.35)',
    },
    label: {
      show: true,
      position: 'bottom',
      fontSize: 11,
      color: '#475569',
      formatter: (p: any) => {
        const t = p.data._raw?.type || ''
        const prefix = { Deployment: 'D', Pod: 'P', Service: 'S', Ingress: 'I' }[t] || ''
        return `${prefix}·${truncate(p.name, 16)}`
      },
    },
    _raw: n,
  }))

  // 边数据
  const chartEdges = edges.map((e: any) => ({
    source: e.source,
    target: e.target,
    lineStyle: {
      color: e.type === 'owns' ? '#94a3b8' : '#cbd5e1',
      width: 1.5,
      type: e.type === 'owns' ? 'solid' : 'dashed',
      curveness: 0.1,
    },
  }))

  chart.setOption({
    tooltip: {
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const n = params.data._raw
          return `
            <b>${n.name}</b><br/>
            类型: ${n.type}<br/>
            命名空间: ${n.namespace}<br/>
            健康度: ${healthText(n.health)}
          `
        }
        return ''
      },
    },
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      draggable: true,
      focusNodeAdjacency: true,
      force: {
        repulsion: 450,
        edgeLength: [100, 180],
        gravity: 0.05,
        layoutAnimation: true,
      },
      label: { show: true },
      edgeSymbol: ['none', 'arrow'],
      edgeSymbolSize: [0, 8],
      data: chartNodes,
      links: chartEdges,
    }],
  })

  chart.off('click')
  chart.on('click', (params: any) => {
    if (params.dataType === 'node' && params.data._raw) {
      selectedNode.value = params.data._raw
      drawerVisible.value = true
    }
  })
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + '...' : s
}

// 类型过滤变化时重绘
watch(visibleTypes, () => renderChart(), { deep: true })

// 窗口 resize 时自适应
function onResize() { chart?.resize() }

onMounted(async () => {
  await loadNamespaces()
  await loadTopology()
  window.addEventListener('resize', onResize)
  await nextTick()
  chart?.resize()
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
})
</script>

<style scoped>
.topology-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 112px);
}

.toolbar-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  margin-bottom: 16px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.toolbar-right { margin-left: auto; }

.legend {
  margin-top: 12px;
  display: flex;
  gap: 20px;
  font-size: 12px;
  color: #64748b;
}
.legend-item { display: flex; align-items: center; gap: 6px; }
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.dot.healthy { background: #10b981; }
.dot.warning { background: #f59e0b; }
.dot.error { background: #ef4444; }
.line {
  width: 20px;
  height: 2px;
  display: inline-block;
}
.line.solid { background: #94a3b8; }
.line.dashed {
  background: repeating-linear-gradient(to right, #cbd5e1 0, #cbd5e1 4px, transparent 4px, transparent 8px);
}

.graph-container {
  flex: 1;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  position: relative;
  overflow: hidden;
}
.graph {
  width: 100%;
  height: 100%;
  min-height: 500px;
}

.empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 节点详情 */
.node-detail { padding: 8px 4px; }
.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  font-size: 13px;
}
.detail-row .label {
  color: #64748b;
  font-weight: 500;
  flex-shrink: 0;
  margin-right: 12px;
}
.detail-row .value {
  color: #1e293b;
  word-break: break-all;
  text-align: right;
}
</style>