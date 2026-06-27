<template>
  <div class="study-shell">
    <div class="study-layout">
      <aside class="article-list-panel" :style="{ width: `${articleListWidth}px` }">
        <section class="article-list-card">
          <div class="article-list-head">
            <h2>伤寒论条文</h2>
          </div>
          <label class="article-search">
            <span>搜索条文</span>
            <div class="article-search-wrap">
              <input
                v-model="articleSearch"
                type="search"
                placeholder="条文序号、原文、辨证要点…"
              />
            </div>
          </label>
          <p class="article-list-summary">{{ articleListSummary }}</p>
          <div ref="articleListRef" class="article-list" @scroll="clearArticleHover">
            <button
              v-for="article in filteredArticles"
              :key="article.id"
              type="button"
              class="article-item"
              :class="{
                active: Number(article.number) === selectedArticleNo,
                'is-completed': isArticleCompleted(article.number)
              }"
              @mouseenter="showArticleHover(article, $event)"
              @focus="showArticleHover(article, $event)"
              @mouseleave="clearArticleHover"
              @blur="clearArticleHover"
              @click="switchToArticle(article.number)"
            >
              <span class="article-item-index">{{ formatArticleIndex(article.number) }}</span>
              <span class="article-item-body">
                <span class="article-item-name">{{ articleHeadline(article) }}</span>
              </span>
              <span
                class="article-item-status"
                :class="{ 'is-done': isArticleCompleted(article.number) }"
              >
                <span
                  v-if="isArticleCompleted(article.number)"
                  class="article-item-done"
                  aria-label="已完成"
                >
                  <svg viewBox="0 0 12 12" aria-hidden="true">
                    <path d="M2.5 6.2 5.1 8.8 9.5 3.8" />
                  </svg>
                </span>
              </span>
            </button>
            <p v-if="!filteredArticles.length" class="article-empty-hint">暂无匹配条文</p>
          </div>
        </section>
        <div
          v-if="hoverArticle"
          class="article-hover-preview"
          :style="articleHoverStyle"
          role="tooltip"
        >
          <span class="article-hover-no">第 {{ hoverArticle.number }} 条</span>
          <p class="article-hover-text">{{ articleHeadline(hoverArticle) }}</p>
        </div>
        <button
          type="button"
          class="article-list-resizer"
          aria-label="拖动调整条文列表宽度"
          title="拖动调整宽度"
          @mousedown="startArticleListResize"
        />
      </aside>

      <main class="chat-main">
        <div class="chat-context-bar">
          <div class="chat-context-inner">
            <div class="chat-context-top-row">
              <div class="chat-context-head">
                <span class="chat-context-title">第 {{ selectedArticleNo }} 条</span>
                <p class="chat-context-original" v-html="formatMessage(articleOriginal)" />
              </div>
              <span class="chat-context-count">{{ chatRoundCount }} 轮</span>
            </div>
            <div class="chat-article-progress">
              <span class="chat-article-progress-label">本条进度</span>
              <div class="chat-article-progress-track" aria-hidden="true">
                <div
                  class="chat-article-progress-fill"
                  :style="{ width: `${currentArticleProgress.percent}%` }"
                />
              </div>
              <span class="chat-article-progress-value">{{ currentArticleProgress.text }}</span>
            </div>
          </div>
        </div>
        <section v-loading="loading || chatSwitching" class="chat-feed" ref="feedRef">
          <div v-if="!messages.length && !loading && !chatSwitching" class="empty-chat">
            <el-icon><ChatDotRound /></el-icon>
            <h2>第 {{ selectedArticleNo }} 条 · 从这里开始</h2>
            <p>可以直接派任务、请求抽查，或让 AI 讲解当前条文。</p>
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
            <div class="chat-bubble" :class="{ 'is-streaming': message.streaming }">
              <div v-if="message.displayContent" v-html="formatMessage(message.displayContent)" />
              <span v-else-if="message.streaming" class="stream-cursor" aria-hidden="true" />
              <div v-if="message.quiz && !message.streaming" class="quiz-card">
                <div class="quiz-kicker">{{ message.quiz.type === 'judge' ? '判断题' : '选择题' }}</div>
                <div class="quiz-question" v-html="formatMessage(message.quiz.question)" />
                <div class="quiz-options">
                  <button
                    v-for="option in message.quiz.options"
                    :key="option.key"
                    type="button"
                    class="quiz-option"
                    :class="quizOptionClass(message, option.key)"
                    :disabled="Boolean(quizSelections[message.key]) || sending"
                    @click="chooseQuizAnswer(message, option.key)"
                  >
                    <span class="quiz-option-key">{{ option.key }}</span>
                    <span class="quiz-option-text" v-html="formatInline(option.text)" />
                  </button>
                </div>
              </div>
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
          <div class="composer-shell">
            <div class="composer-field">
              <el-input
                v-model="draft"
                type="textarea"
                :autosize="{ minRows: 1, maxRows: 5 }"
                resize="none"
                placeholder="问当前条文、让 AI 抽查、要求轻量版讲解，或直接输入你的归纳"
                @keydown.enter="onComposerEnter"
              />
            </div>
            <el-button
              v-if="sending"
              class="composer-send composer-stop"
              @click="stopMessage"
            >
              <el-icon><VideoPause /></el-icon>
              停止
            </el-button>
            <el-button
              v-else
              type="primary"
              class="composer-send"
              :disabled="!draft.trim()"
              @click="submitComposerMessage"
            >
              <el-icon><Promotion /></el-icon>
              发送
            </el-button>
          </div>
          <p class="composer-hint">Enter 发送 · Shift + Enter 换行</p>
        </section>
      </main>

      <aside class="lesson-side">
        <section class="side-panel progress-panel">
          <div class="panel-heading panel-heading-with-action">
            <div class="panel-heading-left">
              <el-icon><DataLine /></el-icon>
              <span>我的学习进度</span>
            </div>
            <el-button
              type="primary"
              plain
              size="small"
              class="dispatch-task-btn"
              :disabled="sending"
              @click="dispatchTodayTask"
            >
              派今日任务
            </el-button>
          </div>

          <div class="progress-hero">
            <div class="progress-hero-top">
              <span class="progress-learned">{{ studyProgress.learnedCount }}</span>
              <span class="progress-total">/ {{ studyProgress.totalCount || '—' }} 条</span>
            </div>
            <div class="progress-bar-track" aria-hidden="true">
              <div class="progress-bar-fill" :style="{ width: `${studyProgress.percent}%` }" />
            </div>
          </div>

          <div class="progress-stats">
            <div class="progress-stat">
              <span class="progress-stat-value">{{ studyProgress.todayCount }}</span>
              <span class="progress-stat-label">今日已读</span>
            </div>
            <div class="progress-stat">
              <span class="progress-stat-value">{{ studyProgress.reviewCount }}</span>
              <span class="progress-stat-label">待复习</span>
            </div>
          </div>

          <div v-if="studyProgress.lastSessionDate" class="progress-meta">
            <div class="progress-meta-row">
              <span class="progress-meta-label">最近学习</span>
              <span class="progress-meta-value">{{ studyProgress.lastSessionDate }}</span>
            </div>
          </div>

          <div v-if="studyProgress.masteryItems.length" class="progress-section">
            <p class="progress-section-title">掌握情况</p>
            <div class="mastery-tags">
              <span
                v-for="item in studyProgress.masteryItems"
                :key="item.label"
                class="mastery-tag"
                :class="`is-${item.tone}`"
              >
                {{ item.label }} {{ item.count }}
              </span>
            </div>
          </div>

          <div v-if="studyProgress.recentArticles.length" class="progress-section">
            <p class="progress-section-title">最近完成</p>
            <div class="recent-articles">
              <button
                v-for="no in studyProgress.recentArticles"
                :key="no"
                type="button"
                class="recent-article-chip"
                :class="{ 'is-active': no === selectedArticleNo }"
                @click="switchToArticle(no)"
              >
                第{{ no }}条
              </button>
            </div>
          </div>

          <div v-if="studyProgress.todayArticles.length" class="progress-section">
            <p class="progress-section-title">今日在读</p>
            <div class="recent-articles">
              <button
                v-for="no in studyProgress.todayArticles"
                :key="`today-${no}`"
                type="button"
                class="recent-article-chip is-today"
                :class="{ 'is-active': no === selectedArticleNo }"
                @click="switchToArticle(no)"
              >
                第{{ no }}条
              </button>
            </div>
          </div>
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
            <span class="control-label">AI 回答规范</span>
            <el-button class="prompt-config-entry" plain @click="openPromptConfig">
              编辑学习 Skill
            </el-button>
            <p class="prompt-config-meta">
              {{ promptConfigUsingDefault ? '当前使用默认规则' : '已启用自定义规则' }}
            </p>
          </div>
        </section>

      </aside>
    </div>

    <el-drawer
      v-model="promptConfigVisible"
      title="AI 回答规范配置"
      size="780px"
      class="prompt-config-drawer"
      destroy-on-close
    >
      <div v-loading="promptConfigLoading" class="prompt-config-panel">
        <p class="prompt-config-desc">
          这里配置伤寒论课堂的学习 Skill 和上课模式。保存后，下一轮 AI 回复会按新规则执行。
        </p>

        <section class="prompt-config-section">
          <div class="prompt-config-section-head">
            <div class="prompt-config-section-title">
              <h3>学习 Skill</h3>
              <span>{{ promptConfigForm.skillText.length }} / {{ promptConfigMaxLength }}</span>
            </div>
            <el-segmented
              v-model="skillConfigView"
              size="small"
              :options="promptConfigViewOptions"
            />
          </div>
          <textarea
            v-show="skillConfigView === 'edit'"
            v-model="promptConfigForm.skillText"
            class="prompt-config-textarea"
            :maxlength="promptConfigMaxLength"
            spellcheck="false"
            placeholder="填写你的伤寒论学习规则，例如上课节奏、提问方式、点评标准等。"
          />
          <div
            v-show="skillConfigView === 'preview'"
            class="prompt-config-preview"
            v-html="formatPromptDoc(promptConfigForm.skillText)"
          />
        </section>

        <section class="prompt-config-section">
          <div class="prompt-config-section-head">
            <div class="prompt-config-section-title">
              <h3>上课模式</h3>
              <span>{{ promptConfigForm.classroomText.length }} / {{ promptConfigMaxLength }}</span>
            </div>
            <el-segmented
              v-model="classroomConfigView"
              size="small"
              :options="promptConfigViewOptions"
            />
          </div>
          <textarea
            v-show="classroomConfigView === 'edit'"
            v-model="promptConfigForm.classroomText"
            class="prompt-config-textarea is-compact"
            :maxlength="promptConfigMaxLength"
            spellcheck="false"
            placeholder="填写课堂模式，例如标准版、轻量版、复习、抽查的组织方式。"
          />
          <div
            v-show="classroomConfigView === 'preview'"
            class="prompt-config-preview is-compact"
            v-html="formatPromptDoc(promptConfigForm.classroomText)"
          />
        </section>

        <section class="prompt-config-section">
          <div class="prompt-config-section-head">
            <div class="prompt-config-section-title">
              <h3>硬规则预览</h3>
              <span>只读</span>
            </div>
          </div>
          <div class="prompt-config-preview is-readonly" v-html="formatPromptDoc(promptConfigHardRules)" />
        </section>
      </div>

      <template #footer>
        <div class="prompt-config-footer">
          <el-button @click="promptConfigVisible = false">取消</el-button>
          <el-button :loading="promptConfigResetting" @click="resetPromptConfig">
            恢复默认
          </el-button>
          <el-button type="primary" :loading="promptConfigSaving" @click="savePromptConfig">
            保存并生效
          </el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { shanghanStudyApi } from '../api'

