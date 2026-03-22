import { create } from 'zustand'

interface ToastState {
  message: string | null
  type: 'success' | 'error' | 'info'
  show: (message: string, type?: 'success' | 'error' | 'info') => void
  hide: () => void
}

export const useToast = create<ToastState>((set) => ({
  message: null,
  type: 'success',
  show: (message, type = 'success') => {
    set({ message, type })
    setTimeout(() => set({ message: null }), 3000)
  },
  hide: () => set({ message: null }),
}))

export default function Toast() {
  const { message, type } = useToast()

  if (!message) return null

  const colors = {
    success: 'bg-gray-900 text-white',
    error: 'bg-red-600 text-white',
    info: 'bg-blue-600 text-white',
  }

  const icons = {
    success: <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>,
    error: <svg className="w-4 h-4 text-red-200" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>,
    info: <svg className="w-4 h-4 text-blue-200" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  }

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 animate-in fade-in slide-in-from-bottom-4">
      <div className={`${colors[type]} px-4 py-2.5 rounded-xl shadow-lg text-xs font-medium flex items-center gap-2`}>
        {icons[type]}
        <span>{message}</span>
      </div>
    </div>
  )
}
