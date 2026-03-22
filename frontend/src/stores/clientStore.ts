import { create } from 'zustand'
import api from '../api/client'

export interface Client {
  id: string
  name: string
  code: string
  is_active: boolean
  product_count: number
  published_count: number
  template_count: number
}

interface ClientState {
  clients: Client[]
  activeClientId: string | null
  activeClient: Client | null
  isLoading: boolean
  loadClients: () => Promise<void>
  setActiveClient: (clientId: string) => void
}

export const useClientStore = create<ClientState>((set, get) => ({
  clients: [],
  activeClientId: localStorage.getItem('pc2_active_client'),
  activeClient: null,
  isLoading: false,

  loadClients: async () => {
    set({ isLoading: true })
    try {
      const { data } = await api.get<Client[]>('/clients')
      const activeId = get().activeClientId
      const active = activeId ? data.find(c => c.id === activeId) : data[0]

      set({
        clients: data,
        activeClientId: active?.id || data[0]?.id || null,
        activeClient: active || data[0] || null,
        isLoading: false,
      })

      if (active?.id) localStorage.setItem('pc2_active_client', active.id)
    } catch {
      set({ isLoading: false })
    }
  },

  setActiveClient: (clientId: string) => {
    const client = get().clients.find(c => c.id === clientId)
    set({ activeClientId: clientId, activeClient: client || null })
    localStorage.setItem('pc2_active_client', clientId)
  },
}))
