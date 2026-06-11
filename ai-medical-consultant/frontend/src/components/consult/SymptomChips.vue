<template>
  <div class="symptom-chips">
    <div
      ref="chipsWrapRef"
      class="chips"
      :class="{ 'is-editing': editing }"
      @dragover.prevent="onDragOver"
      @drop.prevent="onDrop"
    >
      <span v-if="editing" class="symptom-hint">双击改文字 · 可拖拽排序</span>
      <span
        v-for="(symptom, index) in displayChips"
        :key="`${blockLabel}-${symptom}-${index}`"
        class="chip-item"
        :class="{ active: selected[symptom], 'is-dragging': dragIndex === index, 'is-drop-target': dropIndex === index }"
        role="group"
        draggable="false"
        @dragend="onDragEnd"
      >
        <span
          v-if="editing"
          class="chip-drag"
          draggable="true"
          aria-label="拖拽排序"
          @dragstart="(e) => onDragStart(e, index)"
        >⋮⋮</span>
        <span
          class="chip-text"
          :contenteditable="editing"
          :class="{ 'is-editing': editingText === symptom }"
          @click="onChipClick(symptom, $event)"
          @dblclick="onChipDblClick(symptom, $event)"
          @blur="(e) => onChipBlur(symptom, e)"
          @keydown.enter.prevent="(e) => e.target.blur()"
          @keydown.esc.prevent="cancelEdit"
        >{{ symptom }}</span>
        <button
          v-if="editing"
          type="button"
          class="chip-remove"
          aria-label="删除症状"
          @click.stop="removeChip(symptom)"
        >×</button>
      </span>
      <button v-if="editing" type="button" class="chip-add" @click="addChip">+ 添加</button>
      <button
        type="button"
        class="symptoms-edit-btn"
        :aria-pressed="editing"
        :disabled="saving"
        @click="toggleEdit"
      >
        {{ saving ? '保存中…' : editing ? '完成' : '编辑' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { consultApi } from '../../api'
import { removeSymptomFromNote, renameSymptomInNote, toggleSymptomInNote } from '../../utils/consultSymptoms'

const props = defineProps({
  blockLabel: { type: String, required: true },
  chips: { type: Array, default: () => [] },
  selected: { type: Object, default: () => ({}) },
  note: { type: String, default: '' }
})

const emit = defineEmits(['update:chips', 'update:note', 'toggle-selected', 'persisted'])

const editing = ref(false)
const saving = ref(false)
const chipsAtEditStart = ref([])
const editingText = ref('')
const editStartText = ref('')
const dragIndex = ref(-1)
const dropIndex = ref(-1)
const chipsWrapRef = ref(null)

const displayChips = computed(() => props.chips.filter(Boolean))

function chipsSignature(list) {
  return (list || []).filter(Boolean).join('\u0001')
}

async function persistChipsIfChanged() {
  const symptoms = displayChips.value
  if (chipsSignature(symptoms) === chipsSignature(chipsAtEditStart.value)) return true
  saving.value = true
  try {
    const data = await consultApi.updateBlockSymptoms(props.blockLabel, { symptoms })
    const next = data?.symptoms || symptoms
    emit('update:chips', [...next])
    emit('persisted', [...next])
    ElMessage.success('常见症状已保存，对所有医案生效')
    return true
  } catch {
    ElMessage.error('保存失败，请确认已登录')
    return false
  } finally {
    saving.value = false
  }
}

async function toggleEdit() {
  if (saving.value) return
  if (editing.value) {
    editingText.value = ''
    const ok = await persistChipsIfChanged()
    if (!ok) return
    editing.value = false
    chipsAtEditStart.value = []
    return
  }
  chipsAtEditStart.value = [...displayChips.value]
  editing.value = true
}

function onChipClick(symptom, event) {
  if (editing.value && event.target.classList.contains('is-editing')) return
  const next = !props.selected[symptom]
  emit('toggle-selected', { symptom, active: next })
  emit('update:note', toggleSymptomInNote(props.note, symptom, next))
}

function onChipDblClick(symptom, event) {
  if (!editing.value) return
  event.preventDefault()
  event.stopPropagation()
  editingText.value = symptom
  editStartText.value = symptom
}

function onChipBlur(symptom, event) {
  if (!editing.value || editingText.value !== symptom) return
  const newText = event.target.textContent.replace(/\s+/g, ' ').trim()
  editingText.value = ''
  if (!newText) {
    removeChip(symptom)
    return
  }
  if (newText !== symptom) {
    const list = [...props.chips]
    const idx = list.indexOf(symptom)
    if (idx >= 0) list[idx] = newText
    emit('update:chips', list)
    if (props.selected[symptom]) {
      emit('update:note', renameSymptomInNote(props.note, symptom, newText))
      emit('toggle-selected', { symptom, active: false })
      emit('toggle-selected', { symptom: newText, active: true })
    }
  }
  editStartText.value = ''
}

function cancelEdit() {
  editingText.value = ''
  editStartText.value = ''
}

function removeChip(symptom) {
  if (props.selected[symptom]) {
    emit('update:note', removeSymptomFromNote(props.note, symptom))
    emit('toggle-selected', { symptom, active: false })
  }
  emit('update:chips', props.chips.filter((item) => item !== symptom))
}

function addChip() {
  const text = window.prompt('输入症状')
  const value = (text || '').trim()
  if (!value || props.chips.includes(value)) return
  emit('update:chips', [...props.chips, value])
}

function onDragStart(event, index) {
  dragIndex.value = index
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', displayChips.value[index])
}

function onDragEnd() {
  dragIndex.value = -1
  dropIndex.value = -1
}

function onDragOver(event) {
  if (dragIndex.value < 0) return
  const item = event.target.closest('.chip-item')
  if (!item) return
  const nodes = [...chipsWrapRef.value?.querySelectorAll('.chip-item') || []]
  dropIndex.value = nodes.indexOf(item)
}

function onDrop(event) {
  if (dragIndex.value < 0) return
  const target = event.target.closest('.chip-item')
  const list = [...props.chips]
  const [moved] = list.splice(dragIndex.value, 1)
  if (!target) {
    list.push(moved)
  } else {
    const nodes = [...chipsWrapRef.value.querySelectorAll('.chip-item')]
    let targetIndex = nodes.indexOf(target)
    const rect = target.getBoundingClientRect()
    if (event.clientX >= rect.left + rect.width / 2) targetIndex += 1
    if (targetIndex > dragIndex.value) targetIndex -= 1
    list.splice(Math.max(0, targetIndex), 0, moved)
  }
  emit('update:chips', list)
  onDragEnd()
}

watch(editing, (val) => {
  if (!val) {
    editingText.value = ''
    editStartText.value = ''
  }
})
</script>

<style scoped>
.symptom-hint {
  flex: 1 1 100%;
  color: #8a94a6;
  font-size: 11px;
  line-height: 22px;
}
.symptoms-edit-btn {
  flex-shrink: 0;
  height: 22px;
  padding: 0 8px;
  border: 1px solid #e3e9f0;
  border-radius: 6px;
  background: transparent;
  color: #8a94a6;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
}
.symptoms-edit-btn:hover {
  border-color: #cdd6e2;
  color: #667085;
  background: #f8fafc;
}
.symptoms-edit-btn[aria-pressed='true'] {
  border-color: #b5dfc8;
  color: #2a8f5c;
  background: #f3fbf7;
}
.symptoms-edit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 3px 4px;
  align-items: center;
  row-gap: 3px;
}
.chip-item {
  display: inline-flex;
  align-items: center;
  gap: 1px;
  min-height: 22px;
  padding: 0 7px;
  border: 1px solid #e0e6ee;
  border-radius: 999px;
  background: #fff;
  color: #5b6777;
  font-size: 11px;
  cursor: pointer;
  transition: background 0.16s ease, border-color 0.16s ease, color 0.16s ease, box-shadow 0.16s ease;
}
.chip-item:hover {
  border-color: #cdd6e2;
  background: #fafbfc;
}
.chip-item.active {
  color: var(--chip-active-fg, var(--path-fg, #2a8f5c));
  background: var(--chip-active-bg, var(--path-bg, #e8f6ee));
  border-color: var(--chip-active-border, var(--path-border, #b5dfc8));
  font-weight: 700;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
}
.chip-item.is-dragging {
  opacity: 0.45;
}
.chip-item.is-drop-target {
  box-shadow: 0 0 0 2px rgba(24, 160, 88, 0.25);
}
.chip-drag {
  color: #98a2b3;
  font-size: 10px;
  cursor: grab;
  user-select: none;
  padding: 0 2px;
}
.chip-text {
  outline: none;
  padding: 0 2px;
}
.chip-text.is-editing {
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 0 0 1px #9fd4b6 inset;
}
.chip-remove,
.chip-add {
  border: none;
  background: transparent;
  color: #98a2b3;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  padding: 0 4px;
}
.chip-remove:hover {
  color: #c2410c;
}
.chip-add {
  min-height: 22px;
  padding: 0 7px;
  border: 1px dashed #cbd6e2;
  border-radius: 999px;
  color: #475467;
  font-size: 11px;
  font-weight: 600;
}
.chip-add:hover {
  border-color: #9fd4b6;
  color: #0f7c43;
  background: #f3fbf7;
}
.chips:not(.is-editing) .chip-drag,
.chips:not(.is-editing) .chip-remove {
  display: none;
}
</style>
