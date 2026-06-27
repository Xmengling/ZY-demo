<template>
  <div ref="prescriptionRoot" class="prescription-block">
    <div class="prescription-block-title">
      <div class="prescription-title-main">
        <span>合方录入</span>
        <label class="prescription-target-wrap">
          目标用量
          <el-input-number
            v-model="localTarget"
            :min="1"
            :step="1"
            :controls="false"
            class="target-input"
            @change="emitUpdate"
          />
          <span>g</span>
        </label>
      </div>
      <div class="prescription-title-actions">
        <el-button
          v-if="showImportPrevious"
          size="small"
          class="import-previous-btn"
          @click="$emit('import-previous')"
        >
          引入上诊方剂
        </el-button>
        <el-button size="small" class="add-btn" @click="addRow">+ 添加方剂</el-button>
      </div>
    </div>

    <div class="formula-table-wrap">
      <table class="formula-table">
        <colgroup>
          <col class="col-action" />
          <col class="col-name" />
          <col class="col-pathology" />
          <col class="col-main-symptoms" />
          <col class="col-basis" />
          <col class="col-unit" />
          <col class="col-portions" />
          <col class="col-final" />
          <col class="col-drag" />
        </colgroup>
        <thead>
          <tr>
            <th class="col-action" aria-label="删除" />
            <th class="col-name">方剂名</th>
            <th class="col-pathology">病理</th>
            <th class="col-main-symptoms">主要症状</th>
            <th class="col-basis">用方依据</th>
            <th class="num">单方量</th>
            <th class="num">份数</th>
            <th class="num">最终用量</th>
            <th class="col-drag" aria-label="排序" />
          </tr>
        </thead>
        <tbody>
          <tr v-if="!modelValue.rows.length" class="formula-empty-row">
            <td colspan="8">暂未添加方剂，点击「+ 添加方剂」开始录入</td>
          </tr>
          <tr
            v-for="(row, index) in modelValue.rows"
            :key="row.id"
            class="formula-table-row"
            :class="{
              'is-missing-total': rowMeta(row).missing,
              'is-dragging': dragRowIndex === index,
              'is-drop-target': dropRowIndex === index && dragRowIndex !== index
            }"
            @dragover.prevent="onRowDragOver(index)"
            @drop.prevent="onRowDrop(index)"
          >
            <td class="col-action">
              <button type="button" class="formula-remove-btn" aria-label="删除方剂" @click="removeRow(index)">
                <svg class="formula-remove-icon" viewBox="0 0 12 12" aria-hidden="true">
                  <path d="M2.5 2.5l7 7M9.5 2.5l-7 7" />
                </svg>
              </button>
            </td>
            <td class="col-name">
              <el-autocomplete
                v-model="row.name"
                :fetch-suggestions="queryFormula"
                placeholder="方剂名"
                :trigger-on-focus="true"
                clearable
                class="name-input"
                @select="() => emitUpdate()"
                @blur="emitUpdate"
              />
            </td>
            <td class="col-pathology">
              <span class="formula-pathology-cell">
                <span v-if="!rowMeta(row).pathology.length" class="muted">—</span>
                <PathologyTag v-for="tag in rowMeta(row).pathology" :key="tag" :label="tag" />
              </span>
            </td>
            <td class="col-main-symptoms">
              <span
                class="formula-main-symptoms-cell"
                :title="rowMeta(row).mainSymptomsText || undefined"
              >
                {{ rowMeta(row).mainSymptomsText || '—' }}
              </span>
            </td>
            <td class="col-basis">
              <el-input
                v-model="row.basis"
                class="basis-input"
                type="textarea"
                :rows="1"
                placeholder="输入用方依据"
                @input="handleBasisInput"
                @change="handleBasisInput"
                @blur="handleBasisInput"
              />
            </td>
            <td class="num">
              <span class="formula-unit-total" :class="{ 'is-auto': rowMeta(row).unitTotal > 0 }">
                {{ rowMeta(row).unitTotal > 0 ? rowMeta(row).unitTotal : '—' }}
              </span>
            </td>
            <td class="num">
              <el-input-number
                v-model="row.portions"
                :min="1"
                :max="99"
                :controls="false"
                class="portions-input"
                @change="emitUpdate"
              />
            </td>
            <td class="num">
              <strong class="formula-final-dose">{{ rowMeta(row).finalDose }}</strong>
            </td>
            <td class="col-drag">
              <button
                type="button"
                class="formula-drag-handle"
                draggable="true"
                aria-label="拖拽调整方剂顺序"
                title="拖拽调整顺序"
                @dragstart="onRowDragStart(index, $event)"
                @dragend="onRowDragEnd"
              >
                <span class="formula-drag-grip" aria-hidden="true">
                  <i /><i /><i /><i /><i /><i />
                </span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="herbDoseItems.length" class="herb-dose-panel">
      <div class="herb-dose-title">中药用量（g）</div>
      <div class="herb-dose-list">
        <label v-for="item in herbDoseItems" :key="item.herb" class="herb-dose-chip">
          <span class="herb-name">{{ item.herb }}</span>
          <el-input-number
            :model-value="item.doseValue"
            :min="0"
            :step="0.1"
            :precision="1"
            :controls="false"
            class="herb-dose-input"
            @change="(value) => updateHerbDose(item.herb, value)"
          />
        </label>
      </div>
    </div>

    <div class="prescription-note-field">
      <label>处方备注</label>
      <el-input
        v-model="localNote"
        type="textarea"
        :rows="2"
        placeholder="煎服法、忌口、复诊提醒等"
        @input="emitUpdate"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import PathologyTag from './PathologyTag.vue'
