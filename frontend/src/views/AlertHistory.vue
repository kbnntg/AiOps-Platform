<template>
  <div class="alert-page">
    <!-- ========== 筛选工具栏 ========== -->
    <el-card shadow="never">
      <div class="toolbar">
        <el-input
          v-model="keyword"
          placeholder="搜索节点 / 资源 / AI 建议"
          clearable
          style="width: 240px"
        />
        <el-select v-model="statusFilter" style="width: 150px">
          <el-option label="全部状态" value="all" />
          <el-option label="未处理" value="open" />
          <el-option label="已解决" value="resolved" />
          <el-option label="已标记误报" value="false_positive" />
        </el-select>
        <el-select v-model="resourceFilter" placeholder="全部资源" clearable style="width: 140px">
          <el-option v-for="r in resourceOptions" :key="r" :label="r" :value="r" />
        </el-select>
        <el-date-picker
          v-model="timeRange"
          type="datetimerange"
          value-format="YYYY-MM-DD HH:mm:ss"
          range-separator="~"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          style="width: 360px"
        />
        <el-button type="primary" :loading="loading" @click="load()">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
        <el-button :disabled="!hasFilter" @click="resetFilters">重置筛选</el-button>
      </div>

      <div class="toolbar-bottom">
        <div class="toolbar-summary">
          共 <b>{{ alerts.length }}</b> 条记录
          <template v-if="hasFilter">，筛选后 <b>{{ filtered.length }}</b> 条</template>
          <span v-if="lastLoadedAt" class="muted">· 更新于 {{ lastLoadedAt }}</span>
        </div>
        <div class="toolbar-actions">
          <el-switch v-model="autoRefresh" size="small" />
          <span class="switch-label">自动刷新（30 秒）</span>
          <el-button
            type="success"
            plain
            size="small"
            :disabled="!filtered.length"
            @click="handleExport"
          >
            <el-icon><Download /></el-icon> 导出筛选结果
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- ========== 告警列表 ========== -->
    <el-card shadow="never" class="mt-4">
      <el-table
        :data="paged"
        border
        stripe
        v-loading="loading"
        empty-text="暂无告警记录"
        :default-sort="{ prop: 'triggered_at', order: 'descending' }"
        @sort-change="onSortChange"
      >
        <el-table-column prop="triggered_at" label="触发时间" width="200" sortable="custom">
          <template #default="{ row }">
            <div class="time-cell">
              <span>{{ row.triggered_at }}</span>
              <span class="muted">{{ fromNow(row.triggered_at) }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="node" label="节点" width="180" show-overflow-tooltip />

        <el-table-column prop="resource" label="资源" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.resource === '聚合' ? 'warning' : ''">
              {{ row.resource }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="value" label="当前值" width="100" align="center" sortable="custom" />

        <el-table-column prop="threshold" label="阈值" width="90" align="center" />

        <el-table-column prop="raw_count" label="原始告警数" width="120" align="center" sortable="custom">
          <template #default="{ row }">
            <el-tag v-if="row.raw_count > 1" type="warning" size="small">
              {{ row.raw_count }} 条
            </el-tag>
            <span v-else>{{ row.raw_count || 1 }}</span>
          </template>
        </el-table-column>

        <el-table-column label="处理人" width="110">
          <template #default="{ row }">
            <span v-if="row.resolved_by">{{ row.resolved_by }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tooltip
              v-if="row.status === 'RESOLVED' && row.resolved_at"
              :content="`解决于 ${row.resolved_at}`"
              placement="top"
            >
              <el-tag :type="statusInfo(row).type" size="small">{{ statusInfo(row).text }}</el-tag>
            </el-tooltip>
            <el-tag v-else :type="statusInfo(row).type" size="small">
              {{ statusInfo(row).text }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="AI 建议" min-width="220">
          <template #default="{ row }">
            <el-popover v-if="row.ai_advice" placement="left" width="450" trigger="click">
              <pre class="ai-advice">{{ row.ai_advice }}</pre>
              <template #reference>
                <el-button size="small" type="primary" text>查看建议</el-button>
              </template>
            </el-popover>
            <span v-else class="muted">无</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="190" fixed="right" v-if="isAdmin">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'OPEN' && !row.is_false_positive"
              size="small"
              type="success"
              @click="handleResolve(row)"
            >
              标记解决
            </el-button>
            <el-button
              v-if="!row.is_false_positive"
              size="small"
              type="warning"
              @click="handleFalsePositive(row)"
            >
              误报
            </el-button>
            <span v-if="row.is_false_positive" class="muted">已误报</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- ========== 分页 ========== -->
      <div class="pager">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="filtered.length"
          :page-sizes="[10, 20, 50, 100]"
          v-model:current-page="page"
          v-model:page-size="pageSize"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAlerts, resolveAlert, markFalsePositive } from '@/api/alerts'
import { useAuthStore } from '@/stores/auth'
import { useAlertStore } from '@/stores/alerts'
import { exportCsv, type CsvColumn } from '@/utils/exportCsv'
import { formatDateTime, fromNow, parseTime } from '@/utils/datetime'

/** 后端 /api/alerts 的 limit 上限为 500，筛选与分页都在前端完成 */
const MAX_ROWS = 500
const AUTO_REFRESH_MS = 30_000

const authStore = useAuthStore()
const alertStore = useAlertStore()
const isAdmin = computed(() => authStore.role === 'admin')

const alerts = ref<any[]>([])
const loading = ref(false)
const lastLoadedAt = ref('')

// ========== 筛选条件 ==========
const keyword = ref('')
const statusFilter = ref('all')
const resourceFilter = ref('')
const timeRange = ref<[string, string] | null>(null)

// ========== 排序 / 分页 ==========
const sortProp = ref('triggered_at')
const sortOrder = ref<'ascending' | 'descending'>('descending')
const page = ref(1)
const pageSize = ref(20)
const autoRefresh = ref(false)

const resourceOptions = computed(() => {
  const set = new Set<string>()
  alerts.value.forEach((a) => {
    if (a.resource) set.add(a.resource)
  })
  return Array.from(set).sort()
})

const hasFilter = computed(
  () =>
    !!keyword.value.trim() ||
    statusFilter.value !== 'all' ||
    !!resourceFilter.value ||
    !!(timeRange.value && timeRange.value.length === 2),
)

/** 前端筛选：状态 / 资源 / 时间范围 / 关键字 */
const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  const startTs = parseTime(timeRange.value?.[0])
  const endTs = parseTime(timeRange.value?.[1])

  return alerts.value.filter((a) => {
    if (statusFilter.value === 'open' && !(a.status === 'OPEN' && !a.is_false_positive)) return false
    if (statusFilter.value === 'resolved' && a.status !== 'RESOLVED') return false
    if (statusFilter.value === 'false_positive' && !a.is_false_positive) return false
    if (resourceFilter.value && a.resource !== resourceFilter.value) return false

    if (startTs || endTs) {
      const ts = parseTime(a.triggered_at)
      if (startTs && ts < startTs) return false
      if (endTs && ts > endTs) return false
    }

    if (kw) {
      const haystack = `${a.node || ''} ${a.resource || ''} ${a.ai_advice || ''}`.toLowerCase()
      if (!haystack.includes(kw)) return false
    }
    return true
  })
})

/** 前端排序（对完整筛选结果排序，而不是只排当前页） */
const sorted = computed(() => {
  const list = [...filtered.value]
  const dir = sortOrder.value === 'ascending' ? 1 : -1
  const prop = sortProp.value

  list.sort((a, b) => {
    let av: number
    let bv: number
    if (prop === 'value' || prop === 'raw_count') {
      av = Number(a[prop]) || 0
      bv = Number(b[prop]) || 0
    } else {
      av = parseTime(a[prop])
      bv = parseTime(b[prop])
    }
    if (av === bv) return 0
    return (av < bv ? -1 : 1) * dir
  })
  return list
})

const paged = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return sorted.value.slice(start, start + pageSize.value)
})