const stateOptions = [
  { label: '清醒', value: 'clear' },
  { label: '一般', value: 'normal' },
  { label: '很散', value: 'scattered' }
]

const promptConfigViewOptions = [
  { label: '编辑', value: 'edit' },
  { label: '预览', value: 'preview' }
]

const ARTICLE_STUDY_STEPS = {
  light: [
    { label: '原文', patterns: [/片段\s*1|原文入门|一、原文|今日任务卡/] },
    { label: '小测', patterns: [/片段\s*2|小测|一句话记忆/] }
  ],
  standard: [
    { label: '原文', patterns: [/片段\s*1|原文入门|一、原文|今日任务卡/] },
    { label: '胡希恕', patterns: [/片段\s*2|胡希恕/] },
    { label: '李冠杰', patterns: [/片段\s*3|李冠杰/] },
    { label: '病理边界', patterns: [/片段\s*4|病理分类|病理.*边界|四、/] },
    { label: '小测', patterns: [/片段\s*5|一句话记忆.*小测|本条小测|片段5/] }
  ]
}

const MASTERY_PROGRESS = {
  熟: 100,
  半熟: 85,
  生: 55,
  卡住: 35
}

const quickPrompts = [
  '给我派今天任务卡',
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
const selectedState = ref('clear')
const selectedArticleNo = ref(1)
const loading = ref(false)
const sending = ref(false)
const chatAbortController = ref(null)
const promptConfigVisible = ref(false)
const promptConfigLoading = ref(false)
const promptConfigSaving = ref(false)
const promptConfigResetting = ref(false)
const promptConfigUsingDefault = ref(true)
const promptConfigMaxLength = ref(20000)
const promptConfigHardRules = ref('')
const promptConfigForm = ref({
  skillText: '',
  classroomText: ''
})
const skillConfigView = ref('edit')
const classroomConfigView = ref('edit')
const feedRef = ref(null)
const quizSelections = ref({})
const reviews = ref([])
const ARTICLE_LIST_WIDTH_KEY = 'shanghan-study-article-list-width'
const ARTICLE_LIST_MIN_WIDTH = 220
const ARTICLE_LIST_MAX_WIDTH = 480

const articles = ref([])
const articleSearch = ref('')
const articleListRef = ref(null)
const hoverArticle = ref(null)
const articleHoverStyle = ref({})
const hoverArticleItemEl = ref(null)
const articleListWidth = ref(readArticleListWidth())
const chatSwitching = ref(false)
const articleProgressCache = ref({})
let stopArticleListResize = null
let loadChatSeq = 0

const MASTERY_TONES = {
  熟: 'solid',
  半熟: 'half',
  生: 'weak',
  卡住: 'weak'
}

const studyProgress = computed(() => {
  const p = progress.value || {}
  const totalCount = Number(p.articleCount) || 0
  const nextNo = Number(p.nextArticleNo) || 1
  const completedByNext = Math.max(0, nextNo - 1)
  const masteryMap = p.masteryByArticle || {}
  const masteryEntries = Object.entries(masteryMap)
    .map(([no, level]) => ({ no: Number(no), level: String(level || '半熟') }))
    .filter((item) => item.no > 0)
    .sort((a, b) => a.no - b.no)
  const learnedCount = Math.max(completedByNext, masteryEntries.length)
  const percent = totalCount > 0 ? Math.min(100, Math.round((learnedCount / totalCount) * 100)) : 0
  const todayArticles = [...new Set((p.todayRead || []).map(Number).filter((n) => n > 0))].sort((a, b) => a - b)
  const touchedArticles = [
    ...new Set(messages.value.map((item) => Number(item.articleNo)).filter((n) => n > 0))
  ].sort((a, b) => a - b)
  const masteryCounter = { 熟: 0, 半熟: 0, 生: 0, 卡住: 0 }
  masteryEntries.forEach(({ level }) => {
    if (Object.prototype.hasOwnProperty.call(masteryCounter, level)) masteryCounter[level] += 1
    else masteryCounter['半熟'] += 1
  })
  const masteryItems = Object.entries(masteryCounter)
    .filter(([, count]) => count > 0)
    .map(([label, count]) => ({
      label,
      count,
      tone: MASTERY_TONES[label] || 'half'
    }))
  const recentArticles = masteryEntries.map((item) => item.no).slice(-6).reverse()

  return {
    totalCount,
    learnedCount,
    nextNo,
    percent,
    points: Number(p.points) || 0,
    todayCount: todayArticles.length,
    todayArticles,
    touchedCount: touchedArticles.length,
    currentLevel: p.currentLevel || '太阳病入门',
    lastSessionDate: p.lastSessionDate || '',
    reviewCount: reviews.value.length,
    masteryItems,
    recentArticles
  }
})

const articleOriginal = computed(() => {
  return currentArticle.value?.originalText || currentArticle.value?.original || '当前条文资料待加载。'
})

const renderedMessages = computed(() => {
  return messages.value
    .map((message, index) => {
      const key = `${message.role}-${index}-${message.createdAt || index}`
      const parsed =
        message.role === 'assistant' && !message.streaming
          ? parseQuizMessage(message.content)
          : null
      const rawContent = message.streaming ? message.content : parsed?.content || message.content
      return {
        ...message,
        key,
        displayContent: isInvalidMessageContent(rawContent) ? '' : rawContent,
        quiz: message.streaming ? null : parsed?.quiz || null
      }
    })
    .filter((message) => !(message.role === 'user' && !String(message.displayContent || '').trim()))
})

const chatRoundCount = computed(() => {
  const currentNo = selectedArticleNo.value
  return messages.value.filter((item) => {
    if (item.role !== 'user') return false
    const messageNo = Number(item.articleNo)
    return !messageNo || messageNo === currentNo
  }).length
})

const studyMode = computed(() => {
  if (selectedState.value === 'scattered') return 'light'
  return 'standard'
})

function buildArticleProgress(articleNo) {
  const steps = ARTICLE_STUDY_STEPS[studyMode.value] || ARTICLE_STUDY_STEPS.standard
  const totalSteps = steps.length
  const mastery = progress.value?.masteryByArticle?.[String(articleNo)] || ''

  if (mastery === '熟') {
    return {
      percent: 100,
      currentStep: totalSteps,
      totalSteps,
      text: `片段 ${totalSteps}/${totalSteps} · 已掌握`
    }
  }

  const assistantTexts = messages.value
    .filter((message) => {
      if (message.role !== 'assistant') return false
      const messageNo = Number(message.articleNo)
      return !messageNo || messageNo === articleNo
    })
    .map((message) => plainMessageText(message.content))

  let currentStep = 0
  let currentLabel = '未开始'
  steps.forEach((step, index) => {
    if (assistantTexts.some((text) => step.patterns.some((pattern) => pattern.test(text)))) {
      currentStep = index + 1
      currentLabel = step.label
    }
  })

  const userRounds = messages.value.filter((message) => {
    if (message.role !== 'user') return false
    const messageNo = Number(message.articleNo)
    return !messageNo || messageNo === articleNo
  }).length

  if (currentStep === 0 && userRounds > 0) {
    currentStep = 1
    currentLabel = steps[0].label
  }

  let percent = totalSteps > 0 ? Math.round((currentStep / totalSteps) * 100) : 0
  if (mastery && MASTERY_PROGRESS[mastery] != null) {
    percent = Math.max(percent, MASTERY_PROGRESS[mastery])
  }

  const text =
    currentStep > 0
      ? `片段 ${currentStep}/${totalSteps} · ${currentLabel}`
      : '尚未开始'

  return {
    percent,
    currentStep,
    totalSteps,
    text
  }
}

function rememberArticleProgress(articleNo) {
  const no = Number(articleNo)
  if (!no) return
  articleProgressCache.value = {
    ...articleProgressCache.value,
    [no]: buildArticleProgress(no)
  }
}

const currentArticleProgress = computed(() => buildArticleProgress(selectedArticleNo.value))

const completedArticleSet = computed(() => {
  const set = new Set()
  const p = progress.value || {}
  const nextNo = Number(p.nextArticleNo) || 1
  const masteryMap = p.masteryByArticle || {}

  articles.value.forEach((article) => {
    const no = Number(article.number)
    if (!no) return
    if (no < nextNo) set.add(no)
    if (masteryMap[String(no)] === '熟') set.add(no)

    const cached = articleProgressCache.value[no]
    if (cached?.currentStep >= cached?.totalSteps && cached.totalSteps > 0) {
      set.add(no)
    }

    if (no === selectedArticleNo.value) {
      const articleProgress = buildArticleProgress(no)
      if (articleProgress.currentStep >= articleProgress.totalSteps && articleProgress.totalSteps > 0) {
        set.add(no)
      }
    }
  })

  return set
})

function isArticleCompleted(articleNo) {
  return completedArticleSet.value.has(Number(articleNo))
}

const filteredArticles = computed(() => {
  const query = articleSearch.value.trim().toLowerCase()
  const list = [...articles.value].sort(compareArticles)
  if (!query) return list
  return list.filter((article) => articleMatchesSearch(article, query))
})

const articleListSummary = computed(() => {
  const total = articles.value.length
  if (!total) return ''
  const query = articleSearch.value.trim()
  if (query) return `找到 ${filteredArticles.value.length} / ${total} 条条文`
  return `共 ${total} 条条文`
})

onMounted(async () => {
  window.addEventListener('resize', updateArticleHoverPosition)
  await Promise.all([loadArticles(), loadChat(), loadPromptConfig()])
})

onUnmounted(() => {
  window.removeEventListener('resize', updateArticleHoverPosition)
  chatAbortController.value?.abort()
  stopArticleListResize?.()
})

async function loadArticles() {
  try {
    const data = await shanghanStudyApi.articles()
    articles.value = data.articles || []
  } catch {
    articles.value = []
  }
}

async function loadChat(articleNo) {
  const targetNo = Number(articleNo || selectedArticleNo.value || 1)
  if (!Number.isFinite(targetNo) || targetNo <= 0) return

  const seq = ++loadChatSeq
  chatSwitching.value = true
  loading.value = true
  selectedArticleNo.value = targetNo

  const localArticle = findArticleByNo(targetNo)
  if (localArticle) currentArticle.value = localArticle

  try {
    const data = await shanghanStudyApi.chatHistory(targetNo)
    if (seq !== loadChatSeq) return

    progress.value = data.progress
    currentArticle.value = localArticle || data.article || findArticleByNo(targetNo) || currentArticle.value
    messages.value = sanitizeChatMessages(data.messages)
    selectedArticleNo.value = targetNo
    rememberArticleProgress(targetNo)
    quizSelections.value = {}
    restoreQuizSelectionsFromHistory(messages.value)
    await scrollToBottom()
    scrollActiveArticleIntoView()
  } catch {
    if (seq !== loadChatSeq) return
    messages.value = []
  } finally {
    if (seq === loadChatSeq) {
      loading.value = false
      chatSwitching.value = false
      if (!reviews.value.length) {
        shanghanStudyApi.reviews()
          .then((reviewData) => {
            reviews.value = reviewData.reviews || []
          })
          .catch(() => {})
      }
    }
  }
}

function applyPromptConfig(config = {}) {
  promptConfigForm.value = {
    skillText: config.skillText || '',
    classroomText: config.classroomText || ''
  }
  promptConfigHardRules.value = config.hardRulesText || ''
  promptConfigUsingDefault.value = Boolean(config.usingDefault)
  promptConfigMaxLength.value = Number(config.maxLength) || 20000
}

async function loadPromptConfig() {
  promptConfigLoading.value = true
  try {
    const data = await shanghanStudyApi.promptConfig()
    applyPromptConfig(data.config || {})
  } catch {
    /* 配置加载失败不影响正常上课。 */
  } finally {
    promptConfigLoading.value = false
  }
}

async function openPromptConfig() {
  promptConfigVisible.value = true
  await loadPromptConfig()
}

async function savePromptConfig() {
  const skillText = promptConfigForm.value.skillText.trim()
  const classroomText = promptConfigForm.value.classroomText.trim()
  if (!skillText) {
    ElMessage.warning('学习 Skill 不能为空')
    return
  }

  promptConfigSaving.value = true
  try {
    const data = await shanghanStudyApi.savePromptConfig({
      skillText,
      classroomText
    })
    applyPromptConfig(data.config || {})
    ElMessage.success(sending.value ? '已保存，下一轮回复生效' : '已保存并生效')
  } finally {
    promptConfigSaving.value = false
  }
}

async function resetPromptConfig() {
  try {
    await ElMessageBox.confirm(
      '确定恢复为本地默认 Skill 吗？当前自定义规则会被清除。',
      '恢复默认',
      {
        type: 'warning',
        confirmButtonText: '恢复默认',
        cancelButtonText: '取消'
      }
    )
  } catch {
    return
  }

  promptConfigResetting.value = true
  try {
    const data = await shanghanStudyApi.resetPromptConfig()
    applyPromptConfig(data.config || {})
    ElMessage.success('已恢复默认规则')
  } finally {
    promptConfigResetting.value = false
  }
}

function readArticleListWidth() {
  const saved = Number(localStorage.getItem(ARTICLE_LIST_WIDTH_KEY))
  if (!Number.isFinite(saved)) return 280
  return Math.min(ARTICLE_LIST_MAX_WIDTH, Math.max(ARTICLE_LIST_MIN_WIDTH, saved))
}

function startArticleListResize(event) {
  event.preventDefault()
  stopArticleListResize?.()

  const startX = event.clientX
  const startWidth = articleListWidth.value

  const onMove = (moveEvent) => {
    const nextWidth = startWidth + moveEvent.clientX - startX
    articleListWidth.value = Math.min(
      ARTICLE_LIST_MAX_WIDTH,
      Math.max(ARTICLE_LIST_MIN_WIDTH, nextWidth)
    )
  }

  const onUp = () => {
    document.body.classList.remove('is-resizing-article-list')
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    stopArticleListResize = null
    localStorage.setItem(ARTICLE_LIST_WIDTH_KEY, String(articleListWidth.value))
  }

  document.body.classList.add('is-resizing-article-list')
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
  stopArticleListResize = onUp
}

async function switchToArticle(articleNo) {
  if (sending.value) return
  const no = Number(articleNo)
  if (!Number.isFinite(no) || no <= 0) return
  if (no === selectedArticleNo.value && !chatSwitching.value) return

  rememberArticleProgress(selectedArticleNo.value)
  clearArticleHover()
  messages.value = []
  quizSelections.value = {}
  draft.value = ''

  await loadChat(no)
}

function findArticleByNo(articleNo) {
  const no = Number(articleNo)
  if (!no) return null
  return articles.value.find((item) => Number(item.number) === no) || null
}

function stripMarkup(value = '') {
  return String(value)
    .replace(/\[\[\*\*(.*?)\*\*\]\]/g, '$1')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/^顶格条文[：:]\s*/g, '')
    .replace(/^降(?:一|两|二)格[：:]\s*/g, '')
    .trim()
}

