<template>
  <div class="ai-chat-shell" :class="{ 'is-standalone': !embedded }">
    <header class="ai-chat-head">
      <div class="ai-chat-head-left">
        <div class="ai-chat-logo" aria-hidden="true">
          <el-icon :size="16"><ChatDotRound /></el-icon>
        </div>
        <div>
          <div class="ai-chat-title">AI 问答</div>
          <div class="ai-chat-subtitle">基于本地知识库 · 上传资料 / 方剂 / 伤寒论</div>
        </div>
      </div>
      <div class="ai-chat-head-actions">
        <button
          v-if="showCaseLink"
          type="button"
          class="ai-chat-case-btn"
          @click="goToCase"
        >
          进入医案
        </button>
        <span class="ai-chat-pill" :class="{ online: aiReady }">
          <i class="ai-chat-pill-dot" />
          {{ aiReady ? '在线' : '未配置' }}
        </span>
      </div>
    </header>

    <div ref="messageBoxRef" class="ai-chat-body">
      <div v-if="!messages.length && !sending" class="ai-chat-welcome">
        <p class="ai-chat-welcome-text">{{ welcomeText }}</p>
        <div class="ai-chat-suggestions">
          <button
            v-for="item in suggestions"
            :key="item"
            type="button"
            class="ai-chat-suggestion"
            :disabled="sending"
            @click="applySuggestion(item)"
          >
            {{ item }}
          </button>
        </div>
      </div>

      <div
        v-for="(msg, index) in messages"
        :key="`${msg.role}-${index}`"
        class="ai-chat-row"
        :class="msg.role"
      >
        <div class="ai-chat-avatar" :class="msg.role">
          <el-icon :size="14">
            <User v-if="msg.role === 'user'" />
            <ChatDotRound v-else />
          </el-icon>
        </div>
        <div class="ai-chat-bubble-wrap">
          <button
            v-if="canCopyMessage(msg)"
            type="button"
            class="ai-chat-copy"
            title="复制"
            aria-label="复制"
            @click="copyMessage(msg)"
          >
            <el-icon :size="13"><DocumentCopy /></el-icon>
          </button>
          <div class="ai-chat-bubble">
          <div v-if="msg.images?.length" class="ai-chat-images">
            <img
              v-for="(src, imgIndex) in msg.images"
              :key="`${index}-${imgIndex}`"
              :src="src"
              alt="上传图片"
              class="ai-chat-image"
            />
          </div>
          <div v-if="displayContent(msg)" class="ai-chat-text">{{ displayContent(msg) }}</div>
          <div
            v-if="msg.role === 'assistant' && msg.references?.length"
            class="ai-chat-refs"
          >
            <span class="ai-chat-refs-label">参考来源</span>
            <div class="ai-chat-refs-list">
              <template v-for="(ref, refIndex) in msg.references" :key="`${index}-ref-${refIndex}`">
                <button
                  v-if="isUploadReference(ref)"
                  type="button"
                  class="ai-chat-ref-chip is-upload"
                  :title="uploadRefHint(ref)"
                  @click="openUploadSnippet(ref)"
                >
                  <span class="ai-chat-ref-cat">{{ referenceCategoryLabel(ref) }}</span>
                  <span class="ai-chat-ref-title">{{ referenceDisplayTitle(ref) }}</span>
                </button>
                <router-link
                  v-else-if="referenceRoute(ref)"
                  :to="referenceRoute(ref)"
                  class="ai-chat-ref-chip"
                  :title="refHint(ref)"
                >
                  <span class="ai-chat-ref-cat">{{ referenceCategoryLabel(ref) }}</span>
                  <span class="ai-chat-ref-title">{{ referenceDisplayTitle(ref) }}</span>
                </router-link>
                <span
                  v-else
                  class="ai-chat-ref-chip is-static"
                  :title="refHint(ref)"
                >
                  <span class="ai-chat-ref-cat">{{ referenceCategoryLabel(ref) }}</span>
                  <span class="ai-chat-ref-title">{{ referenceDisplayTitle(ref) }}</span>
                </span>
              </template>
            </div>
          </div>
          </div>
        </div>
      </div>

      <div v-if="sending && !isStreamingReply" class="ai-chat-row assistant pending">
        <div class="ai-chat-avatar assistant">
          <el-icon :size="14"><ChatDotRound /></el-icon>
        </div>
        <div class="ai-chat-bubble pending-bubble">
          <span class="typing-dot" />
          <span class="typing-dot" />
          <span class="typing-dot" />
        </div>
      </div>
    </div>

    <div v-if="ruleSuggestion" class="ai-rule-confirm">
      <div class="ai-rule-confirm-main">
        <div class="ai-rule-confirm-title">检测到纠正意见，是否记入永久规则？</div>
        <div class="ai-rule-confirm-text">{{ ruleSuggestion.rule_text }}</div>
      </div>
      <div class="ai-rule-confirm-actions">
        <button
          type="button"
          class="ai-rule-btn is-primary"
          :disabled="savingRule"
          @click="confirmSaveRule"
        >
          {{ savingRule ? '保存中…' : '记入永久规则' }}
        </button>
        <button type="button" class="ai-rule-btn" :disabled="savingRule" @click="dismissRuleSuggestion">
          暂不
        </button>
      </div>
    </div>

    <footer class="ai-chat-composer">
      <div v-if="pendingImages.length" class="ai-chat-pending-images">
        <div v-for="(item, index) in pendingImages" :key="item.id" class="ai-chat-pending-item">
          <img :src="item.url" alt="待发送图片" />
          <button type="button" class="ai-chat-pending-remove" aria-label="移除图片" @click="removePendingImage(index)">
            ×
          </button>
        </div>
      </div>
      <div class="ai-chat-composer-box">
        <input
          ref="fileInputRef"
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          multiple
          class="ai-chat-file-input"
          @change="onImagePick"
        />
        <button
          type="button"
          class="ai-chat-attach"
          :disabled="sending || pendingImages.length >= maxImages"
          aria-label="上传图片"
          title="上传图片"
          @click="openImagePicker"
        >
          <el-icon :size="16"><Picture /></el-icon>
        </button>
        <el-input
          v-model="draft"
          type="textarea"
          :autosize="{ minRows: 1, maxRows: 4 }"
          resize="none"
          placeholder="输入问题或上传图片，Enter 发送，Shift+Enter 换行"
          :disabled="sending"
          @keydown="onKeydown"
        />
        <button
          type="button"
          class="ai-chat-send"
          :class="{ active: canSend }"
          :disabled="!canSend || sending"
          aria-label="发送"
          @click="send"
        >
          <el-icon :size="16"><Promotion /></el-icon>
        </button>
      </div>
    </footer>

    <el-dialog
      v-model="snippetDialogVisible"
      :title="snippetDialogTitle"
      width="min(720px, 92vw)"
      class="ai-chat-snippet-dialog"
      destroy-on-close
      append-to-body
    >
      <div v-loading="snippetDialogLoading" class="ai-chat-snippet-body">
        <p class="ai-chat-snippet-tip">以下为本次问答检索到的关联片段</p>
        <pre class="ai-chat-snippet-content">{{ snippetDialogContent }}</pre>
      </div>
      <template #footer>
        <el-button @click="snippetDialogVisible = false">关闭</el-button>
        <el-button type="primary" plain @click="goKnowledgePage">在知识库查看全文</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ChatDotRound, DocumentCopy, Picture, Promotion, User } from '@element-plus/icons-vue'
