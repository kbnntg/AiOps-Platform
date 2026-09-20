<template>
  <div>
    <el-card shadow="never">
      <el-table :data="alerts" border stripe v-loading="loading" empty-text="暂无告警记录">
        <el-table-column prop="triggered_at" label="触发时间" width="180" />
        <el-table-column prop="node" label="节点" width="200" />
        <el-table-column prop="resource" label="资源" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.resource === '聚合' ? 'warning' : ''">
              {{ row.resource }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="value" label="当前值" width="90" align="center" />
        <el-table-column prop="threshold" label="阈值" width="90" align="center" />
        <el-table-column label="原始告警数" width="110" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.raw_count > 1" type="warning" size="small">
              {{ row.raw_count }} 条
            </el-tag>
            <span v-else>{{ row.raw_count || 1 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="AI 建议" min-width="240">
          <template #default="{ row }">
            <el-popover v-if="row.ai_advice" placement="left" width="450" trigger="click">
              <pre class="ai-advice">{{ row.ai_advice }}</pre>
              <template #reference>
                <el-button size="small" type="primary" text>查看建议</el-button>
              </template>
            </el-popover>
            <span v-else style="color:#c0c4cc">无</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_false_positive" type="info" size="small">误报</el-tag>
            <el-tag v-else :type="row.status === 'OPEN' ? 'danger' : 'success'" size="small">
              {{ row.status === 'OPEN' ? '未处理' : '已解决' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" v-if="authStore.role === 'admin'">
          <template #default="{ row }">
            <el-button v-if="row.status === 'OPEN' && !row.is_false_positive"
                       size="small" type="success" @click="handleResolve(row)">
              标记解决
            </el-button>
            <el-button v-if="!row.is_false_positive"
                       size="small" type="warning" @click="handleFalsePositive(row)">
              误报
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAlerts, resolveAlert, markFalsePositive } from '@/api/alerts'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const alerts = ref<any[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const data: any = await getAlerts(200)
    // 兼容旧字段（没有 raw_count / is_false_positive 时给默认值）
    alerts.value = data.map((a: any) => ({
      ...a,
      raw_count: a.raw_count ?? 1,
      is_false_positive: a.is_false_positive ?? 0,
    }))
  } finally {
    loading.value = false
  }
}

async function handleResolve(row: any) {
  await resolveAlert(row.id)
  ElMessage.success('已标记解决')
  load()
}

async function handleFalsePositive(row: any) {
  ElMessageBox.confirm(
    `确认将告警 #${row.id} 标记为误报？这会算入误报率统计。`,
    '标记误报',
    { type: 'warning' }
  ).then(async () => {
    await markFalsePositive(row.id)
    ElMessage.success('已标记为误报')
    load()
  }).catch(() => {})
}

onMounted(load)
</script>

<style scoped>
.ai-advice { white-space: pre-wrap; font-size: 13px; line-height: 1.6; }
</style>