<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="brand">
        <el-icon :size="40" color="#18a058"><FirstAidKit /></el-icon>
        <h1>AI 智能问诊系统</h1>
        <p class="text-muted">LLM + Agent + RAG 驱动的 7×24 智能健康助手</p>
      </div>

      <el-tabs v-model="tab" stretch>
        <el-tab-pane label="登录" name="login" />
        <el-tab-pane label="注册" name="register" />
      </el-tabs>

      <el-form :model="form" @submit.prevent>
        <el-form-item>
          <el-input v-model="form.username" size="large" placeholder="用户名" :prefix-icon="User" />
        </el-form-item>
        <el-form-item v-if="tab === 'register'">
          <el-input v-model="form.fullName" size="large" placeholder="姓名（选填）" :prefix-icon="Avatar" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" size="large" placeholder="密码" :prefix-icon="Lock" show-password @keyup.enter="submit" />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="submit">
          {{ tab === 'login' ? '登录' : '注册并登录' }}
        </el-button>
      </el-form>

      <div class="demo-tip">
        <el-icon><InfoFilled /></el-icon>
        演示账号：<b>demo</b> / <b>demo123</b>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { User, Lock, Avatar } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const tab = ref('login')
const loading = ref(false)
const form = reactive({ username: 'demo', password: 'demo123', fullName: '' })

async function submit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    if (tab.value === 'login') {
      await auth.login(form.username, form.password)
    } else {
      await auth.register(form.username, form.password, form.fullName)
    }
    ElMessage.success('欢迎使用 AI 智能问诊系统')
    router.push(route.query.redirect || '/')
  } catch (e) {
    /* 错误已由拦截器提示 */
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #18a058 0%, #0f7c43 100%);
}
.login-card {
  width: 400px;
  background: #fff;
  border-radius: 16px;
  padding: 36px 36px 28px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}
.brand {
  text-align: center;
  margin-bottom: 8px;
}
.brand h1 {
  font-size: 22px;
  margin: 10px 0 4px;
}
.brand p {
  margin: 0 0 6px;
  font-size: 13px;
}
.demo-tip {
  margin-top: 16px;
  text-align: center;
  font-size: 13px;
  color: #8a94a6;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
</style>