import { consultApi, knowledgeApi } from '../../api'
import {
  isUploadReference,
  normalizeReferences,
  referenceCategoryLabel,
  referenceDisplayTitle,
  referenceRoute
} from '../../utils/aiReferences'
import { formatAiReply } from '../../utils/aiReplyFormat'
import { MAX_IMAGES, readImageAsDataUrl, validateImageFile } from '../../utils/imageUpload'
import { buildHomeSuggestions } from '../../utils/homeSuggestions'
import { isLinkedCaseSession } from '../../utils/sessionCase'

const props = defineProps({
  sessionId: { type: Number, default: null },
  caseContext: { type: String, default: '' },
  welcomeMode: { type: String, default: 'consult' },
  askedQuestions: { type: Array, default: () => [] },
  formulaNames: { type: Array, default: () => [] },
  pathologyScores: { type: Array, default: () => [] },
  hasChiefComplaint: { type: Boolean, default: false },
  redirectToConsult: { type: Boolean, default: true },
  embedded: { type: Boolean, default: true }
})

const emit = defineEmits(['session-created', 'message-sent'])

const router = useRouter()
const messages = ref([])
const draft = ref('')
const pendingImages = ref([])
const sending = ref(false)
const savingRule = ref(false)
const ruleSuggestion = ref(null)
const messageBoxRef = ref(null)
const fileInputRef = ref(null)
const aiReady = ref(true)
const linkedCase = ref(false)
const maxImages = MAX_IMAGES
const snippetDialogVisible = ref(false)
const snippetDialogLoading = ref(false)
const snippetDialogTitle = ref('')
const snippetDialogContent = ref('')