import {
  formatDoseNumber,
  formatMainSymptomsText,
  lookupFormulaPowder,
  runDoseCalc
} from '../../utils/formulaPowder'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({
      targetDose: 200,
      note: '',
      herbDoses: {},
      rows: []
    })
  },
  formulaIndex: { type: Map, default: () => new Map() },
  formulaNames: { type: Array, default: () => [] },
  showImportPrevious: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'import-previous'])

const localTarget = ref(props.modelValue.targetDose ?? 200)
const localNote = ref(props.modelValue.note ?? '')
const prescriptionRoot = ref(null)
const dragRowIndex = ref(null)
const dropRowIndex = ref(null)

let rowSeq = 1
function newRowId() {
  rowSeq += 1
  return `r${Date.now()}-${rowSeq}`
}

const calc = computed(() => {
  const rows = (props.modelValue.rows || []).map((row) => {
    const hit = lookupFormulaPowder(props.formulaIndex, row.name)
    return {
      id: row.id,
      name: row.name,
      unitTotal: hit?.total || 0,
      portions: Number(row.portions) || 0
    }
  })
  return runDoseCalc(rows, localTarget.value)
})

const finalMap = computed(() => {
  const map = new Map()
  calc.value.rows.forEach((r) => map.set(r.id, r))
  return map
})

const herbDoseItems = computed(() => {
  const coefficient = calc.value.coefficient
  if (!Number.isFinite(coefficient)) return []

  const doseMap = new Map()
  for (const row of props.modelValue.rows || []) {
    const hit = lookupFormulaPowder(props.formulaIndex, row.name)
    const portions = Number(row.portions) || 0
    if (!hit?.items?.length || portions <= 0) continue

    for (const item of hit.items) {
      const dose = item.amount * portions * coefficient
      doseMap.set(item.herb, (doseMap.get(item.herb) || 0) + dose)
    }
  }

  const manualDoses = props.modelValue.herbDoses || {}
  return Array.from(doseMap.entries()).map(([herb, dose]) => ({
    herb,
    dose: formatDoseNumber(dose),
    doseValue: Number.isFinite(Number(manualDoses[herb]))
      ? Number(manualDoses[herb])
      : Number(formatDoseNumber(dose))
  }))
})

function rowMeta(row) {
  const hit = lookupFormulaPowder(props.formulaIndex, row.name)
  const unitTotal = hit?.total || 0
  const calcRow = finalMap.value.get(row.id)
  const mainSymptomsText = hit
    ? formatMainSymptomsText(hit.mainSymptoms, hit.clinicalSymptoms)
    : ''
  return {
    unitTotal,
    pathology: hit?.pathology || [],
    mainSymptomsText,
    finalDose: calcRow?.finalDose ?? '—',
    missing: calcRow?.missing ?? true
  }
}

function queryFormula(query, cb) {
  const q = (query || '').trim()
  cb(
    props.formulaNames
      .filter((name) => !q || name.includes(q))
      .slice(0, 12)
      .map((name) => ({ value: name }))
  )
}

function addRow() {
  const rows = [...(props.modelValue.rows || []), { id: newRowId(), name: '', basis: '', portions: 1 }]
  emit('update:modelValue', buildPayload(rows))
}

function removeRow(index) {
  emit('update:modelValue', buildPayload(props.modelValue.rows.filter((_, i) => i !== index)))
}

function reorderRows(fromIndex, toIndex) {
  const rows = [...(props.modelValue.rows || [])]
  if (fromIndex === toIndex || fromIndex < 0 || toIndex < 0 || fromIndex >= rows.length || toIndex >= rows.length) return
  const [moved] = rows.splice(fromIndex, 1)
  rows.splice(toIndex, 0, moved)
  emit('update:modelValue', buildPayload(rows))
  nextTick(resizeBasisTextareas)
}

function onRowDragStart(index, event) {
  dragRowIndex.value = index
  dropRowIndex.value = index
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', String(index))
}

