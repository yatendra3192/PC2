import api from './client'

export interface User {
  id: string
  email: string
  full_name: string | null
  role: 'admin' | 'reviewer' | 'viewer'
  client_id: string | null
  is_active: boolean
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export const authApi = {
  login: (email: string, password: string) =>
    api.post<LoginResponse>('/auth/login', { email, password }),

  getMe: () => api.get<User>('/auth/me'),

  forgotPassword: (email: string) =>
    api.post('/auth/forgot-password', null, { params: { email } }),
}