const consultBaseSuggestions = ['分析一下本例医案？', '还需追问哪些信息？', '使用方剂参考？']

const homeSuggestions = computed(() => {
  const history = [...(props.askedQuestions || [])]
  for (const msg of messages.value) {
    if (msg.role === 'user' && msg.content && msg.content !== '（已发送图片）') {
      history.push(msg.content)
    }
  }
  return buildHomeSuggestions(history)
})

const suggestions = computed(() => (
  props.welcomeMode === 'home'
    ? homeSuggestions.value
    : uniqueSuggestions([...consultBaseSuggestions, ...dynamicConsultSuggestions.value])
))

const welcomeText = computed(() =>
  props.welcomeMode === 'home'
    ? '试试下方问题，回答会紧扣问题组织，便于复习'
    : '试试下方问题，将结合本例摘要灵活作答'
)

const normalizedFormulaNames = computed(() =>
  uniqueSuggestions(
    (props.formulaNames || [])
      .map((name) => String(name || '').trim())
      .filter(Boolean)
  )
)

const pathologyScoreLabels = computed(() =>
  (props.pathologyScores || [])
    .map((item) => String(item?.label || item || '').trim())
    .filter(Boolean)
    .slice(0, 2)
)

const dynamicConsultSuggestions = computed(() => {
  const items = []
  const formulaQuestion = buildFormulaQuestion(normalizedFormulaNames.value)
  if (formulaQuestion) items.push(formulaQuestion)
  if (props.hasChiefComplaint) items.push('这类症状更偏向哪类方证？')
  if (pathologyScoreLabels.value.length) {
    items.push(`${pathologyScoreLabels.value.join('、')}在本例中证据是否充分？`)
  }
  return items
})

function uniqueSuggestions(items) {
  return [...new Set((items || []).filter(Boolean))]
}

function buildFormulaQuestion(names) {
  if (!names.length) return ''
  if (names.includes('五苓散') || names.includes('猪苓汤')) return '五苓散与猪苓汤如何鉴别？'
  if (names.length >= 2) return `${names[0]}与${names[1]}如何鉴别？`
  return `${names[0]}与相近方证如何鉴别？`
}

const canSend = computed(() => Boolean(draft.value.trim() || pendingImages.value.length))
const showCaseLink = computed(
  () => props.welcomeMode === 'home' && Boolean(props.sessionId) && linkedCase.value
)

function goToCase() {
  if (!props.sessionId) return
  router.push({ path: `/consult/${props.sessionId}`, query: { module: 'base' } })
}

function scrollToBottom() {
  nextTick(() => {
    const box = messageBoxRef.value
    if (box) box.scrollTop = box.scrollHeight
  })
}

async function applySuggestion(text) {
  if (!text || sending.value) return
  await send(text)
}

function displayContent(msg) {
  if (!msg?.content && !msg?.streaming) return ''
  if (msg.role === 'assistant') {
    return msg.streaming ? msg.content : formatAiReply(msg.content)
  }
  return msg.content
}

function canCopyMessage(msg) {
  if (!msg || msg.streaming) return false
  const text = String(displayContent(msg) || '').trim()
  return Boolean(text && text !== '（已发送图片）')
}

async function copyTextToClipboard(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  document.body.removeChild(textarea)
}