function onRowDragOver(index) {
  if (dragRowIndex.value === null) return
  dropRowIndex.value = index
}

function onRowDrop(index) {
  if (dragRowIndex.value !== null) reorderRows(dragRowIndex.value, index)
  onRowDragEnd()
}

function onRowDragEnd() {
  dragRowIndex.value = null
  dropRowIndex.value = null
}

function buildPayload(rows) {
  const herbDoses = Object.fromEntries(
    Object.entries(props.modelValue.herbDoses || {}).filter(
      ([, value]) => Number.isFinite(Number(value)) && Number(value) >= 0
    )
  )
  return {
    targetDose: localTarget.value,
    note: localNote.value,
    herbDoses,
    rows: rows.map((r) => ({
      id: r.id,
      name: r.name,
      basis: String(r.basis || '').trim(),
      portions: Number(r.portions) || 1
    }))
  }
}

function emitUpdate() {
  emit('update:modelValue', buildPayload(props.modelValue.rows || []))
}

function updateHerbDose(herb, value) {
  const herbDoses = { ...(props.modelValue.herbDoses || {}) }
  const dose = Number(value)
  if (!herb || !Number.isFinite(dose)) {
    delete herbDoses[herb]
  } else {
    herbDoses[herb] = dose
  }
  emit('update:modelValue', {
    ...buildPayload(props.modelValue.rows || []),
    herbDoses
  })
}

function resizeBasisTextareas() {
  const root = prescriptionRoot.value
  if (!root) return
  root.querySelectorAll('.basis-input textarea').forEach((textarea) => {
    textarea.style.height = 'auto'
    textarea.style.height = `${textarea.scrollHeight}px`
  })
}

function handleBasisInput() {
  emitUpdate()
  nextTick(resizeBasisTextareas)
}

watch(
  () => props.modelValue,
  (val) => {
    localTarget.value = val?.targetDose ?? 200
    localNote.value = val?.note ?? ''
    nextTick(resizeBasisTextareas)
  },
  { deep: true }
)

onMounted(() => {
  nextTick(resizeBasisTextareas)
})
</script>

