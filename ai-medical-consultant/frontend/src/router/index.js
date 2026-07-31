import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue'), meta: { public: true } },
  {
    path: '/cards',
    name: 'formulaLibrary',
    component: () => import('../views/FormulaLibrary.vue'),
    meta: { public: true }
  },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('../views/Home.vue') },
      { path: 'consult/:id?', name: 'consult', component: () => import('../views/Chat.vue') },
      { path: 'records', name: 'records', component: () => import('../views/Records.vue') },
      { path: 'knowledge', name: 'knowledge', component: () => import('../views/Knowledge.vue') },
      {
        path: 'formulas',
        name: 'formulas',
        component: () => import('../views/Formulas.vue'),
        meta: { admin: true }
      },
      { path: 'shanghan', name: 'shanghan', component: () => import('../views/Shanghan.vue') },
      { path: 'shanghan-study', name: 'shanghanStudy', component: () => import('../views/ShanghanStudy.vue') }
    ]
  }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  const verifiedAdminUser = to.meta.admin && auth.isLoggedIn
    ? await auth.refreshUser()
    : auth.user
  if (to.meta.admin && verifiedAdminUser?.role !== 'admin') {
    return { name: 'formulaLibrary', query: { access: 'viewer' } }
  }
  if (to.name === 'login' && auth.isLoggedIn) {
    return { name: 'home' }
  }
})

export default router