async function copyMessage(msg) {
  const text = String(displayContent(msg) || '').trim()
  if (!text) return
  try {
    await copyTextToClipboard(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

const isStreamingReply = computed(() =>
  messages.value.some((msg) => msg.role === 'assistant' && msg.streaming)
)

function refHint(ref) {
  const parts = [referenceCategoryLabel(ref), referenceDisplayTitle(ref)]
  if (ref?.score > 0) parts.push(`相关度 ${ref.score}`)
  return parts.filter(Boolean).join(' · ')
}

function uploadRefHint(ref) {
  return `${refHint(ref)} · 点击查看关联片段`
}

function goKnowledgePage() {
  snippetDialogVisible.value = false
  router.push({ name: 'knowledge' })
}

async function resolveUploadFileId(ref) {
  if (ref?.fileId) return ref.fileId
  const name = referenceDisplayTitle(ref)
  if (!name) return null
  try {
    const files = await knowledgeApi.listFiles()
    const row = (files || []).find((item) => item.filename === name)
    return row?.id || null
  } catch {
    return null
  }
}

async function openUploadSnippet(ref) {
  snippetDialogTitle.value = referenceDisplayTitle(ref) || '上传资料'
  snippetDialogContent.value = ''
  snippetDialogVisible.value = true

  if (ref?.snippet) {
    snippetDialogContent.value = ref.snippet
    return
  }

  snippetDialogLoading.value = true
  try {
    const fileId = await resolveUploadFileId(ref)
    if (!fileId) {
      snippetDialogContent.value = '未找到该文件或暂无检索片段。'
      return
    }
    const res = await knowledgeApi.previewFile(fileId)
    const content = String(res?.content || '').trim()
    snippetDialogContent.value = content
      ? content.slice(0, 4000) + (content.length > 4000 ? '\n…' : '')
      : '（文件为空）'
  } catch {
    snippetDialogContent.value = '加载片段失败，请稍后在知识库页查看。'
  } finally {
    snippetDialogLoading.value = false
  }
}

async function loadMessages(id) {
  if (!id) {
    messages.value = []
    linkedCase.value = false
    return
  }
  try {
    const detail = await consultApi.getSession(id)
    linkedCase.value = isLinkedCaseSession(detail)
    messages.value = (detail.messages || [])
      .filter((m) => m.role === 'user' || m.role === 'assistant')
      .map((m) => ({
        role: m.role,
        content: m.content,
        images: Array.isArray(m.meta?.images) ? m.meta.images : [],
        references: m.role === 'assistant' ? normalizeReferences(m.meta?.references) : []
      }))
    scrollToBottom()
  } catch {
    messages.value = []
    linkedCase.value = false
  }
}

function onKeydown(event) {
  if (event.key !== 'Enter' || event.shiftKey) return
  event.preventDefault()
  send()
}

function openImagePicker() {
  fileInputRef.value?.click()
}

async function onImagePick(event) {
  const input = event.target
  const files = Array.from(input.files || [])
  input.value = ''
  if (!files.length) return

  const remain = maxImages - pendingImages.value.length
  if (remain <= 0) {
    ElMessage.warning(`最多上传 ${maxImages} 张图片`)
    return
  }

  for (const file of files.slice(0, remain)) {
    const err = validateImageFile(file)
    if (err) {
      ElMessage.error(err)
      continue
    }
    try {
      const url = await readImageAsDataUrl(file)
      pendingImages.value.push({ id: `${Date.now()}-${Math.random()}`, url })
    } catch {
      ElMessage.error(`「${file.name}」处理失败`)
    }
  }
}

function removePendingImage(index) {
  pendingImages.value.splice(index, 1)
}

async function send(messageText) {
  const text = (typeof messageText === 'string' ? messageText : draft.value).trim()
  const images = pendingImages.value.map((item) => item.url)
  if ((!text && !images.length) || sending.value) return

  sending.value = true
  if (typeof messageText !== 'string') {
    draft.value = ''
  }
  pendingImages.value = []
  messages.value.push({
    role: 'user',
    content: text || '（已发送图片）',
    images: [...images]
  })
  scrollToBottom()

  try {
    let sid = props.sessionId || null

    const assistantIndex = messages.value.length
    messages.value.push({
      role: 'assistant',
      content: '',
      references: [],
      streaming: true
    })
    scrollToBottom()

    await consultApi.assistantChatStream(
      {
        session_id: sid,
        message: text,
        images,
        case_context: props.caseContext || ''
      },
      {
        onStart(payload) {
          if (payload?.session_id) {
            sid = payload.session_id
            if (!props.sessionId) {
              emit('session-created', sid)
              if (props.redirectToConsult) {
                router.replace({ path: `/consult/${sid}`, query: router.currentRoute.value.query })
              }
            }
          }
        },
        onToken(token) {
          const msg = messages.value[assistantIndex]
          if (!msg) return
          msg.content += token
          scrollToBottom()
        },
        onDone(payload) {
          const msg = messages.value[assistantIndex]
          if (!msg) return
          msg.content = payload.reply || msg.content
          msg.references = normalizeReferences(payload.references)
          msg.streaming = false
          sid = payload.session_id || sid
          aiReady.value = true
          if (payload?.rule_suggestion?.rule_text) {
            ruleSuggestion.value = payload.rule_suggestion
          }
          emit('message-sent', sid)
          scrollToBottom()
        }
      }
    )
  } catch (err) {
    const last = messages.value.at(-1)
    const prev = messages.value.at(-2)
    if (last?.role === 'assistant' && last.streaming) messages.value.pop()
    if (prev?.role === 'user') messages.value.pop()
    draft.value = text
    pendingImages.value = images.map((url, index) => ({ id: `restore-${index}`, url }))
    const status = err?.response?.status
    if (status === 503) aiReady.value = false
    const detail = err?.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : 'AI 回复失败')
  } finally {
    sending.value = false
  }
}

function dismissRuleSuggestion() {
  ruleSuggestion.value = null
}

async function confirmSaveRule() {
  const suggestion = ruleSuggestion.value
  if (!suggestion?.rule_text || savingRule.value) return
  savingRule.value = true
  try {
    const res = await consultApi.saveAssistantRule({
      rule_text: suggestion.rule_text,
      source_message: suggestion.source_message || ''
    })
    ElMessage.success(res?.message || '已记入永久规则')
    ruleSuggestion.value = null
  } catch (err) {
    const detail = err?.response?.data?.detail
    ElMessage.warning(typeof detail === 'string' ? detail : '保存失败')
  } finally {
    savingRule.value = false
  }
}

watch(
  () => props.sessionId,
  (id) => {
    if (sending.value || isStreamingReply.value) return
    ruleSuggestion.value = null
    loadMessages(id)
  },
  { immediate: true }
)
</script>

<style scoped>
.ai-chat-shell {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid #e3eaf3;
  border-radius: 10px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
  overflow: hidden;
}

.ai-chat-shell.is-standalone {
  border: none;
  border-radius: 0;
  box-shadow: none;
  background: #fff;
}

.ai-chat-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid #e8eef6;
  background: rgba(255, 255, 255, 0.92);
}

.ai-chat-head-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.ai-chat-logo {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, #477cff 0%, #2f6bff 100%);
  box-shadow: 0 4px 12px rgba(47, 107, 255, 0.28);
  flex-shrink: 0;
}

.ai-chat-title {
  font-size: 14px;
  font-weight: 800;
  color: #182230;
  line-height: 1.2;
}

.ai-chat-subtitle {
  margin-top: 2px;
  font-size: 11px;
  color: #7b8794;
  line-height: 1.3;
}

.ai-chat-head-actions {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.ai-chat-case-btn {
  height: 28px;
  padding: 0 12px;
  border: 1px solid #bfe8cf;
  border-radius: 999px;
  background: linear-gradient(180deg, #fff 0%, #f3fbf7 100%);
  color: #0f7c43;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.ai-chat-case-btn:hover {
  background: #ecfdf3;
  border-color: #9fd4b6;
}

.ai-chat-pill {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: #fff7ed;
  color: #b45309;
  font-size: 11px;
  font-weight: 700;
  border: 1px solid #fed7aa;
}

.ai-chat-pill.online {
  background: #ecfdf3;
  color: #067647;
  border-color: #abefc6;
}

.ai-chat-pill-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.ai-chat-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  scrollbar-width: thin;
  scrollbar-color: #c5d8fb transparent;
}

.ai-chat-body::-webkit-scrollbar {
  width: 5px;
}

.ai-chat-body::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: #c5d8fb;
}

.ai-chat-welcome {
  margin: auto 0;
  width: 100%;
  max-width: 360px;
  align-self: center;
  padding: 4px 8px 8px;
}

.ai-chat-welcome-text {
  margin: 0 0 8px;
  font-size: 11px;
  line-height: 1.5;
  color: #667085;
  text-align: center;
}

.ai-chat-welcome .ai-chat-suggestions {
  gap: 6px;
}

.ai-chat-welcome .ai-chat-suggestion {
  width: 100%;
  font-size: 11px;
  font-weight: 600;
  padding: 5px 10px;
  border-radius: 8px;
  text-align: left;
  line-height: 1.45;
}

.ai-chat-suggestions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ai-chat-suggestion {
  border: 1px solid #d6e4ff;
  border-radius: 999px;
  background: #fff;
  color: #3559b8;
  font-size: 12px;
  font-weight: 600;
  padding: 7px 12px;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}

.ai-chat-suggestion:hover:not(:disabled) {
  background: #f0f5ff;
  border-color: #9ebfff;
}

.ai-chat-suggestion:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.ai-chat-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  max-width: 100%;
}

