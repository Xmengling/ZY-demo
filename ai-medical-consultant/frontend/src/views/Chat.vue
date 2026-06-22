<template>
  <div class="consult-page" :class="{ 'is-summary-docked-left': summaryDockedLeft }">
    <section
      class="collector panel consult-form"
      :class="{ 'has-summary-overlay': summaryDockedLeft }"
      @focusout="handleCollectFocusout"
    >
      <div class="collector-hero">
        <div class="hero-top">
          <h2>问诊信息采集</h2>
          <nav v-if="sessionId" class="case-nav" aria-label="医案切换">
            <button
              type="button"
              class="case-nav-btn"
              :disabled="!prevSessionId"
              :title="adjacentCaseHint.prev ? `上一则：${adjacentCaseHint.prev}` : '已是第一则（最新）'"
              @click="goAdjacentSession('prev')"
            >
              <el-icon :size="14"><ArrowLeft /></el-icon>
              <span class="case-nav-btn-text">上一则</span>
            </button>
            <span class="case-nav-pos" :title="caseNavTitle">{{ caseNavPosition }}</span>
            <button
              type="button"
              class="case-nav-btn"
              :disabled="!nextSessionId"
              :title="adjacentCaseHint.next ? `下一则：${adjacentCaseHint.next}` : '已是最后一则（最早）'"
              @click="goAdjacentSession('next')"
            >
              <span class="case-nav-btn-text">下一则</span>
              <el-icon :size="14"><ArrowRight /></el-icon>
            </button>
          </nav>
          <div class="hero-top-right">
            <div class="visit-mode-switch" aria-label="诊次切换">
              <button
                type="button"
                :class="{ active: activeVisitMode === 'first' }"
                @click="switchVisitMode('first')"
              >
                首诊
              </button>
              <button
                v-for="(visit, index) in form.followups"
                :key="visit.id || index"
                type="button"
                class="visit-mode-tab"
                :class="{ active: activeVisitMode === 'followup' && activeFollowupIndex === index }"
                @click="switchFollowup(index)"
              >
                <span>{{ visit.label || visitLabel(index) }}</span>
                <span
                  v-if="isFollowupEmpty(visit)"
                  class="visit-tab-delete"
                  title="删除空复诊"
                  @click.stop="deleteEmptyFollowup(index)"
                >×</span>
              </button>
            </div>
            <el-button size="small" type="success" plain @click="addFollowup">复诊</el-button>
            <el-button size="small" type="primary" plain @click="fillDialogVisible = true">粘贴自动填充</el-button>
            <el-tag :type="sessionId ? 'success' : 'warning'" effect="light">
              {{ sessionId ? '已建档' : draftSavedAt ? '草稿已保存' : '未保存' }}
            </el-tag>
          </div>
        </div>
      </div>

      <nav v-if="activeVisitMode === 'first'" class="module-nav" aria-label="问诊模块导航">
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
            :title="allVisibleCollapsed ? '展开全部' : '折叠全部'"
            :aria-label="allVisibleCollapsed ? '展开全部' : '折叠全部'"
            @click="toggleAllSections"
          >
            <span
              class="module-nav-action-btn__chevrons"
              :class="allVisibleCollapsed ? 'is-expand' : 'is-collapse'"
              aria-hidden="true"
            >
              <i /><i />
            </span>
          </button>
        </div>
      </nav>

      <div v-if="activeVisitMode === 'first'" ref="formScrollRef" class="form-scroll">
        <!-- 基础信息 -->
        <section
          v-show="isSectionVisible('base')"
          class="form-section collect-section"
          :class="{ 'is-collapsed': collapsed.base }"
        >
          <div class="section-head" role="button" tabindex="0" @click="toggleSection('base')" @keydown.enter="toggleSection('base')">
            <div class="section-head-main">
              <div class="section-name">
                <span class="num">1</span>
                <span class="section-title-text">基础信息与主诉</span>
              </div>
            </div>
            <div class="section-head-meta">
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
                <label>就诊时间</label>
                <el-date-picker
                  v-model="form.visit_time"
                  type="date"
                  value-format="YYYY-MM-DD"
                  placeholder="选择日期"
                  style="width: 100%"
                />
              </div>
              <div class="field slim">
                <label>主诊医生</label>
                <el-input v-model="form.doctor" placeholder="主诊医生" />
              </div>
              <div class="field slim">
                <label>现代诊断</label>
                <el-input v-model="form.modern_diagnosis" placeholder="现代诊断/检查" />
              </div>
              <div class="field half">
                <label>主诉</label>
                <el-input
                  v-model="form.chief_complaint"
                  class="consult-textarea"
                  type="textarea"
                  :rows="3"
                  placeholder="最困扰的症状、开始时间、加重或缓解因素"
                />
              </div>
              <div class="field half">
                <label>病史</label>
                <el-input
                  v-model="form.history"
                  class="consult-textarea"
                  type="textarea"
                  :rows="3"
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
                <span class="section-title-text">{{ sectionDisplayTitle(section.title) }}</span>
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
                :class="[
                  pathologyToneClass(block.label),
                  { 'is-block-collapsed': isBlockCollapsed(block.label) }
                ]"
              >
                <div
                  class="biao-label"
                  role="button"
                  tabindex="0"
                  @click="toggleBlock(block.label)"
                  @keydown.enter="toggleBlock(block.label)"
                >
                  {{ block.label }}
                </div>
                <div
                  v-if="isBlockCollapsed(block.label)"
                  class="biao-collapsed-bar"
                  role="button"
                  tabindex="0"
                  @click="toggleBlock(block.label)"
                  @keydown.enter="toggleBlock(block.label)"
                >
                  <span class="biao-block-preview">{{ blockPreview(block) || '暂无症状，点击展开' }}</span>
                </div>
                <div v-else class="biao-body">
                  <div class="biao-row">
                    <div class="biao-input">
                      <el-input
                        v-model="form.notes[block.label]"
                        type="textarea"
                        :rows="1"
                        :autosize="{ minRows: 1, maxRows: 6 }"
                        class="consult-textarea biao-note-textarea"
                        placeholder="记录本例所见、程度、时间、诱因"
                      />
                      <div class="biao-input-symptoms">
                        <SymptomChips
                          :block-label="block.label"
                          :chips="chipsForBlock(block)"
                          :selected="form.selected"
                          :note="form.notes[block.label] || ''"
                          @update:chips="(list) => setChipList(block.label, list)"
                          @persisted="(list) => onBlockSymptomsPersisted(block.label, list)"
                          @update:note="(val) => (form.notes[block.label] = val)"
                          @toggle-selected="onToggleSelected"
                        />
                      </div>
                    </div>
                    <div class="biao-aside">
                      <button
                        type="button"
                        class="biao-block-chevron"
                        :aria-label="isBlockCollapsed(block.label) ? '展开' : '折叠'"
                        @click.stop="toggleBlock(block.label)"
                      />
                      <div class="biao-score">
                        <PathologyStarRating
                          :model-value="Number(form.scores[block.label]) || 0"
                          :tone-class="pathologyToneClass(block.label)"
                          @update:model-value="(value) => setPathologyScore(block.label, value)"
                        />
                      </div>
                    </div>
                  </div>
                </div>
                <button
                  v-if="isBlockCollapsed(block.label)"
                  type="button"
                  class="biao-block-chevron is-collapsed"
                  aria-label="展开"
                  @click.stop="toggleBlock(block.label)"
                />
              </div>
            </div>
          </div>
        </section>

        <!-- 舌脉腹诊 -->
        <section
          v-show="isSectionVisible('tongue')"
          class="form-section collect-section"
          :class="{ 'is-collapsed': collapsed.tongue }"
        >
          <div class="section-head" role="button" tabindex="0" @click="toggleSection('tongue')" @keydown.enter="toggleSection('tongue')">
            <div class="section-head-main">
              <div class="section-name">
                <span class="num">9</span>
                <span class="section-title-text">舌诊、脉诊、腹诊</span>
              </div>
            </div>
            <div class="section-head-meta">
              <span class="section-chevron" aria-hidden="true" />
            </div>
          </div>
          <div v-show="!collapsed.tongue" class="section-content">
            <div class="base-grid tongue-three-grid">
              <div class="field">
                <label>舌像</label>
                <el-input v-model="form.tongue_image" placeholder="如淡红有齿痕，苔薄黄" />
              </div>
              <div class="field">
                <label>脉像</label>
                <el-input v-model="form.pulse" placeholder="如略弦，脉律不齐，约120次/分" />
              </div>
              <div class="field">
                <label>腹诊</label>
                <el-input v-model="form.abdominal" placeholder="心下、胸胁、少腹、拒按/喜按" />
              </div>
            </div>
          </div>
        </section>

        <!-- 处方 -->
        <section
          v-show="isSectionVisible('prescription')"
          class="form-section collect-section prescription-section"
          :class="{ 'is-collapsed': collapsed.prescription }"
        >
          <div class="section-head" role="button" tabindex="0" @click="toggleSection('prescription')" @keydown.enter="toggleSection('prescription')">
            <div class="section-head-main">
              <div class="section-name">
                <span class="num">10</span>
                <span class="section-title-text">处方</span>
              </div>
            </div>
            <div class="section-head-meta">
              <div v-if="prescriptionSectionTags.length" class="section-score-summary">
                <el-tag
                  v-for="name in prescriptionSectionTags"
                  :key="name"
                  type="success"
                  effect="light"
                >
                  {{ name }}
                </el-tag>
              </div>
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

      <div v-else ref="formScrollRef" class="form-scroll followup-scroll">
        <section class="form-section collect-section followup-section">
          <div class="section-head">
            <div class="section-head-main">
              <div class="section-name">
                <span class="num">2</span>
                <span class="section-title-text">{{ currentFollowup.label }}</span>
              </div>
            </div>
            <div class="section-head-meta">
              <div v-if="currentFollowup.changes?.length" class="section-score-summary">
                <el-tag
                  v-for="item in currentFollowup.changes"
                  :key="item"
                  type="success"
                  effect="light"
                >
                  {{ item }}
                </el-tag>
              </div>
            </div>
          </div>
          <div class="section-content">
            <div class="followup-grid">
              <div class="field followup-full followup-card followup-change-card">
                <label class="followup-card-title">服药后变化</label>
                <div class="followup-change-fields">
                  <div class="followup-change-field is-improved">
                    <label>好转的症状</label>
                    <el-input
                      v-model="currentFollowup.improved_symptoms"
                      class="consult-textarea followup-change-textarea"
                      type="textarea"
                      :autosize="{ minRows: 1, maxRows: 4 }"
                      placeholder="如便秘好转、胃痛减轻、睡眠改善"
                    />
                  </div>
                  <div class="followup-change-field is-worsened">
                    <label>加重的症状</label>
                    <el-input
                      v-model="currentFollowup.worsened_symptoms"
                      class="consult-textarea followup-change-textarea"
                      type="textarea"
                      :autosize="{ minRows: 1, maxRows: 4 }"
                      placeholder="如小便灼痛加重、新增腹胀"
                    />
                  </div>
                  <div class="followup-change-field is-remaining">
                    <label>仍存在的症状</label>
                    <el-input
                      v-model="currentFollowup.remaining_symptoms"
                      class="consult-textarea followup-change-textarea"
                      type="textarea"
                      :autosize="{ minRows: 1, maxRows: 4 }"
                      placeholder="如口干仍存、头晕仍有、睡眠仍浅"
                    />
                  </div>
                </div>
              </div>

              <div class="field followup-full followup-card followup-prescription-card">
                <label class="followup-card-title">本次调整方剂</label>
                <PrescriptionBlock
                  v-model="currentFollowup.prescription"
                  :formula-index="formulaIndex"
                  :formula-names="formulaNames"
                  show-import-previous
                  @import-previous="importPreviousPrescription"
                />
              </div>
            </div>
          </div>
        </section>
      </div>

      <div class="actions">
        <span class="text-muted">{{ draftHint }}</span>
        <div class="action-buttons">
          <el-button :disabled="!hasCaseContent" @click="copyCaseText">
            <el-icon><DocumentCopy /></el-icon>
            复制医案
          </el-button>
          <el-button :disabled="!hasCaseContent" @click="exportCaseText">
            <el-icon><Download /></el-icon>
            导出医案
          </el-button>
          <el-button @click="resetForm">清空</el-button>
          <el-button type="primary" :loading="saving" @click="saveIntake">保存问诊</el-button>
        </div>
      </div>

    </section>

    <aside class="analysis panel">
      <div class="analysis-body" :class="{ 'is-chat-expanded': summaryDockedLeft }">
        <div class="status-card summary-card" :class="{ 'is-docked-left': summaryDockedLeft }">
          <div class="status-title">
            <span>病例摘要</span>
            <div class="status-title-actions">
              <el-button
                size="small"
                text
                :title="summaryDockedLeft ? '放回右侧上方' : '翻到左侧覆盖问诊区'"
                @click="summaryDockedLeft = !summaryDockedLeft"
              >
                <el-icon><component :is="summaryDockedLeft ? ArrowRight : ArrowLeft" /></el-icon>
                {{ summaryDockedLeft ? '右侧' : '左侧' }}
              </el-button>
              <el-button size="small" text :disabled="!hasConsultSummary" @click="copyCaseSummary">
                <el-icon><DocumentCopy /></el-icon>
                复制
              </el-button>
            </div>
          </div>
          <div class="summary-list">
            <div v-if="!hasConsultSummary" class="is-empty">左侧录入后，这里会生成病例摘要。</div>
            <template v-else>
              <section
                v-for="group in consultSummaryGroups"
                :key="group.key"
                class="summary-visit-group"
              >
                <h4>{{ group.label }}</h4>
                <ul>
                  <li
                    v-for="item in group.lines"
                    :key="`${group.key}-${item.label}-${item.kind}`"
                    :class="{ 'summary-change-row': item.kind === 'changeGroups' }"
                    :title="formatConsultSummaryLine(item)"
                  >
                    <template v-if="item.kind === 'changeGroups'">
                      <div class="summary-change-groups">
                        <div
                          v-for="changeGroup in item.groups.filter((changeItem) => changeItem.text)"
                          :key="changeGroup.key"
                          class="summary-change-group"
                          :class="`is-${changeGroup.tone}`"
                        >
                          <span class="summary-change-label">{{ changeGroup.label }}</span>
                          <span class="summary-change-text">{{ changeGroup.text }}</span>
                        </div>
                      </div>
                    </template>
                    <template v-else>
                      <span
                        class="summary-pathology-label"
                        :class="item.kind === 'pathology' ? pathologyToneClass(item.label) : 'summary-label-meta'"
                      >{{ item.label }}<template v-if="item.score != null"><span class="summary-pathology-score">{{ item.score }}</span></template>：</span>
                      <span class="summary-line-text">{{ item.text }}</span>
                    </template>
                  </li>
                </ul>
              </section>
            </template>
          </div>
        </div>

        <div class="consult-ai-chat-wrap">
          <ConsultAiChat
            :session-id="sessionId"
            :case-context="caseSummaryText"
            :formula-names="prescriptionSectionTags"
            :pathology-scores="pathologyScores"
            :has-chief-complaint="hasChiefComplaint"
            @session-created="onAiSessionCreated"
          />
        </div>
      </div>
    </aside>

    <el-dialog v-model="fillDialogVisible" title="粘贴医案自动填充" width="640px" :close-on-click-modal="false">
      <p class="autofill-tip">
        粘贴医案或病历文字，AI 会识别姓名、性别、年龄、主诉、病程、舌脉腹诊、现代诊断，并从预设症状中勾选命中项。复诊内容不参与解析。
      </p>
      <el-input
        v-model="fillText"
        type="textarea"
        :rows="12"
        placeholder="在此粘贴医案原文"
      />
      <template #footer>
        <el-button :disabled="autoFilling" @click="fillDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="autoFilling" @click="applyAutoFill">AI 解析并填充</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="candidateDialogVisible"
      title="确认未自动填充的症状"
      width="760px"
      :close-on-click-modal="false"
    >
      <p class="autofill-tip">
        这些词来自原文，但 AI 没有直接勾选。请确认是否填入本次医案，或加入对应症状目录，方便以后自动识别。
      </p>
      <div class="autofill-candidates">
        <div
          v-for="candidate in pendingSymptomCandidates"
          :key="candidate.id"
          class="autofill-candidate"
          :class="{ 'is-ignored': candidate.action === 'ignore' }"
        >
          <div class="candidate-main">
            <div class="candidate-title">{{ candidate.raw_text }}</div>
            <div v-if="candidate.reason" class="candidate-reason">{{ candidate.reason }}</div>
            <div v-if="candidate.suggested_symptoms.length" class="candidate-suggestions">
              近似症状：{{ candidate.suggested_symptoms.join('、') }}
            </div>
          </div>
          <div class="candidate-controls">
            <el-select v-model="candidate.action" size="small" class="candidate-action">
              <el-option label="填入本次" value="fill" />
              <el-option label="填入并加入目录" value="add" />
              <el-option label="忽略" value="ignore" />
            </el-select>
            <el-select
              v-model="candidate.block_label"
              size="small"
              class="candidate-block"
              filterable
              placeholder="选择病理"
              :disabled="candidate.action === 'ignore'"
            >
              <el-option
                v-for="block in pathologyBlockOptions"
                :key="block.label"
                :label="block.label"
                :value="block.label"
              />
            </el-select>
            <el-select
              v-if="candidate.suggested_symptoms.length"
              v-model="candidate.selected_symptom"
              size="small"
              class="candidate-symptom"
              clearable
              placeholder="匹配已有症状"
              :disabled="candidate.action === 'ignore'"
            >
              <el-option
                v-for="symptom in candidate.suggested_symptoms"
                :key="symptom"
                :label="symptom"
                :value="symptom"
              />
            </el-select>
            <el-input
              v-model="candidate.symptom_name"
              size="small"
              class="candidate-name"
              placeholder="症状名"
              :disabled="candidate.action === 'ignore' || Boolean(candidate.selected_symptom)"
            />
          </div>
        </div>
      </div>
      <template #footer>
        <el-button :disabled="candidateApplying" @click="candidateDialogVisible = false">稍后处理</el-button>
        <el-button type="primary" :loading="candidateApplying" @click="applySymptomCandidates">确认填充</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, ArrowRight, DocumentCopy, Download } from '@element-plus/icons-vue'
