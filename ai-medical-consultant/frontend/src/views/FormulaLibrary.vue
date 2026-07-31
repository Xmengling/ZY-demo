<template>
  <div class="library-page">
    <header class="library-header">
      <router-link class="brand" to="/cards" aria-label="经方卡片馆首页">
        <span class="brand-mark" aria-hidden="true">方</span>
        <span>
          <strong>经方卡片馆</strong>
          <small>一方一证 · 清晰辨方</small>
        </span>
      </router-link>

      <div class="header-center" aria-label="页面能力">
        <span><i></i> {{ formulaCount ? `${formulaCount} 首经方卡片` : '经方卡片' }}</span>
        <span>可搜索</span>
        <span>可下载 PDF</span>
      </div>

      <div class="header-actions">
        <span v-if="auth.isLoggedIn" class="role-pill">
          {{ auth.isAdmin ? '管理员' : '普通用户' }}
        </span>
        <button class="admin-button" type="button" @click="goAdmin">
          <el-icon><EditPen v-if="auth.isAdmin" /><Lock v-else /></el-icon>
          {{ auth.isAdmin ? '进入编辑后台' : '管理员登录' }}
        </button>
      </div>
    </header>

    <section class="library-intro">
      <div>
        <span class="eyebrow">JINGFANG FORMULA LIBRARY</span>
        <h1>把经典方证，做成随时可查的学习卡片</h1>
      </div>
      <p>按表、里、半、水、血、气、阴分类浏览。普通用户可查看和下载，内容编辑仅对管理员开放。</p>
    </section>

    <div class="library-frame-wrap">
      <iframe
        class="library-frame"
        src="/jingfang/index.html?mode=viewer&v=role1"
        title="经方卡片浏览与下载"
      />
    </div>

    <div v-if="route.query.access === 'viewer'" class="access-toast">
      当前账号为普通用户，已进入只读卡片馆。
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { formulasApi } from '../api'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const formulaCount = ref(0)

onMounted(async () => {
  if (auth.isLoggedIn) auth.refreshUser()
  try {
    const data = await formulasApi.list()
    formulaCount.value = data.formulas?.length || 0
  } catch {
    formulaCount.value = 0
  }
})

function goAdmin() {
  if (auth.isAdmin) {
    router.push('/formulas')
    return
  }
  if (auth.isLoggedIn) auth.logout()
  router.push({ name: 'login', query: { redirect: '/formulas' } })
}
</script>

<style scoped>
.library-page {
  --navy: #12243a;
  --blue: #356fdd;
  --blue-soft: #edf4ff;
  min-height: 100vh;
  height: 100vh;
  display: grid;
  grid-template-rows: 72px auto minmax(0, 1fr);
  overflow: hidden;
  color: var(--navy);
  background:
    radial-gradient(circle at 16% -20%, rgba(91, 148, 255, 0.18), transparent 32%),
    #f3f7fc;
}

.library-header {
  z-index: 2;
  display: grid;
  grid-template-columns: minmax(230px, 1fr) auto minmax(230px, 1fr);
  align-items: center;
  gap: 24px;
  padding: 0 32px;
  border-bottom: 1px solid rgba(31, 65, 111, 0.1);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(18px);
  box-shadow: 0 8px 30px rgba(35, 69, 115, 0.05);
}

.brand {
  justify-self: start;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  color: inherit;
  text-decoration: none;
}

.brand-mark {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 13px 13px 13px 4px;
  color: #fff;
  background: linear-gradient(145deg, #467ddd, #2356b8);
  font-family: "Songti SC", "STSong", serif;
  font-size: 23px;
  font-weight: 800;
  box-shadow: 0 8px 18px rgba(53, 111, 221, 0.25);
}

.brand strong,
.brand small {
  display: block;
}

.brand strong {
  font-family: "Songti SC", "STSong", serif;
  font-size: 19px;
  letter-spacing: 0.08em;
}

.brand small {
  margin-top: 2px;
  color: #789;
  font-size: 10px;
  letter-spacing: 0.14em;
}

.header-center {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #687b93;
  font-size: 12px;
}

.header-center span {
  padding: 7px 11px;
  border: 1px solid #dce8f8;
  border-radius: 999px;
  background: #f8fbff;
}

.header-center i {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 4px;
  border-radius: 50%;
  background: #30a46c;
  box-shadow: 0 0 0 4px rgba(48, 164, 108, 0.1);
}

.header-actions {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 10px;
}

.role-pill {
  padding: 7px 10px;
  border-radius: 999px;
  color: #61738a;
  background: #edf2f8;
  font-size: 12px;
  font-weight: 700;
}

.admin-button {
  height: 38px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 16px;
  border: 1px solid #c9d9ef;
  border-radius: 10px;
  color: #2c5fb7;
  background: #fff;
  font-weight: 700;
  cursor: pointer;
  transition: 0.18s ease;
}

.admin-button:hover {
  border-color: #8db1ed;
  transform: translateY(-1px);
  box-shadow: 0 7px 18px rgba(53, 111, 221, 0.12);
}

.library-intro {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.7fr);
  align-items: end;
  gap: 36px;
  padding: 22px 34px 20px;
}

.eyebrow {
  display: block;
  margin-bottom: 7px;
  color: #4a72ad;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.2em;
}

.library-intro h1 {
  margin: 0;
  font-family: "Songti SC", "STSong", serif;
  font-size: clamp(24px, 2.2vw, 36px);
  font-weight: 800;
  letter-spacing: 0.025em;
}

.library-intro p {
  max-width: 520px;
  margin: 0;
  color: #63758c;
  font-size: 13px;
  line-height: 1.85;
}

.library-frame-wrap {
  min-height: 0;
  margin: 0 24px 20px;
  overflow: hidden;
  border: 1px solid #d6e2f2;
  border-radius: 18px;
  background: #eef5ff;
  box-shadow: 0 20px 60px rgba(40, 73, 116, 0.1);
}

.library-frame {
  width: 100%;
  height: 100%;
  display: block;
  border: 0;
}

.access-toast {
  position: fixed;
  right: 28px;
  bottom: 28px;
  z-index: 10;
  padding: 12px 16px;
  border: 1px solid #cfe0f7;
  border-radius: 12px;
  color: #315c96;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 12px 36px rgba(36, 81, 142, 0.16);
  font-size: 13px;
}

@media (max-width: 900px) {
  .library-page {
    grid-template-rows: 64px auto minmax(0, 1fr);
  }

  .library-header {
    grid-template-columns: 1fr auto;
    padding: 0 16px;
  }

  .header-center {
    display: none;
  }

  .library-intro {
    grid-template-columns: 1fr;
    gap: 8px;
    padding: 18px 18px 16px;
  }

  .library-frame-wrap {
    margin: 0 10px 10px;
    border-radius: 13px;
  }
}

@media (max-width: 560px) {
  .brand small,
  .role-pill,
  .library-intro p {
    display: none;
  }

  .brand strong {
    font-size: 16px;
  }

  .admin-button {
    width: 38px;
    padding: 0;
    justify-content: center;
    font-size: 0;
  }
}
</style>
