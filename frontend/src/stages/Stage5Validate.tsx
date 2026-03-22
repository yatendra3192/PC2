import { useState } from 'react'
import { usePipelineStore } from '../stores/pipelineStore'

interface ValidationResult {
  rule: string
  field: string
  value: string
  status: 'pass' | 'warning' | 'fail'
  message: string
  fix: string | null
  fixed_value: string | null
}

interface Props {
  metadata: Record<string, unknown>
  onAdvance: () => void
  onFixField: (field: string, value: string) => void
}

export default function Stage5Validate({ metadata, onAdvance, onFixField }: Props) {
  const showTech = usePipelineStore(s => s.showTechDetails)
  const [fixValues, setFixValues] = useState<Record<string, string>>({})

  const passed = (metadata?.passed as number) ?? 0
  const warnings = (metadata?.warnings as number) ?? 0
  const failures = (metadata?.failures as number) ?? 0
  const results = (metadata?.results as ValidationResult[]) || []

  const statusConfig = {
    pass: { bg: 'bg-green-50', border: 'border-green-200', icon: '✓', iconBg: 'bg-green-500', badge: 'bg-green-100 text-green-700' },
    warning: { bg: 'bg-amber-50', border: 'border-amber-200', icon: '!', iconBg: 'bg-amber-500', badge: 'bg-amber-100 text-amber-700' },
    fail: { bg: 'bg-red-50', border: 'border-red-200', icon: '✕', iconBg: 'bg-red-500', badge: 'bg-red-100 text-red-600' },
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
          <span className="text-2xl font-bold text-green-700">{passed}</span>
          <p className="text-xs text-green-600 mt-1">Passed</p>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-center">
          <span className="text-2xl font-bold text-amber-700">{warnings}</span>
          <p className="text-xs text-amber-600 mt-1">Warnings</p>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center">
          <span className="text-2xl font-bold text-red-600">{failures}</span>
          <p className="text-xs text-red-600 mt-1">Failures</p>
        </div>
      </div>

      {/* Validation Results */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">Validation Results</h3>
          {showTech && <span className="text-[10px] text-gray-400">{metadata?.ip_label as string}</span>}
        </div>
        <div className="divide-y divide-gray-50">
          {results.map((r, i) => {
            const cfg = statusConfig[r.status]
            const isFail = r.status === 'fail'

            return (
              <div key={i} className={`flex flex-col sm:flex-row sm:items-center gap-3 px-4 py-3 ${isFail ? 'bg-red-50/50 border-l-4 border-red-400' : ''}`}>
                <span className={`w-5 h-5 rounded-full ${cfg.iconBg} text-white flex items-center justify-center text-[10px] font-bold flex-shrink-0`}>
                  {cfg.icon}
                </span>
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-medium text-gray-700">{r.rule} — {r.field}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${cfg.badge}`}>{r.status}</span>
                  </div>
                  <p className="text-[10px] text-gray-500 mt-0.5">{r.message}</p>
                  {r.fix && <p className="text-[10px] text-blue-600 mt-0.5">Fix: {r.fix}</p>}
                </div>

                {/* Inline fix for failures */}
                {isFail && (
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <input
                      type="text"
                      placeholder={r.fix || 'Enter value'}
                      value={fixValues[r.field] || r.fixed_value || ''}
                      onChange={(e) => setFixValues(v => ({ ...v, [r.field]: e.target.value }))}
                      className="px-2 py-1.5 border border-red-200 rounded text-xs w-28 outline-none focus:border-blue-400"
                    />
                    <button
                      onClick={() => onFixField(r.field, fixValues[r.field] || r.fixed_value || '')}
                      className="px-3 py-1.5 bg-blue-600 text-white text-[10px] font-medium rounded-lg hover:bg-blue-700"
                    >Save</button>
                  </div>
                )}

                {/* Pass with conversion shown */}
                {r.status === 'pass' && r.fixed_value && (
                  <span className="text-[10px] text-green-600 font-medium flex-shrink-0">→ {r.fixed_value}</span>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* AI Anomaly Detections */}
      {(metadata?.anomalies as Array<Record<string, unknown>>)?.length > 0 && (
        <div className="bg-white rounded-xl border border-purple-200">
          <div className="px-4 py-3 border-b border-purple-100 bg-purple-50 rounded-t-xl flex items-center gap-2">
            <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
            <h3 className="text-sm font-semibold text-purple-800">AI Anomaly Detection</h3>
            <span className="text-[10px] text-purple-600 ml-auto">Compared against similar products in this class</span>
          </div>
          <div className="divide-y divide-purple-50">
            {(metadata?.anomalies as Array<Record<string, unknown>>)?.map((anomaly, i) => (
              <div key={i} className="px-4 py-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                    anomaly.severity === 'high' ? 'bg-red-100 text-red-700' :
                    anomaly.severity === 'medium' ? 'bg-amber-100 text-amber-700' :
                    anomaly.severity === 'info' ? 'bg-blue-100 text-blue-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>{(anomaly.severity as string)?.toUpperCase()}</span>
                  <span className="text-xs font-semibold text-gray-900">{String(anomaly.field_name)}</span>
                  <span className="text-xs text-gray-500">= {String(anomaly.value)}</span>
                  {String(anomaly.class_avg) !== 'undefined' && (
                    <span className="text-[10px] text-gray-400">· Class avg: {String(anomaly.class_avg)} · Range: {String(anomaly.class_range)}</span>
                  )}
                </div>
                <p className="text-[10px] text-gray-600">{String(anomaly.message)}</p>
                {String(anomaly.ai_assessment) !== 'undefined' && (
                  <p className="text-[10px] text-purple-600 mt-1 flex items-start gap-1">
                    <span className="font-medium">AI:</span> {String(anomaly.ai_assessment)}
                  </p>
                )}
                {String(anomaly.ai_suggestion) !== 'undefined' && (
                  <p className="text-[10px] text-blue-600 mt-0.5">Suggestion: {String(anomaly.ai_suggestion)}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Advance */}
      <div className="flex justify-end">
        <button
          onClick={onAdvance}
          disabled={failures > 0}
          className="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {failures > 0 ? `Fix ${failures} failure${failures > 1 ? 's' : ''} to continue` : 'Approve & Continue to Transform'}
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
        </button>
      </div>
    </div>
  )
}
