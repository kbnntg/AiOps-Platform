<template>
  <div class="rag-page">
    <!-- 状态卡片 -->
    <div class="status-cards">
      <div class="status-card">
        <div class="status-icon">📚</div>
        <div class="status-body">
          <div class="status-value">{{ status.count || 0 }}</div>
          <div class="status-label">知识库条数</div>
        </div>
      </div>
      <div class="status-card">
        <div class="status-icon">{{ status.ready ? '✅' : '⚠️' }}</div>
        <div class="status-body">
          <div class="status-value">{{ status.ready ? '就绪' : '空' }}</div>
          <div class="status-label">知识库状态</div>
        </div>
      </div>
      <div class="status-card actions">
        <el-button type="primary" :loading="indexing" @click="handleIndex" v-if="isAdmin">
          <el-icon><Refresh /></el-icon> 同步历史告警
        </el-button>
        <el-button type="danger" @click="handleClear" v-if="isAdmin">
          <el-icon><Delete /></el-icon> 清空知识库
        </el-button>
      </div>
    </div>

    <!-- 检索测试 -->
    <el-card shadow="never" class="search-card">
      <template #header>
        <div class="card-header">
          <span>🔍 检索测试</span>
          <span class="hint">输入问题，看看知识库里能匹配到什么历史案例</span>
        </div>
      </template>

      <div class="search-bar">
        <el-input
          v-model="searchQuery"
          placeholder="例如：CPU 使用率过高 / 内存溢出 / 磁盘满了"
          @keydown.enter="handleSearch"
          clearable
        />
        <el-button type="primary" @click="handleSearch" :loading="searching">
          检索
        </el-button>
      </div>

      <!-- 检索结果 -->
      <div v-if="searchResults.length > 0" class="results">
        <div
          v-for="(hit, idx) in searchResults"
          :key="idx"
          class="result-item"
        >
          <div class="result-header">
            <el-tag :type="similarityTag(hit.similarity)" size="small">
              相似度 {{ (hit.similarity * 100).toFixed(1) }}%
            </el-tag>
            <el-tag size="small" type="info">{{ hit.metadata.resource }}</el-tag>
            <span class="result-node">{{ hit.metadata.node }}</span>
            <span class="result-time">{{ hit.metadata.triggered_at }}</span>
          </div>
          <pre class="result-text">{{ hit.text }}</pre>
        </div>
      </div>

      <el-empty
        v-else-if="searched"
        description="没有找到相似的历史案例"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getRagStatus, triggerIndex, searchRag, clearRag } from '@/api/rag'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.role === 'admin')

const status = ref<any>({ count: 0, ready: false })
const indexing = ref(false)
const searching = ref(false)
const searchQuery = ref('')
const searchResults = ref<any[]>([])
const searched = ref(false)

// 拉取状态
async function loadStatus() {
  try {
    status.value = await getRagStatus()
  } catch (e) {
    console.error('加载状态失败', e)
  }
}

// 触发索引
async function handleIndex() {
  indexing.value = true
  try {
    const res: any = await triggerIndex()
    ElMessage.success(`索引完成：新增 ${res.indexed} 条，共 ${res.total_in_rag} 条`)
    await loadStatus()
  } catch (e: any) {
    ElMessage.error(`索引失败: ${e.response?.data?.detail || e.message}`)
  } finally {
    indexing.value = false
  }
}

// 检索
async function handleSearch() {
  if (!searchQuery.value.trim()) return
  searching.value = true
  searched.value = true
  try {
    const res: any = await searchRag(searchQuery.value, 5)
    searchResults.value = res.hits || []
  } catch (e) {
    searchResults.value = []
    ElMessage.error('检索失败')
  } finally {
    searching.value = false
  }
}

// 清空
async function handleClear() {
  ElMessageBox.confirm('确定清空知识库？所有已索引的案例都会被删除。', '危险操作', {
    type: 'warning',
  }).then(async () => {
    await clearRag()
    ElMessage.success('已清空')
    searchResults.value = []
    await loadStatus()
  }).catch(() => {})
}

// 相似度颜色
function similarityTag(s: number): string {
  if (s >= 0.7) return 'success'
  if (s >= 0.5) return 'warning'
  return 'info'
}

onMounted(loadStatus)
</script>

<style scoped>
.rag-page { padding-bottom: 24px; }

/* ========== 状态卡片 ========== */
.status-cards {
  display: grid;
  grid-template-columns: 200px 200px 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.status-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}
.status-card.actions {
  justify-content: flex-end;
}

.status-icon { font-size: 32px; }
.status-value {
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1;
}
.status-label {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

/* ========== 搜索卡片 ========== */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}
.hint {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 400;
}

.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

/* ========== 检索结果 ========== */
.results {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-item {
  padding: 14px 16px;
  background: #f8fafc;
  border-radius: 10px;
  border-left: 4px solid #6366f1;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.result-node {
  font-family: Consolas, monospace;
  font-size: 12px;
  color: #64748b;
}
.result-time {
  font-size: 12px;
  color: #94a3b8;
  margin-left: auto;
}

.result-text {
  margin: 0;
  font-size: 12px;
  color: #475569;
  line-height: 1.7;
  white-space: pre-wrap;
  font-family: inherit;
}
</style>