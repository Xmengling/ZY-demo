<template>
  <div class="consult-page">
    <section class="collector panel consult-form">
      <div class="collector-hero">
        <div class="hero-top">
          <h2>问诊信息采集</h2>
          <el-tag :type="sessionId ? 'success' : 'warning'" effect="light">
            {{ sessionId ? '已建档' : draftSavedAt ? '草稿已保存' : '未保存' }}
          </el-tag>
        </div>
      </div>

      <nav class="module-nav" aria-label="问诊模块导航">
        <div class="module-tab-list">
          <button
            v-for="m in moduleNav"
            :key="m.key"
            type="button"
            :class="{ active: activeModule === m.key }"
            @click="showModule(m.key)"
          >
            {{ m.label }}
          </button>
        </div>
        <div class="module-nav-right">
          <span class="selected-count">{{ selectedSymptoms.length }} 个症状</span>
          <button
            type="button"
            class="module-nav-action-btn"
            :class="allVisibleCollapsed ? 'expand-all' : 'collapse-all'"
            :title="allVisibleCollapsed ? '展开全部' : '折叠全部'"
            :aria-label="allVisibleCollapsed ? '展开全部' : '折叠全部'"
            @click="toggleAllSections"
          />
        </div>
      </nav>

      <div ref="formScrollRef" class="form-scroll">
        <!-- 基础信息 -->
        <section
          v-show="isSectionVisible('base')"
          class="form-section"
          :class="{ 'is-collapsed': collapsed.base }"
        >
          <div class="section-head" role="button" tabindex="0" @click="toggleSection('base')" @keydown.enter="toggleSection('base')">
            <div class="section-head-main">
              <div class="section-name"><span class="num">1</span>基础信息与主诉</div>
            </div>
            <div class="section-head-meta">
              <el-tag type="warning" effect="light">必填</el-tag>
              <span class="section-chevron" aria-hidden="true" />
            </div>
          </div>
          <div v-show="!collapsed.base" class="section-content">
            <div class="base-grid base-info-grid">
              <div class="field slim">
                <label>姓名</label>
                <el-input v-model="form.patient_name" placeholder="患者姓名" />
              </div>
              <div class="field slim">
                <label>年龄</label>
                <el-input v-model="form.age" placeholder="年龄" />
              </div>
              <div class="field slim">
                <label>性别</label>
                <el-select v-model="form.gender" placeholder="选择" style="width: 100%">
                  <el-option label="女" value="女" />
                  <el-option label="男" value="男" />
                </el-select>
              </div>
              <div class="field slim">
                <label>电话</label>
                <el-input v-model="form.phone" placeholder="联系电话" />
              </div>
              <div class="field slim">
                <label>住址</label>
                <el-input v-model="form.address" placeholder="住址或地区" />
              </div>
              <div class="field slim">
                <label>现代诊断</label>
                <el-input v-model="form.modern_diagnosis" placeholder="现代诊断/检查" />
              </div>
              <div class="field wide">
                <label>主诉</label>
                <el-input
                  v-model="form.chief_complaint"
                  class="consult-textarea"
                  type="textarea"
                  :rows="2"
                  placeholder="最困扰的症状、开始时间、加重或缓解因素"
                />
              </div>
              <div class="field wide label-wide">
                <label>病程/诱因/既往史/用药史</label>
                <el-input
                  v-model="form.history"
                  class="consult-textarea"
                  type="textarea"
                  :rows="2"
                  placeholder="病程、诱因、既往病史、正在用药、过敏史"
                />
              </div>
            </div>
          </div>
        </section>

        <!-- 证候采集 -->
        <section
          v-for="section in sections"
          :key="section.key"
          v-show="isSectionVisible(section.key)"
          class="form-section collect-section"
          :class="{ 'is-collapsed': collapsed[section.key] }"
        >
          <div
            class="section-head"
            role="button"
            tabindex="0"
            @click="toggleSection(section.key)"
            @keydown.enter="toggleSection(section.key)"
          >
            <div class="section-head-main">
              <div class="section-name">
                <span class="num">{{ section.order }}</span>
                <span class="section-title-text">{{ section.title }}</span>
                <InquiryHints
                  :module-key="section.key"
                  :hints="section.inquiry_hints || []"
                  @updated="(list) => updateSectionHints(section.key, list)"
                />
              </div>
            </div>
            <div class="section-head-meta">
              <div v-if="scoredBlocks(section).length" class="section-score-summary">
                <PathologyTag
                  v-for="block in scoredBlocks(section)"
                  :key="block.label"
                  :label="block.label"
                  :score="form.scores[block.label]"
                />
              </div>
              <span class="section-chevron" aria-hidden="true" />
            </div>
          </div>
          <div v-show="!collapsed[section.key]" class="section-content">
            <div class="biao-list">
              <div
                v-for="block in section.blocks"
                :key="block.label"
                class="biao-block"
                :class="pathologyToneClass(block.label)"
              >
                <div class="biao-label">{{ block.label }}</div>
                <div class="biao-body">
                  <div class="biao-row">
                    <div class="biao-symptoms">
                      <SymptomChips
                        :block-label="block.label"
                        :chips="chipsForBlock(block)"
                        :selected="form.selected"
                        :note="form.notes[block.label] || ''"
                        @update:chips="(list) => setChipList(block.label, list)"
                        @update:note="(val) => (form.notes[block.label] = val)"
                        @toggle-selected="onToggleSelected"
                      />
                    </div>
                    <div class="biao-input">
                      <div class="biao-input-title">本例所见</div>
                      <el-input
                        v-model="form.notes[block.label]"
                        type="textarea"
                        :rows="2"
                        class="consult-textarea"
                        placeholder="记录本例所见、程度、时间、诱因"
                      />
                    </div>
                    <div class="biao-score">
                      <div class="score-title">病理打分</div>
                      <el-input-number
                        v-model="form.scores[block.label]"
                        :min="0"
                        :max="100"
                        :controls="false"
                        class="score-input"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 舌脉腹诊 -->
        <section
          v-show="isSectionVisible('tongue')"
          class="form-section"
          :class="{ 'is-collapsed': collapsed.tongue }"
        >
          <div class="section-head" role="button" tabindex="0" @click="toggleSection('tongue')" @keydown.enter="toggleSection('tongue')">
            <div class="section-head-main">
              <div class="section-name"><span class="num">9</span>舌诊、脉诊、腹诊</div>
            </div>
            <div class="section-head-meta">
              <el-tag type="success" effect="light">证据补强</el-tag>
              <span class="section-chevron" aria-hidden="true" />
            </div>
          </div>
          <div v-show="!collapsed.tongue" class="section-content">
            <div class="base-grid">
              <div class="field">
                <label>舌质</label>
                <el-input v-model="form.tongue_body" placeholder="如淡、红、暗、胖大齿痕" />
              </div>
              <div class="field">
                <label>舌苔</label>
                <el-input v-model="form.tongue_coat" placeholder="如薄白、黄腻、少苔" />
              </div>
              <div class="field">
                <label>脉象</label>
                <el-input v-model="form.pulse" placeholder="如浮、沉、弦、滑、数、微细" />
              </div>
              <div class="field">
                <label>腹诊</label>
                <el-input v-model="form.abdominal" placeholder="心下、胸胁、少腹、拒按/喜按" />
              </div>
              <div class="field wide">
                <label>备注</label>
                <el-input v-model="form.diagnosis_note" type="textarea" :rows="2" placeholder="舌照说明、腹诊补充、望闻切其他信息" />
              </div>
            </div>
          </div>
        </section>

        <!-- 处方 -->
        <section
          v-show="isSectionVisible('prescription')"
          class="form-section prescription-section"
          :class="{ 'is-collapsed': collapsed.prescription }"
        >
          <div class="section-head" role="button" tabindex="0" @click="toggleSection('prescription')" @keydown.enter="toggleSection('prescription')">
            <div class="section-head-main">
              <div class="section-name"><span class="num">10</span>处方</div>
            </div>
            <div class="section-head-meta">
              <el-tag type="success" effect="light">开方</el-tag>
              <span class="section-chevron" aria-hidden="true" />
            </div>
          </div>
          <div v-show="!collapsed.prescription" class="section-content">
            <PrescriptionBlock
              v-model="form.prescription"
              :formula-index="formulaIndex"
              :formula-names="formulaNames"
            />
          </div>
        </section>
      </div>

      <div class="actions">
        <span class="text-muted">{{ draftHint }}</span>
        <div>
          <el-button @click="resetForm">清空</el-button>
          <el-button type="primary" :loading="saving" @click="saveIntake">保存问诊</el-button>
        </div>
      </div>
    </section>

    <aside class="analysis panel">
      <div class="analysis-head">
        <h3>AI 分析</h3>
      </div>

      <div class="analysis-body">
        <div class="status-card">
          <div class="status-title">
            <span>问诊摘要</span>
            <el-tag type="info" effect="light">本地汇总</el-tag>
          </div>
          <ul class="summary-list">
            <li v-for="line in summaryLines" :key="line">{{ line }}</li>
          </ul>
        </div>

        <div class="status-card">
          <div class="status-title">
            <span>十二字病理记录</span>
            <el-tag type="warning" effect="light">手动分数</el-tag>
          </div>
          <div class="pathology-grid">
            <div
              v-for="item in pathologyScores"
              :key="item.label"
              class="pathology"
              :class="pathologyToneClass(item.label)"
            >
              <PathologyTag :label="item.label" />
              <span class="pathology-score">{{ item.score }}</span>
            </div>
            <div v-if="!pathologyScores.length" class="empty-hint pathology-empty">填写病理打分后会在这里汇总。</div>
          </div>
        </div>

        <div class="status-card">
          <div class="status-title">
            <span>关键追问</span>
            <el-tag effect="light">待接 AI</el-tag>
          </div>
          <div v-for="q in followUpQuestions" :key="q.text" class="question">
            {{ q.text }}
            <small v-if="q.hint">{{ q.hint }}</small>
          </div>
        </div>

        <div class="status-card">
          <div class="status-title">
            <span>方证候选</span>
            <el-tag type="primary" effect="light">学习参考</el-tag>
          </div>
          <div v-for="item in formulaCandidates" :key="item.name" class="formula-row">
            <div>
              <div class="formula-head">
                <strong>{{ item.name }}</strong>
                <span class="formula-pathology">
                  <PathologyTag v-for="tag in item.pathology" :key="tag" :label="tag" />
                </span>
              </div>
              <div class="muted">{{ item.note }}</div>
            </div>
            <el-tag :type="item.tagType" effect="light">{{ item.level }}</el-tag>
          </div>
          <div v-if="!formulaCandidates.length" class="empty-hint">录入处方或保存后，可结合 AI 生成方证候选。</div>
        </div>

        <div class="notice">
          出现持续高热、剧烈腹痛、胸痛、呕血便血、呼吸困难等情况，应及时线下就医；本页内容用于学习和辅助整理，不替代医生诊疗。
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { consultApi, formulasApi } from '../api'
import SymptomChips from '../components/consult/SymptomChips.vue'
import PrescriptionBlock from '../components/consult/PrescriptionBlock.vue'
import PathologyTag from '../components/consult/PathologyTag.vue'
import InquiryHints from '../components/consult/InquiryHints.vue'
import { buildFormulaPowderIndex, lookupFormulaPowder } from '../utils/formulaPowder'
import { getPathologyToneClass } from '../utils/pathologyTone'

