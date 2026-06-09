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
    ElMessage.error(typeof msg === 'string' ? msg : '请求失败')
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
  listSessions: () => api.get('/v1/consult/sessions'),
  symptomPresets: () => api.get('/v1/consult/symptom-presets'),
  updateModuleHints: (moduleKey, data) => api.put(`/v1/consult/module-hints/${moduleKey}`, data),
  getSession: (id) => api.get(`/v1/consult/sessions/${id}`),
  createSession: (data) => api.post('/v1/consult/sessions', data),
  saveIntake: (id, data) => api.patch(`/v1/consult/sessions/${id}/intake`, data),
  deleteSession: (id) => api.delete(`/v1/consult/sessions/${id}`),
  chat: (data) => api.post('/v1/consult/chat', data)
}

export const knowledgeApi = {
  list: ({ category, page = 1, pageSize = 20 } = {}) =>
    api.get('/v1/knowledge', {
      params: {
        category: category || undefined,
        page,
        page_size: pageSize
      }
    }),
  categories: () => api.get('/v1/knowledge/categories'),
  createCategory: (name) => api.post('/v1/knowledge/categories', { name }),
  renameCategory: (oldName, newName) =>
    api.patch('/v1/knowledge/categories', { old_name: oldName, new_name: newName }),
  search: (q, k = 5) => api.get('/v1/knowledge/search', { params: { q, k } }),
  create: (data) => api.post('/v1/knowledge', data),
  upload: (file, category, chunk) => {
    const form = buildUploadForm(file, category, chunk)
    return api.post('/v1/knowledge/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000
    })
  },
  preview: (file, category, chunk) => {
    const form = buildUploadForm(file, category, chunk)
    return api.post('/v1/knowledge/preview', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000
    })
  },
  sources: () => api.get('/v1/knowledge/sources'),
  deleteSource: (source) => api.delete('/v1/knowledge/source', { params: { source } }),
  deleteCategory: (category) => api.delete('/v1/knowledge/category', { params: { category } })
}

function buildUploadForm(file, category, chunk = {}) {
  const form = new FormData()
  form.append('file', file)
  form.append('category', category || '上传资料')
  form.append('chunk_strategy', chunk.strategy || 'fixed')
  form.append('chunk_size', chunk.size ?? 600)
  form.append('chunk_overlap', chunk.overlap ?? 100)
  form.append('separators', chunk.separators || '')
  return form
}

export default api
