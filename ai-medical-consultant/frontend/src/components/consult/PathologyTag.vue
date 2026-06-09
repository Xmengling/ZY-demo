<template>
  <span class="pathology-tag" :class="toneClass">
    <span class="pathology-tag__text">{{ label }}</span>
    <strong
      v-if="showScore"
      class="pathology-tag__score"
      :class="{ 'is-empty': isEmptyScore }"
    >{{ displayScore }}</strong>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { getPathologyToneClass } from '../../utils/pathologyTone'

const props = defineProps({
  label: { type: String, required: true },
  score: { type: [String, Number], default: null }
})

const toneClass = computed(() => getPathologyToneClass(props.label))
const showScore = computed(() => props.score !== null && props.score !== undefined)
const isEmptyScore = computed(() => displayScore.value === '—')
const displayScore = computed(() => {
  if (!showScore.value) return ''
  const raw = props.score
  if (raw === undefined || raw === null || raw === '') return '—'
  return raw
})
</script>
