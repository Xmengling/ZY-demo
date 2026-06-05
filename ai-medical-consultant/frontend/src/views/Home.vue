<template>
  <div class="page">
    <div class="hero gradient-hero">
      <div>
        <h1>您好，{{ auth.user?.full_name || auth.user?.username }} 👋</h1>
        <p>描述您的症状（寒热、汗出、舌脉、二便等），AI 将结合经方方证知识库为您辨证分析、匹配可能相关的方证并给出调护建议。</p>
        <el-button size="large" round @click="$router.push('/consult')">
          <el-icon><ChatDotRound /></el-icon>&nbsp;开始智能问诊
        </el-button>
      </div>
      <el-icon :size="120" class="hero-icon"><FirstAidKit /></el-icon>
    </div>

    <h3 class="section-title">核心能力</h3>
    <el-row :gutter="16">
      <el-col :span="8" v-for="f in features" :key="f.title">
        <el-card shadow="hover" class="feature">
          <div class="feature-icon" :style="{ background: f.bg }">
            <el-icon :size="24" :color="f.color"><component :is="f.icon" /></el-icon>
          </div>
          <h4>{{ f.title }}</h4>
          <p class="text-muted">{{ f.desc }}</p>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const features = [
  { title: '方证问诊', desc: '多轮对话收集症状舌脉，AI 辨证分析', icon: 'ChatDotRound', bg: '#e6f7ef', color: '#18a058' },
  { title: '经方知识库', desc: '基于向量检索的经方方证知识精准匹配', icon: 'Reading', bg: '#eef2ff', color: '#4f46e5' },
  { title: '问诊记录', desc: '持久化存储问诊历史，支持回溯', icon: 'Tickets', bg: '#fdeeee', color: '#cf1322' }
]
</script>

<style scoped>
.hero {
  border-radius: 16px;
  padding: 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.hero h1 {
  margin: 0 0 10px;
}
.hero p {
  margin: 0 0 18px;
  max-width: 560px;
  opacity: 0.92;
}
.hero-icon {
  opacity: 0.3;
}
.section-title {
  margin: 26px 0 14px;
}
.feature {
  border-radius: 12px;
  min-height: 150px;
}
.feature-icon {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
}
.feature h4 {
  margin: 0 0 6px;
}
.feature p {
  margin: 0;
  font-size: 13px;
}
</style>
