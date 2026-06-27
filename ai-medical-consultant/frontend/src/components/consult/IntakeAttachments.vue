<template>
  <div class="intake-attachments">
    <el-upload
      class="attachment-uploader"
      drag
      multiple
      :show-file-list="false"
      :disabled="uploading"
      :http-request="handleUpload"
      :before-upload="beforeUpload"
      accept="image/*,.pdf,.doc,.docx,.txt,.md,.xls,.xlsx,.ppt,.pptx,.zip,.rar,.7z,.csv"
    >
      <div class="upload-inner">
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <p class="upload-title">拖拽文件到此处，或点击上传</p>
        <p class="upload-hint">支持图片、PDF、Word、Excel 等常见格式 · 单个文件 ≤20MB</p>
      </div>
    </el-upload>

    <div v-if="uploading" class="attachment-uploading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>正在上传「{{ uploadingName }}」…</span>
    </div>

    <div v-if="modelValue.length" class="attachment-grid">
      <article
        v-for="(item, index) in modelValue"
        :key="item.id"
        class="attachment-card"
        :class="{
          'is-image': item.isImage,
          'is-dragging': dragIndex === index,
          'is-drop-target': dropIndex === index && dragIndex !== index
        }"
        @dragover.prevent="onCardDragOver(index)"
        @drop.prevent="onCardDrop(index)"
      >
        <button
          type="button"
          class="attachment-drag-handle"
          draggable="true"
          aria-label="拖拽调整附件顺序"
          title="拖拽调整顺序"
          @dragstart="onCardDragStart(index, $event)"
          @dragend="onCardDragEnd"
        >
          <span class="attachment-drag-grip" aria-hidden="true">
            <i /><i /><i /><i /><i /><i />
          </span>
        </button>

        <button type="button" class="attachment-remove" aria-label="删除附件" @click="removeAttachment(item)">
          <svg viewBox="0 0 12 12" aria-hidden="true">
            <path d="M2.5 2.5l7 7M9.5 2.5l-7 7" />
          </svg>
        </button>

        <button
          v-if="item.isImage"
          type="button"
          class="attachment-preview"
          @click="openPreview(item)"
        >
          <img :src="previewUrls[item.id]" :alt="item.name" loading="lazy" />
        </button>

        <div v-else class="attachment-file">
          <el-icon class="attachment-file-icon"><Document /></el-icon>
          <span class="attachment-file-name" :title="item.name">{{ item.name }}</span>
        </div>

        <div class="attachment-meta">
          <span class="attachment-name" :title="item.name">{{ item.name }}</span>
          <span class="attachment-size">{{ formatSize(item.size) }}</span>
        </div>

        <button type="button" class="attachment-download" @click="downloadAttachment(item)">下载</button>
      </article>
    </div>

    <el-image-viewer
      v-if="previewVisible"
      :url-list="previewList"
      :initial-index="previewIndex"
      teleported
      @close="previewVisible = false"
    />
  </div>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Loading, UploadFilled } from '@element-plus/icons-vue'
import { consultApi } from '../../api'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  sessionId: { type: Number, default: null },
  ensureSession: { type: Function, required: true }
})

const emit = defineEmits(['update:modelValue', 'changed'])

const uploading = ref(false)
const uploadingName = ref('')
const previewUrls = ref({})
const previewVisible = ref(false)
const previewList = ref([])
const previewIndex = ref(0)
const dragIndex = ref(null)
const dropIndex = ref(null)
let previewToken = 0

const MAX_SIZE = 20 * 1024 * 1024