<style scoped>
.prescription-block {
  min-width: 0;
  max-width: 100%;
  background: #fff;
  border: 1px solid #e6ebf2;
  border-radius: 8px;
  padding: 12px;
  box-sizing: border-box;
}
.prescription-block-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eef2f6;
  font-size: 14px;
  font-weight: 800;
  color: #1f2933;
}
.prescription-title-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.prescription-target-wrap {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px 4px 12px;
  border: 1px solid #e4e9ef;
  border-radius: 999px;
  background: #f8fafc;
  font-size: 12px;
  font-weight: 600;
  color: #667085;
}
.target-input {
  width: 72px;
}
.target-input :deep(.el-input__wrapper) {
  padding: 0 8px;
}
.add-btn {
  flex-shrink: 0;
  border-color: #d7e8de;
  color: #0f7c43;
}
.prescription-title-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.import-previous-btn {
  flex-shrink: 0;
  border-color: #b9d8c7;
  background: #f4fbf7;
  color: #0f7c43;
  font-weight: 700;
}
.formula-table-wrap {
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  border: 1px solid #e8edf3;
  border-radius: 7px;
  box-sizing: border-box;
}
.formula-table {
  width: 100%;
  min-width: 900px;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 12px;
}
.formula-table .col-name {
  width: 15%;
}
.formula-table .col-pathology {
  width: 14%;
}
.formula-table .col-main-symptoms {
  width: 24%;
}
.formula-table .col-basis {
  width: 18%;
}
.formula-table .col-unit {
  width: 78px;
}
.formula-table .col-portions {
  width: 86px;
}
.formula-table .col-final {
  width: 86px;
}
.formula-table th,
.formula-table td {
  border-bottom: 1px solid #eef2f6;
  padding: 8px 10px;
  vertical-align: middle;
  background: #fff;
}
.formula-table th.col-action,
.formula-table td.col-action,
.formula-table th.col-drag,
.formula-table td.col-drag {
  padding-left: 6px;
  padding-right: 6px;
}
.formula-table th {
  background: #f8fafc;
  color: #667085;
  font-size: 11px;
  font-weight: 600;
}
.formula-table th.col-name,
.formula-table td.col-name {
  text-align: left;
}
.formula-table th.col-pathology,
.formula-table td.col-pathology,
.formula-table th.col-main-symptoms,
.formula-table td.col-main-symptoms,
.formula-table th.col-basis,
.formula-table td.col-basis {
  text-align: left;
  vertical-align: top;
}
.formula-table td.num,
.formula-table th.num,
.formula-table td.col-action,
.formula-table th.col-action,
.formula-table td.col-drag,
.formula-table th.col-drag {
  text-align: center;
  vertical-align: middle;
  font-variant-numeric: tabular-nums;
}
.formula-table .col-action,
.formula-table .col-drag {
  width: 36px;
}
.formula-table tbody tr:hover td {
  background: #fbfcfd;
}
.formula-table-row.is-dragging td {
  opacity: 0.58;
  background: #eef5ff;
}
.formula-table-row.is-drop-target td {
  background: #eff6ff;
  box-shadow: inset 0 2px 0 #3b82f6;
}
.formula-table-row.is-missing-total td {
  background: #fffaf3;
}
.formula-table-row.is-missing-total.is-dragging td,
.formula-table-row.is-missing-total.is-drop-target td {
  background: #eff6ff;
}
.formula-empty-row td {
  padding: 24px 12px;
  text-align: center;
  color: #98a2b3;
  font-size: 12px;
  background: #fafbfc;
}
.formula-drag-handle {
  display: grid;
  place-items: center;
  margin: 0 auto;
  width: 20px;
  height: 26px;
  padding: 0;
  border: 1px solid #e4e9ef;
  border-radius: 5px;
  background: #f8fafc;
  color: #98a2b3;
  cursor: grab;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
}
.formula-drag-grip {
  display: grid;
  grid-template-columns: repeat(2, 2px);
  gap: 2px 3px;
}
.formula-drag-grip i {
  display: block;
  width: 2px;
  height: 2px;
  border-radius: 50%;
  background: currentColor;
}
.formula-table-row:hover .formula-drag-handle {
  border-color: #d7e8de;
  background: #f4fbf7;
  color: #6b8f7a;
}
.formula-drag-handle:hover {
  border-color: #b9d8c7;
  background: #ecf8f1;
  color: #0f7c43;
  box-shadow: 0 1px 2px rgba(15, 124, 67, 0.08);
}
.formula-drag-handle:active,
.formula-table-row.is-dragging .formula-drag-handle {
  cursor: grabbing;
  border-color: #9fd4b6;
  background: #dff5e9;
  color: #0a6b39;
}
.name-input {
  width: 100%;
}
.name-input :deep(.el-input__inner) {
  text-align: left;
}
.basis-input {
  width: min(100%, 200px);
}
.basis-input :deep(.el-input__wrapper) {
  min-height: 34px;
  border-radius: 7px;
}
.basis-input :deep(.el-textarea__inner) {
  min-height: 34px !important;
  padding: 7px 10px;
  border-radius: 7px;
  font-size: 11px;
  line-height: 1.42;
  resize: none;
  overflow-y: hidden;
  text-align: left;
  word-break: break-word;
}
.portions-input {
  width: 64px;
  margin: 0 auto;
}
.portions-input :deep(.el-input__inner) {
  text-align: center;
}
.formula-pathology-cell {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: flex-start;
}
.formula-main-symptoms-cell {
  display: block;
  color: #475467;
  line-height: 1.35;
  white-space: normal;
  word-break: break-word;
  text-align: left;
}
.formula-unit-total {
  color: #475467;
  font-weight: 600;
}
.formula-unit-total.is-auto {
  color: #344054;
}
.formula-final-dose {
  color: #0f7c43;
  font-weight: 700;
}
.herb-dose-panel {
  margin-top: 10px;
  padding: 10px 12px;
  border: 1px solid #e1ecdf;
  border-radius: 7px;
  background: #fbfefb;
}
.herb-dose-title {
  margin-bottom: 8px;
  color: #344054;
  font-size: 12px;
  font-weight: 700;
}
.herb-dose-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
}
.herb-dose-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 28px;
  color: #344054;
  font-size: 12px;
  line-height: 1.2;
}
.herb-dose-input {
  width: 58px;
}
.herb-dose-input :deep(.el-input__wrapper) {
  min-height: 24px;
  padding: 0 5px;
  border-radius: 5px;
  box-shadow: none;
  background: #f8fcf9;
}
.herb-dose-input :deep(.el-input__inner) {
  color: #0f7c43;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  text-align: center;
}
.herb-name {
  font-weight: 600;
}
.formula-remove-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: 1px solid #f5cfc5;
  border-radius: 50%;
  background: #fff3ef;
  color: #d85a45;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease, transform 0.15s ease;
}
.formula-remove-icon {
  display: block;
  width: 11px;
  height: 11px;
  flex-shrink: 0;
}
.formula-remove-icon path {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
}
.formula-remove-btn:hover {
  color: #b42318;
  border-color: #e8a99a;
  background: #fde4dc;
  transform: scale(1.04);
}
.formula-remove-btn:active {
  transform: scale(0.96);
}
.muted {
  color: #98a2b3;
}
.prescription-note-field {
  margin-top: 12px;
}
.prescription-note-field label {
  display: block;
  margin-bottom: 6px;
  color: #667085;
  font-size: 12px;
  font-weight: 600;
}
</style>
