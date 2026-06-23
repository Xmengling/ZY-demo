<template>
  <div class="study-shell">
    <div class="study-layout">
      <main class="chat-main">
        <section class="chat-feed" ref="feedRef">
          <div v-if="!messages.length && !loading" class="empty-chat">
            <el-icon><ChatDotRound /></el-icon>
            <h2>直接问，也可以让 AI 派任务</h2>
            <p>比如：今天从当前条文开始上课；抽查我上一条；第1条怎么抓症状组合。</p>
          </div>

          <div
            v-for="message in renderedMessages"
            :key="message.key"
            class="chat-row"
            :class="message.role"
          >
            <div class="chat-avatar">
              <el-icon v-if="message.role === 'assistant'"><Reading /></el-icon>
              <el-icon v-else><User /></el-icon>
            </div>
            <div class="chat-bubble">
              <div v-html="formatMessage(message.displayContent)" />
              <div v-if="message.quiz" class="quiz-card">
                <div class="quiz-kicker">{{ message.quiz.type === 'judge' ? '判断题' : '选择题' }}</div>
                <div class="quiz-question" v-html="formatMessage(message.quiz.question)" />
                <div class="quiz-options">
                  <button
                    v-for="option in message.quiz.options"
                    :key="option.key"
                    type="button"
                    class="quiz-option"
                    :class="quizOptionClass(message, option.key)"
                    :disabled="Boolean(quizSelections[message.key])"
                    @click="chooseQuizAnswer(message.key, option.key)"
                  >
                    <span class="quiz-option-key">{{ option.key }}</span>
                    <span class="quiz-option-text" v-html="formatInline(option.text)" />
                  </button>
                </div>
                <div
                  v-if="quizSelections[message.key]"
                  class="quiz-result"
                  :class="quizResultClass(message)"
                >
                  <strong>{{ quizResultTitle(message) }}</strong>
                  <span v-if="message.quiz.answer">正确答案：{{ message.quiz.answer }}。</span>
                  <span>{{ message.quiz.explanation || '这道题没有返回解析，可以继续让 AI 点评你的选择。' }}</span>
                </div>
              </div>
            </div>
          </div>

          <div v-if="sending" class="chat-row assistant">
            <div class="chat-avatar"><el-icon><Reading /></el-icon></div>
            <div class="chat-bubble pending">
              <el-icon class="spin"><Loading /></el-icon>
              正在结合当前条文生成回答…
            </div>
          </div>
        </section>

        <section class="quick-actions">
          <button
            v-for="item in quickPrompts"
            :key="item"
            type="button"
            class="prompt-chip"
            @click="usePrompt(item)"
          >
            {{ item }}
          </button>
        </section>

        <section class="composer">
          <div class="composer-box">
            <el-input
              v-model="draft"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 6 }"
              resize="none"
              placeholder="问当前条文、让 AI 抽查、要求轻量版讲解，或直接输入你的归纳。"
              @keydown.meta.enter.prevent="sendMessage"
              @keydown.ctrl.enter.prevent="sendMessage"
            />
          </div>
          <el-button type="primary" :loading="sending" @click="sendMessage">
            <el-icon><Promotion /></el-icon>
            发送
          </el-button>
        </section>
      </main>

      <aside class="lesson-side">
        <section class="side-panel">
          <div class="panel-heading">
            <el-icon><Tickets /></el-icon>
            <span>今日任务卡</span>
          </div>
          <p class="task-main">{{ currentArticleTitle }}：先抓原文症状组合，再辨病理和边界。</p>
          <ul class="task-list">
            <li>先让 AI 给出原文片段和一个问题</li>
            <li>你先归纳，AI 再点评</li>
            <li>结束前做 1 到 2 个小测</li>
          </ul>
          <el-button type="success" plain @click="usePrompt('按我的读书 skill，给我派今天任务卡')">
            派任务卡
          </el-button>
        </section>

        <section class="side-panel">
          <div class="panel-heading">
            <el-icon><Operation /></el-icon>
            <span>课堂设置</span>
          </div>
          <div class="side-control">
            <span class="control-label">今日状态</span>
            <el-segmented v-model="selectedState" :options="stateOptions" />
          </div>
          <div class="side-control">
            <span class="control-label">学习模式</span>
            <el-segmented v-model="selectedMode" :options="modeOptions" />
          </div>
        </section>

        <section class="side-panel">
          <div class="panel-heading">
            <el-icon><Document /></el-icon>
            <span>当前条文资料</span>
          </div>
          <p class="article-original" v-html="formatMessage(articleOriginal)" />
        </section>

      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { shanghanStudyApi } from '../api'

