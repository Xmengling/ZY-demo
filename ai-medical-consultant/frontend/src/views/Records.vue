<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>医案记录（共 {{ sessions.length }} 条）</span>
          <el-button type="primary" @click="$router.push('/consult')">
            <el-icon><Plus /></el-icon>&nbsp;新建问诊
          </el-button>
        </div>
      </template>

      <div class="record-filters">
        <el-input
          v-model="filters.chief_complaint"
          clearable
          placeholder="搜索主诉"
          @keyup.enter="load"
          @clear="load"
        />
        <el-input
          v-model="filters.patient_name"
          clearable
          placeholder="搜索患者"
          @keyup.enter="load"
          @clear="load"
        />
        <el-input
          v-model="filters.doctor"
          clearable
          placeholder="搜索主诊医生"
          @keyup.enter="load"
          @clear="load"
        />
        <el-button type="primary" plain @click="load">搜索</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>

      <el-table
        :data="sessions"
        stripe
        @row-click="(row) => $router.push({ path: `/consult/${row.id}`, query: { from: 'records' } })"
        style="cursor: pointer"
      >
        <el-table-column prop="chief_complaint" label="主诉" min-width="240">
          <template #default="{ row }">{{ row.chief_complaint || row.title || '—' }}</template>
        </el-table-column>
        <el-table-column prop="patient_name" label="患者" width="130">
          <template #default="{ row }">{{ row.patient_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="doctor" label="主诊医生" width="150">
          <template #default="{ row }">{{ row.doctor || '—' }}</template>
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
      <el-empty v-if="!sessions.length" description="还没有医案记录" />
    </el-card>
  </div>
</template>

<script setup>
import { reactive, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { consultApi } from '../api'
import { confirmDeleteTwice } from '../utils/confirm'

const sessions = ref([])
const filters = reactive({
  chief_complaint: '',
  patient_name: '',
  doctor: ''
})

function formatTime(t) {
  return new Date(t).toLocaleString('zh-CN')
}
function statusText(status) {
  const map = { collecting: '采集中', analyzed: '已分析', completed: '已完成' }
  return map[status] || '采集中'
}
async function load() {
  sessions.value = await consultApi.listSessions({
    chief_complaint: filters.chief_complaint || undefined,
    patient_name: filters.patient_name || undefined,
    doctor: filters.doctor || undefined
  })
}
async function resetFilters() {
  filters.chief_complaint = ''
  filters.patient_name = ''
  filters.doctor = ''
  await load()
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
.record-filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr)) auto auto;
  gap: 10px;
  margin-bottom: 16px;
  align-items: center;
}
@media (max-width: 900px) {
  .record-filters {
    grid-template-columns: 1fr;
  }
}
</style>
