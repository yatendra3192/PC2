import { create } from 'zustand'
import { authApi, type User } from '../api/auth'

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  loadUser: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('pc2_token'),
  isAuthenticated: !!localStorage.getItem('pc2_token'),
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null })
    try {
      const { data } = await authApi.login(email, password)
      localStorage.setItem('pc2_token', data.access_token)
      set({ user: data.user, token: data.access_token, isAuthenticated: true, isLoading: false })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Login failed'
      set({ error: msg, isLoading: false })
      throw err
    }
  },

  logout: () => {
    localStorage.removeItem('pc2_token')
    set({ user: null, token: null, isAuthenticated: false })
  },

  loadUser: async () => {
    try {
      const { data } = await authApi.getMe()
      set({ user: data, isAuthenticated: true })
    } catch {
      localStorage.removeItem('pc2_token')
      set({ user: null, token: null, isAuthenticated: false })
    }
  },
}))
