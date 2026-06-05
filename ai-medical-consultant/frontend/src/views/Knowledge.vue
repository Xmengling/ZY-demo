<template>
  <div class="page">
    <div class="knowledge-layout">
      <!-- 左栏：上传导入 -->
      <el-card shadow="never" class="col-card col-left">
      <template #header>
        <div class="card-header">
          <span>上传资料导入知识库</span>
          <span class="text-muted upload-tip">支持 txt / md / docx / json，单文件 ≤ 10MB</span>
        </div>
      </template>
      <div class="upload-bar">
        <div class="chunk-config">
          <div class="cfg-row">
            <span class="cfg-label">分类</span>
            <el-select
              v-model="uploadCategory"
              filterable
              allow-create
              default-first-option
              placeholder="选择或输入分类"
              style="width: 200px"
            >
              <el-option v-for="c in categories" :key="c.name" :label="`${c.name} (${c.count})`" :value="c.name" />
            </el-select>

            <span class="cfg-label">切片方式</span>
            <el-select v-model="chunkStrategy" style="width: 160px">
              <el-option label="固定长度" value="fixed" />
              <el-option label="按段落" value="paragraph" />
              <el-option label="按分隔符/标题" value="separator" />
              <el-option label="整篇不切" value="whole" />
            </el-select>
          </div>

          <div class="cfg-row" v-if="chunkStrategy === 'fixed'">
            <span class="cfg-label">片段长度</span>
            <el-input-number v-model="chunkSize" :min="50" :max="5000" :step="50" controls-position="right" style="width: 130px" />
            <span class="cfg-label">重叠长度</span>
            <el-input-number v-model="chunkOverlap" :min="0" :max="1000" :step="20" controls-position="right" style="width: 130px" />
          </div>

          <div class="cfg-row" v-else-if="chunkStrategy === 'paragraph'">
            <span class="cfg-label">合并上限</span>
            <el-input-number v-model="chunkSize" :min="50" :max="5000" :step="50" controls-position="right" style="width: 130px" />
            <span class="text-muted cfg-hint">相邻短段落合并到此长度以内</span>
          </div>

          <div class="cfg-row cfg-col" v-else-if="chunkStrategy === 'separator'">
            <span class="cfg-label">分隔符</span>
            <el-input
              v-model="separators"
              type="textarea"
              :rows="2"
              placeholder="每行一个，支持正则。填 ## 即按行首二级标题切（每个方剂一块）"
              style="width: 100%"
            />
            <span class="text-muted cfg-hint">仅在分隔符处切开，不在块内按字数截断；填 <code>##</code> 时自动按行首 <code>^##</code> 匹配</span>
          </div>
          <div class="cfg-row" v-else>
            <span class="text-muted cfg-hint">整篇作为一条知识，不做切分（适合短文档）</span>
          </div>
        </div>

        <el-upload
          :show-file-list="false"
          :before-upload="beforeUpload"
          :http-request="onPick"
          accept=".txt,.md,.docx,.json,.jsonl"
          drag
          class="uploader"
        >
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <div class="el-upload__text">将文件拖到此处，或<em>点击选择文件</em></div>
          <div class="text-muted upload-subtip">选择后可先预览切片效果，再确认导入</div>
        </el-upload>
        <div v-if="uploading" class="uploading-hint">
          <el-icon class="is-loading"><Loading /></el-icon>
          正在处理「{{ uploadingName }}」…
        </div>
      </div>

      <div v-if="sources.length" class="sources">
        <div class="sources-title">已上传来源（{{ sources.length }}）</div>
        <div class="source-list">
          <div v-for="s in sources" :key="s.source" class="source-item">
            <el-icon class="src-icon"><Document /></el-icon>
            <span class="src-name" :title="s.source">{{ s.source }}</span>
            <el-tag size="small" effect="plain">{{ s.category }}</el-tag>
            <span class="text-muted src-count">{{ s.count }} 片段</span>
            <el-button link type="danger" size="small" @click="removeSource(s.source)">删除</el-button>
          </div>
        </div>
      </div>
      </el-card>

      <!-- 右栏：搜索 + 浏览 -->
      <div class="col-right">
        <el-card shadow="never" class="col-card">
          <template #header>
            <span class="panel-title">向量检索</span>
          </template>
          <div class="search-bar">
            <el-input
              v-model="query"
              placeholder="搜索经方方证，例如：桂枝汤、发热恶寒无汗"
              :prefix-icon="Search"
              clearable
              @keyup.enter="search"
            />
            <el-button type="primary" :loading="searching" @click="search">检索</el-button>
          </div>
          <div v-if="results.length" class="results">
            <el-card v-for="r in results" :key="r.title" shadow="hover" class="result-card">
              <div class="result-head">
                <span class="result-title">{{ r.title }}</span>
                <el-tag size="small" type="success">相关度 {{ (r.score * 100).toFixed(0) }}%</el-tag>
              </div>
              <div class="result-meta">
                <el-tag size="small" effect="plain">{{ r.category }}</el-tag>
                <el-tag size="small" effect="plain" type="warning">{{ r.department }}</el-tag>
              </div>
              <p class="result-snippet">{{ r.snippet }}</p>
            </el-card>
          </div>
        </el-card>

        <el-card shadow="never" class="col-card browse-card" v-loading="listLoading">
      <template #header>
        <div class="card-header card-header--browse">
          <span class="panel-title">知识库浏览 <span class="text-muted" v-if="total">（共 {{ total }} 条）</span></span>
          <div class="browse-tools">
            <el-radio-group v-model="activeCategory" @change="onCategoryChange">
              <el-radio-button label="">全部</el-radio-button>
              <el-radio-button v-for="c in categories" :key="c.name" :label="c.name">
                {{ c.name }} ({{ c.count }})
              </el-radio-button>
            </el-radio-group>
            <el-button plain size="small" @click="openCategoryManage">分类管理</el-button>
          </div>
        </div>
      </template>
      <el-collapse v-if="docs.length" accordion>
        <el-collapse-item v-for="d in docs" :key="d.id" :name="d.id">
          <template #title>
            <span class="doc-title">{{ d.title }}</span>
            <el-tag size="small" effect="plain" style="margin-left: 10px">{{ d.category }}</el-tag>
            <el-tag size="small" effect="plain" type="warning" style="margin-left: 6px">{{ d.department }}</el-tag>
          </template>
          <p class="doc-content">{{ d.content }}</p>
        </el-collapse-item>
      </el-collapse>
      <el-empty v-else-if="!listLoading" description="暂无知识条目" />

      <div v-if="total > 0" class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 30, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="loadList"
          @size-change="onPageSizeChange"
        />
      </div>
        </el-card>
      </div>
    </div>

    <el-dialog v-model="categoryManageVisible" title="分类管理" width="560px" @open="loadCategories">
      <p class="category-manage-tip">可预先添加空分类，或重命名已有分类（将同步更新该分类下全部条目）。</p>
      <el-table :data="categories" size="small" max-height="320" empty-text="暂无分类">
        <el-table-column prop="name" label="分类名称" min-width="160" />
        <el-table-column prop="count" label="条目数" width="88" align="center" />
        <el-table-column label="操作" width="140" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openRename(row.name)">重命名</el-button>
            <el-button link type="danger" size="small" @click="removeCategory(row.name)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="category-add-row">
        <el-input
          v-model="newCategoryName"
          placeholder="新分类名称，如：医案笔记"
          maxlength="64"
          show-word-limit
          clearable
          @keyup.enter="addCategory"
        />
        <el-button type="primary" :loading="categorySaving" @click="addCategory">添加分类</el-button>
      </div>
    </el-dialog>

    <el-dialog v-model="renameVisible" title="重命名分类" width="420px" @closed="resetRename">
      <el-form label-width="80px">
        <el-form-item label="原名称">
          <el-input :model-value="renameOld" disabled />
        </el-form-item>
        <el-form-item label="新名称">
          <el-input
            v-model="renameNew"
            placeholder="输入新的分类名称"
            maxlength="64"
            show-word-limit
            clearable
            @keyup.enter="confirmRename"
          />
        </el-form-item>
      </el-form>
      <p v-if="renameOldCount > 0" class="rename-hint text-muted">
        该分类下有 {{ renameOldCount }} 条知识，重命名后将全部归入新分类并重建向量索引。
      </p>
      <template #footer>
        <el-button @click="renameVisible = false">取消</el-button>
        <el-button type="primary" :loading="categorySaving" @click="confirmRename">确认重命名</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="previewVisible" title="切片预览" width="640px">
      <div v-loading="previewLoading">
        <div class="preview-summary" v-if="previewData">
          文件「{{ previewData.filename }}」按<b>{{ strategyLabel(previewData.strategy) }}</b>共切成
          <b>{{ previewData.total }}</b> 个片段（仅展示前 {{ previewData.preview.length }} 个）：
        </div>
        <div v-for="(p, i) in previewData?.preview || []" :key="i" class="preview-item">
          <div class="preview-head">
            <span class="preview-title">{{ p.title }}</span>
            <span class="text-muted">{{ p.length }} 字</span>
          </div>
          <p class="preview-snippet">{{ p.snippet }}</p>
        </div>
      </div>
      <template #footer>
        <el-button @click="previewVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="confirmImport">确认导入（{{ previewData?.total || 0 }} 条）</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Search, UploadFilled, Loading, Document } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { knowledgeApi } from '../api'
