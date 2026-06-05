<template>
  <div class="chat-layout">
    <!-- 会话列表 -->
    <div class="sessions">
      <el-button type="primary" class="new-btn" @click="newConsult">
        <el-icon><Plus /></el-icon>&nbsp;新建问诊
      </el-button>
      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === sessionId }"
          @click="openSession(s.id)"
        >
          <el-icon><ChatLineRound /></el-icon>
          <span class="session-title">{{ s.title }}</span>
          <el-icon class="del" @click.stop="removeSession(s.id)"><Delete /></el-icon>
        </div>
        <el-empty v-if="!sessions.length" description="暂无问诊记录" :image-size="60" />
      </div>
    </div>

    <!-- 对话区 -->
    <div class="chat-main">
      <div ref="scrollRef" class="messages">
        <div v-if="!messages.length" class="welcome">
          <el-icon :size="46" color="#18a058"><FirstAidKit /></el-icon>
          <h3>您好，我是中医方证问诊助手「智诊」</h3>
          <p class="text-muted">请描述您的症状（寒热、汗出、口渴、舌苔、脉象、二便、部位与诱因等），我会结合经方方证知识库为您辨证分析。</p>
          <div class="examples">
            <el-tag v-for="ex in examples" :key="ex" effect="plain" class="ex" @click="useExample(ex)">{{ ex }}</el-tag>
          </div>
        </div>

        <div v-for="(m, i) in messages" :key="i" class="msg-row" :class="m.role">
          <div class="avatar" :class="m.role === 'user' ? 'avatar-user' : 'avatar-ai'">
            <el-icon v-if="m.role === 'user'"><User /></el-icon>
            <el-icon v-else><Service /></el-icon>
          </div>
          <div class="bubble" :class="m.role === 'user' ? 'bubble-user' : 'bubble-ai'">
            <span v-if="m.content">{{ m.content }}</span>
            <span v-else class="typing">正在思考<span class="dot">…</span></span>
          </div>
        </div>
      </div>

      <div class="input-area">
        <el-input
          v-model="draft"
          type="textarea"
          :rows="2"
          resize="none"
          placeholder="请输入症状描述，回车发送（Shift+Enter 换行）"
          @keydown.enter.exact.prevent="send"
        />
        <el-button type="primary" size="large" :loading="streaming" @click="send">发送</el-button>
      </div>
    </div>

    <!-- 知识库引用 -->
    <div class="ref-panel">
      <h4>📚 知识库引用</h4>
      <div v-if="references.length">
        <el-card v-for="r in references" :key="r.title" shadow="never" class="ref-card">
          <div class="ref-title">{{ r.title }}</div>
          <div class="ref-meta">
            <el-tag size="small" effect="plain">{{ r.category }}</el-tag>
            <span class="text-muted">相关度 {{ (r.score * 100).toFixed(0) }}%</span>
          </div>
        </el-card>
      </div>
      <el-empty v-else description="暂无引用" :image-size="50" />
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, onBeforeUnmount, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { consultApi } from '../api'
import { confirmDeleteTwice } from '../utils/confirm'

const route = useRoute()
const router = useRouter()

const sessions = ref([])
const sessionId = ref(route.params.id ? Number(route.params.id) : null)
const messages = ref([])
const references = ref([])
const draft = ref('')
const streaming = ref(false)
const scrollRef = ref(null)
let ws = null

const examples = [
  '怕冷、低热、出汗、头痛、脖子发紧，舌苔薄白',
  '发热恶寒、无汗、身体疼痛、咳嗽，舌苔白',
  '胃胀、反酸、嗳气、口苦、食欲差',
  '头晕、呕吐、手脚发凉，颠顶头痛'
]

async function loadSessions() {
  sessions.value = await consultApi.listSessions()
}

async function openSession(id) {
  sessionId.value = id
  const detail = await consultApi.getSession(id)
  messages.value = detail.messages.map((m) => ({ role: m.role, content: m.content }))
  const lastAi = [...detail.messages].reverse().find((m) => m.role === 'assistant')
  references.value = lastAi?.meta?.references || []
  router.replace(`/consult/${id}`)
  scrollToBottom()
}