function plainMessageText(content = '') {
  return stripMarkup(String(content))
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/[#>*`_~-]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function articleHeadline(article) {
  const plain = stripMarkup(article?.originalText || article?.original || '')
  const firstLine = plain.split(/\n+/).map((item) => item.trim()).find(Boolean)
  return firstLine || '未填写原文'
}

function showArticleHover(article, event) {
  hoverArticle.value = article
  hoverArticleItemEl.value = event.currentTarget
  updateArticleHoverPosition()
}

function updateArticleHoverPosition() {
  const itemEl = hoverArticleItemEl.value
  const panelEl = itemEl?.closest('.article-list-panel')
  if (!itemEl || !panelEl || !hoverArticle.value) return

  const panelRect = panelEl.getBoundingClientRect()
  const itemRect = itemEl.getBoundingClientRect()
  const previewWidth = 300
  const gap = 10
  let left = panelRect.right + gap
  let top = itemRect.top

  const maxLeft = window.innerWidth - previewWidth - 16
  if (left > maxLeft) {
    left = Math.max(16, panelRect.left - previewWidth - gap)
  }

  top = Math.min(Math.max(12, top), window.innerHeight - 140)

  articleHoverStyle.value = {
    top: `${top}px`,
    left: `${left}px`,
    width: `${previewWidth}px`
  }
}

function clearArticleHover() {
  hoverArticle.value = null
  hoverArticleItemEl.value = null
  articleHoverStyle.value = {}
}

function formatArticleIndex(number) {
  const no = String(number || '').trim()
  if (no && /^\d+$/.test(no)) return String(Number(no)).padStart(2, '0')
  return no || '--'
}

function articleMatchesSearch(article, query) {
  const fields = [
    article.number,
    article.level,
    article.original,
    article.originalText,
    article.terms,
    article.huXishu,
    article.huExcerpt,
    article.liGuanjie,
    article.liExcerpt,
    article.summary
  ]
  if (Array.isArray(article.termItems)) {
    article.termItems.forEach((item) => {
      fields.push(item.label, item.text)
    })
  }
  return fields.some((value) => String(value || '').toLowerCase().includes(query))
}

function compareArticles(a, b) {
  const an = Number.parseInt(String(a.number || '').trim(), 10)
  const bn = Number.parseInt(String(b.number || '').trim(), 10)
  const aValid = !Number.isNaN(an)
  const bValid = !Number.isNaN(bn)
  if (aValid && bValid && an !== bn) return an - bn
  if (aValid && !bValid) return -1
  if (!aValid && bValid) return 1
  return String(a.number || '').localeCompare(String(b.number || ''), 'zh-CN', { numeric: true })
}

async function scrollActiveArticleIntoView() {
  await nextTick()
  const root = articleListRef.value
  if (!root) return
  const active = root.querySelector('.article-item.active')
  if (active) active.scrollIntoView({ block: 'nearest' })
}

function usePrompt(text) {
  sendMessage(text)
}

function dispatchTodayTask() {
  sendMessage('给我派今天任务卡')
}

function isEventLike(value) {
  if (value == null || typeof value !== 'object') return false
  const tag = Object.prototype.toString.call(value)
  return tag.endsWith('Event]') || typeof value.preventDefault === 'function'
}

function isInvalidMessageContent(content) {
  const text = String(content ?? '').trim()
  return /^\[object (\w+Event|\w+)\]$/.test(text)
}

function sanitizeChatMessages(list) {
  if (!Array.isArray(list)) return []
  return list.filter((item) => !isInvalidMessageContent(item?.content))
}

function resolveOutgoingText(overrideText) {
  if (typeof overrideText === 'string') return overrideText.trim()
  if (isEventLike(overrideText)) return String(draft.value || '').trim()
  return String(draft.value || '').trim()
}

function submitComposerMessage() {
  sendMessage()
}

function onComposerEnter(event) {
  if (event.shiftKey || event.metaKey || event.ctrlKey || event.altKey) return
  event.preventDefault()
  submitComposerMessage()
}

function isRequestAborted(err) {
  return err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError'
}

function stopMessage() {
  chatAbortController.value?.abort()
}

async function sendMessage(overrideText) {
  const text = resolveOutgoingText(overrideText)
  if (!text || isInvalidMessageContent(text) || sending.value) return
  const sendForArticleNo = selectedArticleNo.value
  const fromComposer = typeof overrideText !== 'string' || isEventLike(overrideText)
  const localUserMessage = {
    role: 'user',
    content: text,
    articleNo: sendForArticleNo,
    createdAt: Date.now()
  }
  messages.value = [...messages.value, localUserMessage]
  if (fromComposer) draft.value = ''

  const assistantIndex = messages.value.length
  messages.value.push({
    role: 'assistant',
    content: '',
    articleNo: sendForArticleNo,
    createdAt: Date.now(),
    streaming: true
  })

  const controller = new AbortController()
  chatAbortController.value = controller
  sending.value = true
  await scrollToBottom()

  let pendingLine = ''

  const appendStreamToken = (token) => {
    const msg = messages.value[assistantIndex]
    if (!msg) return
    pendingLine += token
    let newlineIndex = pendingLine.indexOf('\n')
    while (newlineIndex >= 0) {
      msg.content += pendingLine.slice(0, newlineIndex + 1)
      pendingLine = pendingLine.slice(newlineIndex + 1)
      newlineIndex = pendingLine.indexOf('\n')
    }
    scrollToBottom()
  }

  try {
    await shanghanStudyApi.chatStream(
      {
        message: text,
        articleNo: sendForArticleNo,
        mode: studyMode.value,
        state: selectedState.value
      },
      {
        onToken: appendStreamToken,
        onDone(payload) {
          if (sendForArticleNo !== selectedArticleNo.value) return
          const msg = messages.value[assistantIndex]
          if (msg) msg.streaming = false
          if (Array.isArray(payload.messages)) {
            messages.value = sanitizeChatMessages(payload.messages)
          } else if (msg) {
            msg.content = payload.reply || `${msg.content}${pendingLine}`
          }
          rememberArticleProgress(sendForArticleNo)
          restoreQuizSelectionsFromHistory(messages.value)
          progress.value = payload.progress
          if (Number(payload.article?.number || payload.articleNo) === sendForArticleNo) {
            currentArticle.value = payload.article
          }
          scrollToBottom()
        }
      },
      controller.signal
    )
  } catch (err) {
    if (isRequestAborted(err)) {
      const msg = messages.value[assistantIndex]
      if (msg?.streaming) {
        if (pendingLine) msg.content += pendingLine
        if (!String(msg.content || '').trim()) {
          messages.value.splice(assistantIndex, 1)
        } else {
          msg.streaming = false
        }
      }
      return
    }
    const msg = messages.value[assistantIndex]
    if (msg?.streaming) messages.value.splice(assistantIndex, 1)
    ElMessage.error(err.message || 'AI 回复失败')
  } finally {
    sending.value = false
    chatAbortController.value = null
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

function parseQuizAnswerFromUserMessage(content = '', quiz) {
  const text = String(content).trim()
  const judgeMatch = text.match(/^我判断[：:]\s*(对|错)/)
  if (judgeMatch) return judgeMatch[1]
  const choiceMatch = text.match(/^我选\s*([A-D])/i)
  if (choiceMatch) return choiceMatch[1].toUpperCase()
  if (quiz?.type === 'judge' && /^(对|错)\s*$/.test(text)) return text
  if (quiz?.type !== 'judge' && /^[A-D]\s*$/.test(text)) return text.toUpperCase()
  return ''
}

function restoreQuizSelectionsFromHistory(messageList = []) {
  const selections = {}
  messageList.forEach((msg, index) => {
    if (msg.role !== 'assistant') return
    const parsed = parseQuizMessage(msg.content)
    if (!parsed?.quiz) return
    const key = `${msg.role}-${index}-${msg.createdAt || index}`
    for (let j = index + 1; j < messageList.length; j += 1) {
      if (messageList[j].role !== 'user') continue
      const answerKey = parseQuizAnswerFromUserMessage(messageList[j].content, parsed.quiz)
      if (answerKey) selections[key] = answerKey
      break
    }
  })
  quizSelections.value = selections
}

function buildQuizAnswerText(quiz, optionKey) {
  const option = quiz?.options?.find((item) => item.key === optionKey)
  const optionText = String(option?.text || '').trim()
  if (quiz?.type === 'judge') {
    return `我判断：${optionKey}${optionText ? `（${optionText}）` : ''}`
  }
  return `我选 ${optionKey}${optionText ? `（${optionText}）` : ''}`
}

async function chooseQuizAnswer(message, optionKey) {
  if (quizSelections.value[message.key] || sending.value || !message.quiz) return
  quizSelections.value = {
    ...quizSelections.value,
    [message.key]: optionKey
  }
  await sendMessage(buildQuizAnswerText(message.quiz, optionKey))
}

function quizOptionClass(message, optionKey) {
  const selected = quizSelections.value[message.key]
  if (!selected) return ''
  if (optionKey === selected) return 'selected'
  return ''
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
    if (line.startsWith('# ')) {
      flushList()
      blocks.push(`<h1 class="md-heading md-heading-1">${formatInline(line.slice(2))}</h1>`)
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

function formatPromptDoc(value = '') {
  const html = formatMessage(value)
  return html || '<p class="md-paragraph md-empty">暂无内容</p>'
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
    .replace(/`([^`]+)`/g, (_, text) => stashToken(`<code class="md-code">${text}</code>`))
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
  --blue: #477cff;
  --blue-dark: #245ed6;
  --blue-soft: #edf4ff;
  --line: #d8e5ff;
  --orange: #ff9a35;
  --red: #ef3b35;
  --ink: #172033;
  --muted: #607089;
  --paper: #ffffff;
  --bg: #eef5ff;

  height: 100%;
  box-sizing: border-box;
  padding: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at 12% 8%, rgba(255, 154, 53, .12), transparent 28%),
    radial-gradient(circle at 82% 14%, rgba(71, 124, 255, .14), transparent 30%),
    var(--bg);
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

.control-hint {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
}

.study-layout {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) 340px;
  gap: 16px;
  flex: 1;
  min-height: 0;
  max-width: min(1680px, 100%);
  width: 100%;
  margin: 0 auto;
  align-items: stretch;
}

.article-list-panel {
  position: relative;
  height: 100%;
  min-height: 0;
  flex-shrink: 0;
  z-index: 2;
}

.article-hover-preview {
  position: fixed;
  z-index: 3200;
  box-sizing: border-box;
  padding: 12px 14px;
  border: 1px solid #cfe0ff;
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(255, 255, 255, .99) 0%, rgba(248, 251, 255, .98) 100%);
  box-shadow:
    0 16px 40px rgba(34, 70, 130, .14),
    0 0 0 1px rgba(255, 255, 255, .85) inset;
  pointer-events: none;
}

.article-hover-no {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 9px;
  border-radius: 999px;
  background: linear-gradient(180deg, #edf4ff 0%, #e3edff 100%);
  color: #245ed6;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.03em;
  white-space: nowrap;
}

.article-hover-text {
  margin: 8px 0 0;
  color: #172033;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.72;
  letter-spacing: 0.01em;
  white-space: normal;
  word-break: break-word;
}

.article-list-resizer {
  position: absolute;
  top: 0;
  right: -10px;
  z-index: 5;
  width: 18px;
  height: 100%;
  border: 0;
  border-radius: 999px;
  padding: 0;
  background: transparent;
  cursor: col-resize;
  touch-action: none;
}

.article-list-resizer::before {
  content: "";
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 4px;
  height: 48px;
  border-radius: 999px;
  background: #c5d8fb;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, .8);
  transition: background .16s ease, height .16s ease, box-shadow .16s ease;
}

.article-list-resizer:hover::before,
.article-list-resizer:focus-visible::before,
:global(body.is-resizing-article-list) .article-list-resizer::before {
  height: 72px;
  background: var(--blue);
  box-shadow: 0 0 0 4px rgba(71, 124, 255, .12);
}

:global(body.is-resizing-article-list) {
  cursor: col-resize;
  user-select: none;
}

.article-list-card,
.chat-main,
.side-panel {
  border: 1px solid #cfe0ff;
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(255, 255, 255, .98) 0%, rgba(248, 251, 255, .94) 100%);
  box-shadow: 0 12px 32px rgba(34, 70, 130, .08);
}

.article-list-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 16px 14px 14px;
  overflow: hidden;
}

.article-list-head h2 {
  margin: 0 0 14px;
  color: var(--blue-dark);
  font-size: 18px;
  font-weight: 900;
  letter-spacing: 0.02em;
}

.article-search {
  display: grid;
  gap: 8px;
  margin-bottom: 8px;
  flex-shrink: 0;
}

.article-search > span {
  color: #35445c;
  font-size: 13px;
  font-weight: 900;
}

.article-search-wrap {
  position: relative;
}

.article-search-wrap::before {
  content: "⌕";
  position: absolute;
  left: 11px;
  top: 50%;
  transform: translateY(-52%);
  color: #8aa3cc;
  font-size: 15px;
  font-weight: 700;
  pointer-events: none;
}

.article-search input {
  width: 100%;
  min-height: 38px;
  padding: 0 12px 0 32px;
  border: 1px solid #c5d8fb;
  border-radius: 10px;
  background: #fff;
  color: var(--ink);
  font-size: 14px;
  outline: none;
  transition: border-color .18s ease, box-shadow .18s ease;
}

.article-search input:focus {
  border-color: var(--blue);
  box-shadow: 0 0 0 3px rgba(71, 124, 255, .12);
}

.article-list-summary {
  margin: 0 0 10px;
  padding: 0 2px;
  color: #7b8ba6;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
  flex-shrink: 0;
}

.article-list {
  display: grid;
  gap: 4px;
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 2px;
  scrollbar-width: thin;
  scrollbar-color: #c5d8fb transparent;
}

.article-list::-webkit-scrollbar {
  width: 5px;
}

.article-list::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: #c5d8fb;
}

.article-item {
  width: 100%;
  min-height: 36px;
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 5px 8px 5px 8px;
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) 22px;
  gap: 8px;
  align-items: center;
  background: #fff;
  color: var(--ink);
  text-align: left;
  cursor: pointer;
  transition: background .15s ease, border-color .15s ease, box-shadow .15s ease;
}

.article-item.is-completed:not(.active) {
  background: linear-gradient(90deg, #f4fbf7 0%, #fcfffe 55%, #fff 100%);
  border-color: rgba(31, 157, 101, 0.1);
}

.article-item.is-completed:not(.active) .article-item-index {
  background: linear-gradient(180deg, #ecfdf3 0%, #dff5ea 100%);
  color: #2f8f62;
  box-shadow: inset 0 0 0 1px rgba(31, 157, 101, 0.12);
}

.article-item.is-completed:not(.active) .article-item-name {
  color: #355447;
}

.article-item:hover {
  border-color: #d0e0ff;
  background: #f6f9ff;
  box-shadow: 0 2px 8px rgba(71, 124, 255, .06);
}

.article-item.is-completed:not(.active):hover {
  background: linear-gradient(90deg, #eefaf3 0%, #f6f9ff 100%);
  border-color: rgba(31, 157, 101, 0.16);
}

.article-item.active {
  border-color: #9ebfff;
  background: linear-gradient(90deg, #edf4ff 0%, #f8fbff 100%);
  box-shadow: inset 3px 0 0 var(--blue), 0 2px 10px rgba(71, 124, 255, .1);
}

.article-item.active.is-completed {
  border-color: #8eb5ff;
}

.article-item-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  border-radius: 6px;
  background: #f0f5ff;
  color: #7b8ba6;
  font-size: 11px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.article-item.active .article-item-index {
  background: var(--blue);
  color: #fff;
}

.article-item-body {
  min-width: 0;
}

.article-item-name {
  display: block;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.25;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.article-item.active .article-item-name {
  color: var(--blue-dark);
}

.article-item-status {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.article-item-done {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #ecfdf3 0%, #d9f7e8 100%);
  box-shadow: inset 0 0 0 1px rgba(31, 157, 101, 0.18);
}

.article-item-done svg {
  width: 11px;
  height: 11px;
}

.article-item-done svg path {
  fill: none;
  stroke: #1f9d65;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.article-item.active .article-item-done {
  background: #fff;
  box-shadow:
    inset 0 0 0 1px rgba(31, 157, 101, 0.28),
    0 1px 4px rgba(24, 160, 88, 0.12);
}

.article-item.active .article-item-done svg path {
  stroke: #18a058;
}

.article-empty-hint {
  margin: 0;
  padding: 10px 6px;
  color: #7b8ba6;
  font-size: 12px;
  font-weight: 700;
}

.chat-main {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-context-bar {
  padding: 8px 14px;
  border-bottom: 1px solid var(--line);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  flex-shrink: 0;
}

.chat-context-inner {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.chat-context-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.chat-context-head {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}

.chat-article-progress {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
}

.chat-article-progress-label {
  color: #667085;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.chat-article-progress-value {
  color: var(--blue-dark);
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
}

.chat-article-progress-track {
  height: 4px;
  border-radius: 999px;
  background: #e3edff;
  overflow: hidden;
}

.chat-article-progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--blue) 0%, #6b96ff 100%);
  transition: width 0.24s ease;
}

.chat-context-original {
  margin: 0;
  flex: 1;
  min-width: 0;
  color: var(--ink);
  font-size: 14px;
  line-height: 1.45;
  font-weight: 600;
  word-break: break-word;
}

.chat-context-original :deep(mark) {
  color: #d93025;
  background: transparent;
  font-weight: 800;
}

.chat-context-original :deep(strong) {
  color: var(--blue-dark);
  background: transparent;
  font-weight: 800;
}

.chat-context-title {
  flex-shrink: 0;
  color: var(--blue-dark);
  font-size: 15px;
  font-weight: 900;
}

.chat-context-count {
  flex-shrink: 0;
  min-height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  background: var(--blue-soft);
  color: var(--blue-dark);
  font-size: 11px;
  font-weight: 800;
  line-height: 22px;
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
  background: var(--blue-soft);
  border-radius: 999px;
}

.chat-feed::-webkit-scrollbar-thumb {
  background: #b8cff5;
  border: 2px solid var(--blue-soft);
  border-radius: 999px;
}

.chat-feed::-webkit-scrollbar-thumb:hover {
  background: #94b4f0;
}

.empty-chat {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #667085;
  text-align: center;
}

.empty-chat .el-icon {
  margin-bottom: 18px;
  color: var(--blue);
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

.chat-row.assistant {
  width: 100%;
  align-items: flex-start;
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
  background: var(--blue-soft);
  color: var(--blue-dark);
}

.chat-row.user .chat-avatar {
  background: #e6efff;
  color: #3d6bcc;
}

.chat-bubble {
  padding: 15px 17px;
  border-radius: 12px;
  background: var(--blue-soft);
  color: var(--ink);
  font-size: 15px;
  line-height: 1.68;
  word-break: break-word;
}

.chat-row.assistant .chat-bubble {
  flex: 1;
  min-width: 0;
  max-width: calc(100% - 44px);
  background: rgba(255, 255, 255, .96);
  border: 1px solid #cfe0ff;
  box-shadow: 0 8px 24px rgba(34, 70, 130, .07);
}

.chat-row.user .chat-bubble {
  max-width: min(560px, 72%);
  background: linear-gradient(180deg, #f4f8ff 0%, #e8f0ff 100%);
  color: #1a2d4f;
  border: 1px solid #c8d9f5;
  box-shadow: 0 2px 10px rgba(71, 124, 255, .08);
}

.chat-bubble :deep(mark) {
  padding: 0;
  border-radius: 0;
  background: transparent;
  color: var(--red);
  font-weight: 900;
}

.chat-bubble :deep(.md-heading) {
  margin: 0;
  color: var(--ink);
  line-height: 1.35;
}

.chat-bubble :deep(.md-heading-2) {
  margin: 2px 0 11px;
  padding-bottom: 9px;
  border-bottom: 1px solid var(--line);
  font-size: 20px;
  font-weight: 850;
}

.chat-bubble :deep(.md-heading-3) {
  margin: 14px 0 9px;
  padding: 5px 0 5px 13px;
  border-left: 3px solid var(--blue);
  font-size: 16px;
  font-weight: 800;
  color: var(--blue-dark);
}

.chat-bubble :deep(.md-paragraph) {
  margin: 0 0 8px;
}

.chat-bubble :deep(.md-paragraph:last-child) {
  margin-bottom: 0;
}

.chat-bubble :deep(.md-list) {
  margin: 6px 0 10px;
  padding-left: 20px;
}

.chat-bubble :deep(.md-list li) {
  margin: 4px 0;
  padding-left: 2px;
}

.chat-bubble :deep(.md-quote) {
  margin: 9px 0 13px;
  padding: 11px 13px;
  border: 1px solid var(--line);
  border-left: 3px solid var(--blue);
  border-radius: 0 8px 8px 0;
  background: var(--blue-soft);
  color: var(--ink);
  font-size: 15px;
  font-weight: 700;
}

.chat-bubble :deep(.md-quote mark) {
  background: transparent;
  color: var(--red);
  box-shadow: none;
}

.chat-bubble :deep(.md-divider) {
  height: 1px;
  margin: 16px 0;
  border: 0;
  background: var(--line);
}

.quiz-card {
  margin-top: 14px;
  padding: 14px;
  border: 1px solid #cfe0ff;
  border-radius: 12px;
  background:
    linear-gradient(135deg, rgba(71, 124, 255, .06), rgba(71, 124, 255, .02)),
    #fff;
}

.quiz-kicker {
  display: inline-flex;
  align-items: center;
  margin-bottom: 9px;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--blue-soft);
  color: var(--blue-dark);
  font-size: 13px;
  font-weight: 850;
}

.quiz-question {
  margin-bottom: 11px;
  color: #172033;
  font-size: 15px;
  font-weight: 800;
  line-height: 1.62;
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
  border: 1px solid #d8e5ff;
  border-radius: 10px;
  background: #fff;
  color: var(--ink);
  text-align: left;
  cursor: pointer;
  transition: all 0.16s ease;
}

.quiz-option:hover:not(:disabled) {
  border-color: var(--blue);
  background: var(--blue-soft);
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
  background: var(--blue-soft);
  color: var(--muted);
  font-weight: 900;
}

.quiz-option-text {
  font-size: 15px;
  font-weight: 700;
  line-height: 1.52;
}

.quiz-option.selected {
  border-color: var(--blue);
  background: var(--blue-soft);
}

.quiz-option.correct {
  border-color: var(--blue-dark);
  background: var(--blue-soft);
}

.quiz-option.correct .quiz-option-key {
  background: var(--blue);
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
  background: var(--blue-soft);
  color: var(--blue-dark);
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
  color: var(--blue-dark);
  font-weight: 850;
  background: transparent;
  padding: 0;
  border-radius: 0;
}

.quiz-result strong {
  color: inherit;
}

.chat-row.user .chat-bubble :deep(.md-heading),
.chat-row.user .chat-bubble :deep(strong) {
  color: var(--blue-dark);
}

.chat-row.user .chat-bubble :deep(.md-quote) {
  border-left-color: #8eb0f0;
  background: rgba(255, 255, 255, 0.62);
  color: var(--ink);
}

.chat-row.assistant .chat-bubble.is-streaming {
  min-height: 44px;
}

.stream-cursor {
  display: inline-block;
  width: 8px;
  height: 1.05em;
  margin-top: 2px;
  border-radius: 2px;
  background: var(--blue);
  vertical-align: text-bottom;
  animation: stream-cursor-blink 1s step-end infinite;
}

@keyframes stream-cursor-blink {
  50% {
    opacity: 0;
  }
}

.quick-actions {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 10px 18px 0;
  border-top: 1px solid var(--line);
  background: #fff;
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
  height: 32px;
  flex: 0 0 auto;
  padding: 0 12px;
  border: 1px solid #dbe7ff;
  border-radius: 999px;
  background: #f8fbff;
  color: #5b6b86;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
  transition: all 0.16s ease;
}

.prompt-chip:hover {
  border-color: #9ebfff;
  background: #edf4ff;
  color: var(--blue-dark);
}

.composer {
  padding: 10px 18px 14px;
  background: #fff;
}

.composer-shell {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 8px 10px 8px 14px;
  border: 1px solid #cfe0ff;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 6px 20px rgba(34, 70, 130, 0.06);
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.composer-shell:focus-within {
  border-color: #8eb5ff;
  box-shadow:
    0 0 0 3px rgba(71, 124, 255, 0.1),
    0 6px 20px rgba(34, 70, 130, 0.08);
}

.composer-field {
  flex: 1;
  min-width: 0;
}

.composer-field :deep(.el-textarea__inner) {
  min-height: 40px !important;
  padding: 6px 0;
  border: 0 !important;
  box-shadow: none !important;
  background: transparent !important;
  color: #1f2937;
  font-size: 15px;
  line-height: 1.55;
  resize: none;
}

.composer-field :deep(.el-textarea__inner:hover),
.composer-field :deep(.el-textarea__inner:focus) {
  border: 0 !important;
  box-shadow: none !important;
}

.composer-field :deep(.el-textarea__inner::placeholder) {
  color: #9aa8bc;
}

.composer-send {
  flex-shrink: 0;
  height: 40px;
  min-width: 78px;
  margin-bottom: 1px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 800;
}

.composer-send :deep(.el-icon) {
  margin-right: 2px;
}

.composer-stop {
  --el-button-text-color: #475467;
  --el-button-bg-color: #fff;
  --el-button-border-color: #d5dfeb;
  --el-button-hover-text-color: #dc2626;
  --el-button-hover-bg-color: #fff5f5;
  --el-button-hover-border-color: #fca5a5;
  --el-button-active-text-color: #b91c1c;
  --el-button-active-bg-color: #fee2e2;
  --el-button-active-border-color: #f87171;
}

.composer-hint {
  margin: 6px 2px 0;
  color: #9aa8bc;
  font-size: 11px;
  font-weight: 600;
  text-align: right;
}

.composer-send.el-button--primary {
  --el-button-bg-color: var(--blue);
  --el-button-border-color: var(--blue);
  --el-button-hover-bg-color: var(--blue-dark);
  --el-button-hover-border-color: var(--blue-dark);
  --el-button-active-bg-color: var(--blue-dark);
  --el-button-active-border-color: var(--blue-dark);
  --el-button-disabled-bg-color: #c5d8fb;
  --el-button-disabled-border-color: #c5d8fb;
}

.lesson-side {
  display: flex;
  flex-direction: column;
  gap: 14px;
  height: 100%;
  min-height: 0;
  overflow: auto;
}

.side-panel {
  padding: 16px;
}

.side-panel :deep(.el-button--primary.is-plain) {
  --el-button-text-color: var(--blue-dark);
  --el-button-border-color: #bad0ff;
  --el-button-bg-color: var(--blue-soft);
  --el-button-hover-text-color: #fff;
  --el-button-hover-bg-color: var(--blue);
  --el-button-hover-border-color: var(--blue);
}

.panel-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: var(--blue-dark);
  font-weight: 800;
}

.panel-heading-with-action {
  justify-content: space-between;
  gap: 10px;
}

.panel-heading-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.dispatch-task-btn {
  flex-shrink: 0;
  min-height: 30px;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 800;
}

.prompt-config-entry {
  width: 100%;
  min-height: 34px;
  justify-content: center;
  border-color: #d8e5ff;
  border-radius: 10px;
  background: #f8fbff;
  color: var(--blue-dark);
  font-weight: 800;
}

.prompt-config-meta {
  margin: 2px 0 0;
  color: #7b8ba6;
  font-size: 12px;
  font-weight: 700;
}

.prompt-config-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding-right: 2px;
}

.prompt-config-desc {
  margin: 0;
  padding: 7px 12px;
  border: 1px solid #d8e5ff;
  border-radius: 10px;
  background: linear-gradient(180deg, #ffffff 0%, #f4f8ff 100%);
  color: #607089;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.45;
}

.prompt-config-section {
  display: grid;
  gap: 10px;
}

.prompt-config-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.prompt-config-section-title {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.prompt-config-section-title h3 {
  margin: 0;
  color: var(--blue-dark);
  font-size: 15px;
  font-weight: 900;
}

.prompt-config-section-title span {
  color: #8a98ad;
  font-size: 12px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.prompt-config-textarea {
  display: block;
  width: 100%;
  min-height: 360px;
  max-height: 48vh;
  padding: 16px 18px;
  border: 1px solid #cfe0ff;
  border-radius: 12px;
  background: linear-gradient(180deg, #fbfdff 0%, #f6f9ff 100%);
  color: #172033;
  font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: 14px;
  line-height: 1.85;
  letter-spacing: 0.01em;
  resize: vertical;
  box-sizing: border-box;
  outline: none;
  transition: border-color .15s ease, box-shadow .15s ease;
}

.prompt-config-textarea.is-compact {
  min-height: 240px;
}

.prompt-config-textarea:focus {
  border-color: #8eb5ff;
  box-shadow: 0 0 0 3px rgba(71, 124, 255, .1);
  background: #fff;
}

.prompt-config-preview {
  min-height: 360px;
  max-height: 48vh;
  overflow: auto;
  padding: 16px 18px;
  border: 1px solid #dbe7ff;
  border-radius: 12px;
  background: #fff;
  color: var(--ink);
  font-size: 14px;
  line-height: 1.75;
}

.prompt-config-preview.is-compact {
  min-height: 240px;
}

.prompt-config-preview.is-readonly {
  min-height: 220px;
  max-height: 36vh;
  background: linear-gradient(180deg, #fafcff 0%, #f4f8ff 100%);
}

.prompt-config-preview :deep(.md-heading) {
  margin: 0;
  color: var(--ink);
  line-height: 1.35;
}

.prompt-config-preview :deep(.md-heading-1) {
  margin: 0 0 14px;
  padding-bottom: 10px;
  border-bottom: 2px solid #d8e5ff;
  font-size: 22px;
  font-weight: 900;
  color: var(--blue-dark);
}

.prompt-config-preview :deep(.md-heading-2) {
  margin: 4px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
  font-size: 18px;
  font-weight: 850;
}

.prompt-config-preview :deep(.md-heading-3) {
  margin: 16px 0 8px;
  padding: 4px 0 4px 12px;
  border-left: 3px solid var(--blue);
  font-size: 15px;
  font-weight: 800;
  color: var(--blue-dark);
}

.prompt-config-preview :deep(.md-paragraph) {
  margin: 0 0 8px;
}

.prompt-config-preview :deep(.md-paragraph:last-child) {
  margin-bottom: 0;
}

.prompt-config-preview :deep(.md-empty) {
  color: #8a98ad;
  font-style: italic;
}

.prompt-config-preview :deep(.md-list) {
  margin: 6px 0 12px;
  padding-left: 22px;
}

.prompt-config-preview :deep(.md-list li) {
  margin: 5px 0;
  padding-left: 2px;
}

.prompt-config-preview :deep(.md-list li::marker) {
  color: var(--blue);
}

.prompt-config-preview :deep(.md-code) {
  padding: 2px 7px;
  border: 1px solid #dbe7ff;
  border-radius: 6px;
  background: #f4f8ff;
  color: #2f5fbf;
  font-family: Consolas, "Courier New", monospace;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.prompt-config-preview :deep(.md-quote) {
  margin: 8px 0 12px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-left: 3px solid var(--blue);
  border-radius: 0 8px 8px 0;
  background: var(--blue-soft);
  color: var(--ink);
  font-size: 14px;
  font-weight: 700;
}

.prompt-config-preview :deep(.md-divider) {
  height: 1px;
  margin: 14px 0;
  border: 0;
  background: var(--line);
}

.prompt-config-preview :deep(mark),
.prompt-config-preview :deep(strong) {
  color: var(--red);
  font-weight: 900;
}

.prompt-config-preview :deep(mark) {
  padding: 0;
  background: transparent;
}

.prompt-config-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.progress-panel {
  padding-bottom: 18px;
}

.progress-hero {
  margin-bottom: 14px;
  padding: 14px;
  border: 1px solid #d8e5ff;
  border-radius: 12px;
  background: linear-gradient(180deg, #ffffff 0%, #f4f8ff 100%);
}

.progress-hero-top {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 10px;
}

.progress-learned {
  color: var(--blue-dark);
  font-size: 34px;
  font-weight: 900;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.progress-total {
  color: var(--muted);
  font-size: 14px;
  font-weight: 700;
}

.progress-bar-track {
  height: 8px;
  border-radius: 999px;
  background: #e3edff;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--blue) 0%, #6b96ff 100%);
  transition: width 0.35s ease;
}

.progress-percent {
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
}

.progress-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 14px;
}

.progress-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 6px;
  border: 1px solid #e3edff;
  border-radius: 10px;
  background: #fff;
}

.progress-stat-value {
  color: var(--blue-dark);
  font-size: 20px;
  font-weight: 900;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.progress-stat-label {
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
}

.progress-meta {
  display: grid;
  gap: 8px;
  margin-bottom: 14px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(237, 244, 255, .55);
}

.progress-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.progress-meta-label {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.progress-meta-value {
  color: var(--ink);
  font-size: 13px;
  font-weight: 800;
  text-align: right;
}

.progress-meta-link {
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--blue-dark);
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  text-align: right;
}

.progress-meta-link:hover {
  color: var(--blue);
  text-decoration: underline;
}

.progress-section {
  margin-top: 12px;
}

.progress-section-title {
  margin: 0 0 8px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.mastery-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.mastery-tag {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.mastery-tag.is-solid {
  border: 1px solid #9ebfff;
  background: var(--blue-soft);
  color: var(--blue-dark);
}

.mastery-tag.is-half {
  border: 1px solid #ffd7a8;
  background: #fff7eb;
  color: #b45309;
}

.mastery-tag.is-weak {
  border: 1px solid #f2c6c6;
  background: #fff5f5;
  color: #b42318;
}

.recent-articles {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.recent-article-chip {
  min-height: 28px;
  padding: 0 10px;
  border: 1px solid #cfe0ff;
  border-radius: 999px;
  background: #fff;
  color: var(--blue-dark);
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.16s ease;
}

.recent-article-chip:hover {
  border-color: var(--blue);
  background: var(--blue-soft);
}

.recent-article-chip.is-today {
  border-color: #ffd7a8;
  background: #fffaf3;
  color: #9a3412;
}

.recent-article-chip.is-today:hover {
  border-color: var(--orange);
  background: #fff4e8;
}

.recent-article-chip.is-active {
  border-color: var(--blue);
  background: var(--blue-soft);
  color: var(--blue-dark);
  box-shadow: inset 0 0 0 1px rgba(71, 124, 255, .12);
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

@media (max-width: 1280px) {
  .study-layout {
    grid-template-columns: auto minmax(0, 1fr) 320px;
  }
}

@media (max-width: 1100px) {
  .study-shell {
    height: auto;
    min-height: calc(100vh - 44px);
    overflow: auto;
  }

  .study-layout {
    display: flex;
    flex-direction: column;
  }

  .article-list-panel,
  .lesson-side {
    position: static;
    height: auto;
    max-height: none;
    width: auto !important;
  }

  .article-list-resizer {
    display: none;
  }

  .article-list-card {
    max-height: 320px;
  }

  .article-hover-preview {
    display: none;
  }
}

@media (max-width: 720px) {
  .study-shell {
    padding: 14px;
  }

  .composer {
    padding: 10px 14px 12px;
  }

  .composer-shell {
    flex-direction: column;
    align-items: stretch;
    padding: 10px 12px;
  }

  .composer-send {
    width: 100%;
    height: 44px;
    margin-bottom: 0;
  }

  .composer-hint {
    text-align: center;
  }

  .chat-main {
    height: auto;
    min-height: 420px;
  }

  .chat-row.user .chat-bubble {
    max-width: 86%;
  }
}
</style>

<style>
.main:has(.study-shell) {
  overflow: hidden;
  height: calc(100vh - 44px);
  padding: 0;
}

@media (max-width: 1100px) {
  .main:has(.study-shell) {
    overflow: auto;
    height: auto;
    min-height: calc(100vh - 44px);
  }
}
</style>
