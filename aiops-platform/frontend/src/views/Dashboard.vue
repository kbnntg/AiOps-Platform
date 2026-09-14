<template>
  <div class="dashboard fade-in-up">
    <!-- 节点卡片 -->
    <el-row :gutter="20">
      <el-col :span="8" v-for="(node, idx) in nodes" :key="node.name">
        <div class="node-card" :style="{ animationDelay: idx * 0.1 + 's' }">
          <div class="node-header">
            <div class="node-icon">
              <el-icon><Monitor /></el-icon>
            </div>
            <div class="node-title">
              <h3>{{ node.name }}</h3>
              <span class="node-status">运行中</span>
            </div>
          </div>

          <div class="metric-row">
            <div class="metric-label">
              <span>CPU</span>
              <span class="metric-value">{{ node.cpu || 0 }}%</span>
            </div>
            <el-progress :percentage="node.cpu || 0" :color="getColor(node.cpu)"
                         :stroke-width="10" :show-text="false" />
          </div>

          <div class="metric-row">
            <div class="metric-label">
              <span>内存</span>
              <span class="metric-value">{{ node.memory || 0 }}%</span>
            </div>
            <el-progress :percentage="node.memory || 0" :color="getColor(node.memory)"
                         :stroke-width="10" :show-text="false" />
          </div>

          <div class="metric-row">
            <div class="metric-label">
              <span>磁盘</span>
              <span class="metric-value">{{ node.disk || 0 }}%</span>
            </div>
            <el-progress :percentage="node.disk || 0" :stroke-width="10" :show-text="false" />
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 趋势图 -->
    <div class="chart-card">
      <div class="chart-header">
        <div class="chart-title">
          <div class="dot" style="background: #6366f1"></div>
          <h3>CPU 使用率趋势</h3>
        </div>
        <el-radio-group v-model="hours" size="small" @change="loadCharts">
          <el-radio-button :value="1">1小时</el-radio-button>
          <el-radio-button :value="6">6小时</el-radio-button>
          <el-radio-button :value="24">24小时</el-radio-button>
        </el-radio-group>
      </div>
      <ResourceChart :data="cpuData" :height="'320px'" />
    </div>

    <div class="chart-card">
      <div class="chart-header">
        <div class="chart-title">
          <div class="dot" style="background: #a855f7"></div>
          <h3>内存使用率趋势</h3>
        </div>
      </div>
      <ResourceChart :data="memData" :height="'320px'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getNodes, getCpu, getMemory } from '@/api/metrics'
import ResourceChart from '@/components/ResourceChart.vue'

const nodes = ref<any[]>([])
const cpuData = ref<any[]>([])
const memData = ref<any[]>([])
const hours = ref(1)

function getColor(v: number): string {
  if (v > 80) return '#f43f5e'
  if (v > 60) return '#f59e0b'
  return '#10b981'
}

async function loadNodes() { nodes.value = await getNodes() as any }
async function loadCharts() {
  cpuData.value = await getCpu(hours.value) as any
  memData.value = await getMemory(hours.value) as any
}

onMounted(() => { loadNodes(); loadCharts() })
</script>

<style scoped>
.dashboard { padding-bottom: 24px; }

/* ========== 节点卡片 ========== */
.node-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  animation: cardSlideIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
  position: relative;
  overflow: hidden;
}
.node-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, #6366f1, #a855f7);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.3s;
}
.node-card:hover::before { transform: scaleX(1); }
.node-card:hover {
  box-shadow: 0 12px 40px rgba(99, 102, 241, 0.15);
  transform: translateY(-4px);
}

@keyframes cardSlideIn {
  from { opacity: 0; transform: translateY(20px); }
  to   { opacity: 1; transform: translateY(0); }
}

.node-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f1f5f9;
}

.node-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #eef2ff, #e0e7ff);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6366f1;
  font-size: 20px;
}

.node-title h3 {
  margin: 0 0 2px;
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  word-break: break-all;
}
.node-status {
  font-size: 12px;
  color: #10b981;
  display: flex;
  align-items: center;
  gap: 4px;
}
.node-status::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
  animation: blink 2s ease-in-out infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.metric-row { margin-bottom: 16px; }
.metric-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
  color: #64748b;
}
.metric-value {
  font-weight: 600;
  color: #1e293b;
  font-variant-numeric: tabular-nums;
}

/* ========== 图表卡片 ========== */
.chart-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  margin-top: 20px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  transition: all 0.3s;
  animation: cardSlideIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
}
.chart-card:hover {
  box-shadow: 0 8px 32px rgba(99, 102, 241, 0.1);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.chart-title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.chart-title h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  box-shadow: 0 0 8px currentColor;
}
</style>