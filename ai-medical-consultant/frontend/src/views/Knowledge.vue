<template>
  <div class="page knowledge-page">
    <el-card shadow="never" class="upload-card">
      <template #header>
        <div class="card-header">
          <div>
            <div class="card-title">上传文件</div>
            <div class="text-muted">支持 txt / md / docx / json / jsonl，单文件 ≤ 10MB，整文件保存、不切片</div>
          </div>
        </div>
      </template>

      <el-upload
        :show-file-list="false"
        :before-upload="beforeUpload"
        :http-request="onUpload"
        accept=".txt,.md,.docx,.json,.jsonl"
        drag
        class="uploader"
        :disabled="uploading"
      >
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="el-upload__text">将文件拖到此处，或<em>点击选择文件</em></div>
      </el-upload>

      <div v-if="uploading" class="uploading-hint">
        <el-icon class="is-loading"><Loading /></el-icon>
        正在上传「{{ uploadingName }}」…
      </div>
    </el-card>

    <el-card shadow="never" class="list-card" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span class="card-title">文件列表</span>
          <span class="text-muted">共 {{ files.length }} 个 · 点击文件名可预览</span>
        </div>
      </template>

      <el-table v-if="files.length" :data="files" stripe>
        <el-table-column prop="filename" label="文件名" min-width="260">
          <template #default="{ row }">
            <button type="button" class="file-link" :title="row.filename" @click="openPreview(row)">
              {{ row.filename }}
            </button>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="110" align="center">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column label="上传时间" width="180" align="center">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button link type="danger" @click.stop="removeFile(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="还没有上传文件" />
    </el-card>

    <el-dialog
      v-model="previewVisible"
      :title="previewTitle"
      width="min(920px, 92vw)"
      class="preview-dialog"
      destroy-on-close
      @closed="resetPreview"
    >
      <div v-loading="previewLoading" class="preview-body">
        <p v-if="previewTruncated" class="preview-tip">内容较长，仅显示前 30 万字符。</p>
        <pre class="preview-content" :class="{ 'is-json': previewFormat === 'json' }">{{ previewContent }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { UploadFilled, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { knowledgeApi } from '../api'
import { confirmDeleteTwice } from '../utils/confirm'

const files = ref([])
const loading = ref(false)
const uploading = ref(false)
const uploadingName = ref('')
const ALLOWED = ['txt', 'md', 'docx', 'json', 'jsonl']

const previewVisible = ref(false)
const previewLoading = ref(false)
const previewTitle = ref('')
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
  return new Date(value).toLocaleString('zh-CN')
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

async function loadFiles() {
  loading.value = true
  try {
    files.value = await knowledgeApi.listFiles()
  } finally {
    loading.value = false
  }
}

async function onUpload({ file }) {
  uploading.value = true
  uploadingName.value = file.name
  try {
    await knowledgeApi.upload(file)
    ElMessage.success('上传成功')
    await loadFiles()
  } finally {
    uploading.value = false
    uploadingName.value = ''
  }
}

async function openPreview(row) {
  previewVisible.value = true
  previewTitle.value = row.filename
  previewLoading.value = true
  previewContent.value = ''
  previewTruncated.value = false
  try {
    const res = await knowledgeApi.previewFile(row.id)
    previewContent.value = res.content || ''
    previewFormat.value = res.format || 'text'
    previewTruncated.value = Boolean(res.truncated)
  } catch {
    previewVisible.value = false
  } finally {
    previewLoading.value = false
  }
}

function resetPreview() {
  previewContent.value = ''
  previewFormat.value = 'text'
  previewTruncated.value = false
}

async function removeFile(row) {
  const ok = await confirmDeleteTwice(
    `将删除文件「${row.filename}」。`,
    `再次确认：删除后无法恢复，确定删除「${row.filename}」吗？`
  )
  if (!ok) return
  const res = await knowledgeApi.deleteFile(row.id)
  ElMessage.success(res.message || '已删除')
  await loadFiles()
}

onMounted(loadFiles)
</script>

<style scoped>
.knowledge-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 960px;
}
.upload-card,
.list-card {
  border-radius: 12px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.card-title {
  font-size: 16px;
  font-weight: 700;
  color: #182230;
}
.text-muted {
  margin-top: 4px;
  font-size: 12px;
  color: #667085;
}
.uploader {
  width: 100%;
}
.uploader :deep(.el-upload),
.uploader :deep(.el-upload-dragger) {
  width: 100%;
}
.upload-icon {
  font-size: 40px;
  color: #98a2b3;
  margin-bottom: 8px;
}
.uploading-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  font-size: 13px;
  color: #0f7c43;
}
.file-link {
  border: none;
  background: none;
  padding: 0;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #0f7c43;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
}
.file-link:hover {
  color: #0b5f34;
  text-decoration: underline;
}
.preview-body {
  min-height: 200px;
  max-height: min(72vh, 720px);
  overflow: auto;
}
.preview-tip {
  margin: 0 0 10px;
  font-size: 12px;
  color: #b54708;
}
.preview-content {
  margin: 0;
  padding: 14px 16px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e8edf3;
  color: #344054;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
}
.preview-content.is-json {
  font-size: 12px;
}
.preview-dialog :deep(.el-dialog__body) {
  padding-top: 8px;
}
</style>
