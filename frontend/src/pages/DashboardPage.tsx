import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import { useClientStore } from '../stores/clientStore'
import { useReviewStats } from '../api/review'

export default function DashboardPage() {
  const navigate = useNavigate()
  const clientId = useClientStore(s => s.activeClientId)
  const clientName = useClientStore(s => s.activeClient?.name)

  const { data: stats } = useQuery({
    queryKey: ['dashboard-stats', clientId],
    queryFn: () => api.get('/admin/dashboard/stats', { params: clientId ? { client_id: clientId } : {} }).then(r => r.data),
  })

  const { data: reviewStats } = useReviewStats()

  const kpis = [
    { label: 'Total Records', value: stats?.total_products ?? '—', color: 'text-gray-900' },
    { label: 'In Pipeline', value: stats?.in_pipeline ?? '—', color: 'text-blue-600' },
    { label: 'Awaiting Review', value: stats?.awaiting_review ?? '—', color: 'text-amber-600' },
    { label: 'Published', value: stats?.published ?? '—', color: 'text-green-600' },
  ]

  return (
    <div className="p-4 lg:p-6 max-w-[1400px]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Dashboard</h2>
          <p className="text-sm text-gray-500">Pipeline overview for <span className="font-medium">{clientName || 'all clients'}</span></p>
        </div>
        <button onClick={() => navigate('/upload')} className="px-3 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700">+ Upload Batch</button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        {kpis.map(s => (
          <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-4">
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
            <p className="text-xs text-gray-500 mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Review summary */}
        {reviewStats && (
          <div className="bg-white rounded-xl border border-gray-200">
            <div className="px-4 py-3 border-b border-gray-100 flex justify-between items-center">
              <h3 className="text-sm font-semibold text-gray-900">Review Queue Summary</h3>
              <button onClick={() => navigate('/review')} className="text-xs text-blue-600 font-medium hover:underline">View queue</button>
            </div>
            <div className="p-4 grid grid-cols-3 gap-3">
              <div className="text-center p-3 bg-red-50 rounded-lg"><span className="text-lg font-bold text-red-600">{reviewStats.low_confidence}</span><p className="text-[9px] text-red-500">Low Conf</p></div>
              <div className="text-center p-3 bg-amber-50 rounded-lg"><span className="text-lg font-bold text-amber-600">{reviewStats.needs_review}</span><p className="text-[9px] text-amber-500">Review</p></div>
              <div className="text-center p-3 bg-green-50 rounded-lg"><span className="text-lg font-bold text-green-600">{reviewStats.human_approved + reviewStats.human_edited}</span><p className="text-[9px] text-green-500">Done</p></div>
            </div>
          </div>
        )}

        {/* Quick actions */}
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-100">
            <h3 className="text-sm font-semibold text-gray-900">Quick Actions</h3>
          </div>
          <div className="p-4 space-y-2">
            <button onClick={() => navigate('/upload')} className="w-full flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 text-left">
              <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
              <div><p className="text-xs font-medium text-gray-900">Upload Batch</p><p className="text-[10px] text-gray-400">Process new supplier data</p></div>
            </button>
            <button onClick={() => navigate('/review')} className="w-full flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 text-left">
              <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              <div><p className="text-xs font-medium text-gray-900">Review Queue</p><p className="text-[10px] text-gray-400">{reviewStats?.total_pending || 0} items pending</p></div>
            </button>
            <button onClick={() => navigate('/published')} className="w-full flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 text-left">
              <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8" /></svg>
              <div><p className="text-xs font-medium text-gray-900">Published Records</p><p className="text-[10px] text-gray-400">View and export</p></div>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
