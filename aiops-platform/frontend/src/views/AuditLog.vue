<template>
  <div>
    <el-card shadow="never">
      <el-table :data="logs" border stripe v-loading="loading" empty-text="暂无审计记录">
        <el-table-column prop="created_at" label="时间" width="180" />
        <el-table-column prop="username" label="操作人" width="120" />
        <el-table-column prop="action" label="操作" width="130">
          <template #default="{ row }">
            <el-tag size="small" :type="actionType(row.action)">{{ row.action }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="resource_type" label="资源类型" width="110" />
        <el-table-column prop="resource_name" label="资源名" min-width="200" />
        <el-table-column prop="namespace" label="命名空间" width="120" />
        <el-table-column prop="result" label="结果" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.result === 'SUCCESS' ? 'success' : 'danger'">
              {{ row.result === 'SUCCESS' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getAuditLogs } from '@/api/alerts'

const logs = ref<any[]>([])
const loading = ref(false)

function actionType(a: string): string {
  if (a.includes('DELETE')) return 'danger'
  if (a.includes('SCALE')) return 'warning'
  return 'info'
}

async function load() {
  loading.value = true
  try { logs.value = await getAuditLogs(200) as any }
  finally { loading.value = false }
}

onMounted(load)
</script>