<template>
  <div class="prescription-block">
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
      <el-button size="small" class="add-btn" @click="addRow">+ 添加方剂</el-button>
    </div>

    <div class="formula-table-wrap">
      <table class="formula-table">
        <colgroup>
          <col class="col-name" />
          <col class="col-pathology" />
          <col class="col-main-symptoms" />
          <col class="col-unit" />
          <col class="col-portions" />
          <col class="col-final" />
          <col class="col-action" />
        </colgroup>
        <thead>
          <tr>
            <th class="col-name">方剂名</th>
            <th class="col-pathology">病理</th>
            <th class="col-main-symptoms">主要症状</th>
            <th class="num">单方量</th>
            <th class="num">份数</th>
            <th class="num">最终用量</th>
            <th class="col-action" aria-label="操作" />
          </tr>
        </thead>
        <tbody>
          <tr v-if="!modelValue.rows.length" class="formula-empty-row">
            <td colspan="7">暂未添加方剂，点击「+ 添加方剂」开始录入</td>
          </tr>
          <tr
            v-for="(row, index) in modelValue.rows"
            :key="row.id"
            class="formula-table-row"
            :class="{ 'is-missing-total': rowMeta(row).missing }"
          >
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
            <td class="col-action">
              <button type="button" class="formula-remove-btn" aria-label="删除方剂" @click="removeRow(index)">×</button>
            </td>
          </tr>
        </tbody>
      </table>
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
import { computed, ref, watch } from 'vue'
import PathologyTag from './PathologyTag.vue'
import { formatMainSymptomsText, lookupFormulaPowder, runDoseCalc } from '../../utils/formulaPowder'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({
      targetDose: 200,
      note: '',
      rows: []
    })
  },
  formulaIndex: { type: Map, default: () => new Map() },
  formulaNames: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue'])

const localTarget = ref(props.modelValue.targetDose ?? 200)
const localNote = ref(props.modelValue.note ?? '')

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
  const rows = [...(props.modelValue.rows || []), { id: newRowId(), name: '', portions: 1 }]
  emit('update:modelValue', buildPayload(rows))
}

function removeRow(index) {
  emit('update:modelValue', buildPayload(props.modelValue.rows.filter((_, i) => i !== index)))
}

function buildPayload(rows) {
  return {
    targetDose: localTarget.value,
    note: localNote.value,
    rows: rows.map((r) => ({ id: r.id, name: r.name, portions: Number(r.portions) || 1 }))
  }
}

function emitUpdate() {
  emit('update:modelValue', buildPayload(props.modelValue.rows || []))
}

watch(
  () => props.modelValue,
  (val) => {
    localTarget.value = val?.targetDose ?? 200
    localNote.value = val?.note ?? ''
  },
  { deep: true }
)
</script>

<style scoped>
.prescription-block {
  background: #fff;
  border: 1px solid #e6ebf2;
  border-radius: 8px;
  padding: 12px;
}
.prescription-block-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
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
  border-color: #d7e8de;
  color: #0f7c43;
}
.formula-table-wrap {
  overflow-x: auto;
  border: 1px solid #e8edf3;
  border-radius: 7px;
}
.formula-table {
  width: 100%;
  min-width: 820px;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 12px;
}
.formula-table .col-name {
  width: 16%;
}
.formula-table .col-pathology {
  width: 22%;
}
.formula-table .col-main-symptoms {
  width: 30%;
}
.formula-table th,
.formula-table td {
  border-bottom: 1px solid #eef2f6;
  padding: 8px 10px;
  vertical-align: middle;
  background: #fff;
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
.formula-table td.col-main-symptoms {
  text-align: left;
  vertical-align: top;
}
.formula-table td.num,
.formula-table th.num,
.formula-table td.col-action,
.formula-table th.col-action {
  text-align: center;
  vertical-align: middle;
  font-variant-numeric: tabular-nums;
}
.formula-table .col-action {
  width: 44px;
}
.formula-table tbody tr:hover td {
  background: #fbfcfd;
}
.formula-table-row.is-missing-total td {
  background: #fffaf3;
}
.formula-empty-row td {
  padding: 24px 12px;
  text-align: center;
  color: #98a2b3;
  font-size: 12px;
  background: #fafbfc;
}
.name-input {
  width: 100%;
}
.name-input :deep(.el-input__inner) {
  text-align: left;
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
.formula-remove-btn {
  width: 28px;
  height: 28px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: #98a2b3;
  font-size: 15px;
  cursor: pointer;
}
.formula-remove-btn:hover {
  color: #c2410c;
  border-color: #f3d8cf;
  background: #fff7f4;
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
