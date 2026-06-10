<template>
  <div class="ai-home-page">
    <aside class="ai-home-sidebar">
      <div class="ai-home-sidebar-head">
        <button type="button" class="ai-home-new-btn" @click="startNewChat">
          <el-icon><Plus /></el-icon>
          <span>新对话</span>
        </button>
      </div>

      <div v-loading="loading" class="ai-home-conv-list">
        <p v-if="!loading && !sessions.length" class="ai-home-empty">暂无对话，点击「新对话」开始</p>
        <button
          v-for="item in sessions"
          :key="item.id"
          type="button"
          class="ai-home-conv-item"
          :class="{ active: item.id === activeSessionId }"
          @click="selectSession(item.id)"
        >
          <span class="ai-home-conv-title">{{ item.title || '新的对话' }}</span>
          <span class="ai-home-conv-time">{{ formatTime(item.updated_at) }}</span>
          <span
            class="ai-home-conv-delete"
            role="button"
            tabindex="0"
            title="删除对话"
            @click.stop="removeSession(item)"
            @keydown.enter.stop.prevent="removeSession(item)"
          >
            <el-icon :size="14"><Delete /></el-icon>
          </span>
        </button>
      </div>
    </aside>

    <section class="ai-home-main">
      <ConsultAiChat
        :key="chatKey"
        :session-id="activeSessionId"
        :case-context="''"
        welcome-mode="home"
        :redirect-to-consult="false"
        :embedded="false"
        @session-created="onSessionCreated"
        @message-sent="onMessageSent"
      />
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Delete, Plus } from '@element-plus/icons-vue'
import ConsultAiChat from '../components/consult/ConsultAiChat.vue'
import { consultApi } from '../api'
import { confirmDeleteTwice } from '../utils/confirm'

const route = useRoute()
const router = useRouter()

const sessions = ref([])
const loading = ref(false)
const activeSessionId = ref(null)
const chatKey = computed(() => activeSessionId.value || 'new')

function parseSessionQuery(value) {
  const raw = Array.isArray(value) ? value[0] : value
  if (!raw) return null
  const id = Number(raw)
  return Number.isFinite(id) && id > 0 ? id : null
}

function formatTime(value) {
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function loadSessions() {
  loading.value = true
  try {
    sessions.value = await consultApi.listAiChats()
    const queryId = parseSessionQuery(route.query.session)
    if (queryId && sessions.value.some((item) => item.id === queryId)) {
      activeSessionId.value = queryId
    } else if (activeSessionId.value && !sessions.value.some((item) => item.id === activeSessionId.value)) {
      activeSessionId.value = null
    }
  } finally {
    loading.value = false
  }
}

function startNewChat() {
  activeSessionId.value = null
  router.replace({ path: '/', query: {} })
}

function selectSession(id) {
  activeSessionId.value = id
  router.replace({ path: '/', query: { session: id } })
}

function onSessionCreated(id) {
  activeSessionId.value = id
  router.replace({ path: '/', query: { session: id } })
  loadSessions()
}

function onMessageSent() {
  loadSessions()
}

async function removeSession(item) {
  const ok = await confirmDeleteTwice(
    `将删除对话「${item.title || '新的对话'}」。`,
    `再次确认：删除后无法恢复，确定删除吗？`
  )
  if (!ok) return
  await consultApi.deleteSession(item.id)
  ElMessage.success('对话已删除')
  if (activeSessionId.value === item.id) {
    startNewChat()
  }
  await loadSessions()
}

watch(
  () => route.query.session,
  (value) => {
    const id = parseSessionQuery(value)
    if (id !== activeSessionId.value) {
      activeSessionId.value = id
    }
  }
)

onMounted(loadSessions)
</script>

<style scoped>
.ai-home-page {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 0;
  height: calc(100vh - 44px);
  background: #fff;
}

.ai-home-sidebar {
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-right: 1px solid #e8eef6;
  background: #f8fafc;
}

.ai-home-sidebar-head {
  flex-shrink: 0;
  padding: 12px;
  border-bottom: 1px solid #e8eef6;
}

.ai-home-new-btn {
  width: 100%;
  height: 38px;
  border: 1px solid #c7e7d5;
  border-radius: 10px;
  background: linear-gradient(180deg, #fff 0%, #f3fbf7 100%);
  color: #0f7c43;
  font-size: 13px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.ai-home-new-btn:hover {
  background: #ecfdf3;
  border-color: #9fd4b6;
}

.ai-home-conv-list {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 8px;
}

.ai-home-empty {
  margin: 24px 8px;
  font-size: 12px;
  line-height: 1.6;
  color: #98a2b3;
  text-align: center;
}

.ai-home-conv-item {
  width: 100%;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  padding: 10px 34px 10px 10px;
  margin-bottom: 4px;
  text-align: left;
  cursor: pointer;
  position: relative;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.ai-home-conv-item:hover {
  background: #fff;
  border-color: #e8eef6;
}

.ai-home-conv-item.active {
  background: #fff;
  border-color: #bfe8cf;
  box-shadow: 0 2px 8px rgba(15, 124, 67, 0.08);
}

.ai-home-conv-title {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: #182230;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ai-home-conv-time {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: #98a2b3;
}

.ai-home-conv-delete {
  position: absolute;
  top: 50%;
  right: 8px;
  transform: translateY(-50%);
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #98a2b3;
  opacity: 0;
  transition: opacity 0.15s ease, background 0.15s ease, color 0.15s ease;
}

.ai-home-conv-item:hover .ai-home-conv-delete,
.ai-home-conv-item.active .ai-home-conv-delete {
  opacity: 1;
}

.ai-home-conv-delete:hover {
  background: #fee4e2;
  color: #d92d20;
}

.ai-home-main {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 12px;
  background: #fff;
}

@media (max-width: 900px) {
  .ai-home-page {
    grid-template-columns: 1fr;
    height: auto;
    min-height: calc(100vh - 44px);
  }

  .ai-home-sidebar {
    max-height: 220px;
    border-right: none;
    border-bottom: 1px solid #e8eef6;
  }

  .ai-home-main {
    min-height: 520px;
  }
}
</style>