function newConsult() {
  sessionId.value = null
  messages.value = []
  references.value = []
  router.replace('/consult')
}

async function removeSession(id) {
  const ok = await confirmDeleteTwice(
    '将删除该条问诊记录及其全部对话内容。',
    '再次确认：删除后无法恢复，确定要删除这条问诊记录吗？'
  )
  if (!ok) return
  await consultApi.deleteSession(id)
  await loadSessions()
  if (sessionId.value === id) newConsult()
  ElMessage.success('已删除')
}

function useExample(ex) {
  draft.value = ex
}

function scrollToBottom() {
  nextTick(() => {
    if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  })
}

function send() {
  const text = draft.value.trim()
  if (!text || streaming.value) return
  draft.value = ''
  messages.value.push({ role: 'user', content: text })
  const aiMsg = { role: 'assistant', content: '' }
  messages.value.push(aiMsg)
  streaming.value = true
  scrollToBottom()

  const token = localStorage.getItem('token')
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${proto}://${location.host}/api/ws/chat?token=${token}`)

  ws.onopen = () => {
    ws.send(JSON.stringify({ message: text, session_id: sessionId.value }))
  }
  ws.onmessage = (evt) => {
    const data = JSON.parse(evt.data)
    if (data.type === 'meta') {
      sessionId.value = data.session_id
      references.value = data.references || []
    } else if (data.type === 'token') {
      aiMsg.content += data.content
      scrollToBottom()
    } else if (data.type === 'done') {
      finishStream()
    } else if (data.type === 'error') {
      ElMessage.error(data.message || '出错了')
      finishStream()
    }
  }
  ws.onerror = () => {
    if (!aiMsg.content) aiMsg.content = '连接失败，请稍后再试。'
    finishStream()
  }
  ws.onclose = () => {
    if (streaming.value) finishStream()
  }
}

async function finishStream() {
  streaming.value = false
  if (ws) {
    try { ws.close() } catch (e) {}
    ws = null
  }
  router.replace(`/consult/${sessionId.value}`)
  await loadSessions()
  scrollToBottom()
}

onMounted(async () => {
  await loadSessions()
  if (sessionId.value) await openSession(sessionId.value)
})

onBeforeUnmount(() => {
  if (ws) try { ws.close() } catch (e) {}
})
</script>

<style scoped>
.chat-layout {
  display: grid;
  grid-template-columns: 240px 1fr 300px;
  height: 100%;
}
.sessions {
  background: #fff;
  border-right: 1px solid #eef1f6;
  display: flex;
  flex-direction: column;
  padding: 14px;
}
.new-btn {
  width: 100%;
  margin-bottom: 12px;
}
.session-list {
  flex: 1;
  overflow: auto;
}
.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  color: #4b5563;
}
.session-item:hover {
  background: #f3f6fb;
}
.session-item.active {
  background: #e6f7ef;
  color: var(--brand-dark);
}
.session-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}
.del {
  opacity: 0;
  transition: 0.2s;
}
.session-item:hover .del {
  opacity: 0.6;
}
.del:hover {
  opacity: 1;
  color: #cf1322;
}
.chat-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.messages {
  flex: 1;
  overflow: auto;
  padding: 24px 28px;
}
.welcome {
  text-align: center;
  margin-top: 40px;
}
.welcome h3 {
  margin: 12px 0 6px;
}
.examples {
  margin-top: 20px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
}
.ex {
  cursor: pointer;
  padding: 8px 12px;
}
.ex:hover {
  background: #e6f7ef;
}
.input-area {
  border-top: 1px solid #eef1f6;
  background: #fff;
  padding: 14px 20px;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
.input-area .el-button {
  height: 54px;
}
.typing .dot {
  animation: blink 1.2s infinite;
}
@keyframes blink {
  50% { opacity: 0.2; }
}
.ref-panel {
  background: #fff;
  border-left: 1px solid #eef1f6;
  padding: 18px;
  overflow: auto;
}
.ref-panel h4 {
  margin: 0 0 10px;
}
.ref-card {
  margin-bottom: 8px;
  border-radius: 8px;
}
.ref-card :deep(.el-card__body) {
  padding: 10px 12px;
}
.ref-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 6px;
}
.ref-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
}
</style>
