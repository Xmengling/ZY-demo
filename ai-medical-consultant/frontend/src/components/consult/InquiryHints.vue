<template>
  <div class="inquiry-hints-text-wrap" @click.stop>
    <template v-if="!editing">
      <span class="inquiry-hints-text">{{ displayText }}</span>
      <button type="button" class="inquiry-hints-link" @click="toggleEdit">编辑</button>
    </template>
    <template v-else>
      <span class="inquiry-hints-colon">：</span>
      <input
        ref="inputRef"
        v-model="editText"
        class="inquiry-hints-input"
        type="text"
        placeholder="输入问诊提示"
        @keydown.enter.prevent="save"
        @keydown.esc.prevent="toggleEdit"
      />
      <button type="button" class="inquiry-hints-link" :disabled="saving" @click="save">保存</button>
      <button type="button" class="inquiry-hints-link" @click="toggleEdit">取消</button>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { consultApi } from '../../api'

const props = defineProps({
  moduleKey: { type: String, required: true },
  hints: { type: Array, default: () => [] }
})

const emit = defineEmits(['updated'])

const editing = ref(false)
const saving = ref(false)
const editText = ref('')
const inputRef = ref(null)

const displayText = computed(() => {
  const list = (props.hints || []).filter(Boolean)
  return list.length ? list.join(' · ') : ''
})

function hintsToEditText(hints) {
  return (hints || []).filter(Boolean).join(' · ')
}

function editTextToHints(text) {
  const raw = String(text || '').trim()
  if (!raw) return []
  if (raw.includes(' · ')) {
    return raw.split(' · ').map((s) => s.trim()).filter(Boolean)
  }
  return [raw]
}

async function toggleEdit() {
  if (editing.value) {
    editing.value = false
    return
  }
  editText.value = hintsToEditText(props.hints)
  editing.value = true
  await nextTick()
  inputRef.value?.focus()
  inputRef.value?.select()
}

async function save() {
  const hints = editTextToHints(editText.value)
  saving.value = true
  try {
    const data = await consultApi.updateModuleHints(props.moduleKey, { hints })
    const next = data?.hints || []
    editing.value = false
    emit('updated', next)
    ElMessage.success('已保存')
  } catch {
    ElMessage.error('保存失败，请确认已登录')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.inquiry-hints-text-wrap {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  text-align: left;
  line-height: 1.5;
  font-size: 12px;
  font-weight: 400;
  color: #8a94a6;
  min-width: 0;
}
.inquiry-hints-text {
  color: #8a94a6;
}
.inquiry-hints-text::before {
  content: '：';
  color: #c5cdd8;
  margin-right: 2px;
}
.inquiry-hints-colon {
  color: #c5cdd8;
  flex-shrink: 0;
}
.inquiry-hints-input {
  flex: 1;
  min-width: 160px;
  max-width: 100%;
  height: 26px;
  padding: 0 8px;
  border: 1px solid #dce3ec;
  border-radius: 6px;
  background: #fff;
  color: #4b5563;
  font-size: 12px;
  outline: none;
}
.inquiry-hints-input:focus {
  border-color: #9fd4b6;
  box-shadow: 0 0 0 2px rgba(24, 160, 88, 0.1);
}
.inquiry-hints-link {
  padding: 0;
  border: none;
  background: none;
  color: #98a2b3;
  font-size: 12px;
  cursor: pointer;
  flex-shrink: 0;
}
.inquiry-hints-link:hover {
  color: #667085;
}
.inquiry-hints-link:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
