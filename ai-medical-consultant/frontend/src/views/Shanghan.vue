<template>
  <div class="shanghan-shell">
    <iframe
      v-if="ready"
      class="shanghan-frame"
      src="/shanghan/index.html"
      title="伤寒论条文解读"
    />
    <div v-else class="shanghan-loading">
      <el-icon class="spin"><Loading /></el-icon>
      <span>加载条文解读…</span>
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
.shanghan-shell {
  height: calc(100vh - 60px);
  background: #f4f6f9;
}
.shanghan-frame {
  width: 100%;
  height: 100%;
  border: 0;
  display: block;
}
.shanghan-loading {
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