import { consultApi, formulasApi } from '../api'
import SymptomChips from '../components/consult/SymptomChips.vue'
import PrescriptionBlock from '../components/consult/PrescriptionBlock.vue'
import ConsultAiChat from '../components/consult/ConsultAiChat.vue'
import PathologyTag from '../components/consult/PathologyTag.vue'
import PathologyStarRating from '../components/consult/PathologyStarRating.vue'
import InquiryHints from '../components/consult/InquiryHints.vue'
import { buildFormulaPowderIndex, lookupFormulaPowder, runDoseCalc } from '../utils/formulaPowder'
import { getPathologyToneClass } from '../utils/pathologyTone'
import { parseCaseText, FIELD_LABELS } from '../utils/caseTextParser'
import {
  buildConsultSummaryLines,
  buildFollowupChangeGroups,
  buildFollowupSummaryLines,
  formatConsultSummaryLine,
  formatConsultSummaryGroups,
  formatVisitDate
} from '../utils/consultSymptoms'

const pathologyToneClass = getPathologyToneClass

const route = useRoute()
const router = useRouter()
const sessionId = ref(route.params.id ? Number(route.params.id) : null)
const summaryDockedLeft = ref(false)
const activeModule = ref('all')
const activeVisitMode = ref('first')
const activeFollowupIndex = ref(0)
const saving = ref(false)
const autoSaving = ref(false)
const autoSavePending = ref(false)
const autoSaveSnapshot = ref('')
const draftSavedAt = ref('')
const formScrollRef = ref(null)
const formulaIndex = ref(new Map())
const formulaNames = ref([])
const fillDialogVisible = ref(false)
const fillText = ref('')
const autoFilling = ref(false)
const candidateDialogVisible = ref(false)
const pendingSymptomCandidates = ref([])
const candidateApplying = ref(false)
const sessionNavList = ref([])
const collapsed = reactive({
  base: false,
  tongue: false,
  prescription: false
})
const blockCollapsed = reactive({})
const blockCollapseManual = reactive({})
const sectionCollapseManual = reactive({})