const pathologyToneClass = getPathologyToneClass

const route = useRoute()
const router = useRouter()
const sessionId = ref(route.params.id ? Number(route.params.id) : null)
const activeModule = ref('all')
const saving = ref(false)
const draftSavedAt = ref('')
const formScrollRef = ref(null)
const formulaIndex = ref(new Map())
const formulaNames = ref([])

const collapsed = reactive({
  base: false,
  tongue: false,
  prescription: false
})

const fallbackSections = [
  {
    key: 'surface',
    order: 2,
    title: '表证采集',
    tag: '表/半表',
    tone: 'tone-blue',
    blocks: [
      { label: '表虚', symptoms: ['恶风', '汗出', '自汗', '发热', '头痛', '鼻鸣', '干呕', '脉浮缓', '脉浮弱', '项背不舒'] },
      { label: '表实', symptoms: ['恶寒', '发热', '无汗', '头痛', '身痛', '骨节疼痛', '项背强', '喘', '咳嗽', '脉浮紧', '脉浮数'] }
    ]
  },
  {
    key: 'interior',
    order: 3,
    title: '里证采集',
    tag: '里热/里寒/里虚',
    tone: 'tone-amber',
    blocks: [
      { label: '里热', symptoms: ['口渴喜冷', '心烦', '便干', '小便短赤', '舌红苔黄'] },
      { label: '里寒', symptoms: ['腹痛喜温', '下利清谷', '喜热饮', '四肢冷', '舌淡苔白'] },
      { label: '里虚', symptoms: ['食欲差', '乏力', '胃脘隐痛', '喜按', '久病体虚'] },
      { label: '里实', symptoms: ['腹满拒按', '大便不通', '烦躁', '潮热', '腹痛固定'] }
    ]
  },
  {
    key: 'half',
    order: 4,
    title: '半证采集',
    tag: '半表/半热/半虚',
    tone: 'tone-blue',
    blocks: [
      { label: '半表', symptoms: ['往来寒热', '胸胁苦满', '口苦', '咽干', '目眩'] },
      { label: '半热', symptoms: ['口苦心烦', '胸胁不舒', '恶心欲呕', '苔黄', '脉弦数'] },
      { label: '半虚', symptoms: ['默默不欲饮食', '乏力', '胃气弱', '容易反复', '脉虚'] }
    ]
  },
  {
    key: 'water',
    order: 5,
    title: '水证采集',
    tag: '水实/水虚',
    tone: 'tone-green',
    blocks: [
      { label: '水实', symptoms: ['小便不利', '眩晕', '心下悸', '水肿', '痰多'] },
      { label: '水虚', symptoms: ['口干津少', '皮肤干', '便干', '少苔', '久汗伤津'] }
    ]
  },
  {
    key: 'qi',
    order: 6,
    title: '气证采集',
    tag: '气实/气虚',
    tone: 'tone-green',
    blocks: [
      { label: '气实', symptoms: ['胀满', '嗳气', '胸闷', '气上冲', '情绪加重'] },
      { label: '气虚', symptoms: ['短气乏力', '声低', '易汗', '动则加重', '脉弱'] }
    ]
  },
  {
    key: 'blood',
    order: 7,
    title: '血证采集',
    tag: '血实/血虚',
    tone: 'tone-red',
    blocks: [
      { label: '血实', symptoms: ['刺痛固定', '少腹急结', '舌暗紫', '血块', '拒按'] },
      { label: '血虚', symptoms: ['面色萎黄', '心悸失眠', '眩晕', '唇甲淡', '月经量少'] }
    ]
  },
  {
    key: 'yin',
    order: 8,
    title: '阴性采集',
    tag: '阴性证据',
    tone: 'tone-amber',
    blocks: [{ label: '阴性', symptoms: ['精神疲惫', '嗜睡', '畏寒蜷卧', '手足厥冷', '脉微细'] }]
  }
]

