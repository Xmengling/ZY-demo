<template>
  <div class="page records-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="card-header-text">
            <h2 class="card-title">医案记录</h2>
            <p class="card-subtitle">{{ listSummary }}</p>
          </div>
          <el-button type="primary" @click="$router.push('/consult')">
            <el-icon><Plus /></el-icon>
            <span>新建问诊</span>
          </el-button>
        </div>
      </template>

      <div class="record-filters">
        <el-input
          v-model="filters.chief_complaint"
          clearable
          placeholder="按主诉搜索"
          @keyup.enter="load"
          @clear="load"
        />
        <el-input
          v-model="filters.patient_name"
          clearable
          placeholder="按患者搜索"
          @keyup.enter="load"
          @clear="load"
        />
        <el-input
          v-model="filters.doctor"
          clearable
          placeholder="按主诊医生搜索"
          @keyup.enter="load"
          @clear="load"
        />
        <el-button type="primary" plain @click="load">搜索</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>

      <div v-if="selectedRows.length" class="bulk-bar">
        <span class="bulk-count">已选 {{ selectedRows.length }} 条</span>
        <el-button
          type="primary"
          plain
          :disabled="selectedRows.length < 2"
          @click="openMergeDialog"
        >
          合并医案
        </el-button>
        <el-button type="danger" plain @click="bulkRemove">批量删除</el-button>
        <el-button text @click="clearSelection">取消选择</el-button>
      </div>

      <p v-if="hasActiveFilters && total" class="filter-hint">已按当前条件筛选，共 {{ total }} 条结果</p>

      <el-table
        ref="tableRef"
        :data="pagedSessions"
        stripe
        row-key="id"
        class="records-table"
        @row-click="openRecord"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="46" reserve-selection />
        <el-table-column prop="chief_complaint" label="主诉" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="cell-ellipsis">{{ chiefComplaintText(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="patient_name" label="患者" width="112" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="cell-ellipsis">{{ displayCell(row.patient_name) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="doctor" label="主诊医生" width="112" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="cell-ellipsis">{{ displayCell(row.doctor) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="modern_diagnosis" label="现代诊断" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="cell-ellipsis cell-muted">{{ displayCell(row.modern_diagnosis) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="88" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)" effect="light" round>
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="152" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="cell-ellipsis cell-time">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="72" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="danger" @click.stop="remove(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="total" class="record-pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          background
          layout="total, sizes, prev, pager, next, jumper"
        />
      </div>

      <el-empty v-if="!total" :description="emptyDescription">
        <el-button v-if="!hasActiveFilters" type="primary" @click="$router.push('/consult')">
          新建问诊
        </el-button>
        <el-button v-else @click="resetFilters">清空筛选</el-button>
      </el-empty>
    </el-card>

    <el-dialog
      v-model="mergeDialogVisible"
      title="合并医案"
      width="min(560px, 92vw)"
      destroy-on-close
    >
      <p class="merge-tip">
        将把 {{ selectedRows.length }} 条医案合并为 1 条。症状、病理、处方会合并到保留医案中，其余记录将删除。
      </p>
      <div class="merge-target-label">保留哪一条作为主医案？</div>
      <el-radio-group v-model="mergeTargetId" class="merge-target-list">
        <el-radio
          v-for="row in selectedRowsSorted"
          :key="row.id"
          :value="row.id"
          class="merge-target-item"
        >
          <span class="merge-target-title">{{ chiefComplaintText(row) }}</span>
          <span class="merge-target-meta">
            {{ displayCell(row.patient_name) }} · {{ formatTime(row.created_at) }}
          </span>
        </el-radio>
      </el-radio-group>
      <template #footer>
        <el-button @click="mergeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="merging" @click="confirmMerge">确认合并</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { consultApi } from '../api'
import { confirmDeleteTwice } from '../utils/confirm'

const router = useRouter()
const sessions = ref([])
const tableRef = ref(null)
const selectedRows = ref([])
const page = ref(1)
const pageSize = ref(10)
const mergeDialogVisible = ref(false)
const mergeTargetId = ref(null)
const merging = ref(false)
const filters = reactive({
  chief_complaint: '',
  patient_name: '',
  doctor: ''
})

const total = computed(() => sessions.value.length)

const hasActiveFilters = computed(
  () =>
    Boolean(filters.chief_complaint.trim()) ||
    Boolean(filters.patient_name.trim()) ||
    Boolean(filters.doctor.trim())
)

const pagedSessions = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return sessions.value.slice(start, start + pageSize.value)
})

const selectedRowsSorted = computed(() =>
  [...selectedRows.value].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  )
)

const listSummary = computed(() => {
  if (!total.value) {
    return hasActiveFilters.value ? '未找到匹配的医案' : '暂无医案，可先新建问诊'
  }
  if (total.value <= pageSize.value) {
    return `共 ${total.value} 条`
  }
  const start = (page.value - 1) * pageSize.value + 1
  const end = Math.min(page.value * pageSize.value, total.value)
  return `第 ${start}–${end} 条，共 ${total.value} 条`
})

const emptyDescription = computed(() =>
  hasActiveFilters.value ? '没有符合搜索条件的医案' : '还没有医案记录'
)

watch(pageSize, () => {
  page.value = 1
})

function displayCell(value, fallback = '—') {
  const text = String(value ?? '')
    .replace(/[\r\n]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return text || fallback
}

function chiefComplaintText(row) {
  return displayCell(row.chief_complaint || row.title)
}

function formatTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function statusText(status) {
  const map = { collecting: '采集中', analyzed: '已分析', completed: '已完成' }
  return map[status] || '采集中'
}

function statusType(status) {
  const map = { collecting: 'info', analyzed: 'warning', completed: 'success' }
  return map[status] || 'info'
}

function onSelectionChange(rows) {
  selectedRows.value = rows
}

function clearSelection() {
  tableRef.value?.clearSelection()
  selectedRows.value = []
}

function openRecord(row) {
  router.push({ path: `/consult/${row.id}`, query: { from: 'records' } })
}

async function load() {
  sessions.value = await consultApi.listSessions({
    case_only: true,
    chief_complaint: filters.chief_complaint.trim() || undefined,
    patient_name: filters.patient_name.trim() || undefined,
    doctor: filters.doctor.trim() || undefined
  })
  page.value = 1
  clearSelection()
}

async function resetFilters() {
  filters.chief_complaint = ''
  filters.patient_name = ''
  filters.doctor = ''
  await load()
}

async function remove(id) {
  const ok = await confirmDeleteTwice('将删除该条医案及其全部对话内容，删除后无法恢复。')
  if (!ok) return
  await consultApi.deleteSession(id)
  await load()
  ElMessage.success('已删除')
}

async function bulkRemove() {
  const count = selectedRows.value.length
  if (!count) return
  const ok = await confirmDeleteTwice(`将删除已选的 ${count} 条医案及其全部对话内容，删除后无法恢复。`)
  if (!ok) return
  await consultApi.bulkDeleteSessions({
    session_ids: selectedRows.value.map((row) => row.id)
  })
  await load()
  ElMessage.success(`已删除 ${count} 条医案`)
}

function openMergeDialog() {
  if (selectedRows.value.length < 2) {
    ElMessage.warning('请至少选择 2 条医案再合并')
    return
  }
  mergeTargetId.value = selectedRowsSorted.value[0]?.id ?? selectedRows.value[0]?.id
  mergeDialogVisible.value = true
}

async function confirmMerge() {
  if (!mergeTargetId.value || selectedRows.value.length < 2) return
  merging.value = true
  try {
    const res = await consultApi.mergeSessions({
      session_ids: selectedRows.value.map((row) => row.id),
      target_id: mergeTargetId.value
    })
    mergeDialogVisible.value = false
    await load()
    ElMessage.success(`已合并 ${res.merged_count} 条医案`)
    if (res.session_id) {
      router.push({ path: `/consult/${res.session_id}`, query: { from: 'records' } })
    }
  } finally {
    merging.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.records-page :deep(.el-card__header) {
  padding: 14px 18px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-header-text {
  min-width: 0;
}

.card-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.3;
  color: #182230;
}

.card-subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.4;
  color: #98a2b3;
}

.card-header :deep(.el-button) {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.record-filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr)) auto auto;
  gap: 10px;
  margin-bottom: 12px;
  align-items: center;
}

.bulk-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid #dbe7ff;
  border-radius: 10px;
  background: #f5f8ff;
}

.bulk-count {
  font-size: 13px;
  font-weight: 600;
  color: #344054;
  margin-right: 4px;
}

.filter-hint {
  margin: 0 0 10px;
  font-size: 12px;
  color: #667085;
}

.records-table {
  cursor: pointer;
}

.records-table :deep(.el-table__header th) {
  font-size: 13px;
  font-weight: 700;
  color: #475467;
  background: #f8fafc;
}

.records-table :deep(.el-table__cell) {
  padding-top: 11px;
  padding-bottom: 11px;
  font-size: 13px;
  color: #344054;
}

.records-table :deep(.cell) {
  line-height: 1.4;
}

.cell-ellipsis {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell-muted {
  color: #667085;
}

.cell-time {
  font-variant-numeric: tabular-nums;
  color: #667085;
  font-size: 12px;
}

.record-pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 4px;
  border-top: 1px solid #f0f3f7;
}

.records-page :deep(.el-empty) {
  padding: 32px 0 24px;
}

.merge-tip {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.6;
  color: #475467;
}

.merge-target-label {
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #344054;
}

.merge-target-list {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
  width: 100%;
}

.merge-target-item {
  display: flex;
  align-items: flex-start;
  margin: 0;
  padding: 10px 12px;
  border: 1px solid #e8eef6;
  border-radius: 8px;
  width: 100%;
  height: auto;
  white-space: normal;
}

.merge-target-item :deep(.el-radio__label) {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.45;
}

.merge-target-title {
  font-size: 13px;
  color: #182230;
}

.merge-target-meta {
  font-size: 12px;
  color: #98a2b3;
}

@media (max-width: 900px) {
  .record-filters {
    grid-template-columns: 1fr;
  }

  .record-pagination-wrap {
    justify-content: center;
  }

  .record-pagination-wrap :deep(.el-pagination) {
    flex-wrap: wrap;
    justify-content: center;
  }
}
</style>