import { confirmDeleteTwice } from '../utils/confirm'

const query = ref('')
const results = ref([])
const searching = ref(false)
const categories = ref([])
const activeCategory = ref('')
const docs = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const listLoading = ref(false)

const uploadCategory = ref('上传资料')
const categoryManageVisible = ref(false)
const newCategoryName = ref('')
const categorySaving = ref(false)
const renameVisible = ref(false)
const renameOld = ref('')
const renameNew = ref('')
const renameOldCount = ref(0)
const uploading = ref(false)
const uploadingName = ref('')
const sources = ref([])
const ALLOWED = ['txt', 'md', 'docx', 'json', 'jsonl']

const chunkStrategy = ref('fixed')
const chunkSize = ref(600)
const chunkOverlap = ref(100)
const separators = ref('')

const previewVisible = ref(false)
const previewLoading = ref(false)
const previewData = ref(null)
const pendingFile = ref(null)

const STRATEGY_LABELS = {
  fixed: '固定长度',
  paragraph: '按段落',
  separator: '按分隔符/标题',
  whole: '整篇不切'
}
function strategyLabel(s) {
  return STRATEGY_LABELS[s] || s
}
function currentChunkConfig() {
  return {
    strategy: chunkStrategy.value,
    size: chunkSize.value,
    overlap: chunkOverlap.value,
    separators: separators.value
  }
}

