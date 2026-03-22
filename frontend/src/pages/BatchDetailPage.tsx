import { useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import { usePipelineStore } from '../stores/pipelineStore'
import { useBatchProgress } from '../hooks/useRealtimeUpdates'
import { useBulkApprove } from '../api/review'
import { useState } from 'react'

interface BatchProduct {
  id: string
  product_name: string | null
  model_number: string | null
  current_stage: number
  status: string
  completeness_pct: number | null
  overall_confidence: number | null
  review_count: number
}

const STAGE_LABELS = ['', 'Ingest', 'Classify', 'Dedup', 'Enrich', 'Validate', 'Transform', 'Review']
const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-600',
  processing: 'bg-blue-100 text-blue-700',
  review: 'bg-amber-100 text-amber-700',
  published: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-600',
}

export default function BatchDetailPage() {
  const [params] = useSearchParams()
  const batchId = params.get('id')
  const navigate = useNavigate()
  const setProduct = usePipelineStore(s => s.setProduct)
  const bulkApprove = useBulkApprove()
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  useBatchProgress(batchId)

  const { data: batch } = useQuery({
    queryKey: ['batch', batchId],
    queryFn: () => api.get(`/batches/${batchId}`).then(r => r.data),
    enabled: !!batchId,
    refetchInterval: 5000,
  })

  const products = (batch?.products as BatchProduct[]) || []
  const processing = products.filter(p => p.status === 'processing').length
  const review = products.filter(p => p.status === 'review').length
  const published = products.filter(p => p.status === 'published').length
  const total = products.length

  const openProduct = (productId: string) => {
    setProduct(productId)
    navigate('/pipeline')
  }

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds)
    next.has(id) ? next.delete(id) : next.add(id)
    setSelectedIds(next)
  }

  if (!batchId) return <div className="p-6 text-gray-400">No batch selected</div>

  return (
    <div className="p-4 lg:p-6 max-w-[1400px]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <button onClick={() => navigate('/upload')} className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1 mb-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>Back to uploads
          </button>
          <h2 className="text-xl font-bold text-gray-900">{batch?.file_name || 'Batch Detail'}</h2>
          <p className="text-sm text-gray-500">{total} products · {batch?.status}</p>
        </div>
      </div>

      {/* Progress bar */}
      {batch?.status === 'processing' && (
        <div className="bg-white rounded-xl border border-blue-200 p-4 mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-blue-700">Processing batch...</span>
            <span className="text-xs font-bold text-blue-700">{batch?.processed_count || 0} / {total}</span>
          </div>
          <div className="w-full bg-blue-100 rounded-full h-2">
            <div className="bg-blue-600 h-2 rounded-full transition-all" style={{ width: `${total > 0 ? ((batch?.processed_count || 0) / total) * 100 : 0}%` }} />
          </div>
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <div className="bg-gray-50 rounded-lg p-3 text-center"><span className="text-lg font-bold text-gray-700">{total}</span><p className="text-[10px] text-gray-500">Total</p></div>
        <div className="bg-blue-50 rounded-lg p-3 text-center"><span className="text-lg font-bold text-blue-700">{processing}</span><p className="text-[10px] text-blue-500">Processing</p></div>
        <div className="bg-amber-50 rounded-lg p-3 text-center"><span className="text-lg font-bold text-amber-700">{review}</span><p className="text-[10px] text-amber-500">Review</p></div>
        <div className="bg-green-50 rounded-lg p-3 text-center"><span className="text-lg font-bold text-green-700">{published}</span><p className="text-[10px] text-green-500">Published</p></div>
      </div>

      {/* Products table */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">Products in Batch</h3>
          {selectedIds.size > 0 && (
            <button className="px-3 py-1.5 bg-green-600 text-white text-xs font-medium rounded-lg hover:bg-green-700">
              Fast-track {selectedIds.size} items
            </button>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-4 py-2.5 font-medium text-gray-500 w-8"><input type="checkbox" className="w-3.5 h-3.5 rounded border-gray-300" /></th>
                <th className="text-left px-4 py-2.5 font-medium text-gray-500">Product</th>
                <th className="text-left px-4 py-2.5 font-medium text-gray-500 hidden md:table-cell">Model</th>
                <th className="text-left px-4 py-2.5 font-medium text-gray-500">Stage</th>
                <th className="text-left px-4 py-2.5 font-medium text-gray-500">Status</th>
                <th className="text-left px-4 py-2.5 font-medium text-gray-500 hidden lg:table-cell">Completeness</th>
                <th className="text-left px-4 py-2.5 font-medium text-gray-500 hidden md:table-cell">Review</th>
                <th className="text-right px-4 py-2.5 font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {products.map(p => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3"><input type="checkbox" className="w-3.5 h-3.5 rounded border-gray-300" checked={selectedIds.has(p.id)} onChange={() => toggleSelect(p.id)} /></td>
                  <td className="px-4 py-3 font-medium">{p.product_name || '—'}</td>
                  <td className="px-4 py-3 hidden md:table-cell text-gray-500">{p.model_number || '—'}</td>
                  <td className="px-4 py-3">
                    <span className="text-[10px] text-gray-600">{STAGE_LABELS[p.current_stage] || p.current_stage}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${STATUS_COLORS[p.status] || 'bg-gray-100'}`}>{p.status}</span>
                  </td>
                  <td className="px-4 py-3 hidden lg:table-cell">
                    {p.completeness_pct != null ? (
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-200 rounded-full h-1.5"><div className="bg-green-500 h-1.5 rounded-full" style={{ width: `${p.completeness_pct}%` }} /></div>
                        <span className="text-[10px] text-gray-500">{p.completeness_pct}%</span>
                      </div>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    {p.review_count > 0 ? (
                      <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-[10px] font-medium">{p.review_count} items</span>
                    ) : p.status === 'published' ? (
                      <span className="text-green-600 text-[10px]">Done</span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => openProduct(p.id)} className="text-blue-600 font-medium hover:underline">Open</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