function statusInfo(row: any): { text: string; type: string } {
  if (row.is_false_positive) return { text: '误报', type: 'info' }
  return row.status === 'OPEN' ? { text: '未处理', type: 'danger' } : { text: '已解决', type: 'success' }
}

function onSortChange({ prop, order }: { prop: string; order: string | null }) {
  if (!order) {
    sortProp.value = 'triggered_at'
    sortOrder.value = 'descending'
    return
  }
  sortProp.value = prop
  sortOrder.value = order as 'ascending' | 'descending'
  page.value = 1
}

// ========== 加载 ==========
async function load(silent = false) {
  if (!silent) loading.value = true
  try {
    const data: any = await getAlerts(MAX_ROWS, undefined, silent)
    const list = Array.isArray(data) ? data : []
    alerts.value = list.map((a: any) => ({
      ...a,
      // 兼容旧字段（没有 raw_count / is_false_positive 时给默认值）
      raw_count: a.raw_count ?? 1,
      is_false_positive: a.is_false_positive ?? 0,
    }))
    lastLoadedAt.value = formatDateTime(new Date())
  } catch (e) {
    if (!silent) ElMessage.error('加载告警失败')
  } finally {
    if (!silent) loading.value = false
  }
}

function resetFilters() {
  keyword.value = ''
  statusFilter.value = 'all'
  resourceFilter.value = ''
  timeRange.value = null
}