const modeOptions = [
  { label: '轻量版', value: 'light' },
  { label: '标准版', value: 'standard' },
  { label: '深入版', value: 'deep' }
]

const stateOptions = [
  { label: '清醒', value: 'clear' },
  { label: '一般', value: 'normal' },
  { label: '很散', value: 'scattered' }
]

const quickPrompts = [
  '按我的读书 skill，给我派今天任务卡',
  '抽查我上一条的核心抓手',
  '只讲当前条文原文，讲完问我一个问题',
  '给我出本条小测',
  '换成轻量版讲'
]

const autoHighlightTerms = [
  '脉浮，头项强痛而恶寒',
  '脉浮、头项强痛、恶寒',
  '头项强痛而恶寒',
  '太阳病的基本特征',
  '太阳病的基本的特征',
  '太阳病的纲领',
  '太阳病提纲',
  '头项强痛',
  '病位在表',
  '正气趋表',
  '欲汗不得汗',
  '抗病反应',
  '证候反映',
  '同时出现',
  '辨证边界',
  '类方鉴别',
  '症状组合',
  '症状群',
  '脉浮',
  '浮脉',
  '恶寒',
  '恶风',
  '发热',
  '汗出',
  '无汗',
  '项背强',
  '口苦',
  '咽干',
  '目眩',
  '胸胁苦满',
  '往来寒热',
  '太阳病',
  '阳明病',
  '少阳病',
  '表证',
  '表实证',
  '表虚证',
  '提纲',
  '总纲',
  '纲领',
  '误治',
  '传变'
].sort((a, b) => b.length - a.length)

const progress = ref(null)
const currentArticle = ref(null)
const messages = ref([])
const draft = ref('')
const selectedMode = ref('standard')
const selectedState = ref('normal')
const selectedArticleNo = ref(1)
const loading = ref(false)
const sending = ref(false)
const feedRef = ref(null)
const quizSelections = ref({})

const currentArticleTitle = computed(() => {
  const number = currentArticle.value?.number || selectedArticleNo.value || progress.value?.nextArticleNo || 1
  return `第${number}条`
})

const articleOriginal = computed(() => {
  return currentArticle.value?.originalText || currentArticle.value?.original || '当前条文资料待加载。'
})

const renderedMessages = computed(() => {
  return messages.value.map((message, index) => {
    const key = `${message.role}-${index}-${message.createdAt || index}`
    const parsed = message.role === 'assistant' ? parseQuizMessage(message.content) : null
    return {
      ...message,
      key,
      displayContent: parsed?.content || message.content,
      quiz: parsed?.quiz || null
    }
  })
})

onMounted(async () => {
  await loadChat()
})

async function loadChat() {
  loading.value = true
  try {
    const data = await shanghanStudyApi.chatHistory()
    progress.value = data.progress
    currentArticle.value = data.article
    messages.value = data.messages || []
    selectedMode.value = data.progress?.defaultMode || 'standard'
    selectedArticleNo.value = Number(data.article?.number || data.progress?.nextArticleNo || 1)
    await scrollToBottom()
  } finally {
    loading.value = false
  }
}

function usePrompt(text) {
  draft.value = text
}

async function sendMessage() {
  const text = draft.value.trim()
  if (!text || sending.value) return
  const localUserMessage = {
    role: 'user',
    content: text,
    articleNo: selectedArticleNo.value,
    createdAt: Date.now()
  }
  messages.value = [...messages.value, localUserMessage]
  draft.value = ''
  sending.value = true
  await scrollToBottom()
  try {
    const data = await shanghanStudyApi.chat({
      message: text,
      articleNo: selectedArticleNo.value,
      mode: selectedMode.value,
      state: selectedState.value
    })
    messages.value = data.messages || [
      ...messages.value,
      { role: 'assistant', content: data.reply, articleNo: selectedArticleNo.value, createdAt: Date.now() }
    ]
    progress.value = data.progress
    currentArticle.value = data.article
    await scrollToBottom()
  } finally {
    sending.value = false
  }
}

async function scrollToBottom() {
  await nextTick()
  if (feedRef.value) {
    feedRef.value.scrollTop = feedRef.value.scrollHeight
  }
}

