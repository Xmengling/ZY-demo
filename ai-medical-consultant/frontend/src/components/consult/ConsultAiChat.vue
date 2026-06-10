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
      <span class="ai-chat-pill" :class="{ online: aiReady }">
        <i class="ai-chat-pill-dot" />
        {{ aiReady ? '在线' : '未配置' }}
      </span>
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
        </div>
      </div>

      <div v-if="sending" class="ai-chat-row assistant pending">
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
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Picture, Promotion, User } from '@element-plus/icons-vue'
import { consultApi } from '../../api'
import { formatAiReply } from '../../utils/aiReplyFormat'
import { MAX_IMAGES, readImageAsDataUrl, validateImageFile } from '../../utils/imageUpload'

const props = defineProps({
  sessionId: { type: Number, default: null },
  caseContext: { type: String, default: '' },
  welcomeMode: { type: String, default: 'consult' },
  redirectToConsult: { type: Boolean, default: true },
  embedded: { type: Boolean, default: true }
})

const emit = defineEmits(['session-created', 'message-sent'])

const consultSuggestions = ['这个案子主方倾向什么？', '还需追问哪些信息？', '与相近方证如何鉴别？']
const homeSuggestions = ['大青龙汤方证要点是什么？', '太阳病提纲有哪些？', '帮我鉴别相近方剂']

const suggestions = computed(() => (props.welcomeMode === 'home' ? homeSuggestions : consultSuggestions))

const welcomeText = computed(() =>
  props.welcomeMode === 'home'
    ? '仅依据知识库上传资料、100首方剂解读、伤寒论条文解读作答。'
    : '仅依据知识库上传资料、100首方剂解读、伤寒论条文解读作答；发送时会附带当前病例摘要。'
)

const router = useRouter()
const messages = ref([])
const draft = ref('')
const pendingImages = ref([])
const sending = ref(false)
const messageBoxRef = ref(null)
const fileInputRef = ref(null)
const aiReady = ref(true)
const maxImages = MAX_IMAGES

const canSend = computed(() => Boolean(draft.value.trim() || pendingImages.value.length))

function scrollToBottom() {
  nextTick(() => {
    const box = messageBoxRef.value
    if (box) box.scrollTop = box.scrollHeight
  })
}

function applySuggestion(text) {
  draft.value = text
}

function displayContent(msg) {
  if (!msg?.content) return ''
  return msg.role === 'assistant' ? formatAiReply(msg.content) : msg.content
}

async function loadMessages(id) {
  if (!id) {
    messages.value = []
    return
  }
  try {
    const detail = await consultApi.getSession(id)
    messages.value = (detail.messages || [])
      .filter((m) => m.role === 'user' || m.role === 'assistant')
      .map((m) => ({
        role: m.role,
        content: m.content,
        images: Array.isArray(m.meta?.images) ? m.meta.images : []
      }))
    scrollToBottom()
  } catch {
    messages.value = []
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

async function send() {
  const text = draft.value.trim()
  const images = pendingImages.value.map((item) => item.url)
  if ((!text && !images.length) || sending.value) return

  sending.value = true
  draft.value = ''
  pendingImages.value = []
  messages.value.push({
    role: 'user',
    content: text || '（已发送图片）',
    images: [...images]
  })
  scrollToBottom()

  try {
    let sid = props.sessionId
    if (!sid) {
      const created = await consultApi.createSession({ title: text.slice(0, 20) || '图片问诊' })
      sid = created.id
      emit('session-created', sid)
      if (props.redirectToConsult) {
        router.replace({ path: `/consult/${sid}`, query: router.currentRoute.value.query })
      }
    }

    const res = await consultApi.assistantChat({
      session_id: sid,
      message: text,
      images,
      case_context: props.caseContext || ''
    })
    messages.value.push({ role: 'assistant', content: res.reply })
    aiReady.value = true
    emit('message-sent', sid)
    scrollToBottom()
  } catch (err) {
    if (messages.value.at(-1)?.role === 'user') messages.value.pop()
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

watch(
  () => props.sessionId,
  (id) => {
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
  padding: 8px 4px 12px;
  text-align: center;
}

.ai-chat-welcome-text {
  margin: 0 0 12px;
  font-size: 12px;
  line-height: 1.6;
  color: #667085;
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

.ai-chat-suggestion:hover {
  background: #f0f5ff;
  border-color: #9ebfff;
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
  max-width: calc(100% - 40px);
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
  line-height: 1.75;
  letter-spacing: 0.01em;
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
