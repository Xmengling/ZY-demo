<template>
  <el-container style="height: 100vh">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <el-icon :size="24"><FirstAidKit /></el-icon>
        <span>AI 智能问诊</span>
      </div>
      <el-menu :default-active="activeMenu" router class="menu" background-color="transparent" text-color="#cdd6e4" active-text-color="#fff">
        <el-menu-item index="/"><el-icon><HomeFilled /></el-icon><span>首页</span></el-menu-item>
        <el-menu-item index="/consult"><el-icon><ChatDotRound /></el-icon><span>智能问诊</span></el-menu-item>
        <el-menu-item index="/records"><el-icon><Tickets /></el-icon><span>问诊记录</span></el-menu-item>
        <el-menu-item index="/knowledge"><el-icon><Reading /></el-icon><span>知识库</span></el-menu-item>
        <el-menu-item index="/formulas"><el-icon><Collection /></el-icon><span>100首方剂解读</span></el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="title">{{ pageTitle }}</div>
        <el-dropdown @command="onCommand">
          <span class="user">
            <el-avatar :size="30" style="background: var(--brand)">{{ avatarChar }}</el-avatar>
            <span style="margin: 0 6px">{{ auth.user?.full_name || auth.user?.username }}</span>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const titles = { home: '首页', consult: '智能问诊', records: '问诊记录', knowledge: '医学知识库', formulas: '100首方剂解读' }
const pageTitle = computed(() => titles[route.name] || '')
const activeMenu = computed(() => {
  if (route.path.startsWith('/consult')) return '/consult'
  return route.path
})
const avatarChar = computed(() => (auth.user?.full_name || auth.user?.username || 'U').charAt(0).toUpperCase())

function onCommand(cmd) {
  if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.aside {
  background: #11324a;
  display: flex;
  flex-direction: column;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 18px;
  color: #fff;
  font-weight: 600;
  font-size: 17px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.menu {
  border-right: none;
  flex: 1;
  padding-top: 8px;
}
.menu :deep(.el-menu-item) {
  margin: 4px 10px;
  border-radius: 8px;
}
.menu :deep(.el-menu-item.is-active) {
  background: var(--brand);
}
.header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #eef1f6;
}
.title {
  font-size: 18px;
  font-weight: 600;
}
.user {
  display: flex;
  align-items: center;
  cursor: pointer;
  outline: none;
}
.main {
  background: var(--bg);
  padding: 0;
  overflow: auto;
}
</style>
