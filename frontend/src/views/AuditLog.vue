<template>
  <div class="audit-page">
    <!-- ========== 筛选工具栏 ========== -->
    <el-card shadow="never">
      <div class="toolbar">
        <el-input
          v-model="keyword"
          placeholder="搜索操作人 / 资源名 / 命名空间"
          clearable
          style="width: 240px"
        />
        <el-select v-model="actionFilter" placeholder="全部操作" clearable style="width: 180px">
          <el-option v-for="a in actionOptions" :key="a" :label="a" :value="a" />
        </el-select>
        <el-select v-model="resultFilter" style="width: 130px">
          <el-option label="全部结果" value="all" />
          <el-option label="成功" value="SUCCESS" />
          <el-option label="失败" value="FAILED" />
        </el-select>
        <el-select v-model="typeFilter" placeholder="全部资源类型" clearable style="width: 160px">
          <el-option v-for="t in typeOptions" :key="t" :label="t" :value="t" />
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
          共 <b>{{ logs.length }}</b> 条记录
          <template v-if="hasFilter">，筛选后 <b>{{ filtered.length }}</b> 条</template>
          <span v-if="lastLoadedAt" class="muted">· 更新于 {{ lastLoadedAt }}</span>
        </div>
        <div class="toolbar-actions">
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

    <!-- ========== 审计表格 ========== -->
    <el-card shadow="never" class="mt-4">
      <el-table
        :data="paged"
        border
        stripe
        v-loading="loading"
        empty-text="暂无审计记录"
        :default-sort="{ prop: 'created_at', order: 'descending' }"
        @sort-change="onSortChange"
      >
        <el-table-column prop="created_at" label="时间" width="190" sortable="custom">
          <template #default="{ row }">
            <div class="time-cell">
              <span>{{ row.created_at }}</span>
              <span class="muted">{{ fromNow(row.created_at) }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="username" label="操作人" width="120" />

        <el-table-column prop="action" label="操作" width="180">
          <template #default="{ row }">
            <el-tag size="small" :type="actionType(row.action)">{{ row.action }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="resource_type" label="资源类型" width="120" />
        <el-table-column prop="resource_name" label="资源名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="namespace" label="命名空间" width="140" />

        <el-table-column prop="result" label="结果" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.result === 'SUCCESS' ? 'success' : 'danger'">
              {{ row.result === 'SUCCESS' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="详情" width="90">
          <template #default="{ row }">
            <el-popover v-if="row.details" placement="left" width="420" trigger="click">
              <pre class="details">{{ prettyDetails(row.details) }}</pre>
              <template #reference>
                <el-button size="small" type="primary" text>查看</el-button>
              </template>
            </el-popover>
            <span v-else class="muted">—</span>
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
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getAuditLogs } from '@/api/alerts'
import { exportCsv, type CsvColumn } from '@/utils/exportCsv'
import { formatDateTime, fromNow, parseTime } from '@/utils/datetime'

/** 后端 /api/audit 的 limit 上限为 500，筛选与分页在前端完成 */
const MAX_ROWS = 500

const logs = ref<any[]>([])
const loading = ref(false)
const lastLoadedAt = ref('')

const keyword = ref('')
const actionFilter = ref('')
const resultFilter = ref('all')
const typeFilter = ref('')
const timeRange = ref<[string, string] | null>(null)

const sortProp = ref('created_at')
const sortOrder = ref<'ascending' | 'descending'>('descending')
const page = ref(1)
const pageSize = ref(20)

const actionOptions = computed(() =>
  Array.from(new Set(logs.value.map((l) => l.action).filter(Boolean))).sort(),
)
const typeOptions = computed(() =>
  Array.from(new Set(logs.value.map((l) => l.resource_type).filter(Boolean))).sort(),
)

const hasFilter = computed(
  () =>
    !!keyword.value.trim() ||
    !!actionFilter.value ||
    resultFilter.value !== 'all' ||
    !!typeFilter.value ||
    !!(timeRange.value && timeRange.value.length === 2),
)

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  const startTs = parseTime(timeRange.value?.[0])
  const endTs = parseTime(timeRange.value?.[1])

  return logs.value.filter((row) => {
    if (actionFilter.value && row.action !== actionFilter.value) return false
    if (resultFilter.value !== 'all' && row.result !== resultFilter.value) return false
    if (typeFilter.value && row.resource_type !== typeFilter.value) return false

    if (startTs || endTs) {
      const ts = parseTime(row.created_at)
      if (startTs && ts < startTs) return false
      if (endTs && ts > endTs) return false
    }

    if (kw) {
      const haystack =
        `${row.username || ''} ${row.resource_name || ''} ${row.namespace || ''} ${row.action || ''}`.toLowerCase()
      if (!haystack.includes(kw)) return false
    }
    return true
  })
})

const sorted = computed(() => {
  const list = [...filtered.value]
  const dir = sortOrder.value === 'ascending' ? 1 : -1
  list.sort((a, b) => {
    const av = parseTime(a[sortProp.value])
    const bv = parseTime(b[sortProp.value])
    if (av === bv) return 0
    return (av < bv ? -1 : 1) * dir
  })
  return list
})

const paged = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return sorted.value.slice(start, start + pageSize.value)
})

