import { usePipelineStore } from '../stores/pipelineStore'

interface MatchCheck {
  method: string
  status: string
  score: number
}

interface MatchedValue {
  attribute_code: string
  attribute_name: string
  value: string | null
}

interface Props {
  metadata: Record<string, unknown>
  onResolve: (decision: string) => void
}

export default function Stage3Dedup({ metadata, onResolve }: Props) {
  const showTech = usePipelineStore(s => s.showTechDetails)

  const outcome = metadata?.outcome as string || 'new_item'
  const similarity = metadata?.similarity as number || 0
  const matchChecks = (metadata?.match_checks as MatchCheck[]) || []
  const matched = metadata?.matched_product as { id: string; name: string; model_number: string; values: MatchedValue[] } | null
  const incomingValues = (metadata?.incoming_values as MatchedValue[]) || []
  const keyDiffs = (metadata?.key_differences as Record<string, { incoming: unknown; existing: unknown }>) || {}

  const outcomeConfig = {
    new_item: { label: 'New Item', color: 'bg-green-100 text-green-700 border-green-200', icon: '✓' },
    possible_variant: { label: 'Possible Variant', color: 'bg-amber-100 text-amber-700 border-amber-200', icon: '!' },
    likely_duplicate: { label: 'Likely Duplicate', color: 'bg-red-100 text-red-700 border-red-200', icon: '✕' },
  }[outcome] || { label: outcome, color: 'bg-gray-100 text-gray-700', icon: '?' }

  return (
    <div className="space-y-6">
      {/* Match Checks */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">Match Checks</h3>
          {showTech && <span className="text-[10px] text-gray-400">{metadata?.ip_label as string}</span>}
        </div>
        <div className="p-4 space-y-3">
          {matchChecks.map((check, i) => {
            const isMatch = check.status === 'match'
            const isNoMatch = check.status === 'no_match' || check.status === 'below_threshold'
            return (
              <div key={i} className={`flex items-center gap-3 p-3 rounded-lg ${
                isMatch ? 'bg-amber-50 border border-amber-200' : 'bg-green-50'
              }`}>
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                  isMatch ? 'bg-amber-500 text-white' : 'bg-green-500 text-white'
                }`}>
                  {isMatch ? '!' : '✓'}
                </span>
                <span className="text-xs font-medium text-gray-700 flex-1">{check.method}</span>
                <span className={`text-xs font-medium ${isMatch ? 'text-amber-700' : 'text-green-700'}`}>
                  {isMatch ? `${check.score}% match found` : isNoMatch ? 'No match' : check.status}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Side-by-Side Comparison (only if match found) */}
      {matched && (
        <div className={`bg-white rounded-xl border-2 ${outcomeConfig.color.includes('amber') ? 'border-amber-200' : 'border-red-200'}`}>
          <div className={`px-4 py-3 border-b rounded-t-xl flex items-center gap-2 ${
            outcome === 'possible_variant' ? 'bg-amber-50 border-amber-100' : 'bg-red-50 border-red-100'
          }`}>
            <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
              outcome === 'possible_variant' ? 'bg-amber-500 text-white' : 'bg-red-500 text-white'
            }`}>{outcomeConfig.icon}</span>
            <h3 className={`text-sm font-semibold ${
              outcome === 'possible_variant' ? 'text-amber-800' : 'text-red-800'
            }`}>{outcomeConfig.label} — {similarity}% Similarity</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-gray-100">
            {/* Incoming */}
            <div className="p-4">
              <span className="text-[10px] text-blue-600 font-semibold uppercase tracking-wider">Incoming Item</span>
              <div className="mt-3 space-y-2">
                {incomingValues.map((v) => {
                  const isDiff = v.attribute_code in keyDiffs
                  return (
                    <div key={v.attribute_code} className={`flex justify-between ${isDiff ? 'bg-amber-50 -mx-2 px-2 py-1 rounded' : ''}`}>
                      <span className="text-xs text-gray-500">{v.attribute_name}</span>
                      <span className={`text-xs font-medium ${isDiff ? 'text-amber-700' : ''}`}>{v.value || '—'}</span>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Existing */}
            <div className="p-4">
              <span className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider">Existing Catalog Item</span>
              <p className="text-xs font-medium text-gray-900 mt-1">{matched.name} ({matched.model_number})</p>
              <div className="mt-3 space-y-2">
                {matched.values.map((v) => {
                  const isDiff = v.attribute_code in keyDiffs
                  return (
                    <div key={v.attribute_code} className={`flex justify-between ${isDiff ? 'bg-amber-50 -mx-2 px-2 py-1 rounded' : ''}`}>
                      <span className="text-xs text-gray-500">{v.attribute_name}</span>
                      <span className={`text-xs font-medium ${isDiff ? 'text-amber-700' : ''}`}>{v.value || '—'}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-100 rounded-b-xl flex flex-wrap gap-2">
            <button onClick={() => onResolve('keep_variant')} className="px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700">
              Keep as Variant
            </button>
            <button onClick={() => onResolve('merge')} className="px-3 py-1.5 bg-white border border-gray-200 text-xs font-medium text-gray-700 rounded-lg hover:bg-gray-50">
              Merge Records
            </button>
            <button onClick={() => onResolve('reject_incoming')} className="px-3 py-1.5 bg-white border border-gray-200 text-xs font-medium text-gray-700 rounded-lg hover:bg-gray-50">
              Reject Incoming
            </button>
            <button onClick={() => onResolve('override_existing')} className="px-3 py-1.5 bg-white border border-gray-200 text-xs font-medium text-gray-700 rounded-lg hover:bg-gray-50">
              Override Existing
            </button>
          </div>
        </div>
      )}

      {/* New Item — no match */}
      {outcome === 'new_item' && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
          <span className="w-12 h-12 mx-auto bg-green-100 rounded-2xl flex items-center justify-center mb-3">
            <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </span>
          <h3 className="text-sm font-semibold text-green-800">New Item — No Duplicates Found</h3>
          <p className="text-xs text-green-600 mt-1">This product does not match any existing catalog items. Proceeding to enrichment.</p>
          <button onClick={() => onResolve('new_item')} className="mt-4 px-4 py-2 bg-green-600 text-white text-xs font-semibold rounded-lg hover:bg-green-700">
            Continue to Enrichment
          </button>
        </div>
      )}
    </div>
  )
}
