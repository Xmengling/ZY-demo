<template>
  <div class="formulas-shell">
    <iframe
      v-if="ready"
      class="formulas-frame"
      src="/jingfang/index.html"
      title="方剂梳理"
    />
    <div v-else class="formulas-loading">
      <el-icon class="spin"><Loading /></el-icon>
      <span>加载方剂梳理…</span>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

const ready = ref(false)

onMounted(() => {
  ready.value = true
})
</script>

<style scoped>
.formulas-shell {
  height: calc(100vh - 44px);
  background: #f4f6f9;
}
.formulas-frame {
  width: 100%;
  height: 100%;
  border: 0;
  display: block;
}
.formulas-loading {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #667085;
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
