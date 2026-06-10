<template>
  <el-container class="main-shell" :class="{ 'is-sidebar-collapsed': collapsed }" style="height: 100vh">
    <el-aside :width="sidebarWidth" class="aside" :class="{ 'is-collapsed': collapsed }">
      <div class="logo">
        <el-icon :size="24"><FirstAidKit /></el-icon>
        <span v-show="!collapsed" class="logo-text">AI 智能问诊</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="collapsed"
        :collapse-transition="false"
        router
        class="menu"
        background-color="transparent"
        text-color="#cdd6e4"
        active-text-color="#fff"
      >
        <el-menu-item index="/"><el-icon><HomeFilled /></el-icon><span>AI 问答</span></el-menu-item>
        <el-menu-item index="/consult"><el-icon><ChatDotRound /></el-icon><span>智能问诊</span></el-menu-item>
        <el-menu-item index="/records"><el-icon><Tickets /></el-icon><span>医案记录</span></el-menu-item>
        <el-menu-item index="/knowledge"><el-icon><Reading /></el-icon><span>知识库</span></el-menu-item>
        <el-menu-item index="/formulas"><el-icon><Collection /></el-icon><span>100首方剂解读</span></el-menu-item>
        <el-menu-item index="/shanghan"><el-icon><Reading /></el-icon><span>伤寒论条文解读</span></el-menu-item>
      </el-menu>
      <button type="button" class="collapse-btn" :title="collapsed ? '展开菜单' : '折叠菜单'" @click="toggleCollapse">
        <el-icon :size="18">
          <Expand v-if="collapsed" />
          <Fold v-else />
        </el-icon>
        <span v-show="!collapsed">折叠菜单</span>
      </button>
    </el-aside>

    <el-container>
      <el-header class="header" height="44px">
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
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const SIDEBAR_COLLAPSED_KEY = 'sidebar-collapsed'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const collapsed = ref(localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1')
const sidebarWidth = computed(() => (collapsed.value ? '64px' : '220px'))

function toggleCollapse() {
  collapsed.value = !collapsed.value
  localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed.value ? '1' : '0')
}

const titles = { home: 'AI 问答', consult: '智能问诊', records: '医案记录', knowledge: '知识库', formulas: '100首方剂解读', shanghan: '伤寒论条文解读' }
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

<style>
.main-shell {
  --sidebar-width-expanded: 220px;
  --sidebar-width-collapsed: 64px;
  --consult-page-max-width: 1440px;
  --consult-analysis-width: 392px;
}
.main-shell.is-sidebar-collapsed {
  --consult-page-max-width: calc(
    1440px + var(--sidebar-width-expanded) - var(--sidebar-width-collapsed)
  );
  --consult-analysis-width: calc(
    392px + var(--sidebar-width-expanded) - var(--sidebar-width-collapsed)
  );
}
</style>

<style scoped>
.aside {
  background: #11324a;
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease;
  overflow: hidden;
}
.aside.is-collapsed .logo {
  justify-content: center;
  padding: 0;
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
  flex-shrink: 0;
}
.logo-text {
  white-space: nowrap;
}
.menu {
  border-right: none;
  flex: 1;
  padding-top: 8px;
  overflow: hidden auto;
}
.menu:not(.el-menu--collapse) {
  width: 100%;
}
.menu :deep(.el-menu-item) {
  margin: 4px 10px;
  border-radius: 8px;
}
.aside.is-collapsed .menu :deep(.el-menu-item) {
  margin: 4px 8px;
}
.menu :deep(.el-menu-item.is-active) {
  background: var(--brand);
}
.collapse-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  height: 48px;
  border: none;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  background: transparent;
  color: #cdd6e4;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.collapse-btn:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}
.aside.is-collapsed .collapse-btn {
  padding: 0;
}
.header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #eef1f6;
  padding: 0 16px;
}
.title {
  font-size: 16px;
  font-weight: 600;
  line-height: 1.2;
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
