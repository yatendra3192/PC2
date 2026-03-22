import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../api/client'

interface Client {
  id: string
  name: string
  code: string
  is_active: boolean
  product_count: number
  published_count: number
  template_count: number
}

export default function ClientsPage() {
  const qc = useQueryClient()
  const [showAdd, setShowAdd] = useState(false)
  const [newName, setNewName] = useState('')
  const [newCode, setNewCode] = useState('')

  const { data: clients, isLoading } = useQuery({
    queryKey: ['clients'],
    queryFn: () => api.get<Client[]>('/clients').then(r => r.data),
  })

  const createMutation = useMutation({
    mutationFn: (data: { name: string; code: string }) => api.post('/clients', data).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clients'] })
      setShowAdd(false)
      setNewName('')
      setNewCode('')
    },
  })

  return (
    <div className="p-4 lg:p-6 max-w-[1400px]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Client Management</h2>
          <p className="text-sm text-gray-500">Manage retailer clients and their configurations</p>
        </div>
        <button onClick={() => setShowAdd(true)} className="px-3 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700">+ Add Client</button>
      </div>

      {/* Add Client Form */}
      {showAdd && (
        <div className="bg-white rounded-xl border border-blue-200 p-4 mb-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Add New Client</h3>
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1">
              <label className="text-xs text-gray-600 block mb-1">Client Name</label>
              <input type="text" value={newName} onChange={e => setNewName(e.target.value)} placeholder="e.g. Lowe's" className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm outline-none focus:border-blue-500" />
            </div>
            <div className="w-40">
              <label className="text-xs text-gray-600 block mb-1">Code</label>
              <input type="text" value={newCode} onChange={e => setNewCode(e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ''))} placeholder="e.g. lowes" className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm outline-none focus:border-blue-500" />
            </div>
            <div className="flex items-end gap-2">
              <button onClick={() => createMutation.mutate({ name: newName, code: newCode })} disabled={!newName || !newCode} className="px-4 py-2 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50">Create</button>
              <button onClick={() => setShowAdd(false)} className="px-4 py-2 bg-white border border-gray-200 text-xs font-medium rounded-lg">Cancel</button>
            </div>
          </div>
          {createMutation.isError && <p className="text-xs text-red-600 mt-2">Failed to create client. Code may already exist.</p>}
        </div>
      )}

      {/* Client Cards */}
      {isLoading ? (
        <div className="text-center p-8 text-sm text-gray-400">Loading clients...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {clients?.map(client => (
            <div key={client.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:border-gray-300 transition">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="text-sm font-bold text-gray-900">{client.name}</h3>
                  <p className="text-[10px] text-gray-400 mt-0.5">Code: {client.code}</p>
                </div>
                <span className={`w-2.5 h-2.5 rounded-full ${client.is_active ? 'bg-green-500' : 'bg-gray-300'}`} title={client.is_active ? 'Active' : 'Inactive'} />
              </div>
              <div className="grid grid-cols-3 gap-2 mb-4">
                <div className="text-center p-2 bg-gray-50 rounded-lg">
                  <span className="text-lg font-bold text-gray-700">{client.product_count}</span>
                  <p className="text-[9px] text-gray-500">Products</p>
                </div>
                <div className="text-center p-2 bg-green-50 rounded-lg">
                  <span className="text-lg font-bold text-green-700">{client.published_count}</span>
                  <p className="text-[9px] text-green-600">Published</p>
                </div>
                <div className="text-center p-2 bg-blue-50 rounded-lg">
                  <span className="text-lg font-bold text-blue-700">{client.template_count}</span>
                  <p className="text-[9px] text-blue-600">Templates</p>
                </div>
              </div>
              <div className="flex gap-2">
                <button className="flex-1 px-3 py-1.5 bg-gray-50 text-xs font-medium text-gray-700 rounded-lg hover:bg-gray-100">Pipeline Config</button>
                <button className="flex-1 px-3 py-1.5 bg-gray-50 text-xs font-medium text-gray-700 rounded-lg hover:bg-gray-100">Templates</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