function formatSize(size) {
  const value = Number(size) || 0
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / (1024 * 1024)).toFixed(1)} MB`
}

function beforeUpload(file) {
  if (!file?.size) {
    ElMessage.warning('文件为空')
    return false
  }
  if (file.size > MAX_SIZE) {
    ElMessage.warning('单个文件不能超过 20MB')
    return false
  }
  return true
}

async function resolveSessionId() {
  if (props.sessionId) return props.sessionId
  const id = await props.ensureSession()
  if (!id) throw new Error('请先保存问诊后再上传附件')
  return id
}

async function handleUpload(options) {
  const file = options.file
  uploading.value = true
  uploadingName.value = file.name
  try {
    const sessionId = await resolveSessionId()
    const created = await consultApi.uploadAttachment(sessionId, file)
    const next = [...props.modelValue, created]
    emit('update:modelValue', next)
    emit('changed')
    if (created.isImage) {
      await loadPreviewUrl(sessionId, created.id)
    }
    ElMessage.success('附件已上传')
    options.onSuccess?.(created)
  } catch (error) {
    options.onError?.(error)
  } finally {
    uploading.value = false
    uploadingName.value = ''
  }
}

async function loadPreviewUrl(sessionId, attachmentId) {
  if (!sessionId || !attachmentId || previewUrls.value[attachmentId]) return
  const token = previewToken
  try {
    const blob = await consultApi.getAttachmentBlob(sessionId, attachmentId)
    if (token !== previewToken || sessionId !== props.sessionId) return
    previewUrls.value = {
      ...previewUrls.value,
      [attachmentId]: URL.createObjectURL(blob)
    }
  } catch {
    // ignore preview load errors
  }
}

async function refreshPreviews() {
  const token = ++previewToken
  revokePreviewUrls()
  const sessionId = props.sessionId
  if (!sessionId) return
  const imageItems = props.modelValue.filter((item) => item.isImage)
  for (const item of imageItems) {
    if (token !== previewToken || sessionId !== props.sessionId) return
    await loadPreviewUrl(sessionId, item.id)
  }
}

function revokePreviewUrls() {
  Object.values(previewUrls.value).forEach((url) => URL.revokeObjectURL(url))
  previewUrls.value = {}
}

async function openPreview(item) {
  if (!props.sessionId) return
  if (!previewUrls.value[item.id]) {
    await loadPreviewUrl(props.sessionId, item.id)
  }
  const images = props.modelValue.filter((entry) => entry.isImage)
  previewList.value = images
    .map((entry) => previewUrls.value[entry.id])
    .filter(Boolean)
  previewIndex.value = Math.max(0, images.findIndex((entry) => entry.id === item.id))
  if (previewList.value.length) previewVisible.value = true
}

async function downloadAttachment(item) {
  if (!props.sessionId) return
  try {
    const blob = await consultApi.getAttachmentBlob(props.sessionId, item.id, true)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = item.name || 'attachment'
    link.click()
    URL.revokeObjectURL(url)
  } catch {
    ElMessage.error('下载失败')
  }
}

function reorderAttachments(fromIndex, toIndex) {
  const items = [...props.modelValue]
  if (fromIndex === toIndex || fromIndex < 0 || toIndex < 0 || fromIndex >= items.length || toIndex >= items.length) {
    return
  }
  const [moved] = items.splice(fromIndex, 1)
  items.splice(toIndex, 0, moved)
  emit('update:modelValue', items)
  emit('changed')
}

function onCardDragStart(index, event) {
  dragIndex.value = index
  dropIndex.value = index
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', String(index))
}

function onCardDragOver(index) {
  if (dragIndex.value === null) return
  dropIndex.value = index
}

function onCardDrop(index) {
  if (dragIndex.value !== null) reorderAttachments(dragIndex.value, index)
  onCardDragEnd()
}

function onCardDragEnd() {
  dragIndex.value = null
  dropIndex.value = null
}

async function removeAttachment(item) {
  if (!props.sessionId) {
    emit(
      'update:modelValue',
      props.modelValue.filter((entry) => entry.id !== item.id)
    )
    emit('changed')
    return
  }
  try {
    await consultApi.deleteAttachment(props.sessionId, item.id)
    if (previewUrls.value[item.id]) {
      URL.revokeObjectURL(previewUrls.value[item.id])
      const nextUrls = { ...previewUrls.value }
      delete nextUrls[item.id]
      previewUrls.value = nextUrls
    }
    emit(
      'update:modelValue',
      props.modelValue.filter((entry) => entry.id !== item.id)
    )
    emit('changed')
    ElMessage.success('附件已删除')
  } catch {
    ElMessage.error('删除失败')
  }
}

watch(
  () => [props.sessionId, props.modelValue],
  () => {
    refreshPreviews()
  },
  { immediate: true, deep: true }
)

onBeforeUnmount(() => {
  revokePreviewUrls()
})
</script>

<style scoped>
.intake-attachments {
  display: grid;
  gap: 12px;
}
.attachment-uploader :deep(.el-upload) {
  width: 100%;
}
.attachment-uploader :deep(.el-upload-dragger) {
  width: 100%;
  padding: 18px 16px;
  border: 1px dashed #cfd9e6;
  border-radius: 8px;
  background: #fbfcfd;
}
.attachment-uploader :deep(.el-upload-dragger:hover) {
  border-color: #b9d8c7;
  background: #f7fcf9;
}
.upload-inner {
  display: grid;
  gap: 4px;
  justify-items: center;
  color: #667085;
}
.upload-icon {
  font-size: 28px;
  color: #0f7c43;
}
.upload-title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: #344054;
}
.upload-hint {
  margin: 0;
  font-size: 11px;
  color: #98a2b3;
}
.attachment-uploading {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #667085;
  font-size: 12px;
}
.attachment-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
  gap: 10px;
}
.attachment-card {
  position: relative;
  display: grid;
  gap: 6px;
  padding: 8px;
  border: 1px solid #e6ebf2;
  border-radius: 8px;
  background: #fff;
  transition: opacity 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.attachment-card.is-dragging {
  opacity: 0.58;
}
.attachment-card.is-drop-target {
  border-color: #9fd4b6;
  box-shadow: inset 0 0 0 2px #b9d8c7;
}
.attachment-card.is-image {
  grid-template-rows: auto auto auto;
}
.attachment-drag-handle {
  position: absolute;
  top: 6px;
  left: 6px;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  border: 1px solid #e4e9ef;
  border-radius: 50%;
  background: rgba(248, 250, 252, 0.94);
  color: #98a2b3;
  cursor: grab;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.attachment-drag-grip {
  display: grid;
  grid-template-columns: repeat(2, 2px);
  gap: 2px 3px;
}
.attachment-drag-grip i {
  display: block;
  width: 2px;
  height: 2px;
  border-radius: 50%;
  background: currentColor;
}
.attachment-card:hover .attachment-drag-handle {
  border-color: #d7e8de;
  background: rgba(244, 251, 247, 0.96);
  color: #6b8f7a;
}
.attachment-drag-handle:hover {
  border-color: #b9d8c7;
  background: #ecf8f1;
  color: #0f7c43;
}
.attachment-drag-handle:active,
.attachment-card.is-dragging .attachment-drag-handle {
  cursor: grabbing;
  border-color: #9fd4b6;
  background: #dff5e9;
  color: #0a6b39;
}
.attachment-remove {
  position: absolute;
  top: 6px;
  right: 6px;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  border: 1px solid #f5cfc5;
  border-radius: 50%;
  background: rgba(255, 243, 239, 0.92);
  color: #d85a45;
  cursor: pointer;
}
.attachment-remove svg {
  width: 11px;
  height: 11px;
}
.attachment-remove svg path {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
}
.attachment-preview {
  display: block;
  width: 100%;
  aspect-ratio: 1;
  padding: 0;
  border: none;
  border-radius: 6px;
  overflow: hidden;
  background: #f8fafc;
  cursor: zoom-in;
}
.attachment-preview img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.attachment-file {
  display: grid;
  justify-items: center;
  gap: 8px;
  min-height: 96px;
  padding: 16px 8px 8px;
  border-radius: 6px;
  background: #f8fafc;
}
.attachment-file-icon {
  font-size: 28px;
  color: #667085;
}
.attachment-file-name {
  width: 100%;
  text-align: center;
  color: #475467;
  font-size: 11px;
  line-height: 1.35;
  word-break: break-all;
}
.attachment-meta {
  display: grid;
  gap: 2px;
}
.attachment-name {
  color: #344054;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.attachment-size {
  color: #98a2b3;
  font-size: 10px;
}
.attachment-download {
  justify-self: start;
  padding: 0;
  border: none;
  background: transparent;
  color: #0f7c43;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}
.attachment-download:hover {
  color: #0a6b39;
}
</style>