const sections = ref(fallbackSections)

function defaultPrescription() {
  return {
    targetDose: 200,
    note: '',
    rows: []
  }
}

const emptyForm = () => ({
  patient_name: '',
  phone: '',
  address: '',
  age: '',
  gender: '',
  modern_diagnosis: '',
  chief_complaint: '',
  history: '',
  tongue_body: '',
  tongue_coat: '',
  pulse: '',
  abdominal: '',
  diagnosis_note: '',
  selected: {},
  notes: {},
  scores: {},
  chipLists: {},
  prescription: defaultPrescription()
})

const form = reactive(emptyForm())

sections.value.forEach((s) => {
  collapsed[s.key] = false
})

const moduleNav = computed(() => [
  { key: 'all', label: '全部' },
  { key: 'base', label: '基础信息' },
  ...sections.value.map((s) => ({ key: s.key, label: s.title.replace('采集', '') })),
  { key: 'tongue', label: '舌脉腹诊' },
  { key: 'prescription', label: '处方' }
])

const visibleSectionKeys = computed(() => {
  if (activeModule.value === 'all') {
    return ['base', ...sections.value.map((s) => s.key), 'tongue', 'prescription']
  }
  return [activeModule.value]
})

function isSectionVisible(key) {
  return visibleSectionKeys.value.includes(key)
}

