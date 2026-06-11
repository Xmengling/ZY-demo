<template>
  <div
    class="pathology-stars"
    :class="toneClass"
    role="radiogroup"
    :aria-label="ariaLabel"
    @mouseleave="hoverValue = 0"
  >
    <button
      v-for="star in starOrder"
      :key="star"
      type="button"
      class="pathology-star"
      :class="{ active: star <= displayValue, hover: hoverValue > 0 && star <= hoverValue }"
      :aria-label="`${star} 星`"
      :aria-checked="modelValue === star"
      role="radio"
      @mouseenter="hoverValue = star"
      @click="onSelect(star)"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          class="pathology-star__shape"
          d="M12 2.4l2.54 5.15 5.68.83-4.11 4.01.97 5.66L12 15.9l-5.08 2.67.97-5.66-4.11-4.01 5.68-.83L12 2.4z"
        />
      </svg>
    </button>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  toneClass: { type: String, default: '' },
  ariaLabel: { type: String, default: '病理打分' }
})

const emit = defineEmits(['update:modelValue'])

const hoverValue = ref(0)
const starOrder = [1, 2, 3, 4, 5]

const displayValue = computed(() => hoverValue.value || Number(props.modelValue) || 0)

function onSelect(star) {
  emit('update:modelValue', star === props.modelValue ? 0 : star)
}
</script>

<style scoped>
.pathology-stars {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: nowrap;
  gap: 1px;
  width: 100%;
  padding: 0;
  margin: 0;
  --star-active: var(--path-fg, #f5a623);
  --star-active-glow: var(--path-glow, rgba(245, 166, 35, 0.28));
  --star-idle: #e6ebf2;
  --star-idle-stroke: #d5dde8;
}

.pathology-star {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: 4px;
  transition: transform 0.14s ease;
}

.pathology-star svg {
  width: 16px;
  height: 16px;
  display: block;
  filter: drop-shadow(0 0 0 transparent);
  transition: filter 0.14s ease, transform 0.14s ease;
}

.pathology-star__shape {
  fill: var(--star-idle);
  stroke: var(--star-idle-stroke);
  stroke-width: 0.9;
  stroke-linejoin: round;
  transition: fill 0.14s ease, stroke 0.14s ease;
}

.pathology-star:hover {
  transform: scale(1.08);
}

.pathology-star.active .pathology-star__shape,
.pathology-star.hover .pathology-star__shape {
  fill: var(--star-active);
  stroke: color-mix(in srgb, var(--star-active) 72%, #fff);
}

.pathology-star.active svg,
.pathology-star.hover svg {
  filter: drop-shadow(0 1px 3px var(--star-active-glow));
}

.pathology-star:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--star-active) 55%, #fff);
  outline-offset: 1px;
}
</style>
