<template>
  <div class="page knowledge-page">
    <aside class="kb-sidebar panel">
      <div class="kb-upload-bar">
        <div class="kb-upload-text">
          <span class="kb-upload-title">上传资料</span>
          <span class="kb-upload-hint">txt / md / docx / json / jsonl · ≤10MB</span>
        </div>
        <el-upload
          :show-file-list="false"
          :before-upload="beforeUpload"
          :http-request="onUpload"
          accept=".txt,.md,.docx,.json,.jsonl"
          class="kb-uploader"
          :disabled="uploading"
        >
          <el-button type="primary" size="small" :loading="uploading">
            <el-icon v-if="!uploading"><UploadFilled /></el-icon>
            {{ uploading ? '上传中' : '选择文件' }}
          </el-button>
        </el-upload>
      </div>

      <div v-if="uploading && uploadingName" class="kb-uploading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>正在上传「{{ uploadingName }}」</span>
      </div>

      <div class="kb-list-head">
        <span class="kb-list-title">文件列表</span>
        <span class="kb-list-count">{{ files.length }} 个</span>
      </div>

      <div v-loading="loading" class="kb-list-body">
        <el-table
          v-if="files.length"
          :data="files"
          stripe
          highlight-current-row
          class="kb-table"
          :row-class-name="rowClassName"
          @row-click="openPreview"
        >
          <el-table-column label="文件名" min-width="0" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="file-name">{{ row.filename }}</span>
            </template>
          </el-table-column>
          <el-table-column label="大小" width="72" align="right">
            <template #default="{ row }">
              <span class="file-meta">{{ formatSize(row.file_size) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="" width="96" align="center">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click.stop="renameFile(row)">重命名</el-button>
              <el-button link type="danger" size="small" @click.stop="removeFile(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-else class="kb-empty" description="暂无文件，请先上传">
          <el-upload
            :show-file-list="false"
            :before-upload="beforeUpload"
            :http-request="onUpload"
            accept=".txt,.md,.docx,.json,.jsonl"
            :disabled="uploading"
          >
            <el-button type="primary" plain size="small">上传第一个文件</el-button>
          </el-upload>
        </el-empty>
      </div>
    </aside>

    <section class="kb-preview panel">
      <header class="kb-preview-head">
        <div class="kb-preview-head-main">
          <el-icon class="kb-preview-icon" :size="18"><Document /></el-icon>
          <div class="kb-preview-titles">
            <h2 class="kb-preview-name">{{ activeFile?.filename || '文件预览' }}</h2>
            <p v-if="activeFile" class="kb-preview-meta">
              {{ formatSize(activeFile.file_size) }} · {{ formatTime(activeFile.created_at) }}
            </p>
            <p v-else class="kb-preview-meta">在左侧选择文件即可阅读全文</p>
          </div>
        </div>
        <el-tag v-if="previewTruncated" type="warning" size="small" effect="light">已截断</el-tag>
      </header>

      <div v-loading="previewLoading" class="kb-preview-body">
        <p v-if="previewTruncated" class="preview-tip">内容较长，仅显示前 30 万字符。</p>
        <pre
          v-if="activeFileId && previewContent"
          class="preview-content"
          :class="{ 'is-json': previewFormat === 'json' }"
        >{{ previewContent }}</pre>
        <div v-else-if="!previewLoading" class="kb-preview-placeholder">
          <el-icon :size="40" color="#c5cdd8"><Reading /></el-icon>
          <p>点击左侧文件名，在此阅读资料内容</p>
          <span>支持整文件预览，供 AI 问答检索引用</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Document, Loading, Reading, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { knowledgeApi } from '../api'
import { confirmDeleteTwice } from '../utils/confirm'

const files = ref([])
const loading = ref(false)
const uploading = ref(false)
const uploadingName = ref('')
const ALLOWED = ['txt', 'md', 'docx', 'json', 'jsonl']

const activeFileId = ref(null)
const activeFile = ref(null)
const previewLoading = ref(false)
const previewContent = ref('')
const previewFormat = ref('text')
const previewTruncated = ref(false)

function formatSize(bytes) {
  const n = Number(bytes) || 0
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(2)} MB`
}

function formatTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function beforeUpload(file) {
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!ALLOWED.includes(ext)) {
    ElMessage.error(`不支持的文件类型：.${ext}`)
    return false
  }
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error('文件超过 10MB 上限')
    return false
  }
  return true
}

function rowClassName({ row }) {
  return row.id === activeFileId.value ? 'is-active-row' : ''
}

function resetPreview() {
  activeFileId.value = null
  activeFile.value = null
  previewContent.value = ''
  previewFormat.value = 'text'
  previewTruncated.value = false
}

async function loadFiles() {
  loading.value = true
  try {
    files.value = await knowledgeApi.listFiles()
    if (activeFileId.value && !files.value.some((item) => item.id === activeFileId.value)) {
      resetPreview()
    }
  } finally {
    loading.value = false
  }
}

async function onUpload({ file }) {
  uploading.value = true
  uploadingName.value = file.name
  try {
    const created = await knowledgeApi.upload(file)
    ElMessage.success('上传成功')
    await loadFiles()
    const hit = files.value.find((item) => item.id === created?.id) || files.value[0]
    if (hit) await openPreview(hit)
  } finally {
    uploading.value = false
    uploadingName.value = ''
  }
}

async function openPreview(row) {
  if (!row?.id) return
  activeFileId.value = row.id
  activeFile.value = row
  previewLoading.value = true
  previewContent.value = ''
  previewTruncated.value = false
  try {
    const res = await knowledgeApi.previewFile(row.id)
    previewContent.value = res.content || '（文件为空）'
    previewFormat.value = res.format || 'text'
    previewTruncated.value = Boolean(res.truncated)
  } catch {
    previewContent.value = ''
    activeFileId.value = null
    activeFile.value = null
  } finally {
    previewLoading.value = false
  }
}

async function renameFile(row) {
  let value
  try {
    const result = await ElMessageBox.prompt('修改显示名称，扩展名须与原文件一致。', '重命名', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValue: row.filename,
      inputValidator: (input) => {
        if (!input?.trim()) return '文件名不能为空'
        return true
      }
    })
    value = result.value?.trim()
  } catch {
    return
  }
  if (!value) return
  try {
    const updated = await knowledgeApi.renameFile(row.id, value)
    ElMessage.success(`已重命名为「${updated.filename}」`)
    if (activeFileId.value === row.id && activeFile.value) {
      activeFile.value = { ...activeFile.value, filename: updated.filename }
    }
    await loadFiles()
  } catch {
    /* axios 拦截器已提示错误 */
  }
}

async function removeFile(row) {
  const ok = await confirmDeleteTwice(`将删除文件「${row.filename}」，删除后无法恢复。`)
  if (!ok) return
  const res = await knowledgeApi.deleteFile(row.id)
  ElMessage.success(res.message || '已删除')
  if (activeFileId.value === row.id) resetPreview()
  await loadFiles()
}

onMounted(loadFiles)
</script>

<style scoped>
.knowledge-page {
  display: grid;
  grid-template-columns: minmax(320px, 380px) minmax(0, 1fr);
  gap: 12px;
  max-width: none;
  margin: 0;
  padding: 12px;
  height: calc(100vh - 44px);
  box-sizing: border-box;
}

.panel {
  background: #fff;
  border: 1px solid #e3eaf3;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
  min-height: 0;
  overflow: hidden;
}

.kb-sidebar {
  display: flex;
  flex-direction: column;
}

.kb-upload-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid #eef2f6;
  background: linear-gradient(180deg, #fff 0%, #f8fbff 100%);
}

.kb-upload-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.kb-upload-title {
  font-size: 14px;
  font-weight: 700;
  color: #182230;
}

.kb-upload-hint {
  font-size: 11px;
  color: #98a2b3;
  line-height: 1.3;
}

.kb-uploader :deep(.el-upload) {
  display: block;
}

.kb-uploading {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 12px;
  color: #0f7c43;
  background: #f3fbf7;
  border-bottom: 1px solid #e8f5ee;
}

.kb-list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px 8px;
}

.kb-list-title {
  font-size: 13px;
  font-weight: 700;
  color: #344054;
}

.kb-list-count {
  font-size: 11px;
  font-weight: 600;
  color: #98a2b3;
}

.kb-list-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0 8px 8px;
}

.kb-table {
  width: 100%;
  cursor: pointer;
}

.kb-table :deep(.el-table__header th) {
  font-size: 12px;
  font-weight: 700;
  color: #667085;
  background: #f8fafc;
}

.kb-table :deep(.el-table__cell) {
  padding: 8px 0;
  font-size: 13px;
}

.kb-table :deep(.el-table__row.is-active-row) {
  background: #ecfdf3 !important;
}

.kb-table :deep(.el-table__row.is-active-row td) {
  background: #ecfdf3 !important;
}

.file-name {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #182230;
  font-weight: 600;
}

.kb-table :deep(.el-table__row:hover) .file-name {
  color: #0f7c43;
}

.file-meta {
  font-size: 11px;
  color: #98a2b3;
  font-variant-numeric: tabular-nums;
}

.kb-empty {
  padding: 28px 12px;
}

.kb-preview {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.kb-preview-head {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid #eef2f6;
  background: linear-gradient(180deg, #fff 0%, #fafcff 100%);
}

.kb-preview-head-main {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}

.kb-preview-icon {
  flex-shrink: 0;
  margin-top: 2px;
  color: #477cff;
}

.kb-preview-titles {
  min-width: 0;
}

.kb-preview-name {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #182230;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kb-preview-meta {
  margin: 4px 0 0;
  font-size: 12px;
  color: #98a2b3;
  line-height: 1.4;
}

.kb-preview-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 14px 16px 16px;
}

.preview-tip {
  margin: 0 0 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  font-size: 12px;
  color: #b45309;
}

.preview-content {
  margin: 0;
  padding: 16px 18px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e8edf3;
  color: #344054;
  font-size: 13px;
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
}

.preview-content.is-json {
  font-size: 12px;
}

.kb-preview-placeholder {
  height: 100%;
  min-height: 280px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-align: center;
  color: #98a2b3;
}

.kb-preview-placeholder p {
  margin: 8px 0 0;
  font-size: 14px;
  font-weight: 600;
  color: #667085;
}

.kb-preview-placeholder span {
  font-size: 12px;
  color: #98a2b3;
}

@media (max-width: 900px) {
  .knowledge-page {
    grid-template-columns: 1fr;
    height: auto;
    min-height: calc(100vh - 44px);
  }

  .kb-sidebar {
    max-height: 42vh;
  }

  .kb-preview {
    min-height: 48vh;
  }
}
</style>