const allVisibleCollapsed = computed(() => {
  const keys = visibleSectionKeys.value
  return keys.length > 0 && keys.every((k) => collapsed[k])
})

const selectedSymptoms = computed(() => Object.keys(form.selected).filter((k) => form.selected[k]))

const patientLine = computed(() => {
  const parts = [form.patient_name, form.gender, form.age ? `${form.age}岁` : '', form.phone].filter(Boolean)
  return parts.length ? parts.join('，') : '未填写'
})

const diagnosisLine = computed(() => {
  const parts = [
    form.tongue_body && `舌质${form.tongue_body}`,
    form.tongue_coat && `舌苔${form.tongue_coat}`,
    form.pulse && `脉${form.pulse}`,
    form.abdominal && `腹诊${form.abdominal}`
  ].filter(Boolean)
  return parts.length ? parts.join('，') : '未填写'
})

const pathologyScores = computed(() => {
  const items = Object.entries(form.scores)
    .map(([label, score]) => ({ label, score: Number(score || 0) }))
    .filter((i) => i.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 8)
  return items
})

const summaryLines = computed(() => {
  const lines = []
  if (form.chief_complaint) lines.push(`主诉：${form.chief_complaint}`)
  const top = pathologyScores.value.slice(0, 4)
  if (top.length) lines.push(`病理：${top.map((i) => `${i.label}${i.score}分`).join('、')}`)
  if (selectedSymptoms.value.length) {
    lines.push(`现症：${selectedSymptoms.value.slice(0, 12).join('、')}${selectedSymptoms.value.length > 12 ? '…' : ''}`)
  }
  if (diagnosisLine.value !== '未填写') lines.push(`舌脉腹：${diagnosisLine.value}`)
  if (!lines.length) lines.push('左侧录入后，这里会生成本地摘要。')
  return lines
})