function parseQuizMessage(content = '') {
  const rawContent = String(content)
  let quizMeta = null
  let cleanedContent = rawContent.replace(/<!--\s*QUIZ:([\s\S]*?)\s*-->/g, (_, jsonText) => {
    try {
      quizMeta = JSON.parse(jsonText)
    } catch {
      quizMeta = null
    }
    return ''
  })

  const answerPattern = /^\s*(?:答案|正确答案|标准答案)[:：]\s*([A-D对错√×正确错误])(?:[，。,.\s]*(.*))?$/i
  let visibleAnswer = ''
  let visibleExplanation = ''
  cleanedContent = cleanedContent
    .split('\n')
    .filter((line) => {
      const match = line.match(answerPattern)
      if (!match) return true
      visibleAnswer = match[1]
      visibleExplanation = match[2] || ''
      return false
    })
    .join('\n')

  const lines = cleanedContent.split('\n')
  const optionPattern = /^\s*([A-D])[\.\、]\s*(.+?)\s*$/
  const optionStart = lines.findIndex((line) => optionPattern.test(line))
  const judgeQuestionIndex = lines.findIndex((line) => /判断题|对\/错|对错|正确还是错误/.test(line))
  if (optionStart < 0 && judgeQuestionIndex < 0) return null

  const isJudge = quizMeta?.type === 'judge' || (judgeQuestionIndex >= 0 && optionStart < 0)
  const type = isJudge ? 'judge' : 'single'
  const options = []

  if (optionStart >= 0) {
    for (let index = optionStart; index < lines.length; index += 1) {
      const match = lines[index].match(optionPattern)
      if (!match) {
        if (lines[index].trim()) break
        continue
      }
      options.push({ key: match[1], text: match[2] })
    }
  } else {
    options.push({ key: '对', text: '正确' }, { key: '错', text: '错误' })
  }

  if (!options.length) return null

  const questionStart = findQuizQuestionStart(lines, optionStart >= 0 ? optionStart : judgeQuestionIndex)
  const optionEnd = optionStart >= 0 ? findQuizOptionEnd(lines, optionStart) : judgeQuestionIndex + 1
  const questionLines = lines.slice(questionStart, optionStart >= 0 ? optionStart : optionEnd)
  const question = questionLines.join('\n').replace(/^\s*(?:#{2,3}\s*)?(?:小测题|选择题|判断题)[：:]\s*/g, '').trim()
  const displayContent = [
    ...lines.slice(0, questionStart),
    ...lines.slice(optionEnd)
  ].join('\n').trim()

  return {
    content: displayContent,
    quiz: {
      type,
      question: question || (type === 'judge' ? '请判断下面说法是否正确。' : '请选择最准确的一项。'),
      options,
      answer: normalizeQuizAnswer(quizMeta?.answer || visibleAnswer || ''),
      explanation: quizMeta?.explanation || visibleExplanation || ''
    }
  }
}

function findQuizQuestionStart(lines, optionStart) {
  for (let index = optionStart - 1; index >= 0; index -= 1) {
    const line = lines[index].trim()
    if (!line) return index + 1
    if (/^(#{2,3}\s*)?(小测题|选择题|判断题)/.test(line)) return index
  }
  return Math.max(0, optionStart - 1)
}

function findQuizOptionEnd(lines, optionStart) {
  const optionPattern = /^\s*([A-D])[\.\、]\s*(.+?)\s*$/
  let end = optionStart
  for (let index = optionStart; index < lines.length; index += 1) {
    const line = lines[index]
    if (optionPattern.test(line) || !line.trim()) {
      end = index + 1
      continue
    }
    break
  }
  return end
}

function normalizeQuizAnswer(answer = '') {
  const text = String(answer).trim().toUpperCase()
  if (!text) return ''
  if (['A', 'B', 'C', 'D'].includes(text)) return text
  if (['对', '正确', 'TRUE', 'T', '√'].includes(text)) return '对'
  if (['错', '错误', 'FALSE', 'F', '×', 'X'].includes(text)) return '错'
  return text
}

function chooseQuizAnswer(messageKey, optionKey) {
  if (quizSelections.value[messageKey]) return
  quizSelections.value = {
    ...quizSelections.value,
    [messageKey]: optionKey
  }
}

function quizOptionClass(message, optionKey) {
  const selected = quizSelections.value[message.key]
  if (!selected) return ''
  const answer = normalizeQuizAnswer(message.quiz?.answer || '')
  if (answer && optionKey === answer) return 'correct'
  if (answer && optionKey === selected && optionKey !== answer) return 'wrong'
  if (optionKey === selected) return 'selected'
  return ''
}

function quizResultClass(message) {
  const selected = quizSelections.value[message.key]
  const answer = normalizeQuizAnswer(message.quiz?.answer || '')
  if (!answer) return 'neutral'
  return selected === answer ? 'correct' : 'wrong'
}

function quizResultTitle(message) {
  const selected = quizSelections.value[message.key]
  const answer = normalizeQuizAnswer(message.quiz?.answer || '')
  if (!answer) return `已选择：${selected}。`
  return selected === answer ? '答对了。' : '这题不对。'
}

function formatMessage(value = '') {
  const lines = String(value).split('\n')
  const blocks = []
  let listItems = []
  let listType = ''

  const flushList = () => {
    if (!listItems.length) return
    const tag = listType === 'ol' ? 'ol' : 'ul'
    blocks.push(`<${tag} class="md-list">${listItems.map((item) => `<li>${formatInline(item)}</li>`).join('')}</${tag}>`)
    listItems = []
    listType = ''
  }

  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line) {
      flushList()
      continue
    }
    if (/^-{3,}$/.test(line)) {
      flushList()
      blocks.push('<hr class="md-divider">')
      continue
    }
    if (line.startsWith('### ')) {
      flushList()
      blocks.push(`<h3 class="md-heading md-heading-3">${formatInline(line.slice(4))}</h3>`)
      continue
    }
    if (line.startsWith('## ')) {
      flushList()
      blocks.push(`<h2 class="md-heading md-heading-2">${formatInline(line.slice(3))}</h2>`)
      continue
    }
    if (line.startsWith('>')) {
      flushList()
      blocks.push(`<blockquote class="md-quote">${formatInline(line.replace(/^>\s?/, ''))}</blockquote>`)
      continue
    }

    const unordered = line.match(/^[-*]\s+(.+)$/)
    if (unordered) {
      if (listType && listType !== 'ul') flushList()
      listType = 'ul'
      listItems.push(unordered[1])
      continue
    }

    const ordered = line.match(/^\d+[.、]\s*(.+)$/)
    if (ordered) {
      if (listType && listType !== 'ol') flushList()
      listType = 'ol'
      listItems.push(ordered[1])
      continue
    }

    flushList()
    blocks.push(`<p class="md-paragraph">${formatInline(line)}</p>`)
  }
  flushList()
  return blocks.join('')
}

function formatInline(value = '') {
  const tokens = []
  const stashToken = (html) => {
    const key = `@@INLINE_TOKEN_${tokens.length}@@`
    tokens.push([key, html])
    return key
  }
  let result = String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  result = result
    .replace(/\[\[\*\*(.*?)\*\*\]\]/g, (_, text) => stashToken(`<mark>${text}</mark>`))
    .replace(/\*\*(.*?)\*\*/g, (_, text) => stashToken(`<strong>${text}</strong>`))

  result = applyAutoHighlight(result)

  for (const [key, html] of tokens) {
    result = result.replaceAll(key, html)
  }

  return result
}

function applyAutoHighlight(value = '') {
  let result = value
  for (const term of autoHighlightTerms) {
    result = result.replaceAll(term, `<mark>${term}</mark>`)
  }
  return result
}
</script>

<style scoped>
.study-shell {
  min-height: calc(100vh - 44px);
  padding: 22px;
  background:
    linear-gradient(180deg, rgba(24, 160, 88, 0.08), transparent 260px),
    #eef3f8;
}

.eyebrow {
  margin: 0 0 6px;
  color: #607089;
  font-size: 13px;
  font-weight: 700;
}

h1,
h2,
p {
  margin-top: 0;
}

h1 {
  margin-bottom: 0;
  color: #142033;
  font-size: 30px;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.article-control :deep(.el-input-number) {
  width: 110px;
}

.control-label {
  color: #475467;
  font-size: 13px;
  font-weight: 700;
}

.study-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 16px;
  max-width: 1360px;
  margin: 0 auto;
}

.chat-main,
.side-panel {
  border: 1px solid #dbe5ef;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 14px 34px rgba(16, 24, 40, 0.06);
}

.chat-main {
  height: calc(100vh - 76px);
  min-height: 560px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-feed {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  padding: 22px;
  scrollbar-gutter: stable;
}

.chat-feed::-webkit-scrollbar {
  width: 10px;
}

.chat-feed::-webkit-scrollbar-track {
  background: #edf2f7;
  border-radius: 999px;
}

.chat-feed::-webkit-scrollbar-thumb {
  background: #b7c5d6;
  border: 2px solid #edf2f7;
  border-radius: 999px;
}

.chat-feed::-webkit-scrollbar-thumb:hover {
  background: #91a4ba;
}

.empty-chat {
  min-height: 500px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #667085;
  text-align: center;
}

.empty-chat .el-icon {
  margin-bottom: 18px;
  color: #18a058;
  font-size: 56px;
}

.empty-chat h2 {
  margin-bottom: 8px;
  color: #172033;
}

.chat-row {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
}

.chat-row.user {
  flex-direction: row-reverse;
}

.chat-avatar {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 50%;
  background: #e7f6ef;
  color: #0f7c43;
}

.chat-row.user .chat-avatar {
  background: #e8eef8;
  color: #294469;
}

.chat-bubble {
  max-width: min(760px, 78%);
  padding: 16px 18px;
  border-radius: 10px;
  background: #f6f9fc;
  color: #202b3d;
  line-height: 1.72;
  word-break: break-word;
}

.chat-row.user .chat-bubble {
  background: #18a058;
  color: #fff;
}

.chat-bubble :deep(mark),
.article-original :deep(mark) {
  padding: 1px 4px;
  border-radius: 5px;
  background: #ffe8e8;
  color: #c81e1e;
  font-weight: 900;
}

.chat-bubble :deep(.md-heading) {
  margin: 0;
  color: #142033;
  line-height: 1.35;
}

.chat-bubble :deep(.md-heading-2) {
  margin: 2px 0 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #dce6ef;
  font-size: 22px;
  font-weight: 850;
}

.chat-bubble :deep(.md-heading-3) {
  margin: 16px 0 10px;
  padding-left: 10px;
  border-left: 4px solid #18a058;
  font-size: 17px;
  font-weight: 800;
}

.chat-bubble :deep(.md-paragraph) {
  margin: 0 0 10px;
}

.chat-bubble :deep(.md-paragraph:last-child) {
  margin-bottom: 0;
}

.chat-bubble :deep(.md-list) {
  margin: 8px 0 12px;
  padding-left: 22px;
}

.chat-bubble :deep(.md-list li) {
  margin: 6px 0;
  padding-left: 2px;
}

.chat-bubble :deep(.md-quote) {
  margin: 10px 0 14px;
  padding: 12px 14px;
  border-left: 4px solid #18a058;
  border-radius: 0 8px 8px 0;
  background: #eef9f3;
  color: #173427;
  font-size: 17px;
  font-weight: 700;
}

.chat-bubble :deep(.md-quote mark) {
  background: #ffd6d6;
  color: #b91c1c;
  box-shadow: inset 0 -2px 0 rgba(185, 28, 28, 0.18);
}

.chat-bubble :deep(.md-divider) {
  height: 1px;
  margin: 16px 0;
  border: 0;
  background: #dce6ef;
}

.quiz-card {
  margin-top: 14px;
  padding: 14px;
  border: 1px solid #cfe6d9;
  border-radius: 12px;
  background:
    linear-gradient(135deg, rgba(24, 160, 88, 0.08), rgba(24, 160, 88, 0.02)),
    #fff;
}

.quiz-kicker {
  display: inline-flex;
  align-items: center;
  margin-bottom: 10px;
  padding: 3px 9px;
  border-radius: 999px;
  background: #e7f6ef;
  color: #0f7c43;
  font-size: 13px;
  font-weight: 850;
}

.quiz-question {
  margin-bottom: 12px;
  color: #172033;
  font-size: 16px;
  font-weight: 800;
  line-height: 1.65;
}

.quiz-question :deep(.md-paragraph) {
  margin-bottom: 0;
}

.quiz-options {
  display: grid;
  gap: 9px;
}

.quiz-option {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d8e3ee;
  border-radius: 10px;
  background: #fff;
  color: #202b3d;
  text-align: left;
  cursor: pointer;
  transition: all 0.16s ease;
}

.quiz-option:hover:not(:disabled) {
  border-color: #18a058;
  background: #f3fbf7;
  transform: translateY(-1px);
}

.quiz-option:disabled {
  cursor: default;
}

.quiz-option-key {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: #edf3f9;
  color: #475467;
  font-weight: 900;
}

.quiz-option-text {
  font-size: 15px;
  font-weight: 700;
  line-height: 1.55;
}

.quiz-option.selected {
  border-color: #409eff;
  background: #edf6ff;
}

.quiz-option.correct {
  border-color: #18a058;
  background: #eaf8f0;
}

.quiz-option.correct .quiz-option-key {
  background: #18a058;
  color: #fff;
}

.quiz-option.wrong {
  border-color: #ef4444;
  background: #fff1f1;
}

.quiz-option.wrong .quiz-option-key {
  background: #ef4444;
  color: #fff;
}

.quiz-result {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  line-height: 1.6;
}

.quiz-result strong {
  margin-right: 8px;
}

.quiz-result.correct {
  background: #eaf8f0;
  color: #0f7c43;
}

.quiz-result.wrong {
  background: #fff1f1;
  color: #b42318;
}

.quiz-result.neutral {
  background: #f2f4f7;
  color: #475467;
}

.chat-bubble :deep(strong) {
  color: #0f7c43;
  font-weight: 850;
}

.quiz-result strong {
  color: inherit;
}

.chat-row.user .chat-bubble :deep(.md-heading),
.chat-row.user .chat-bubble :deep(strong) {
  color: #fff;
}

.chat-row.user .chat-bubble :deep(.md-quote) {
  border-left-color: rgba(255, 255, 255, 0.75);
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
}

.pending {
  color: #667085;
}

.spin {
  margin-right: 6px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.quick-actions {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding: 12px 18px;
  border-top: 1px solid #e7edf4;
  background: #fbfdff;
  scrollbar-width: thin;
}

.quick-actions::-webkit-scrollbar {
  height: 8px;
}

.quick-actions::-webkit-scrollbar-track {
  background: transparent;
}

.quick-actions::-webkit-scrollbar-thumb {
  background: #cbd6e2;
  border-radius: 999px;
}

.prompt-chip {
  height: 36px;
  flex: 0 0 auto;
  padding: 0 14px;
  border: 1px solid #d8e0ea;
  border-radius: 999px;
  background: #fff;
  color: #475467;
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
  transition: all 0.16s ease;
}

.prompt-chip:hover {
  border-color: #18a058;
  background: #eef9f3;
  color: #0f7c43;
  transform: translateY(-1px);
}

.composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 10px;
  padding: 0 18px 18px;
  background: #fbfdff;
}

.composer-box {
  border: 1px solid #d8e0ea;
  border-radius: 12px;
  background: #fff;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.composer-box:focus-within {
  border-color: #18a058;
  box-shadow: 0 0 0 3px rgba(24, 160, 88, 0.12);
}

.composer-box :deep(.el-textarea__inner) {
  min-height: 76px !important;
  border: 0;
  box-shadow: none;
  padding: 14px 16px;
  color: #1f2937;
  font-size: 15px;
  line-height: 1.6;
}

.composer-box :deep(.el-textarea__inner::placeholder) {
  color: #98a2b3;
}

.composer > .el-button {
  height: 76px;
  min-width: 82px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 800;
}

.lesson-side {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.side-panel {
  padding: 16px;
}

.panel-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: #172033;
  font-weight: 800;
}

.task-main {
  color: #1d2a3a;
  font-weight: 700;
  line-height: 1.6;
}

.task-list {
  margin: 0 0 12px;
  padding-left: 18px;
  color: #344054;
  line-height: 1.7;
}

.article-original {
  margin-bottom: 0;
  color: #344054;
  font-size: 15px;
  line-height: 1.8;
}

.side-control {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.side-control :deep(.el-segmented) {
  width: 100%;
}

.side-control :deep(.el-segmented__item) {
  flex: 1;
}

@media (max-width: 1100px) {
  .study-layout {
    display: flex;
    flex-direction: column;
  }

}

@media (max-width: 720px) {
  .study-shell {
    padding: 14px;
  }

  .control-group,
  .composer {
    align-items: stretch;
    display: flex;
    flex-direction: column;
  }

  .composer > .el-button {
    height: 44px;
  }

  .chat-main {
    height: calc(100vh - 110px);
    min-height: 560px;
  }

  .chat-bubble {
    max-width: 86%;
  }
}
</style>
