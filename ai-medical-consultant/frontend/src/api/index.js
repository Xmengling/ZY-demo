import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({ baseURL: '/api', timeout: 60000 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err?.response?.data?.detail || err.message || '请求失败'
    if (err?.response?.status === 401) {
      localStorage.removeItem('token')
      if (location.pathname !== '/login') location.href = '/login'
    }
    if (!err?.config?.silent) {
      ElMessage.error(typeof msg === 'string' ? msg : '请求失败')
    }
    return Promise.reject(err)
  }
)

export const authApi = {
  login: (data) => api.post('/v1/user/login', data),
  register: (data) => api.post('/v1/user/register', data),
  me: () => api.get('/v1/user/me')
}

export const formulasApi = {
  list: () => api.get('/v1/formulas')
}

export const consultApi = {
  listSessions: (params = {}) => api.get('/v1/consult/sessions', { params }),
  listAiChats: () => api.get('/v1/consult/sessions', { params: { ai_chat: true } }),
  symptomPresets: () => api.get('/v1/consult/symptom-presets'),
  updateModuleHints: (moduleKey, data) => api.put(`/v1/consult/module-hints/${moduleKey}`, data),
  getSession: (id) => api.get(`/v1/consult/sessions/${id}`),
  createSession: (data) => api.post('/v1/consult/sessions', data),
  saveIntake: (id, data) => api.patch(`/v1/consult/sessions/${id}/intake`, data),
  deleteSession: (id) => api.delete(`/v1/consult/sessions/${id}`),
  autoFill: (data) => api.post('/v1/consult/auto-fill', data, { silent: true, timeout: 90000 }),
  chat: (data) => api.post('/v1/consult/chat', data),
  assistantChat: (data) => api.post('/v1/consult/assistant', data, { timeout: 180000 })
}

export const knowledgeApi = {
  listFiles: () => api.get('/v1/knowledge/files'),
  upload: (file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/v1/knowledge/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000
    })
  },
  deleteFile: (id) => api.delete(`/v1/knowledge/files/${id}`),
  previewFile: (id) => api.get(`/v1/knowledge/files/${id}/preview`)
}

export default api