const followUpQuestions = computed(() => {
  const qs = []
  if (!form.selected['往来寒热'] && !form.notes['半表']?.includes('寒热')) {
    qs.push({ text: '是否有往来寒热、胸胁苦满或口苦？', hint: '用于确认半证方向。' })
  }
  if (!form.abdominal) {
    qs.push({ text: '心下、胸胁、少腹按压情况如何？', hint: '用于区分里实、半证与气实。' })
  }
  if (!form.pulse) {
    qs.push({ text: '脉象是否已记录（浮沉迟数、弦滑细等）？', hint: '舌脉腹为重要证据。' })
  }
  if (!qs.length) {
    qs.push({ text: '保存后可由 AI 根据缺失信息生成 3-5 个追问。', hint: '' })
  }
  return qs.slice(0, 3)
})

const formulaCandidates = computed(() => {
  const rows = form.prescription?.rows || []
  return rows
    .filter((r) => r.name?.trim())
    .slice(0, 4)
    .map((r) => {
      const hit = lookupFormulaPowder(formulaIndex.value, r.name)
      return {
        name: `${r.name}方向`,
        pathology: hit?.pathology || [],
        note: hit ? `已录入处方，份数 ${r.portions}；待 AI 结合问诊进一步确认。` : '方名未在数据库命中，请核对。',
        level: hit ? '已录入' : '待核对',
        tagType: hit ? 'success' : 'warning'
      }
    })
})

const draftHint = computed(() => {
  if (sessionId.value) return `已关联问诊 #${sessionId.value}`
  if (draftSavedAt.value) return `本地草稿：${draftSavedAt.value}`
  return '填写内容会自动保存到本地草稿'
})

function chipsForBlock(block) {
  return form.chipLists[block.label]?.length ? form.chipLists[block.label] : [...(block.symptoms || [])]
}

function setChipList(label, list) {
  form.chipLists[label] = list
}

function onToggleSelected({ symptom, active }) {
  form.selected[symptom] = active
  if (!active) delete form.selected[symptom]
}

function hasPathologyScore(label) {
  const raw = form.scores[label]
  if (raw === undefined || raw === null || raw === '') return false
  const num = Number(raw)
  return !Number.isNaN(num) && num > 0
}

function scoredBlocks(section) {
  return (section.blocks || []).filter((block) => hasPathologyScore(block.label))
}

function updateSectionHints(key, hints) {
  const section = sections.value.find((item) => item.key === key)
  if (section) section.inquiry_hints = [...hints]
}

function showModule(key) {
  activeModule.value = key
  visibleSectionKeys.value.forEach((k) => {
    collapsed[k] = false
  })
  formScrollRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
}

function toggleSection(key) {
  collapsed[key] = !collapsed[key]
}

function toggleAllSections() {
  const next = !allVisibleCollapsed.value
  visibleSectionKeys.value.forEach((k) => {
    collapsed[k] = next
  })
}

function draftKey() {
  return sessionId.value ? `consult-draft-${sessionId.value}` : 'consult-draft-new'
}

