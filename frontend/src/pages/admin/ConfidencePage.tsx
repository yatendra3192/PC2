import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../api/client'
import { useClientStore } from '../../stores/clientStore'

const STAGES = [
  { num: 1, label: 'Ingestion' }, { num: 2, label: 'Categorisation' },
  { num: 3, label: 'Deduplication' }, { num: 4, label: 'Enrichment' },
  { num: 5, label: 'Validation' }, { num: 6, label: 'Transform' },
]

export default function ConfidencePage() {
  const clientId = useClientStore(s => s.activeClientId)
  const clientName = useClientStore(s => s.activeClient?.name)
  const [activeStage, setActiveStage] = useState(1)
  const qc = useQueryClient()

  const { data: config } = useQuery({
    queryKey: ['confidence', clientId, activeStage],
    queryFn: () => api.get(`/admin/confidence/${clientId}/${activeStage}`).then(r => r.data),
    enabled: !!clientId,
  })

  const conf = config?.confidence || {}
  const [autoThreshold, setAutoThreshold] = useState(85)
  const [reviewThreshold, setReviewThreshold] = useState(60)

  useEffect(() => {
    if (conf.auto_approve_threshold) setAutoThreshold(conf.auto_approve_threshold)
    if (conf.needs_review_threshold) setReviewThreshold(conf.needs_review_threshold)
  }, [conf])

  const saveMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.put(`/admin/confidence/${clientId}/${activeStage}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['confidence'] }),
  })

  const sourceScores = conf.source_reliability_scores || {}
  const weights = conf.component_weights || {}

  return (
    <div className="p-4 lg:p-6 max-w-[1400px]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Confidence Configuration</h2>
          <p className="text-sm text-gray-500">Configure scoring logic per stage for <span className="font-medium">{clientName}</span></p>
        </div>
      </div>

      {/* Stage tabs */}
      <div className="flex gap-1 mb-6 overflow-x-auto">
        {STAGES.map(s => (
          <button key={s.num} onClick={() => setActiveStage(s.num)}
            className={`px-3 py-2 text-xs font-medium rounded-lg whitespace-nowrap ${activeStage === s.num ? 'bg-blue-600 text-white' : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
            Stage {s.num} — {s.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Thresholds */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Routing Thresholds</h3>
          <div className="space-y-5">
            <div>
              <div className="flex justify-between mb-1"><label className="text-xs text-gray-600">Auto-approve threshold</label><span className="text-xs font-bold text-green-700">{autoThreshold}</span></div>
              <input type="range" min={50} max={100} value={autoThreshold} onChange={e => setAutoThreshold(Number(e.target.value))} className="w-full h-1.5 bg-gray-200 rounded-full appearance-none cursor-pointer accent-blue-600" />
            </div>
            <div>
              <div className="flex justify-between mb-1"><label className="text-xs text-gray-600">Needs review threshold</label><span className="text-xs font-bold text-amber-600">{reviewThreshold}</span></div>
              <input type="range" min={30} max={95} value={reviewThreshold} onChange={e => setReviewThreshold(Number(e.target.value))} className="w-full h-1.5 bg-gray-200 rounded-full appearance-none cursor-pointer accent-blue-600" />
            </div>
          </div>
          <div className="mt-4 p-3 bg-blue-50 rounded-lg">
            <p className="text-[10px] text-blue-700"><strong>Preview:</strong> Score ≥{autoThreshold} → auto-approved. Score {reviewThreshold}–{autoThreshold - 1} → needs review. Score &lt;{reviewThreshold} → low confidence (high priority).</p>
          </div>
        </div>

        {/* Component weights */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Component Weights</h3>
          <div className="space-y-4">
            {Object.entries(weights).map(([key, val]) => (
              <div key={key}>
                <div className="flex justify-between mb-1">
                  <label className="text-xs text-gray-600 capitalize">{key.replace('_', ' ')}</label>
                  <span className="text-xs font-bold">{Math.round((val as number) * 100)}%</span>
                </div>
                <input type="range" min={0} max={100} value={Math.round((val as number) * 100)} className="w-full h-1.5 bg-gray-200 rounded-full appearance-none cursor-pointer accent-blue-600" readOnly />
              </div>
            ))}
          </div>
        </div>

        {/* Source reliability */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Source Reliability Scores</h3>
          <div className="space-y-3">
            {Object.entries(sourceScores).sort(([, a], [, b]) => (b as number) - (a as number)).map(([key, val]) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-xs text-gray-600 capitalize">{key.replace('_', ' ')}</span>
                <input type="number" defaultValue={val as number} className="w-16 text-xs border border-gray-200 rounded px-2 py-1 text-right outline-none" />
              </div>
            ))}
          </div>
        </div>

        {/* Multi-source */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Multi-Source Reconciliation</h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between mb-1"><label className="text-xs text-gray-600">Agreement bonus</label><span className="text-xs font-bold">+{conf.multi_source_agreement_bonus || 10}</span></div>
              <input type="range" min={0} max={20} defaultValue={conf.multi_source_agreement_bonus || 10} className="w-full h-1.5 bg-gray-200 rounded-full appearance-none cursor-pointer accent-blue-600" />
            </div>
            <div>
              <label className="text-xs text-gray-600 block mb-1">Conflict resolution</label>
              <select defaultValue={conf.conflict_resolution || 'highest_reliability'} className="w-full text-xs bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1.5 outline-none">
                <option value="highest_reliability">Highest reliability source wins</option>
                <option value="most_recent">Most recent source wins</option>
                <option value="always_hil">Always route to HIL</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 flex gap-3">
        <button onClick={() => saveMutation.mutate({ auto_approve_threshold: autoThreshold, needs_review_threshold: reviewThreshold })} className="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700">
          {saveMutation.isPending ? 'Saving...' : 'Save Configuration'}
        </button>
        <button className="px-4 py-2 bg-white border border-gray-200 text-xs font-medium text-gray-700 rounded-lg hover:bg-gray-50">Reset to Defaults</button>
      </div>
    </div>
  )
}
