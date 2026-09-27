<template>
  <div class="health-check-page">
    <!-- 工具栏 -->
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <el-select v-model="namespace" style="width:200px" clearable placeholder="全部命名空间">
          <el-option v-for="n in namespaces" :key="n" :label="n" :value="n" />
        </el-select>
        <el-button type="primary" @click="load" :loading="loading">
          <el-icon><Search /></el-icon> 开始巡检
        </el-button>
        <span class="hint" v-if="result">
          已扫描：{{ result.scanned.pods }} 个 Pod、{{ result.scanned.deployments }} 个 Deployment、{{ result.scanned.nodes }} 个节点
        </span>
      </div>
    </el-card>

    <!-- 结果区 -->
    <div v-if="result" class="result-area">
      <!-- 健康分卡片 -->
      <div class="score-cards">
        <div class="score-main" :style="{ borderColor: scoreColor }">
          <div class="score-value" :style="{ color: scoreColor }">{{ result.score }}</div>
          <div class="score-label">健康分</div>
          <div class="score-bar">
            <div class="score-bar-fill" :style="{ width: result.score + '%', background: scoreColor }"></div>
          </div>
        </div>

        <div class="stat-card critical">
          <div class="stat-icon">🔴</div>
          <div class="stat-value">{{ result.summary.critical }}</div>
          <div class="stat-label">严重</div>
        </div>

        <div class="stat-card warning">
          <div class="stat-icon">🟡</div>
          <div class="stat-value">{{ result.summary.warning }}</div>
          <div class="stat-label">警告</div>
        </div>

        <div class="stat-card info">
          <div class="stat-icon">🔵</div>
          <div class="stat-value">{{ result.summary.info }}</div>
          <div class="stat-label">提示</div>
        </div>
      </div>

      <!-- 问题清单 -->
      <el-card shadow="never" class="issues-card">
        <template #header>
          <div class="card-header">
            <span>问题清单（{{ result.total }} 条）</span>
            <el-radio-group v-model="filterSeverity" size="small">
              <el-radio-button value="">全部</el-radio-button>
              <el-radio-button value="critical">严重</el-radio-button>
              <el-radio-button value="warning">警告</el-radio-button>
              <el-radio-button value="info">提示</el-radio-button>
            </el-radio-group>
          </div>
        </template>

        <div v-if="filteredIssues.length === 0" class="empty">
          <el-empty :description="result.total === 0 ? '🎉 集群健康，没有发现问题' : '该分类下没有问题'" />
        </div>

        <div v-else class="issue-list">
          <div
            v-for="(issue, idx) in filteredIssues.slice(0, displayLimit)"
            :key="idx"
            class="issue-item"
            :class="issue.severity"
          >
            <div class="issue-severity">
              <span class="severity-badge" :class="issue.severity">
                {{ severityText(issue.severity) }}
              </span>
            </div>
            <div class="issue-body">
              <div class="issue-header">
                <span class="issue-resource">{{ issue.resource }}</span>
                <el-tag size="small" type="info">{{ issue.rule_name }}</el-tag>
              </div>
              <div class="issue-message">{{ issue.message }}</div>
              <div class="issue-suggestion">
                <el-icon><InfoFilled /></el-icon>
                <span>{{ issue.suggestion }}</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="filteredIssues.length > displayLimit" class="load-more">
          <el-button @click="displayLimit += 20">
            加载更多（还有 {{ filteredIssues.length - displayLimit }} 条）
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- 首次未巡检 -->
    <div v-else class="initial-tip">
      <el-empty description="点击「开始巡检」按钮，对集群做一次健康检查" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { runHealthCheck } from '@/api/healthCheck'
import { getNamespaces } from '@/api/metrics'

const namespace = ref('')
const namespaces = ref<string[]>([])
const loading = ref(false)
const result = ref<any>(null)
const filterSeverity = ref('')
const displayLimit = ref(20)

const scoreColor = computed(() => {
  if (!result.value) return '#6366f1'
  const s = result.value.score
  if (s >= 80) return '#10b981'
  if (s >= 60) return '#f59e0b'
  return '#ef4444'
})

const filteredIssues = computed(() => {
  if (!result.value) return []
  if (!filterSeverity.value) return result.value.issues
  return result.value.issues.filter((i: any) => i.severity === filterSeverity.value)
})

function severityText(s: string): string {
  return { critical: '严重', warning: '警告', info: '提示' }[s] || s
}

async function loadNamespaces() {
  try {
    namespaces.value = await getNamespaces() as any
  } catch (e) {}
}

async function load() {
  loading.value = true
  try {
    result.value = await runHealthCheck(namespace.value || undefined)
  } catch (e: any) {
    result.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadNamespaces()
  load()
})
</script>

<style scoped>
.health-check-page { padding-bottom: 24px; }

.toolbar-card { margin-bottom: 16px; }
.toolbar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.hint { font-size: 12px; color: #94a3b8; margin-left: auto; }

/* ========== 健康分卡片 ========== */
.score-cards {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.score-main {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  border-left: 4px solid #6366f1;
  transition: transform 0.3s;
}
.score-value {
  font-size: 56px;
  font-weight: 700;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.score-label {
  font-size: 14px;
  color: #64748b;
  margin-top: 8px;
}
.score-bar {
  height: 6px;
  background: #f1f5f9;
  border-radius: 3px;
  margin-top: 12px;
  overflow: hidden;
}
.score-bar-fill {
  height: 100%;
  transition: width 0.8s ease;
  border-radius: 3px;
}

.stat-card {
  background: #fff;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  text-align: center;
  transition: transform 0.3s;
}
.stat-card:hover { transform: translateY(-4px); }
.stat-icon { font-size: 24px; margin-bottom: 8px; }
.stat-value {
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
  color: #1e293b;
  font-variant-numeric: tabular-nums;
}
.stat-label {
  font-size: 12px;
  color: #64748b;
  margin-top: 6px;
}
.stat-card.critical .stat-value { color: #ef4444; }
.stat-card.warning .stat-value { color: #f59e0b; }
.stat-card.info .stat-value { color: #6366f1; }

/* ========== 问题列表 ========== */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.issue-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.issue-item {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  background: #f8fafc;
  border-radius: 10px;
  border-left: 4px solid #cbd5e1;
  transition: background-color 0.15s;
}
.issue-item:hover { background: #f1f5f9; }
.issue-item.critical { border-left-color: #ef4444; }
.issue-item.warning { border-left-color: #f59e0b; }
.issue-item.info { border-left-color: #6366f1; }

.severity-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  flex-shrink: 0;
}
.severity-badge.critical { background: #ef4444; }
.severity-badge.warning { background: #f59e0b; }
.severity-badge.info { background: #6366f1; }

.issue-body { flex: 1; min-width: 0; }
.issue-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}
.issue-resource {
  font-family: Consolas, monospace;
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  word-break: break-all;
}
.issue-message {
  font-size: 13px;
  color: #475569;
  margin-bottom: 6px;
  line-height: 1.6;
}
.issue-suggestion {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px 10px;
  background: rgba(99, 102, 241, 0.06);
  border-radius: 6px;
  font-size: 12px;
  color: #6366f1;
  line-height: 1.6;
}

.empty { padding: 20px 0; }
.load-more { text-align: center; padding: 16px 0; }
.initial-tip { padding: 80px 0; }
</style>