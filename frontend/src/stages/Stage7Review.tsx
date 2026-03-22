import { useState } from 'react'
import type { ProductIksulaValue } from '../api/products'
import { usePipelineStore } from '../stores/pipelineStore'
import FieldRow from '../components/pipeline/FieldRow'

interface AuditEntry {
  action: string
  field: string | null
  layer: string | null
  old_value: string | null
  new_value: string | null
  actor: string | null
  model: string | null
  reason: string | null
  timestamp: string
}

interface ClientValue {
  client_field_name: string
  client_value: string
}

interface Props {
  metadata: Record<string, unknown>
  iksulaValues: ProductIksulaValue[]
  product: { product_name?: string | null; model_number?: string | null }
  onApprove: (code: string) => void
  onEdit: (code: string, value: string) => void
  onPublish: () => void
  onExport: (format: string) => void
}

export default function Stage7Review({ metadata, iksulaValues, product, onApprove, onEdit, onPublish, onExport }: Props) {
  const showTech = usePipelineStore(s => s.showTechDetails)
  const [showAudit, setShowAudit] = useState(false)
  const [publishConfirm, setPublishConfirm] = useState(false)

  const summary = (metadata?.summary as Record<string, number>) || {}
  const canPublish = metadata?.can_publish as boolean
  const auditTrail = (metadata?.audit_trail as AuditEntry[]) || []
  const clientValues = (metadata?.client_values as ClientValue[]) || []

  const reviewItems = iksulaValues.filter(v =>
    v.review_status === 'needs_review' || v.review_status === 'low_confidence'
  )

  const actionLabels: Record<string, { label: string; color: string }> = {
    extracted: { label: 'Extracted', color: 'bg-blue-50 text-blue-600' },
    normalised: { label: 'Normalised', color: 'bg-blue-50 text-blue-600' },
    enriched: { label: 'Enriched', color: 'bg-green-50 text-green-600' },
    validated: { label: 'Validated', color: 'bg-green-50 text-green-600' },
    approved: { label: 'Approved', color: 'bg-green-50 text-green-700' },
    edited: { label: 'Edited', color: 'bg-amber-50 text-amber-700' },
    rejected: { label: 'Rejected', color: 'bg-red-50 text-red-600' },
    published: { label: 'Published', color: 'bg-purple-50 text-purple-700' },
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="text-center p-4 bg-green-50 rounded-xl border border-green-200">
          <span className="text-2xl font-bold text-green-700">{summary.auto_approved || 0}</span>
          <p className="text-xs text-green-600 mt-1">Auto-approved</p>
        </div>
        <div className="text-center p-4 bg-blue-50 rounded-xl border border-blue-200">
          <span className="text-2xl font-bold text-blue-700">{(summary.human_approved || 0) + (summary.human_edited || 0)}</span>
          <p className="text-xs text-blue-600 mt-1">Human reviewed</p>
        </div>
        <div className="text-center p-4 bg-amber-50 rounded-xl border border-amber-200">
          <span className="text-2xl font-bold text-amber-700">{(summary.needs_review || 0) + (summary.low_confidence || 0)}</span>
          <p className="text-xs text-amber-600 mt-1">Pending review</p>
        </div>
        <div className="text-center p-4 bg-gray-50 rounded-xl border border-gray-200">
          <span className="text-2xl font-bold text-gray-700">{summary.overall_score || 0}%</span>
          <p className="text-xs text-gray-600 mt-1">Overall score</p>
        </div>
      </div>

      {/* Review Queue (remaining items) */}
      {reviewItems.length > 0 && (
        <div className="bg-white rounded-xl border border-amber-200">
          <div className="px-4 py-3 border-b border-amber-100 bg-amber-50 rounded-t-xl">
            <h3 className="text-sm font-semibold text-amber-800">Items Needing Review ({reviewItems.length})</h3>
            <p className="text-[10px] text-amber-600">Resolve these before publishing</p>
          </div>
          <div className="divide-y divide-gray-50">
            {reviewItems.map(field => (
              <FieldRow key={field.attribute_code} field={field} onApprove={onApprove} onEdit={onEdit} />
            ))}
          </div>
        </div>
      )}

      {/* Complete Record View */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">Complete Record</h3>
          <span className="text-[10px] text-gray-400">{summary.total_fields || 0} fields total</span>
        </div>
        <div className="divide-y divide-gray-50 max-h-[400px] overflow-y-auto">
          {iksulaValues.map(field => (
            <FieldRow key={field.attribute_code} field={field} onApprove={onApprove} onEdit={onEdit} />
          ))}
        </div>
      </div>

      {/* Client Output Preview */}
      {clientValues.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900">Client Output Preview</h3>
            <div className="flex gap-1">
              {['csv', 'json', 'xml'].map(fmt => (
                <button key={fmt} onClick={() => onExport(fmt)} className="px-2 py-1 bg-gray-50 border border-gray-200 text-[10px] font-medium rounded hover:bg-gray-100 uppercase">{fmt}</button>
              ))}
            </div>
          </div>
          <div className="p-4 overflow-x-auto">
            <table className="w-full text-[10px] border border-gray-200 rounded">
              <thead className="bg-gray-100">
                <tr>{clientValues.map((cv, i) => <th key={i} className="px-2 py-1.5 text-left font-medium text-gray-600 whitespace-nowrap">{cv.client_field_name}</th>)}</tr>
              </thead>
              <tbody>
                <tr>{clientValues.map((cv, i) => <td key={i} className="px-2 py-1.5 whitespace-nowrap">{cv.client_value}</td>)}</tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Audit Trail */}
      <div className="bg-white rounded-xl border border-gray-200">
        <button
          onClick={() => setShowAudit(!showAudit)}
          className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 rounded-xl"
        >
          <h3 className="text-sm font-semibold text-gray-900">Audit Trail ({auditTrail.length} entries)</h3>
          <svg className={`w-4 h-4 text-gray-400 transition ${showAudit ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
        </button>
        {showAudit && (
          <div className="border-t border-gray-100 divide-y divide-gray-50 max-h-[300px] overflow-y-auto">
            {auditTrail.map((entry, i) => {
              const cfg = actionLabels[entry.action] || { label: entry.action, color: 'bg-gray-50 text-gray-600' }
              return (
                <div key={i} className="px-4 py-2.5 flex items-start gap-3 text-xs">
                  <span className="text-[10px] text-gray-400 w-28 flex-shrink-0">{new Date(entry.timestamp).toLocaleString()}</span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${cfg.color}`}>{cfg.label}</span>
                      {entry.field && <span className="font-medium text-gray-700">{entry.field}</span>}
                    </div>
                    {entry.old_value && entry.new_value && (
                      <p className="text-[10px] text-gray-400 mt-0.5">"{entry.old_value}" → "{entry.new_value}"</p>
                    )}
                    {entry.actor && <span className="text-[10px] text-gray-400">by {entry.actor}</span>}
                    {showTech && entry.model && <span className="text-[10px] text-gray-400 ml-2">model: {entry.model}</span>}
                    {entry.reason && <p className="text-[10px] text-gray-500 mt-0.5">Reason: {entry.reason}</p>}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Publish Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        {!publishConfirm ? (
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={() => canPublish ? setPublishConfirm(true) : null}
              disabled={!canPublish}
              className="flex-1 px-4 py-3 bg-green-600 text-white text-sm font-semibold rounded-xl hover:bg-green-700 transition flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
              {canPublish ? 'Publish to SiteOne Staging' : `Resolve ${(summary.needs_review || 0) + (summary.low_confidence || 0)} items to publish`}
            </button>
            <button onClick={() => onExport('csv')} className="px-4 py-3 bg-white border border-gray-200 text-sm font-medium text-gray-700 rounded-xl hover:bg-gray-50 flex items-center justify-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
              Export CSV
            </button>
          </div>
        ) : (
          <div className="text-center">
            <div className="w-16 h-16 mx-auto bg-green-100 rounded-2xl flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-1">Publish this record?</h3>
            <p className="text-sm text-gray-500 mb-4">{product.product_name} ({product.model_number}) → SiteOne Staging Catalog</p>
            <div className="flex justify-center gap-3">
              <button onClick={onPublish} className="px-6 py-2.5 bg-green-600 text-white text-sm font-semibold rounded-lg hover:bg-green-700">Confirm Publish</button>
              <button onClick={() => setPublishConfirm(false)} className="px-6 py-2.5 bg-white border border-gray-200 text-sm font-medium text-gray-700 rounded-lg hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