async function loadSources() {
  sources.value = await knowledgeApi.sources()
}

async function removeSource(source) {
  const ok = await confirmDeleteTwice(
    `将删除来源文件「${source}」导入的全部知识片段。`,
    `再次确认：删除「${source}」后，该文件对应的所有分块将从知识库中永久移除。`
  )
  if (!ok) return
  const res = await knowledgeApi.deleteSource(source)
  ElMessage.success(res.message || '已删除')
  await loadCategories()
  await loadSources()
  page.value = 1
  await loadList()
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

async function onPick({ file }) {
  pendingFile.value = file
  previewData.value = null
  previewVisible.value = true
  previewLoading.value = true
  try {
    previewData.value = await knowledgeApi.preview(file, uploadCategory.value, currentChunkConfig())
  } catch (e) {
    previewVisible.value = false
  } finally {
    previewLoading.value = false
  }
}

async function confirmImport() {
  if (!pendingFile.value) return
  uploading.value = true
  uploadingName.value = pendingFile.value.name
  try {
    const res = await knowledgeApi.upload(pendingFile.value, uploadCategory.value, currentChunkConfig())
    ElMessage.success(res.message || '导入成功')
    previewVisible.value = false
    pendingFile.value = null
    await loadCategories()
    await loadSources()
    page.value = 1
    await loadList()
  } catch (e) {
    /* 错误已由拦截器提示 */
  } finally {
    uploading.value = false
    uploadingName.value = ''
  }
}

async function search() {
  if (!query.value.trim()) {
    ElMessage.warning('请输入检索内容')
    return
  }
  searching.value = true
  try {
    results.value = await knowledgeApi.search(query.value.trim(), 5)
  } finally {
    searching.value = false
  }
}

async function loadCategories() {
  const rows = await knowledgeApi.categories()
  categories.value = Array.isArray(rows) ? rows.map((c) => (typeof c === 'string' ? { name: c, count: 0 } : c)) : []
}

function categoryCount(name) {
  return categories.value.find((c) => c.name === name)?.count ?? 0
}

function openCategoryManage() {
  categoryManageVisible.value = true
}

function openRename(name) {
  renameOld.value = name
  renameNew.value = name
  renameOldCount.value = categoryCount(name)
  renameVisible.value = true
}

function resetRename() {
  renameOld.value = ''
  renameNew.value = ''
  renameOldCount.value = 0
}

async function addCategory() {
  const name = newCategoryName.value.trim()
  if (!name) {
    ElMessage.warning('请输入分类名称')
    return
  }
  categorySaving.value = true
  try {
    const res = await knowledgeApi.createCategory(name)
    ElMessage.success(res.message || '已创建')
    newCategoryName.value = ''
    await loadCategories()
    uploadCategory.value = name
  } finally {
    categorySaving.value = false
  }
}

async function confirmRename() {
  const oldName = renameOld.value
  const newName = renameNew.value.trim()
  if (!newName) {
    ElMessage.warning('请输入新分类名称')
    return
  }
  if (newName === oldName) {
    renameVisible.value = false
    return
  }
  try {
    await ElMessageBox.confirm(
      renameOldCount.value > 0
        ? `将把「${oldName}」下的 ${renameOldCount.value} 条知识移至「${newName}」，并重建向量索引。`
        : `将空分类「${oldName}」重命名为「${newName}」。`,
      '重命名确认',
      { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  categorySaving.value = true
  try {
    const res = await knowledgeApi.renameCategory(oldName, newName)
    ElMessage.success(res.message || '已重命名')
    renameVisible.value = false
    if (activeCategory.value === oldName) activeCategory.value = newName
    if (uploadCategory.value === oldName) uploadCategory.value = newName
    await loadCategories()
    await loadSources()
    await loadList()
  } finally {
    categorySaving.value = false
  }
}

async function removeCategory(name) {
  const count = categoryCount(name)
  let ok = false
  if (count > 0) {
    ok = await confirmDeleteTwice(
      `将删除分类「${name}」下的全部 ${count} 个知识片段。`,
      `再次确认：删除分类「${name}」后，该分类下所有分块将从知识库中永久移除，向量索引将同步重建。`
    )
  } else {
    try {
      await ElMessageBox.confirm(`确定删除空分类「${name}」？`, '删除确认', {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消'
      })
      ok = true
    } catch {
      ok = false
    }
  }
  if (!ok) return
  const res = await knowledgeApi.deleteCategory(name)
  ElMessage.success(res.message || '已删除')
  if (activeCategory.value === name) activeCategory.value = ''
  if (uploadCategory.value === name) uploadCategory.value = '上传资料'
  await loadCategories()
  await loadSources()
  page.value = 1
  await loadList()
}

async function loadList() {
  listLoading.value = true
  try {
    const data = await knowledgeApi.list({
      category: activeCategory.value || undefined,
      page: page.value,
      pageSize: pageSize.value
    })
    docs.value = data.items || []
    total.value = data.total || 0
    page.value = data.page || 1
    pageSize.value = data.page_size || pageSize.value
  } finally {
    listLoading.value = false
  }
}

function onCategoryChange() {
  page.value = 1
  loadList()
}

function onPageSizeChange() {
  page.value = 1
  loadList()
}

onMounted(async () => {
  await loadCategories()
  await loadSources()
  await loadList()
})
</script>

<style scoped>
.knowledge-layout {
  display: grid;
  grid-template-columns: minmax(340px, 400px) 1fr;
  gap: 16px;
  align-items: start;
}
.col-right {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}
.col-card {
  border-radius: 12px;
}
.col-left :deep(.el-card__body) {
  max-height: calc(100vh - 140px);
  overflow-y: auto;
}
.browse-card :deep(.el-card__body) {
  max-height: calc(100vh - 320px);
  overflow-y: auto;
}
.panel-title {
  font-weight: 600;
  font-size: 15px;
}
.card-header--browse {
  flex-direction: column;
  align-items: flex-start;
}
.search-bar {
  display: flex;
  gap: 12px;
}
.search-bar .el-input {
  flex: 1;
}
.results {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 240px;
  overflow-y: auto;
}
.result-card {
  border-radius: 10px;
}
.result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.result-title {
  font-weight: 600;
  font-size: 15px;
}
.result-meta {
  margin: 8px 0;
  display: flex;
  gap: 6px;
}
.result-snippet {
  margin: 0;
  color: #4b5563;
  font-size: 13px;
  line-height: 1.6;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.browse-tools {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
.category-manage-tip {
  margin: 0 0 12px;
  font-size: 13px;
  color: #6b7280;
}
.category-add-row {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}
.category-add-row .el-input {
  flex: 1;
}
.rename-hint {
  margin: 0;
  font-size: 12px;
}
.upload-tip {
  font-size: 12px;
}
.upload-bar {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.chunk-config {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.cfg-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.cfg-label {
  font-size: 13px;
  color: #4b5563;
}
.cfg-hint {
  font-size: 12px;
}
.cfg-col {
  flex-direction: column;
  align-items: flex-start;
}
.cfg-col code {
  font-size: 12px;
  background: #f3f4f6;
  padding: 0 4px;
  border-radius: 3px;
}
.upload-subtip {
  font-size: 12px;
  margin-top: 4px;
}
.preview-summary {
  margin-bottom: 14px;
  font-size: 14px;
}
.preview-item {
  border: 1px solid #eef1f6;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 8px;
}
.preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.preview-title {
  font-weight: 600;
  font-size: 14px;
}
.preview-snippet {
  margin: 0;
  font-size: 13px;
  color: #4b5563;
  line-height: 1.6;
  white-space: pre-wrap;
}
.uploader {
  width: 100%;
}
.uploader :deep(.el-upload),
.uploader :deep(.el-upload-dragger) {
  width: 100%;
}
.upload-icon {
  font-size: 38px;
  color: #c0c4cc;
  margin-bottom: 6px;
}
.uploading-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--brand-dark);
  font-size: 13px;
}
.sources {
  margin-top: 16px;
  border-top: 1px solid #eef1f6;
  padding-top: 14px;
}
.sources-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 10px;
  color: #4b5563;
}
.source-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 200px;
  overflow-y: auto;
}
.source-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  background: #f8fafc;
}
.src-icon {
  color: var(--brand);
}
.src-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}
.src-count {
  font-size: 12px;
}
.doc-title {
  font-weight: 600;
}
.doc-content {
  line-height: 1.8;
  color: #374151;
  white-space: pre-wrap;
}
.pager {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
.col-left .card-header {
  flex-direction: column;
  align-items: flex-start;
}
.col-left .cfg-row {
  flex-direction: column;
  align-items: stretch;
}
.col-left .cfg-row .el-select,
.col-left .cfg-row .el-input-number {
  width: 100% !important;
}
@media (max-width: 1100px) {
  .knowledge-layout {
    grid-template-columns: 1fr;
  }
  .col-left :deep(.el-card__body),
  .browse-card :deep(.el-card__body) {
    max-height: none;
  }
}
</style>