// ========== 导出 ==========
const CSV_COLUMNS: CsvColumn<any>[] = [
  { label: 'ID', value: (r) => r.id },
  { label: '触发时间', value: (r) => r.triggered_at },
  { label: '节点', value: (r) => r.node },
  { label: '资源', value: (r) => r.resource },
  { label: '当前值', value: (r) => r.value },
  { label: '阈值', value: (r) => r.threshold },
  { label: '原始告警数', value: (r) => r.raw_count ?? 1 },
  { label: '状态', value: (r) => statusInfo(r).text },
  { label: '处理人', value: (r) => r.resolved_by || '' },
  { label: '解决时间', value: (r) => r.resolved_at || '' },
  { label: 'AI 建议', value: (r) => r.ai_advice || '' },
]

function handleExport() {
  if (!sorted.value.length) {
    ElMessage.warning('当前筛选结果为空，没有可导出的数据')
    return
  }
  exportCsv('alert-history', CSV_COLUMNS, sorted.value)
  ElMessage.success(`已导出 ${sorted.value.length} 条记录`)
}

// ========== 操作 ==========
async function handleResolve(row: any) {
  await resolveAlert(row.id)
  ElMessage.success('已标记解决')
  await load(true)
  alertStore.refresh()
}

async function handleFalsePositive(row: any) {
  ElMessageBox.confirm(
    `确认将告警 #${row.id} 标记为误报？这会算入误报率统计。`,
    '标记误报',
    { type: 'warning' },
  )
    .then(async () => {
      await markFalsePositive(row.id)
      ElMessage.success('已标记为误报')
      await load(true)
      alertStore.refresh()
    })
    .catch(() => {})
}

// ========== 监听 ==========
watch([keyword, statusFilter, resourceFilter, timeRange], () => {
  page.value = 1
})

watch(
  () => filtered.value.length,
  (len) => {
    const maxPage = Math.max(1, Math.ceil(len / pageSize.value))
    if (page.value > maxPage) page.value = maxPage
  },
)

let timer: number | undefined
watch(autoRefresh, (on) => {
  if (timer !== undefined) {
    clearInterval(timer)
    timer = undefined
  }
  if (on) {
    timer = window.setInterval(() => load(true), AUTO_REFRESH_MS)
    ElMessage.success('已开启自动刷新')
  }
})

onMounted(() => load())
onUnmounted(() => {
  if (timer !== undefined) clearInterval(timer)
})
</script>

<style scoped>
.alert-page { padding-bottom: 24px; }
.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.mt-4 { margin-top: 16px; }

.toolbar-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
  flex-wrap: wrap;
}
.toolbar-summary { font-size: 13px; color: #475569; }
.toolbar-summary b { color: var(--primary); }
.toolbar-actions { display: flex; align-items: center; gap: 8px; }
.switch-label { font-size: 12px; color: #64748b; }

.muted { color: #94a3b8; font-size: 12px; }

.time-cell { display: flex; flex-direction: column; line-height: 1.4; }

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.ai-advice { white-space: pre-wrap; font-size: 13px; line-height: 1.6; max-height: 50vh; overflow: auto; margin: 0; }
</style>