.ai-chat-row.user {
  flex-direction: row-reverse;
}

.ai-chat-bubble-wrap {
  position: relative;
  max-width: calc(100% - 40px);
}

.ai-chat-bubble-wrap:hover .ai-chat-copy,
.ai-chat-bubble-wrap:focus-within .ai-chat-copy {
  opacity: 1;
}

.ai-chat-copy {
  position: absolute;
  top: 6px;
  right: 6px;
  z-index: 1;
  width: 24px;
  height: 24px;
  padding: 0;
  border: none;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.92);
  color: #667085;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s ease, background 0.15s ease, color 0.15s ease;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.08);
}

.ai-chat-row.user .ai-chat-copy {
  top: 50%;
  right: auto;
  left: -30px;
  transform: translateY(-50%);
  background: #fff;
  color: #667085;
  border: 1px solid #e8eef6;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06);
}

.ai-chat-copy:hover {
  background: #f0f5ff;
  color: #3559b8;
}

.ai-chat-row.user .ai-chat-copy:hover {
  background: #f0f5ff;
  color: #3559b8;
  border-color: #d6e4ff;
}

.ai-chat-row.assistant .ai-chat-bubble-wrap:has(.ai-chat-copy) .ai-chat-bubble {
  padding-top: 26px;
}

.ai-chat-avatar {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.ai-chat-avatar.user {
  background: #e8f3ff;
  color: #2563eb;
}

.ai-chat-avatar.assistant {
  background: linear-gradient(135deg, #eef4ff 0%, #e8f0ff 100%);
  color: #477cff;
}

.ai-chat-bubble {
  max-width: 100%;
  padding: 9px 12px;
  border-radius: 12px;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.ai-chat-row.user .ai-chat-bubble {
  background: linear-gradient(135deg, #477cff 0%, #3b6ef5 100%);
  color: #fff;
  border-bottom-right-radius: 4px;
  box-shadow: 0 4px 14px rgba(59, 110, 245, 0.22);
}

.ai-chat-row.assistant .ai-chat-bubble {
  background: #fff;
  color: #344054;
  border: 1px solid #e8eef6;
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.pending-bubble {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-width: 52px;
  min-height: 36px;
  background: #fff;
  border: 1px solid #e8eef6;
}

.typing-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #98a2b3;
  animation: ai-typing 1.2s infinite ease-in-out;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.15s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes ai-typing {
  0%,
  80%,
  100% {
    opacity: 0.35;
    transform: translateY(0);
  }
  40% {
    opacity: 1;
    transform: translateY(-3px);
  }
}

.ai-chat-composer {
  flex-shrink: 0;
  padding: 10px 12px 12px;
  border-top: 1px solid #e8eef6;
  background: rgba(255, 255, 255, 0.96);
}

.ai-chat-pending-images {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.ai-chat-pending-item {
  position: relative;
  width: 64px;
  height: 64px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #dce3ec;
  background: #f8fafc;
}

.ai-chat-pending-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.ai-chat-pending-remove {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 18px;
  height: 18px;
  border: none;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.62);
  color: #fff;
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
}

.ai-chat-file-input {
  display: none;
}

.ai-chat-images {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
}

.ai-chat-image {
  max-width: 160px;
  max-height: 120px;
  border-radius: 8px;
  object-fit: cover;
  border: 1px solid rgba(255, 255, 255, 0.35);
  background: #fff;
}

.ai-chat-row.assistant .ai-chat-image {
  border-color: #e8eef6;
}

.ai-chat-text {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.8;
  letter-spacing: 0.01em;
}

.ai-chat-refs {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #e8eef6;
}

.ai-chat-refs-label {
  display: block;
  margin-bottom: 6px;
  font-size: 10px;
  font-weight: 700;
  color: #98a2b3;
  letter-spacing: 0.04em;
}

.ai-chat-refs-list {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.ai-chat-ref-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 100%;
  padding: 2px 7px 2px 5px;
  border: 1px solid #d6e4ff;
  border-radius: 999px;
  background: #f6f9ff;
  color: #344054;
  font-size: 10px;
  line-height: 1.35;
  text-decoration: none;
  font-family: inherit;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.ai-chat-ref-chip.is-upload {
  cursor: pointer;
}

.ai-chat-ref-chip:hover {
  border-color: #9ebfff;
  background: #edf4ff;
  color: #245ed6;
}

.ai-chat-ref-chip.is-static {
  cursor: default;
}

.ai-chat-ref-cat {
  flex-shrink: 0;
  padding: 1px 5px;
  border-radius: 999px;
  background: #e8f0ff;
  color: #477cff;
  font-size: 9px;
  font-weight: 700;
}

.ai-chat-ref-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}

.ai-chat-snippet-body {
  min-height: 120px;
}

.ai-chat-snippet-tip {
  margin: 0 0 8px;
  font-size: 12px;
  color: #667085;
}

.ai-chat-snippet-content {
  margin: 0;
  max-height: 52vh;
  overflow: auto;
  padding: 12px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e8eef6;
  font-size: 12px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  color: #344054;
}

.ai-rule-confirm {
  flex-shrink: 0;
  margin: 0 10px 8px;
  padding: 10px 12px;
  border: 1px solid #f5d0a8;
  border-radius: 10px;
  background: linear-gradient(180deg, #fffaf3 0%, #fff7ec 100%);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.ai-rule-confirm-main {
  min-width: 0;
  flex: 1;
}

.ai-rule-confirm-title {
  font-size: 12px;
  font-weight: 600;
  color: #9a5b13;
  margin-bottom: 4px;
}

.ai-rule-confirm-text {
  font-size: 12px;
  line-height: 1.55;
  color: #5c3b1e;
  word-break: break-word;
}

.ai-rule-confirm-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
}

.ai-rule-btn {
  border: 1px solid #d6e2ef;
  border-radius: 8px;
  background: #fff;
  color: #475467;
  font-size: 12px;
  line-height: 1;
  padding: 8px 10px;
  cursor: pointer;
  white-space: nowrap;
}

.ai-rule-btn.is-primary {
  border-color: #f0b35b;
  background: #fff4e5;
  color: #9a5b13;
  font-weight: 600;
}

.ai-rule-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ai-chat-composer-box {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 6px 6px 6px 8px;
  border: 1px solid #d6e2ef;
  border-radius: 12px;
  background: #fff;
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.03);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.ai-chat-composer-box:focus-within {
  border-color: #9ebfff;
  box-shadow: 0 0 0 3px rgba(71, 124, 255, 0.12);
}

.ai-chat-composer-box :deep(.el-textarea__inner) {
  border: 0;
  box-shadow: none !important;
  padding: 4px 0;
  font-size: 12px;
  line-height: 1.5;
  background: transparent;
}

.ai-chat-attach {
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #f3f6fb;
  color: #667085;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s ease, color 0.15s ease;
}

.ai-chat-attach:hover:not(:disabled) {
  background: #e8f0ff;
  color: #3559b8;
}

.ai-chat-attach:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.ai-chat-send {
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #e8eef6;
  color: #98a2b3;
  cursor: not-allowed;
  flex-shrink: 0;
  transition: background 0.15s ease, color 0.15s ease, transform 0.15s ease;
}

.ai-chat-send.active:not(:disabled) {
  background: linear-gradient(135deg, #477cff 0%, #2f6bff 100%);
  color: #fff;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(47, 107, 255, 0.28);
}

.ai-chat-send.active:not(:disabled):hover {
  transform: translateY(-1px);
}
</style>
