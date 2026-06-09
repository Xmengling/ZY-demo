<template>
  <div class="inquiry-hints-text-wrap" @click.stop>
    <span v-if="!editing" class="inquiry-hints-text">{{ displayText }}</span>
    <template v-else>
      <span
        v-for="(hint, index) in localHints"
        :key="`${hint}-${index}`"
        class="inquiry-hints-text inquiry-hints-text--edit"
      >
        {{ hint }}
        <button type="button" class="inquiry-hints-link" @click="removeHint(index)">删</button>
      </span>
      <button type="button" class="inquiry-hints-link" @click="addHint">添加</button>
      <button type="button" class="inquiry-hints-link" :disabled="saving" @click="save">保存</button>
      <button type="button" class="inquiry-hints-link" @click="toggleEdit">取消</button>
    </template>
    <button v-if="!editing" type="button" class="inquiry-hints-link" @click="toggleEdit">编辑</button>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { consultApi } from '../../api'

const props = defineProps({
  moduleKey: { type: String, required: true },
  hints: { type: Array, default: () => [] }
})

const emit = defineEmits(['updated'])

const editing = ref(false)
const saving = ref(false)
const localHints = ref([])

const displayText = computed(() => {
  const list = (props.hints || []).filter(Boolean)
  return list.length ? list.join(' · ') : ''
})

watch(
  () => props.hints,
  (list) => {
    if (!editing.value) localHints.value = [...(list || [])]
  },
  { immediate: true, deep: true }
)

function toggleEdit() {
  if (editing.value) {
    editing.value = false
    localHints.value = [...(props.hints || [])]
    return
  }
  localHints.value = [...(props.hints || [])]
  editing.value = true
}

function addHint() {
  const text = window.prompt('输入问诊提示')
  const value = (text || '').trim()
  if (!value || localHints.value.includes(value)) return
  localHints.value.push(value)
}

function removeHint(index) {
  localHints.value.splice(index, 1)
}

async function save() {
  saving.value = true
  try {
    const data = await consultApi.updateModuleHints(props.moduleKey, {
      hints: localHints.value.filter(Boolean)
    })
    const next = data?.hints || []
    localHints.value = [...next]
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
  display: inline;
  text-align: left;
  line-height: 1.5;
  font-size: 12px;
  font-weight: 400;
  color: #8a94a6;
}
.inquiry-hints-text {
  color: #8a94a6;
}
.inquiry-hints-text--edit {
  margin-right: 6px;
}
.inquiry-hints-text--edit::after {
  content: ' · ';
  color: #c5cdd8;
}
.inquiry-hints-text-wrap > .inquiry-hints-text:first-child::before {
  content: '：';
  color: #c5cdd8;
  margin-right: 2px;
}
.inquiry-hints-link {
  margin-left: 8px;
  padding: 0;
  border: none;
  background: none;
  color: #98a2b3;
  font-size: 12px;
  cursor: pointer;
}
.inquiry-hints-link:hover {
  color: #667085;
}
.inquiry-hints-link:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
