import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'

interface AuditEntry {
  id: string
  product_name: string | null
  model_number: string | null
  layer: string | null
  field_name: string | null
  action: string
  old_value: string | null
  new_value: string | null
  actor_type: string
  actor_id: string | null
  model_name: string | null
  reason: string | null
  created_at: string
}

const ACTION_COLORS: Record<string, string> = {
  extracted: 'bg-blue-50 text-blue-600',
  normalised: 'bg-blue-50 text-blue-600',
  enriched: 'bg-green-50 text-green-600',
  validated: 'bg-green-50 text-green-600',
  transformed: 'bg-purple-50 text-purple-600',
  approved: 'bg-green-50 text-green-700',
  edited: 'bg-amber-50 text-amber-700',
  rejected: 'bg-red-50 text-red-600',
  published: 'bg-purple-50 text-purple-700',
  mapping_corrected: 'bg-indigo-50 text-indigo-600',
  dq_overridden: 'bg-orange-50 text-orange-600',
}

export default function AuditPage() {
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [page, setPage] = useState(0)

  const { data } = useQuery({
    queryKey: ['audit', filters, page],
    queryFn: () => api.get('/admin/audit', { params: { ...filters, limit: 50, offset: page * 50 } }).then(r => r.data),
  })

  const items = (data?.items as AuditEntry[]) || []
  const total = data?.total || 0

  return (
    <div className="p-4 lg:p-6 max-w-[1400px]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Audit Logs</h2>
          <p className="text-sm text-gray-500">{total} total entries</p>
        </div>
        <button className="px-3 py-2 bg-white border border-gray-200 text-xs font-medium rounded-lg hover:bg-gray-50">Export Logs</button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-3 mb-4 flex flex-wrap gap-2">
        <select onChange={e => setFilters(f => e.target.value ? { ...f, action: e.target.value } : (() => { const n = { ...f }; delete n.action; return n })())} className="text-xs bg-gray-50 border border-gray-200 rounded px-2 py-1 outline-none">
          <option value="">All actions</option>
          <option value="extracted">Extracted</option>
          <option value="enriched">Enriched</option>
          <option value="approved">Approved</option>
          <option value="edited">Edited</option>
          <option value="rejected">Rejected</option>
          <option value="published">Published</option>
          <option value="mapping_corrected">Mapping corrected</option>
        </select>
        <select onChange={e => setFilters(f => e.target.value ? { ...f, layer: e.target.value } : (() => { const n = { ...f }; delete n.layer; return n })())} className="text-xs bg-gray-50 border border-gray-200 rounded px-2 py-1 outline-none">
          <option value="">All layers</option>
          <option value="raw">Raw (Layer 0)</option>
          <option value="iksula">Iksula (Layer 1)</option>
          <option value="client">Client (Layer 2)</option>
          <option value="mapping">Mapping</option>
          <option value="config">Config</option>
        </select>
      </div>

      {/* Log entries */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="divide-y divide-gray-50">
          {items.map(entry => (
            <div key={entry.id} className="px-4 py-3 flex items-start gap-3 text-xs">
              <span className="text-[10px] text-gray-400 w-32 flex-shrink-0 pt-0.5">{new Date(entry.created_at).toLocaleString()}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${ACTION_COLORS[entry.action] || 'bg-gray-100 text-gray-600'}`}>{entry.action}</span>
                  {entry.field_name && <span className="font-medium text-gray-700">{entry.field_name}</span>}
                  {entry.product_name && <span className="text-gray-400">· {entry.product_name} {entry.model_number ? `(${entry.model_number})` : ''}</span>}
                </div>
                {entry.old_value && entry.new_value && (
                  <p className="text-[10px] text-gray-400 mt-0.5">"{entry.old_value}" → "{entry.new_value}"</p>
                )}
                {entry.new_value && !entry.old_value && (
                  <p className="text-[10px] text-gray-400 mt-0.5">→ {entry.new_value}</p>
                )}
                <div className="flex gap-2 mt-0.5 text-[10px] text-gray-400">
                  {entry.actor_id && <span>by {entry.actor_id}</span>}
                  {entry.model_name && <span>model: {entry.model_name}</span>}
                  {entry.layer && <span>layer: {entry.layer}</span>}
                </div>
                {entry.reason && <p className="text-[10px] text-gray-500 mt-0.5">Reason: {entry.reason}</p>}
              </div>
            </div>
          ))}
          {items.length === 0 && (
            <div className="p-8 text-center text-sm text-gray-400">No audit entries found</div>
          )}
        </div>

        {/* Pagination */}
        {total > 50 && (
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-100 flex items-center justify-between rounded-b-xl">
            <span className="text-[10px] text-gray-500">Page {page + 1} of {Math.ceil(total / 50)}</span>
            <div className="flex gap-1">
              <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} className="px-2.5 py-1 bg-white border border-gray-200 text-[10px] rounded hover:bg-gray-50 disabled:opacity-50">Prev</button>
              <button onClick={() => setPage(p => p + 1)} disabled={(page + 1) * 50 >= total} className="px-2.5 py-1 bg-white border border-gray-200 text-[10px] rounded hover:bg-gray-50 disabled:opacity-50">Next</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
