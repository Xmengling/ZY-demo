import { defineStore } from 'pinia'
import { authApi } from '../api'

let expiryTimer = null

function tokenExpiresAt(token) {
  try {
    const [, payload] = token.split('.')
    const { exp } = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')))
    return Number.isFinite(exp) ? exp * 1000 : null
  } catch {
    return null
  }
}

function loginUrl() {
  const redirect = `${location.pathname}${location.search}${location.hash}`
  return `/login?redirect=${encodeURIComponent(redirect)}`
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null')
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    isAdmin: (s) => s.user?.role === 'admin'
  },
  actions: {
    async login(username, password) {
      const data = await authApi.login({ username, password })
      this._save(data)
      return data
    },
    async register(username, password, fullName) {
      const data = await authApi.register({ username, password, full_name: fullName })
      this._save(data)
      return data
    },
    async refreshUser() {
      if (!this.token) return null
      try {
        const user = await authApi.me()
        this.user = user
        localStorage.setItem('user', JSON.stringify(user))
        return user
      } catch {
        return null
      }
    },
    _save(data) {
      this.token = data.access_token
      this.user = data.user
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('user', JSON.stringify(data.user))
      this.scheduleExpiry()
    },
    scheduleExpiry() {
      clearTimeout(expiryTimer)
      const expiresAt = tokenExpiresAt(this.token)
      if (!expiresAt) return
      const delay = expiresAt - Date.now()
      if (delay <= 0) {
        this.expire()
        return
      }
      expiryTimer = window.setTimeout(() => this.expire(), delay)
    },
    expire() {
      this.logout()
      if (location.pathname !== '/login') location.replace(loginUrl())
    },
    logout() {
      clearTimeout(expiryTimer)
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    }
  }
})
