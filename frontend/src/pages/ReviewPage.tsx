import { useState } from 'react'
import {
  useReviewQueue, useReviewProductCard, useReviewStats,
  useBulkApprove, useEditAndApprove,
  type ReviewItem,
} from '../api/review'

const SOURCE_BADGE: Record<string, string> = {
  kb: 'bg-green-50 text-green-600',
  raw_normalised: 'bg-blue-50 text-blue-600',
  ocr: 'bg-blue-50 text-blue-600',
  vision: 'bg-purple-50 text-purple-600',
  llm: 'bg-indigo-50 text-indigo-600',
  web_google: 'bg-sky-50 text-sky-600',
  web_marketplace: 'bg-orange-50 text-orange-600',
  human: 'bg-gray-100 text-gray-700',
}

export default function ReviewPage() {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [activeProductId, setActiveProductId] = useState<string | null>(null)
  const [editingField, setEditingField] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [filters, setFilters] = useState<Record<string, string | number>>({})

  const { data: queue, isLoading } = useReviewQueue(filters)
  const { data: stats } = useReviewStats()
  const { data: productCard } = useReviewProductCard(activeProductId)
  const bulkApprove = useBulkApprove()
  const editAndApprove = useEditAndApprove()

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds)
    next.has(id) ? next.delete(id) : next.add(id)
    setSelectedIds(next)
  }

  const toggleAll = () => {
    if (selectedIds.size === (queue?.length || 0)) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(queue?.map(q => q.id)))
    }
  }

  const handleBulkApprove = () => {
    if (selectedIds.size > 0) {
      bulkApprove.mutate(Array.from(selectedIds))
      setSelectedIds(new Set())
    }
  }

  const handleEdit = (fieldId: string, value: string) => {
    editAndApprove.mutate({ fieldId, value })
    setEditingField(null)
  }

  const startEdit = (item: ReviewItem) => {
    setEditingField(item.id)
    setEditValue(item.value || '')
  }

  return (
    <div className="p-4 lg:p-6 max-w-[1400px]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Review Queue</h2>
          <p className="text-sm text-gray-500">{stats?.total_pending || 0} items awaiting review</p>
        </div>
        {selectedIds.size > 0 && (
          <button
            onClick={handleBulkApprove}
            className="px-4 py-2 bg-green-600 text-white text-xs font-semibold rounded-lg hover:bg-green-700"
          >
            Approve {selectedIds.size} Selected
          </button>
        )}
      </div>

      {/* Stats cards */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 mb-6">
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 text-center">
            <span className="text-lg font-bold text-purple-700">{stats.must_fix}</span>
            <p className="text-[10px] text-purple-500">Must Fix</p>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-center">
            <span className="text-lg font-bold text-red-600">{stats.low_confidence}</span>
            <p className="text-[10px] text-red-500">Low Conf</p>
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-center">
            <span className="text-lg font-bold text-amber-600">{stats.needs_review}</span>
            <p className="text-[10px] text-amber-500">Review</p>
          </div>
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-center">
            <span className="text-lg font-bold text-green-600">{stats.auto_approved}</span>
            <p className="text-[10px] text-green-500">Auto OK</p>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
            <span className="text-lg font-bold text-blue-600">{stats.human_approved}</span>
            <p className="text-[10px] text-blue-500">Approved</p>
          </div>
          <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3 text-center">
            <span className="text-lg font-bold text-indigo-600">{stats.human_edited}</span>
            <p className="text-[10px] text-indigo-500">Edited</p>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-center">
            <span className="text-lg font-bold text-gray-700">{stats.total_pending}</span>
            <p className="text-[10px] text-gray-500">Pending</p>
          </div>
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Left: Review Queue List */}
        <div className="lg:w-1/2">
          {/* Filters */}
          <div className="bg-white rounded-xl border border-gray-200 p-3 mb-4 flex flex-wrap gap-2">
            <select
              className="text-xs bg-gray-50 border border-gray-200 rounded-lg px-2 py-1.5 outline-none"
              onChange={(e) => setFilters(f => e.target.value ? { ...f, priority: e.target.value } : (delete f.priority, { ...f }))}
            >
              <option value="">All priorities</option>
              <option value="must_fix">Must fix</option>
              <option value="low_confidence">Low confidence</option>
              <option value="needs_review">Needs review</option>
            </select>
            <select
              className="text-xs bg-gray-50 border border-gray-200 rounded-lg px-2 py-1.5 outline-none"
              onChange={(e) => setFilters(f => e.target.value ? { ...f, stage: Number(e.target.value) } : (delete f.stage, { ...f }))}
            >
              <option value="">All stages</option>
              {[1, 2, 3, 4, 5, 6, 7].map(s => <option key={s} value={s}>Stage {s}</option>)}
            </select>
          </div>

          {/* Queue items */}
          <div className="bg-white rounded-xl border border-gray-200">
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" className="w-3.5 h-3.5 rounded border-gray-300" onChange={toggleAll} checked={selectedIds.size > 0 && selectedIds.size === queue?.length} />
                <span className="text-xs text-gray-500">Select all</span>
              </label>
              {selectedIds.size > 0 && (
                <button onClick={handleBulkApprove} className="text-[10px] text-green-600 font-medium hover:underline">
                  Approve {selectedIds.size}
                </button>
              )}
            </div>

            {isLoading ? (
              <div className="p-8 text-center"><span className="text-sm text-gray-400">Loading...</span></div>
            ) : !queue?.length ? (
              <div className="p-8 text-center">
                <span className="text-sm text-gray-400">No items to review — all caught up!</span>
              </div>
            ) : (
              <div className="divide-y divide-gray-50 max-h-[600px] overflow-y-auto">
                {queue.map((item) => {
                  const isActive = activeProductId === item.product_id
                  const isEditing = editingField === item.id
                  const confColor = item.confidence < 60 ? 'text-red-600 bg-red-50' : item.confidence < 85 ? 'text-amber-600 bg-amber-50' : 'text-green-600 bg-green-50'

                  return (
                    <div
                      key={item.id}
                      className={`px-4 py-3 cursor-pointer transition ${isActive ? 'bg-blue-50/50 border-l-4 border-blue-500' : 'hover:bg-gray-50 border-l-4 border-transparent'}`}
                      onClick={() => setActiveProductId(item.product_id)}
                    >
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          className="w-3.5 h-3.5 rounded border-gray-300 mt-0.5 flex-shrink-0"
                          checked={selectedIds.has(item.id)}
                          onChange={(e) => { e.stopPropagation(); toggleSelect(item.id) }}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-semibold text-gray-900">{item.attribute_name}</span>
                            {!isEditing && item.value && (
                              <span className="text-xs text-gray-600 truncate max-w-[120px]">{item.value}{item.unit ? ` ${item.unit}` : ''}</span>
                            )}
                            <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${confColor}`}>{item.confidence}%</span>
                          </div>
                          <p className="text-[10px] text-gray-400 mt-0.5 truncate">
                            {item.product_name || 'Unknown'} · Stage {item.stage}
                          </p>

                          {/* Inline edit */}
                          {isEditing && (
                            <div className="flex items-center gap-2 mt-2" onClick={e => e.stopPropagation()}>
                              <input
                                type="text"
                                value={editValue}
                                onChange={e => setEditValue(e.target.value)}
                                className="flex-1 px-2 py-1.5 border border-blue-300 rounded text-xs outline-none focus:ring-1 focus:ring-blue-400"
                                autoFocus
                                onKeyDown={e => { if (e.key === 'Enter') handleEdit(item.id, editValue); if (e.key === 'Escape') setEditingField(null) }}
                              />
                              <button onClick={() => handleEdit(item.id, editValue)} className="px-2 py-1.5 bg-blue-600 text-white text-[10px] font-medium rounded">Save</button>
                              <button onClick={() => setEditingField(null)} className="text-[10px] text-gray-500">Cancel</button>
                            </div>
                          )}
                        </div>

                        {/* Quick actions */}
                        {!isEditing && (
                          <div className="flex items-center gap-1 flex-shrink-0" onClick={e => e.stopPropagation()}>
                            <button
                              onClick={() => bulkApprove.mutate([item.id])}
                              className="px-2 py-1 bg-green-50 text-green-700 text-[10px] font-medium rounded hover:bg-green-100"
                              title="Approve"
                            >✓</button>
                            <button
                              onClick={() => startEdit(item)}
                              className="px-2 py-1 bg-blue-50 text-blue-700 text-[10px] font-medium rounded hover:bg-blue-100"
                              title="Edit"
                            >✎</button>
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right: Product Card (side-by-side) */}
        <div className="lg:w-1/2">
          {productCard ? (
            <div className="bg-white rounded-xl border border-gray-200 sticky top-4">
              {/* Product header */}
              <div className="px-4 py-4 border-b border-gray-100">
                <div className="flex gap-4">
                  {/* Image placeholder */}
                  <div className="w-20 h-20 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <svg className="w-8 h-8 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-bold text-gray-900">{productCard.product_name}</h3>
                    <p className="text-[10px] text-gray-400 mt-0.5">{productCard.model_number} · {productCard.brand}</p>
                    {productCard.product_title && (
                      <p className="text-xs text-gray-600 mt-1 italic">"{productCard.product_title}"</p>
                    )}
                    <div className="flex gap-2 mt-2">
                      <span className="px-1.5 py-0.5 bg-green-100 text-green-700 text-[9px] font-medium rounded">{productCard.auto_approved} auto</span>
                      <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 text-[9px] font-medium rounded">{productCard.needs_review} review</span>
                      <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 text-[9px] font-medium rounded">{productCard.human_approved} done</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Attributes table — simple, scannable */}
              <div className="max-h-[500px] overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="text-left px-4 py-2 font-medium text-gray-500 w-1/3">Attribute</th>
                      <th className="text-left px-4 py-2 font-medium text-gray-500">Value</th>
                      <th className="text-center px-2 py-2 font-medium text-gray-500 w-12">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {productCard.attributes.map((attr) => {
                      const statusIcon = attr.status === 'auto_approved' || attr.status === 'human_approved'
                        ? <span className="w-4 h-4 rounded-full bg-green-100 flex items-center justify-center"><svg className="w-2.5 h-2.5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg></span>
                        : attr.status === 'human_edited'
                          ? <span className="w-4 h-4 rounded-full bg-blue-100 flex items-center justify-center text-[8px] text-blue-600">✎</span>
                          : attr.status === 'needs_review' || attr.status === 'low_confidence'
                            ? <span className="w-4 h-4 rounded-full bg-amber-100 flex items-center justify-center"><span className="w-1.5 h-1.5 rounded-full bg-amber-500" /></span>
                            : <span className="w-4 h-4 rounded-full bg-gray-100" />

                      return (
                        <tr key={attr.id} className={`${attr.status === 'needs_review' || attr.status === 'low_confidence' ? 'bg-amber-50/30' : ''}`}>
                          <td className="px-4 py-2 text-gray-600">
                            {attr.name}
                            {attr.mandatory && <span className="text-red-400 ml-0.5">*</span>}
                          </td>
                          <td className="px-4 py-2">
                            <div className="flex items-center gap-1.5">
                              <span className="font-medium text-gray-900">{attr.value || '—'}</span>
                              {attr.unit && <span className="text-gray-400">{attr.unit}</span>}
                              <span className={`px-1 py-0.5 rounded text-[8px] font-medium ${SOURCE_BADGE[attr.source] || 'bg-gray-100 text-gray-500'}`}>
                                {attr.source === 'raw_normalised' ? 'OCR' : attr.source === 'web_google' ? 'Web' : attr.source === 'web_marketplace' ? 'Amz' : attr.source.toUpperCase()}
                              </span>
                            </div>
                          </td>
                          <td className="px-2 py-2 text-center">{statusIcon}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              {/* Quick description preview */}
              {productCard.short_description && (
                <div className="px-4 py-3 border-t border-gray-100 bg-gray-50/50 rounded-b-xl">
                  <p className="text-[10px] text-gray-400 font-medium mb-1">Description</p>
                  <p className="text-xs text-gray-600">{productCard.short_description}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center sticky top-4">
              <svg className="w-12 h-12 mx-auto text-gray-200 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
              <p className="text-sm text-gray-400">Click an item to see the product card</p>
              <p className="text-xs text-gray-300 mt-1">Image + title + all attributes side by side</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