function saveDraft() {
  const payload = JSON.parse(JSON.stringify(form))
  localStorage.setItem(draftKey(), JSON.stringify(payload))
  draftSavedAt.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function loadDraft() {
  const raw = localStorage.getItem(draftKey())
  if (!raw) return false
  try {
    Object.assign(form, emptyForm(), JSON.parse(raw))
    return true
  } catch {
    return false
  }
}

let draftTimer = null
watch(
  form,
  () => {
    clearTimeout(draftTimer)
    draftTimer = setTimeout(saveDraft, 800)
  },
  { deep: true }
)

function buildCaseText() {
  const scoreLine = pathologyScores.value.length
    ? pathologyScores.value.map((i) => `${i.label}${i.score}分`).join('；')
    : '未记录'
  const rx = (form.prescription?.rows || [])
    .filter((r) => r.name)
    .map((r) => `${r.name}×${r.portions}份`)
    .join('、')
  return [
    '医案整理',
    '',
    `患者：${patientLine.value}`,
    `现代诊断：${form.modern_diagnosis || '未填写'}`,
    `主诉：${form.chief_complaint || '未填写'}`,
    `病程/诱因/既往史/用药史：${form.history || '未填写'}`,
    `现症：${selectedSymptoms.value.join('、') || '未选择'}`,
    `舌脉腹诊：${diagnosisLine.value}`,
    `十二字病理记录：${scoreLine}`,
    `处方：${rx || '未录入'}`,
    `处方备注：${form.prescription?.note || '未填写'}`,
    '风险提示：出现持续高热、剧烈腹痛、胸痛、呕血便血、呼吸困难等情况，应及时线下就医。'
  ].join('\n')
}

function resetForm() {
  Object.assign(form, emptyForm())
  sessionId.value = null
  localStorage.removeItem('consult-draft-new')
  draftSavedAt.value = ''
  router.replace('/consult')
}

function buildPayload(status = 'collecting') {
  return {
    title: form.chief_complaint || form.patient_name || '新的问诊',
    patient_name: form.patient_name,
    phone: form.phone,
    address: form.address,
    gender: form.gender,
    age: form.age,
    modern_diagnosis: form.modern_diagnosis,
    status,
    intake_data: JSON.parse(JSON.stringify(form)),
    case_text: buildCaseText()
  }
}

async function saveIntake() {
  saving.value = true
  try {
    if (!sessionId.value) {
      const created = await consultApi.createSession({ title: form.chief_complaint || form.patient_name || '新的问诊' })
      sessionId.value = created.id
    }
    const saved = await consultApi.saveIntake(sessionId.value, buildPayload('collecting'))
    sessionId.value = saved.id
    localStorage.removeItem('consult-draft-new')
    saveDraft()
    router.replace(`/consult/${saved.id}`)
    ElMessage.success('问诊已保存')
  } finally {
    saving.value = false
  }
}

async function loadSession(id) {
  const detail = await consultApi.getSession(id)
  const data = detail.intake_data || {}
  Object.assign(form, emptyForm(), data)
  if (!form.prescription || !Array.isArray(form.prescription.rows)) {
    form.prescription = { ...defaultPrescription(), ...(form.prescription || {}) }
    if (!Array.isArray(form.prescription.rows)) form.prescription.rows = []
  }
  form.patient_name = detail.patient_name || form.patient_name
  form.phone = detail.phone || form.phone
  form.address = detail.address || form.address
  form.gender = detail.gender || form.gender
  form.age = detail.age || form.age
  form.modern_diagnosis = detail.modern_diagnosis || form.modern_diagnosis
}

async function loadSymptomPresets() {
  try {
    const rows = await consultApi.symptomPresets()
    if (Array.isArray(rows) && rows.length) {
      sections.value = rows.map((section) => ({
        ...section,
        inquiry_hints: section.inquiry_hints || [],
        blocks: (section.blocks || []).map((block) => ({
          ...block,
          tone: block.tone || section.tone
        }))
      }))
      sections.value.forEach((s) => {
        if (collapsed[s.key] === undefined) collapsed[s.key] = false
      })
    }
  } catch {
    sections.value = fallbackSections
  }
}

async function loadFormulas() {
  try {
    const data = await formulasApi.list()
    const formulas = data?.formulas || []
    formulaIndex.value = buildFormulaPowderIndex(formulas)
    formulaNames.value = formulas.map((f) => f.name).filter(Boolean).sort((a, b) => a.localeCompare(b, 'zh-CN'))
  } catch {
    formulaIndex.value = new Map()
    formulaNames.value = []
  }
}

watch(
  () => route.params.id,
  async (id) => {
    sessionId.value = id ? Number(id) : null
    if (sessionId.value) {
      await loadSession(sessionId.value)
    } else if (!loadDraft()) {
      Object.assign(form, emptyForm())
    }
  }
)

onMounted(async () => {
  await Promise.all([loadSymptomPresets(), loadFormulas()])
  if (sessionId.value) await loadSession(sessionId.value)
  else loadDraft()
})
</script>

<style scoped src="../styles/consult-legacy.css"></style>
