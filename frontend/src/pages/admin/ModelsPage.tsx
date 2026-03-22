import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../api/client'

interface Model {
  id: string
  model_name: string
  model_type: string
  provider: string
  capabilities: string[]
  default_for_stages: number[]
  is_active: boolean
  added_by: string
  client_id: string | null
}

export default function ModelsPage() {
  const qc = useQueryClient()
  const [showHealth, setShowHealth] = useState(false)

  const { data: models } = useQuery({
    queryKey: ['models'],
    queryFn: () => api.get('/admin/models').then(r => r.data as Model[]),
  })

  const { data: health } = useQuery({
    queryKey: ['model-health'],
    queryFn: () => api.get('/admin/models/health').then(r => r.data),
    enabled: showHealth,
  })

  const deactivate = useMutation({
    mutationFn: (id: string) => api.delete(`/admin/models/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['models'] }),
  })

  const typeColors: Record<string, string> = {
    llm: 'bg-indigo-100 text-indigo-700',
    ocr: 'bg-blue-100 text-blue-700',
    vision: 'bg-purple-100 text-purple-700',
    kb: 'bg-green-100 text-green-700',
    classification: 'bg-amber-100 text-amber-700',
    embedding: 'bg-sky-100 text-sky-700',
    custom: 'bg-gray-100 text-gray-700',
  }

  return (
    <div className="p-4 lg:p-6 max-w-[1400px]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Model Registry</h2>
          <p className="text-sm text-gray-500">Manage AI/ML models — Iksula, third-party, and client-provided</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowHealth(!showHealth)} className="px-3 py-2 bg-white border border-gray-200 text-xs font-medium rounded-lg hover:bg-gray-50">{showHealth ? 'Hide' : 'Check'} Health</button>
          <button className="px-3 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700">+ Register Model</button>
        </div>
      </div>

      {/* Health status */}
      {showHealth && health && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
          <div className="flex items-center gap-2 mb-3">
            <span className={`w-2 h-2 rounded-full ${health.demo_mode ? 'bg-amber-500' : 'bg-green-500'}`} />
            <span className="text-xs font-medium">{health.demo_mode ? 'Demo Mode (mock responses)' : 'Production Mode (real API calls)'}</span>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {health.providers?.map((p: Record<string, unknown>, i: number) => (
              <div key={i} className="p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold">{p.provider as string}</span>
                  <span className={`w-2 h-2 rounded-full ${p.configured ? (p.healthy ? 'bg-green-500' : 'bg-amber-500') : 'bg-gray-300'}`} />
                </div>
                {String(p.model) !== 'undefined' && <p className="text-[10px] text-gray-500">{String(p.model)}</p>}
                {String(p.key_preview) !== 'undefined' && <p className="text-[10px] text-gray-400 font-mono">{String(p.key_preview)}</p>}
                {!p.configured && <p className="text-[10px] text-red-500">Not configured</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Model cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {models?.map(model => (
          <div key={model.id} className={`bg-white rounded-xl border border-gray-200 p-5 ${!model.is_active ? 'opacity-50' : ''}`}>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-bold text-gray-900">{model.model_name}</h4>
              <span className={`w-2 h-2 rounded-full ${model.is_active ? 'bg-green-500' : 'bg-gray-300'}`} />
            </div>
            <div className="space-y-1.5 text-[10px] text-gray-500 mb-3">
              <div className="flex items-center gap-2">
                <span>Type:</span>
                <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${typeColors[model.model_type] || 'bg-gray-100'}`}>{model.model_type}</span>
              </div>
              <p>Provider: <span className="font-medium text-gray-700 capitalize">{model.provider}</span></p>
              {model.default_for_stages.length > 0 && (
                <p>Default for: <span className="font-medium text-gray-700">Stage {model.default_for_stages.join(', ')}</span></p>
              )}
              {model.capabilities.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1">
                  {model.capabilities.map(c => <span key={c} className="px-1.5 py-0.5 bg-gray-100 rounded text-[9px]">{c}</span>)}
                </div>
              )}
            </div>
            <div className="flex gap-2 pt-2 border-t border-gray-100">
              <button className="text-[10px] text-blue-600 font-medium hover:underline">Configure</button>
              <button className="text-[10px] text-gray-500 hover:underline">Test</button>
              {model.is_active && <button onClick={() => deactivate.mutate(model.id)} className="text-[10px] text-red-500 hover:underline ml-auto">Deactivate</button>}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