function actionType(a: string): string {
  if (!a) return 'info'
  if (a.includes('DELETE')) return 'danger'
  if (a.includes('SCALE')) return 'warning'
  if (a.startsWith('COPILOT')) return 'warning'
  if (a.startsWith('AI_')) return 'success'
  return 'info'
}

function prettyDetails(details: any): string {
  if (details === null || details === undefined || details === '') return ''
  if (typeof details === 'string') {
    try {
      return JSON.stringify(JSON.parse(details), null, 2)
    } catch {
      return details
    }
  }
  try {
    return JSON.stringify(details, null, 2)
  } catch {
    return String(details)
  }
}

function onSortChange({ prop, order }: { prop: string; order: string | null }) {
  if (!order) {
    sortProp.value = 'created_at'
    sortOrder.value = 'descending'
    return
  }
  sortProp.value = prop
  sortOrder.value = order as 'ascending' | 'descending'
  page.value = 1
}

async function load(silent = false) {
  if (!silent) loading.value = true
  try {
    const data: any = await getAuditLogs(MAX_ROWS, silent)
    logs.value = Array.isArray(data) ? data : []
    lastLoadedAt.value = formatDateTime(new Date())
  } catch (e) {
    if (!silent) ElMessage.error('加载审计日志失败')
  } finally {
    if (!silent) loading.value = false
  }
}

function resetFilters() {
  keyword.value = ''
  actionFilter.value = ''
  resultFilter.value = 'all'
  typeFilter.value = ''
  timeRange.value = null
}

const CSV_COLUMNS: CsvColumn<any>[] = [
  { label: '时间', value: (r) => r.created_at },
  { label: '操作人', value: (r) => r.username },
  { label: '操作', value: (r) => r.action },
  { label: '资源类型', value: (r) => r.resource_type },
  { label: '资源名', value: (r) => r.resource_name },
  { label: '命名空间', value: (r) => r.namespace },
  { label: '结果', value: (r) => (r.result === 'SUCCESS' ? '成功' : '失败') },
  { label: '详情', value: (r) => prettyDetails(r.details) },
]

function handleExport() {
  if (!sorted.value.length) {
    ElMessage.warning('当前筛选结果为空，没有可导出的数据')
    return
  }
  exportCsv('operation-audit', CSV_COLUMNS, sorted.value)
  ElMessage.success(`已导出 ${sorted.value.length} 条记录`)
}

watch([keyword, actionFilter, resultFilter, typeFilter, timeRange], () => {
  page.value = 1
})

watch(
  () => filtered.value.length,
  (len) => {
    const maxPage = Math.max(1, Math.ceil(len / pageSize.value))
    if (page.value > maxPage) page.value = maxPage
  },
)

onMounted(() => load())
</script>

<style scoped>
.audit-page { padding-bottom: 24px; }
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

.muted { color: #94a3b8; font-size: 12px; }
.time-cell { display: flex; flex-direction: column; line-height: 1.4; }

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.details {
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 12px;
  line-height: 1.6;
  margin: 0;
  max-height: 50vh;
  overflow: auto;
}
</style>