const fallbackSections = [
  {
    key: 'surface',
    order: 2,
    title: '表证',
    inquiry_hints: ['寒热', '汗出', '恶风', '头痛头晕', '皮肤', '身痒', '肢凉怕冷', '疼痛', '鼻塞流涕', '咽痒咳嗽', '项背不舒', '无汗恶寒'],
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
    title: '里证',
    inquiry_hints: ['食欲、食冷、反酸烧心，呕吐、大便、肠鸣等'],
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
    title: '半证',
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
    title: '水证',
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
    title: '气证',
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
    title: '血证',
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
    title: '阴性',
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

function visitLabel(index = 0) {
  const labels = ['二诊', '三诊', '四诊', '五诊', '六诊', '七诊', '八诊', '九诊', '十诊']
  return labels[index] || `第${index + 2}诊`
}

function defaultFollowup(index = 0) {
  return {
    id: `followup-${Date.now()}-${index}`,
    label: visitLabel(index),
    changes: [],
    improved_symptoms: '',
    worsened_symptoms: '',
    remaining_symptoms: '',
    chief_complaint: '',
    symptoms_text: '',
    selected: {},
    notes: {},
    chipLists: {},
    tongue_image: '',
    pulse: '',
    abdominal: '',
    previous_formula: '',
    prescription: defaultPrescription()
  }
}

const emptyForm = () => ({
  patient_name: '',
  phone: '',
  address: '',
  age: '',
  gender: '',
  visit_time: '',
  doctor: '',
  modern_diagnosis: '',
  chief_complaint: '',
  history: '',
  tongue_image: '',
  pulse: '',
  abdominal: '',
  selected: {},
  notes: {},
  scores: {},
  chipLists: {},
  prescription: defaultPrescription(),
  followups: []
})

const form = reactive(emptyForm())

sections.value.forEach((s) => {
  collapsed[s.key] = false
})

const moduleNav = computed(() => [
  { key: 'all', label: '全部' },
  { key: 'base', label: '基础信息' },
  ...sections.value.map((s) => ({ key: s.key, label: sectionDisplayTitle(s.title) })),
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

const currentFollowup = computed(() => {
  ensureFollowup()
  return form.followups[activeFollowupIndex.value]
})

const pathologyBlockOptions = computed(() => {
  const blocks = []
  for (const section of sections.value || []) {
    for (const block of section.blocks || []) {
      if (block.label) blocks.push({ label: block.label, section: section.title })
    }
  }
  return blocks
})

const pathologyScores = computed(() => {
  const items = Object.entries(form.scores)
    .map(([label, score]) => ({ label, score: Number(score || 0) }))
    .filter((i) => i.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 8)
  return items
})

const consultSummaryLines = computed(() => buildConsultSummaryLines(form, sections.value))

const visibleFollowups = computed(() => (form.followups || []).filter((visit) => {
  return buildFollowupSummaryLines(visit, sections.value).some((item) => item.text)
}))

const consultSummaryGroups = computed(() => {
  const groups = []
  if (consultSummaryLines.value.some((item) => item.text)) {
    groups.push({ key: 'first', label: '首诊', lines: consultSummaryLines.value })
  }
  visibleFollowups.value.forEach((visit, index) => {
    groups.push({
      key: visit.id || `followup-${index}`,
      label: visit.label || visitLabel(index),
      lines: buildFollowupSummaryLines(visit, sections.value)
    })
  })
  return groups
})

const hasConsultSummary = computed(() => consultSummaryGroups.value.some((group) => group.lines.some((item) => item.text)))

const hasChiefComplaint = computed(() => Boolean(String(form.chief_complaint || '').trim()))

const prescriptionSectionTags = computed(() =>
  (form.prescription?.rows || [])
    .map((row) => String(row?.name || '').trim())
    .filter(Boolean)
)

const caseSummaryText = computed(() => formatConsultSummaryGroups(consultSummaryGroups.value))

function sessionNavLabel(row) {
  if (!row) return ''
  const chief = String(row.chief_complaint || row.title || '').trim()
  const patient = String(row.patient_name || '').trim()
  if (chief && patient) return `${patient} · ${chief}`
  return chief || patient || `医案 #${row.id}`
}

const currentNavIndex = computed(() => {
  if (!sessionId.value) return -1
  return sessionNavList.value.findIndex((item) => item.id === sessionId.value)
})

const prevSessionId = computed(() => {
  const idx = currentNavIndex.value
  if (idx <= 0) return null
  return sessionNavList.value[idx - 1]?.id ?? null
})

const nextSessionId = computed(() => {
  const idx = currentNavIndex.value
  if (idx < 0 || idx >= sessionNavList.value.length - 1) return null
  return sessionNavList.value[idx + 1]?.id ?? null
})

const caseNavPosition = computed(() => {
  const idx = currentNavIndex.value
  if (idx < 0 || !sessionNavList.value.length) return '—'
  return `${idx + 1} / ${sessionNavList.value.length}`
})

const caseNavTitle = computed(() => sessionNavLabel(sessionNavList.value[currentNavIndex.value]))

const adjacentCaseHint = computed(() => {
  const idx = currentNavIndex.value
  if (idx < 0) return { prev: '', next: '' }
  return {
    prev: sessionNavLabel(sessionNavList.value[idx - 1]),
    next: sessionNavLabel(sessionNavList.value[idx + 1])
  }
})

async function loadSessionNavList() {
  try {
    sessionNavList.value = await consultApi.listSessions({ case_only: true })
  } catch {
    sessionNavList.value = []
  }
}

function goAdjacentSession(direction) {
  const targetId = direction === 'prev' ? prevSessionId.value : nextSessionId.value
  if (!targetId) return
  const query = { ...route.query }
  delete query.module
  router.push({ path: `/consult/${targetId}`, query })
}

const hasCaseContent = computed(() => {
  const hasFollowupContent = (form.followups || []).some((visit) => buildFollowupSummaryLines(visit, sections.value).some((item) => item.text))
  return Boolean(
    form.patient_name ||
      form.chief_complaint ||
      form.history ||
      form.modern_diagnosis ||
      selectedSymptoms.value.length ||
      pathologyScores.value.length ||
      form.tongue_image ||
      form.pulse ||
      form.abdominal ||
      (form.prescription?.rows || []).some((row) => row.name) ||
      hasFollowupContent
  )
})

function onAiSessionCreated(id) {
  sessionId.value = id
}

const draftHint = computed(() => {
  if (sessionId.value) return `已关联问诊 #${sessionId.value}`
  if (draftSavedAt.value) return `本地草稿：${draftSavedAt.value}`
  return '填写内容会自动保存到本地草稿'
})

function sectionDisplayTitle(title) {
  return String(title || '').replace(/采集$/, '')
}

function normalizeIntakeTongue(data) {
  if (!data) return
  if (!data.tongue_image && (data.tongue_body || data.tongue_coat)) {
    const parts = [data.tongue_body, data.tongue_coat].map((s) => String(s || '').trim()).filter(Boolean)
    data.tongue_image = parts.join('，')
  }
}

function normalizeIntakeFollowups(data) {
  if (!data) return
  if (!Array.isArray(data.followups)) data.followups = []
  data.followups.forEach((visit, index) => normalizeFollowup(visit, index))
}

function chipsForBlock(block) {
  return form.chipLists[block.label]?.length ? form.chipLists[block.label] : [...(block.symptoms || [])]
}

function setChipList(label, list) {
  form.chipLists[label] = list
}

function ensureFollowup() {
  if (!Array.isArray(form.followups)) form.followups = []
  if (!form.followups.length) {
    form.followups.push({
      ...defaultFollowup(0),
      previous_formula: buildPrescriptionSummaryTextForForm(form.prescription)
    })
  }
  if (!form.followups[activeFollowupIndex.value]) activeFollowupIndex.value = 0
  normalizeFollowup(form.followups[activeFollowupIndex.value], activeFollowupIndex.value)
}

function normalizeFollowup(visit, index = 0) {
  if (!visit) return
  if (!visit.id) visit.id = `followup-${Date.now()}-${index}`
  visit.label = visit.label || visitLabel(index)
  visit.symptoms_text = String(visit.symptoms_text || '').trim()
  if (!Array.isArray(visit.changes)) visit.changes = []
  visit.improved_symptoms = String(visit.improved_symptoms || '').trim()
  visit.worsened_symptoms = String(visit.worsened_symptoms || '').trim()
  visit.remaining_symptoms = String(visit.remaining_symptoms || '').trim()
  if (!visit.selected || typeof visit.selected !== 'object') visit.selected = {}
  if (!visit.notes || typeof visit.notes !== 'object') visit.notes = {}
  if (!visit.chipLists || typeof visit.chipLists !== 'object') visit.chipLists = {}
  if (!visit.prescription || !Array.isArray(visit.prescription.rows)) {
    visit.prescription = { ...defaultPrescription(), ...(visit.prescription || {}) }
    if (!Array.isArray(visit.prescription.rows)) visit.prescription.rows = []
  }
  if (!String(visit.previous_formula || '').trim()) {
    visit.previous_formula = buildPrescriptionSummaryTextForForm(form.prescription)
  }
}

function buildPrescriptionSummaryTextForForm(prescription) {
  return (prescription?.rows || [])
    .map((row) => {
      const name = String(row?.name || '').trim()
      if (!name) return ''
      return name
    })
    .filter(Boolean)
    .join('、')
}

function openFollowup() {
  ensureFollowup()
  activeVisitMode.value = 'followup'
  nextTick(() => {
    formScrollRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
  })
}

function addFollowup() {
  if (!Array.isArray(form.followups)) form.followups = []
  const index = form.followups.length
  form.followups.push({
    ...defaultFollowup(index),
    previous_formula: previousFormulaForFollowup(index)
  })
  switchFollowup(index)
}

function isFollowupEmpty(visit) {
  return !buildFollowupSummaryLines(visit, sections.value).some((item) => String(item?.text || '').trim())
}

function deleteEmptyFollowup(index) {
  if (!Array.isArray(form.followups) || !form.followups[index]) return
  if (!isFollowupEmpty(form.followups[index])) {
    ElMessage.warning('该复诊已有内容，不能删除')
    return
  }
  form.followups.splice(index, 1)
  form.followups.forEach((visit, visitIndex) => {
    visit.label = visitLabel(visitIndex)
  })
  if (!form.followups.length) {
    activeVisitMode.value = 'first'
    activeFollowupIndex.value = 0
  } else if (activeVisitMode.value === 'followup') {
    activeFollowupIndex.value = Math.min(index, form.followups.length - 1)
  }
  saveDraft()
}

function previousFormulaForFollowup(index) {
  if (index > 0) {
    const previous = form.followups[index - 1]
    const adjusted = buildPrescriptionSummaryTextForForm(previous?.prescription)
    if (adjusted) return adjusted
    if (previous?.previous_formula) return previous.previous_formula
  }
  return buildPrescriptionSummaryTextForForm(form.prescription)
}

function previousPrescriptionRowsForFollowup(index) {
  const source = index > 0 ? form.followups[index - 1]?.prescription : form.prescription
  return (source?.rows || [])
    .filter((row) => String(row?.name || '').trim())
    .map((row) => ({
      id: `import-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      name: String(row.name || '').trim(),
      basis: String(row.basis || '').trim(),
      portions: Number(row.portions) || 1
    }))
}

function isBlankPrescriptionRow(row) {
  return !String(row?.name || '').trim() && !String(row?.basis || '').trim()
}

function importPreviousPrescription() {
  const visit = currentFollowup.value
  if (!visit?.prescription) return
  const importedRows = previousPrescriptionRowsForFollowup(activeFollowupIndex.value)
  if (!importedRows.length) {
    ElMessage.warning('上诊暂无可引入的方剂')
    return
  }

  const currentRows = (visit.prescription.rows || []).filter((row) => !isBlankPrescriptionRow(row))
  const rowByName = new Map(currentRows.map((row) => [String(row.name || '').trim(), row]))
  let added = 0
  importedRows.forEach((row) => {
    const existing = rowByName.get(row.name)
    if (existing) {
      if (!String(existing.basis || '').trim() && row.basis) existing.basis = row.basis
      if (!Number(existing.portions)) existing.portions = row.portions
      return
    }
    currentRows.push(row)
    rowByName.set(row.name, row)
    added += 1
  })
  visit.prescription.rows = currentRows
  saveDraft()
  autoSaveIntake()
  ElMessage.success(added ? `已引入上诊方剂 ${added} 个` : '上诊方剂已在当前处方中')
}

function switchVisitMode(mode) {
  activeVisitMode.value = mode
  nextTick(() => {
    formScrollRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
  })
}

function switchFollowup(index) {
  if (!Array.isArray(form.followups) || !form.followups[index]) return
  activeFollowupIndex.value = index
  activeVisitMode.value = 'followup'
  normalizeFollowup(form.followups[index], index)
  nextTick(() => {
    formScrollRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
  })
}

function followupChipsForBlock(block) {
  const visit = currentFollowup.value
  return visit.chipLists?.[block.label]?.length ? visit.chipLists[block.label] : [...(block.symptoms || [])]
}

function setFollowupChipList(label, list) {
  currentFollowup.value.chipLists[label] = list
}

function onToggleFollowupSelected({ symptom, active }) {
  const visit = currentFollowup.value
  visit.selected[symptom] = active
  if (!active) delete visit.selected[symptom]
}

function onBlockSymptomsPersisted(label, list) {
  const symptoms = Array.isArray(list) ? list.filter(Boolean) : []
  for (const section of sections.value || []) {
    for (const block of section.blocks || []) {
      if (block.label === label) block.symptoms = [...symptoms]
    }
  }
  delete form.chipLists[label]
}

function findBlockByLabel(label) {
  for (const section of sections.value || []) {
    for (const block of section.blocks || []) {
      if (block.label === label) return block
    }
  }
  return null
}

function appendPathologyNote(label, text) {
  const value = String(text || '').trim()
  if (!label || !value) return
  const current = String(form.notes[label] || '').trim()
  if (!current) {
    form.notes[label] = value
    return
  }
  if (current.includes(value)) return
  form.notes[label] = `${current}，${value}`
}

async function addSymptomToBlockCatalog(label, symptom) {
  const value = String(symptom || '').trim()
  if (!label || !value) return false
  const block = findBlockByLabel(label)
  if (!block) return false
  const current = chipsForBlock(block)
  if (current.includes(value)) return true
  const next = [...current, value]
  const data = await consultApi.updateBlockSymptoms(label, { symptoms: next })
  onBlockSymptomsPersisted(label, data?.symptoms || next)
  return true
}

function normalizeCandidateList(result) {
  const items = []
  const seen = new Set()
  const sources = [
    { list: result?.uncertain_symptoms, defaultAction: 'fill' },
    { list: result?.new_symptom_terms, defaultAction: 'add' }
  ]
  sources.forEach(({ list, defaultAction }) => {
    ;(Array.isArray(list) ? list : []).forEach((item) => {
      const raw = String(item?.raw_text || item?.text || item?.symptom || '').trim()
      if (!raw || seen.has(raw)) return
      const suggestedBlocks = Array.isArray(item?.suggested_blocks)
        ? item.suggested_blocks
        : item?.suggested_block
          ? [item.suggested_block]
          : []
      const suggestedSymptoms = Array.isArray(item?.suggested_symptoms) ? item.suggested_symptoms : []
      const block = suggestedBlocks.find((label) => findBlockByLabel(label)) || ''
      items.push({
        id: `${items.length}-${raw}`,
        raw_text: raw,
        symptom_name: String(item?.symptom_name || raw).trim(),
        suggested_symptoms: suggestedSymptoms.filter(Boolean),
        selected_symptom: suggestedSymptoms[0] || '',
        suggested_blocks: suggestedBlocks.filter(Boolean),
        block_label: block,
        reason: String(item?.reason || '').trim(),
        action: item?.action === 'ignore' ? 'ignore' : item?.action === 'add' ? 'add' : defaultAction
      })
      seen.add(raw)
    })
  })
  return items
}

function onToggleSelected({ symptom, active }) {
  form.selected[symptom] = active
  if (!active) delete form.selected[symptom]
  syncCollapseState()
}

function normalizePathologyScore(value) {
  const num = Number(value)
  if (Number.isNaN(num) || num <= 0) return 0
  if (num <= 5) return Math.round(num)
  return Math.min(5, Math.max(1, Math.round(num / 20)))
}

function setPathologyScore(label, value) {
  const score = normalizePathologyScore(value)
  if (score > 0) form.scores[label] = score
  else delete form.scores[label]
  syncCollapseState()
}

function hasPathologyScore(label) {
  return normalizePathologyScore(form.scores[label]) > 0
}

function formatPathologyScoreStars(label) {
  const count = normalizePathologyScore(form.scores[label])
  if (!count) return ''
  return `${'★'.repeat(count)}${'☆'.repeat(5 - count)}`
}

function scoredBlocks(section) {
  return (section.blocks || []).filter((block) => hasPathologyScore(block.label))
}

function blockHasContent(block) {
  const note = String(form.notes[block.label] || '').trim()
  if (note) return true
  if (hasPathologyScore(block.label)) return true
  return (block.symptoms || []).some((symptom) => form.selected[symptom])
}

function isBlockCollapsed(label) {
  return Boolean(blockCollapsed[label])
}

function blockPreview(block) {
  const note = String(form.notes[block.label] || '').trim()
  if (note) return note.length > 48 ? `${note.slice(0, 48)}…` : note
  const selected = (block.symptoms || []).filter((symptom) => form.selected[symptom])
  if (selected.length) return selected.join('、')
  if (hasPathologyScore(block.label)) return formatPathologyScoreStars(block.label)
  return ''
}

function sectionHasContent(section) {
  return (section.blocks || []).some((block) => blockHasContent(block))
}

function shouldAutoCollapseEmptyBlocks() {
  return route.query.from === 'records'
}

function syncBlockCollapseState() {
  sections.value.forEach((section) => {
    ;(section.blocks || []).forEach((block) => {
      const label = block.label
      if (blockCollapseManual[label]) return
      blockCollapsed[label] = shouldAutoCollapseEmptyBlocks() ? !blockHasContent(block) : false
    })
  })
}

function syncSectionCollapseState() {
  sections.value.forEach((section) => {
    const key = section.key
    if (sectionCollapseManual[key]) return
    collapsed[key] = shouldAutoCollapseEmptyBlocks() ? !sectionHasContent(section) : false
  })
}

function syncCollapseState() {
  syncBlockCollapseState()
  syncSectionCollapseState()
}

function initBlockCollapseState() {
  sections.value.forEach((section) => {
    ;(section.blocks || []).forEach((block) => {
      const label = block.label
      if (blockCollapsed[label] === undefined) {
        blockCollapsed[label] = shouldAutoCollapseEmptyBlocks() ? !blockHasContent(block) : false
      }
    })
  })
}

function toggleBlock(label) {
  blockCollapseManual[label] = true
  blockCollapsed[label] = !blockCollapsed[label]
}

function updateSectionHints(key, hints) {
  const section = sections.value.find((item) => item.key === key)
  if (section) section.inquiry_hints = [...hints]
}

function showModule(key) {
  activeModule.value = key
  visibleSectionKeys.value.forEach((k) => {
    collapsed[k] = false
    sectionCollapseManual[k] = true
  })
  formScrollRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
}

function focusConsultModule(moduleKey = 'base') {
  const key = moduleKey || 'base'
  showModule(key)
  if (key === 'base') {
    collapsed.base = false
    sectionCollapseManual.base = true
  }
  nextTick(() => {
    formScrollRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
  })
}

function toggleSection(key) {
  sectionCollapseManual[key] = true
  collapsed[key] = !collapsed[key]
}

function toggleAllSections() {
  const next = !allVisibleCollapsed.value
  visibleSectionKeys.value.forEach((k) => {
    collapsed[k] = next
    sectionCollapseManual[k] = true
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
    const data = JSON.parse(raw)
    Object.assign(form, emptyForm(), data)
    normalizeIntakeFollowups(form)
    return true
  } catch {
    return false
  }
}

let draftTimer = null
watch(
  form,
  () => {
    syncCollapseState()
    clearTimeout(draftTimer)
    draftTimer = setTimeout(saveDraft, 800)
  },
  { deep: true }
)

function valueOrEmpty(value) {
  const text = String(value ?? '').trim()
  return text || '未填写'
}

function sanitizeFilePart(value) {
  return String(value || '')
    .trim()
    .replace(/[\\/:*?"<>|]/g, '')
    .replace(/\s+/g, '')
}

function buildFormulaExportRows() {
  const rows = (form.prescription?.rows || []).filter((row) => row.name?.trim())
  if (!rows.length) return ['- 未录入']

  const calc = runDoseCalc(
    rows.map((row) => {
      const hit = lookupFormulaPowder(formulaIndex.value, row.name)
      return {
        id: row.id,
        name: row.name,
        unitTotal: hit?.total || 0,
        portions: Number(row.portions) || 0
      }
    }),
    form.prescription?.targetDose || 200
  )
  const finalMap = new Map(calc.rows.map((row) => [row.id, row]))

  return rows.map((row) => {
    const finalDose = finalMap.get(row.id)?.finalDose ?? '—'
    const chunks = [`${row.name} × ${Number(row.portions) || 1}份`]
    if (finalDose !== '—') chunks.push(`最终用量 ${finalDose}g`)
    if (String(row.basis || '').trim()) chunks.push(`用方依据：${String(row.basis).trim()}`)
    return `- ${chunks.join('；')}；`
  })
}

function buildPrescriptionExportRows(prescription) {
  const rows = (prescription?.rows || []).filter((row) => row.name?.trim())
  if (!rows.length) return ['- 未录入']

  const calc = runDoseCalc(
    rows.map((row) => {
      const hit = lookupFormulaPowder(formulaIndex.value, row.name)
      return {
        id: row.id,
        name: row.name,
        unitTotal: hit?.total || 0,
        portions: Number(row.portions) || 0
      }
    }),
    prescription?.targetDose || 200
  )
  const finalMap = new Map(calc.rows.map((row) => [row.id, row]))

  return rows.map((row) => {
    const finalDose = finalMap.get(row.id)?.finalDose ?? '—'
    const chunks = [`${row.name} × ${Number(row.portions) || 1}份`]
    if (finalDose !== '—') chunks.push(`最终用量 ${finalDose}g`)
    if (String(row.basis || '').trim()) chunks.push(`用方依据：${String(row.basis).trim()}`)
    return `- ${chunks.join('；')}；`
  })
}

function buildPathologyExportLines() {
  const lines = []
  for (const section of sections.value || []) {
    for (const block of section.blocks || []) {
      const label = block.label
      const note = String(form.notes?.[label] || '').trim()
      const symptoms = chipsForBlock(block).filter((s) => form.selected?.[s] && !note.includes(s))
      const parts = []
      if (note) parts.push(note)
      if (symptoms.length) parts.push(`症状：${symptoms.join('、')}`)
      if (hasPathologyScore(label)) parts.push(`打分：${Number(form.scores[label])}`)
      if (parts.length) lines.push(`- ${label}：${parts.join('；')}`)
    }
  }
  return lines.length ? lines : ['- 未记录']
}

function buildCaseMarkdown() {
  const visitDate = formatVisitDate(form.visit_time) || valueOrEmpty(form.visit_time)
  const selectedLine = selectedSymptoms.value.length ? selectedSymptoms.value.join('、') : '未选择'
  const patientParts = [
    form.patient_name,
    form.gender,
    form.age ? `${form.age}岁` : '',
    form.phone ? `电话：${form.phone}` : '',
    form.address ? `住址：${form.address}` : ''
  ].filter(Boolean)
  const tonguePulseParts = [
    form.tongue_image ? `舌像：${form.tongue_image}` : '',
    form.pulse ? `脉像：${form.pulse}` : '',
    form.abdominal ? `腹诊：${form.abdominal}` : ''
  ].filter(Boolean)

  const firstVisitLines = [
    '## 首诊',
    `患者：${patientParts.join('，') || '未填写'}`,
    `就诊：${visitDate}；主诊医生：${valueOrEmpty(form.doctor)}`,
    `现代诊断/检查：${valueOrEmpty(form.modern_diagnosis)}`,
    '',
    `主诉：${valueOrEmpty(form.chief_complaint)}`,
    `病程：${valueOrEmpty(form.history)}`,
    '',
    ...buildPathologyExportLines(),
    '',
    `舌脉腹诊：${tonguePulseParts.join('；') || '未填写'}`,
    '',
    `处方：目标用量 ${form.prescription?.targetDose || 200}g`,
    ...buildFormulaExportRows(),
    form.prescription?.note ? `处方备注：${form.prescription.note}` : ''
  ]

  const followupLines = (form.followups || [])
    .map((visit, index) => {
      const lines = buildFollowupSummaryLines(visit, sections.value)
      if (!lines.some((item) => item.text)) return []
      const changeGroups = buildFollowupChangeGroups(visit)
      return [
        '',
        `## ${visit.label || (index === 0 ? '二诊' : `第${index + 2}诊`)}`,
        `好转的症状：${changeGroups.find((item) => item.key === 'improved')?.text || '未填写'}`,
        `加重的症状：${changeGroups.find((item) => item.key === 'worsened')?.text || '未填写'}`,
        `仍存在的症状：${changeGroups.find((item) => item.key === 'remaining')?.text || '未填写'}`,
        `本次调整方剂：目标用量 ${visit.prescription?.targetDose || 200}g`,
        ...buildPrescriptionExportRows(visit.prescription),
        visit.prescription?.note ? `处方备注：${visit.prescription.note}` : ''
      ]
    })
    .flat()

  return [...firstVisitLines, ...followupLines]
    .filter((line, index, arr) => {
      if (line !== '') return true
      return arr[index - 1] !== ''
    })
    .join('\n')
}

function buildCaseText() {
  return buildCaseMarkdown()
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

async function copyCaseSummary() {
  if (!hasConsultSummary.value) {
    ElMessage.warning('暂无可复制的病例摘要')
    return
  }
  await copyTextToClipboard(caseSummaryText.value)
  ElMessage.success('病例摘要已复制')
}

async function copyCaseText() {
  if (!hasCaseContent.value) {
    ElMessage.warning('请先填写医案内容')
    return
  }
  await copyTextToClipboard(buildCaseText())
  ElMessage.success('医案已复制')
}

function exportCaseText() {
  if (!hasCaseContent.value) {
    ElMessage.warning('请先填写医案内容')
    return
  }
  const text = buildCaseText()
  const name = sanitizeFilePart(form.patient_name) || '未命名'
  const date = sanitizeFilePart(form.visit_time) || new Date().toISOString().slice(0, 10)
  const filename = `经方问诊医案_${name}_${date}.md`
  const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  ElMessage.success('医案已导出')
}

function applyFillResult(result, source = 'local') {
  const fields = result?.fields || {}
  const symptoms = Array.isArray(result?.symptoms) ? result.symptoms : []
  const pathologyNotes = result?.pathology_notes || {}
  const candidates = normalizeCandidateList(result)
  const filled = []
  Object.entries(fields).forEach(([key, val]) => {
    if (val) {
      form[key] = val
      filled.push(FIELD_LABELS[key] || key)
    }
  })
  normalizeIntakeTongue(form)
  symptoms.forEach((s) => {
    form.selected[s] = true
  })
  const noteLabels = []
  Object.entries(pathologyNotes).forEach(([label, val]) => {
    if (val) {
      form.notes[label] = val
      noteLabels.push(label)
    }
  })
  if (!filled.length && !symptoms.length && !noteLabels.length && !candidates.length) {
    return false
  }
  fillDialogVisible.value = false
  fillText.value = ''
  if (candidates.length) {
    pendingSymptomCandidates.value = candidates
    candidateDialogVisible.value = true
  }
  const parts = []
  if (filled.length) parts.push(`已填充：${filled.join('、')}`)
  if (symptoms.length) parts.push(`自动勾选 ${symptoms.length} 个症状`)
  if (noteLabels.length) parts.push(`整理 ${noteLabels.length} 个病理项`)
  if (candidates.length) parts.push(`${candidates.length} 个症状待确认`)
  const prefix = source === 'ai' ? 'AI 解析完成' : '已使用本地规则解析'
  ElMessage.success(`${prefix}：${parts.join('；')}`)
  return true
}

async function applySymptomCandidates() {
  const active = pendingSymptomCandidates.value.filter((item) => item.action !== 'ignore')
  const missingBlock = active.find((item) => !item.block_label)
  if (missingBlock) {
    ElMessage.warning(`请先给「${missingBlock.raw_text}」选择病理`)
    return
  }
  candidateApplying.value = true
  try {
    let filled = 0
    let added = 0
    for (const item of active) {
      const rawText = String(item.raw_text || '').trim()
      const symptomName = String(item.selected_symptom || item.symptom_name || rawText).trim()
      const noteText = rawText || symptomName
      if (item.selected_symptom) {
        form.selected[item.selected_symptom] = true
      }
      if (item.action === 'add') {
        await addSymptomToBlockCatalog(item.block_label, symptomName)
        form.selected[symptomName] = true
        added += 1
      }
      appendPathologyNote(item.block_label, noteText)
      filled += 1
    }
    pendingSymptomCandidates.value = []
    candidateDialogVisible.value = false
    syncCollapseState()
    const parts = []
    if (filled) parts.push(`填入 ${filled} 个症状`)
    if (added) parts.push(`加入目录 ${added} 个`)
    ElMessage.success(parts.join('，') || '候选症状已处理')
  } finally {
    candidateApplying.value = false
  }
}

async function parseWithAiOrLocal(text) {
  try {
    const result = await consultApi.autoFill({ raw_text: text })
    if (result?.source === 'ai') return result
  } catch (err) {
    console.warn('AI auto fill failed, fallback to local parser:', err)
  }
  return { ...parseCaseText(text, sections.value), source: 'local' }
}

async function applyAutoFill() {
  const text = fillText.value.trim()
  if (!text) {
    ElMessage.warning('请先粘贴医案文本')
    return
  }
  autoFilling.value = true
  try {
    const result = await parseWithAiOrLocal(text)
    if (!applyFillResult(result, result.source)) {
      ElMessage.warning('未能从文本中识别出可填充的信息，请检查格式')
    }
  } finally {
    autoFilling.value = false
  }
}

function resetBlockCollapseState() {
  Object.keys(blockCollapsed).forEach((key) => delete blockCollapsed[key])
  Object.keys(blockCollapseManual).forEach((key) => delete blockCollapseManual[key])
  Object.keys(sectionCollapseManual).forEach((key) => delete sectionCollapseManual[key])
  initBlockCollapseState()
  sections.value.forEach((section) => {
    collapsed[section.key] = shouldAutoCollapseEmptyBlocks() ? !sectionHasContent(section) : false
  })
}

function resetForm() {
  Object.assign(form, emptyForm())
  sessionId.value = null
  autoSaveSnapshot.value = ''
  autoSavePending.value = false
  activeVisitMode.value = 'first'
  activeFollowupIndex.value = 0
  localStorage.removeItem('consult-draft-new')
  draftSavedAt.value = ''
  resetBlockCollapseState()
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

function intakeSnapshot() {
  return JSON.stringify(buildPayload('collecting'))
}

function rememberAutoSaveSnapshot() {
  autoSaveSnapshot.value = intakeSnapshot()
}

function isAutoSaveField(target) {
  if (!(target instanceof HTMLElement)) return false
  return Boolean(target.closest('input, textarea, select, [contenteditable="true"]'))
}

function handleCollectFocusout(event) {
  if (!isAutoSaveField(event.target)) return
  autoSaveIntake()
}

async function autoSaveIntake() {
  if (autoSaving.value || saving.value) {
    autoSavePending.value = true
    return
  }
  if (!sessionId.value && !hasCaseContent.value) return
  const snapshot = intakeSnapshot()
  if (snapshot === autoSaveSnapshot.value) return

  autoSaving.value = true
  const shouldCreate = !sessionId.value
  try {
    if (!sessionId.value) {
      const created = await consultApi.createSession({ title: form.chief_complaint || form.patient_name || '新的问诊' })
      sessionId.value = created.id
    }
    const saved = await consultApi.saveIntake(sessionId.value, buildPayload('collecting'))
    sessionId.value = saved.id
    if (shouldCreate) {
      localStorage.removeItem('consult-draft-new')
      router.replace(`/consult/${saved.id}`)
      await loadSessionNavList()
    }
    saveDraft()
    rememberAutoSaveSnapshot()
  } finally {
    autoSaving.value = false
    if (autoSavePending.value) {
      autoSavePending.value = false
      autoSaveIntake()
    }
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
    await loadSessionNavList()
    rememberAutoSaveSnapshot()
    ElMessage.success('问诊已保存')
  } finally {
    saving.value = false
  }
}

async function loadSession(id) {
  try {
    const detail = await consultApi.getSession(id)
    const data = detail.intake_data || {}
    Object.assign(form, emptyForm(), data)
    normalizeIntakeFollowups(form)
    if (form.scores && typeof form.scores === 'object') {
      for (const [key, value] of Object.entries(form.scores)) {
        const score = normalizePathologyScore(value)
        if (score > 0) form.scores[key] = score
        else delete form.scores[key]
      }
    }
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
    resetBlockCollapseState()
    rememberAutoSaveSnapshot()
  } catch {
    ElMessage.error('加载问诊记录失败')
  }
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
        if (collapsed[s.key] === undefined) {
          collapsed[s.key] = shouldAutoCollapseEmptyBlocks() ? !sectionHasContent(s) : false
        }
      })
    }
  } catch {
    sections.value = fallbackSections
  }
  initBlockCollapseState()
  syncCollapseState()
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
  () => [route.params.id, route.query.from],
  async ([routeId]) => {
    const id = routeId ? Number(routeId) : null
    sessionId.value = id
    if (sessionId.value) {
      await loadSession(sessionId.value)
    } else if (!loadDraft()) {
      Object.assign(form, emptyForm())
      resetBlockCollapseState()
      rememberAutoSaveSnapshot()
    } else {
      resetBlockCollapseState()
      rememberAutoSaveSnapshot()
    }
  }
)

watch(
  () => route.query.module,
  (moduleKey) => {
    if (!moduleKey || !sessionId.value) return
    focusConsultModule(String(moduleKey))
  }
)

onMounted(async () => {
  await Promise.all([loadSymptomPresets(), loadFormulas(), loadSessionNavList()])
  if (sessionId.value) await loadSession(sessionId.value)
  else if (loadDraft()) {
    resetBlockCollapseState()
    rememberAutoSaveSnapshot()
  } else {
    initBlockCollapseState()
    rememberAutoSaveSnapshot()
  }
  if (route.query.module && sessionId.value) {
    focusConsultModule(String(route.query.module))
  }
})
</script>

<style scoped src="../styles/consult-legacy.css"></style>
