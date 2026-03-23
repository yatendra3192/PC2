import axios from 'axios'

// In production (Railway), VITE_API_URL points to the backend service URL
// In local dev, Vite proxy handles /api/* → localhost:8000
const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : '/api/v1'

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('pc2_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('pc2_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
