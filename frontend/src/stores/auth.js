import { defineStore } from 'pinia'
import api from '@/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    role: (state) => state.user?.role || '',
    isSuperAdmin: (state) => state.user?.role === 'super_admin',
    isUnitAdmin: (state) => state.user?.role === 'unit_admin',
    isAdmin: (state) => ['super_admin', 'unit_admin'].includes(state.user?.role),
    personId: (state) => state.user?.person_id,
    isFirstLogin: (state) => state.user?.first_login === true,
  },

  actions: {
    async login(username, password) {
      const data = await api.post('/auth/login', { username, password })
      this.token = data.access_token
      this.user = {
        username: data.username,
        role: data.role,
        user_id: data.user_id,
        first_login: data.first_login,
      }
      localStorage.setItem('token', this.token)
      localStorage.setItem('user', JSON.stringify(this.user))
      await this.fetchMe()
      return data
    },

    async register(payload) {
      const data = await api.post('/auth/register', payload)
      this.token = data.access_token
      this.user = {
        username: data.username,
        role: data.role,
        user_id: data.user_id,
        first_login: data.first_login,
      }
      localStorage.setItem('token', this.token)
      localStorage.setItem('user', JSON.stringify(this.user))
      await this.fetchMe()
      return data
    },

    async fetchMe() {
      try {
        const data = await api.get('/auth/me')
        this.user = { ...this.user, ...data }
        localStorage.setItem('user', JSON.stringify(this.user))
      } catch (e) {
        // 忽略
      }
    },

    async changeFirstPassword(newPassword) {
      await api.post('/auth/first-login-change-password', { new_password: newPassword })
      this.user.first_login = false
      localStorage.setItem('user', JSON.stringify(this.user))
    },

    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },
  },
})
