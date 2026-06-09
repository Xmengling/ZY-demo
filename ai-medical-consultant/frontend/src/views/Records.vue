<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>问诊记录（共 {{ sessions.length }} 条）</span>
          <el-button type="primary" @click="$router.push('/consult')">
            <el-icon><Plus /></el-icon>&nbsp;新建问诊
          </el-button>
        </div>
      </template>

      <el-table :data="sessions" stripe @row-click="(row) => $router.push(`/consult/${row.id}`)" style="cursor: pointer">
        <el-table-column prop="title" label="主题" min-width="220" />
        <el-table-column prop="patient_name" label="姓名" width="110">
          <template #default="{ row }">{{ row.patient_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="phone" label="电话" width="140">
          <template #default="{ row }">{{ row.phone || '—' }}</template>
        </el-table-column>
        <el-table-column prop="modern_diagnosis" label="现代诊断" min-width="160">
          <template #default="{ row }">{{ row.modern_diagnosis || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="200">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link type="danger" @click.stop="remove(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!sessions.length" description="还没有问诊记录" />
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { consultApi } from '../api'
import { confirmDeleteTwice } from '../utils/confirm'

const sessions = ref([])

function formatTime(t) {
  return new Date(t).toLocaleString('zh-CN')
}
function statusText(status) {
  const map = { collecting: '采集中', analyzed: '已分析', completed: '已完成' }
  return map[status] || '采集中'
}
async function load() {
  sessions.value = await consultApi.listSessions()
}
async function remove(id) {
  const ok = await confirmDeleteTwice(
    '将删除该条问诊记录及其全部对话内容。',
    '再次确认：删除后无法恢复，确定要删除这条问诊记录吗？'
  )
  if (!ok) return
  await consultApi.deleteSession(id)
  await load()
  ElMessage.success('已删除')
}
onMounted(load)
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
