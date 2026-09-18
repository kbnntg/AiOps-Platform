<template>
  <div>
    <el-card shadow="never">
      <div class="toolbar">
        <el-select v-model="ns" style="width:200px" @change="load">
          <el-option v-for="n in namespaces" :key="n" :label="n" :value="n" />
        </el-select>
        <el-button type="primary" @click="load">刷新</el-button>
      </div>
    </el-card>

    <el-card shadow="never" class="mt-4">
      <el-table :data="deployments" border stripe v-loading="loading" empty-text="暂无 Deployment">
        <el-table-column prop="name" label="名称" min-width="200" />
        <el-table-column label="副本数" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.ready_replicas >= row.replicas ? 'success' : 'warning'" size="small">
              {{ row.ready_replicas }} / {{ row.replicas }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="镜像" min-width="250">
          <template #default="{ row }"><code>{{ row.images?.[0] }}</code></template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="openScale(row)"
                       :disabled="authStore.role !== 'admin'">扩容</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialog" :title="`扩容: ${current.name}`" width="400px">
      <el-form label-width="80px">
        <el-form-item label="当前副本"><el-input-number :model-value="current.current" disabled /></el-form-item>
        <el-form-item label="目标副本"><el-input-number v-model="current.target" :min="0" :max="50" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="handleScale">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getDeployments, scaleDeployment } from '@/api/deployments'
import { getNamespaces } from '@/api/metrics'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const ns = ref('privatization')
const namespaces = ref<string[]>([])
const deployments = ref<any[]>([])
const loading = ref(false)
const dialog = ref(false)
const current = ref({ name: '', current: 0, target: 0 })

async function loadNamespaces() { namespaces.value = await getNamespaces() as any }
async function load() {
  loading.value = true
  try { deployments.value = await getDeployments(ns.value) as any }
  finally { loading.value = false }
}

function openScale(row: any) {
  current.value = { name: row.name, current: row.replicas, target: row.replicas }
  dialog.value = true
}

async function handleScale() {
  try {
    await scaleDeployment(ns.value, current.value.name, current.value.target)
    ElMessage.success('扩容成功')
    dialog.value = false
    load()
  } catch (e) {}
}

onMounted(() => { loadNamespaces(); load() })
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; }
.mt-4 { margin-top: 16px; }
</style>