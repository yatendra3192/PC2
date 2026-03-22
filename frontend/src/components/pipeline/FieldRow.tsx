import { useState } from 'react'
import type { ProductIksulaValue } from '../../api/products'
import { usePipelineStore } from '../../stores/pipelineStore'
import ConfidenceExplainer from './ConfidenceExplainer'

const SOURCE_COLORS: Record<string, string> = {
  raw_normalised: 'bg-blue-50 text-blue-600',
  ocr: 'bg-blue-50 text-blue-600',
  vision: 'bg-purple-50 text-purple-600',
  csv: 'bg-green-50 text-green-600',
  kb: 'bg-green-50 text-green-600',
  llm: 'bg-indigo-50 text-indigo-600',
  web_google: 'bg-sky-50 text-sky-600',
  web_marketplace: 'bg-orange-50 text-orange-600',
  human: 'bg-gray-100 text-gray-700',
  not_found: 'bg-amber-50 text-amber-600',
}

const SOURCE_LABELS: Record<string, string> = {
  raw_normalised: 'OCR',
  ocr: 'OCR',
  vision: 'Vision',
  csv: 'CSV',
  kb: 'KB',
  llm: 'LLM',
  web_google: 'Web',
  web_marketplace: 'Amazon',
  human: 'Human',
  not_found: 'Missing',
}

interface Props {
  field: ProductIksulaValue | { attribute_code: string; attribute_name: string; unit?: string; value: null; source: 'not_found'; confidence: 0; review_status: 'pending'; agreement_count?: number; confidence_breakdown?: Record<string, number>; confidence_explanation?: string; confidence_factors?: string[] }
  onApprove?: (code: string) => void
  onEdit?: (code: string, value: string) => void
}

export default function FieldRow({ field, onApprove, onEdit }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editValue, setEditValue] = useState('')
  const showTech = usePipelineStore(s => s.showTechDetails)

  const code = field.attribute_code || (field as any).attribute_code
  const name = field.attribute_name || (field as any).attribute_name
  const value = 'value_text' in field
    ? (field.value_text ?? field.value_numeric?.toString() ?? (field.value_boolean !== null ? String(field.value_boolean) : null) ?? field.value_array?.join(', '))
    : null
  const source = field.source
  const confidence = field.confidence || 0
  const reviewStatus = field.review_status
  const isFound = value !== null && value !== undefined
  const isMissing = source === 'not_found' || !isFound

  const statusIcon = reviewStatus === 'auto_approved'
    ? <span className="w-5 h-5 rounded-full bg-green-100 flex items-center justify-center"><svg className="w-3 h-3 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg></span>
    : reviewStatus === 'needs_review' || reviewStatus === 'low_confidence'
      ? <span className="w-5 h-5 rounded-full bg-amber-100 flex items-center justify-center"><span className="w-2 h-2 rounded-full bg-amber-500" /></span>
      : reviewStatus === 'human_approved' || reviewStatus === 'human_edited'
        ? <span className="w-5 h-5 rounded-full bg-blue-100 flex items-center justify-center"><svg className="w-3 h-3 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg></span>
        : isMissing
          ? <span className="w-5 h-5 rounded-full bg-amber-100 flex items-center justify-center"><span className="text-amber-600 text-[10px] font-bold">?</span></span>
          : <span className="w-5 h-5 rounded-full bg-gray-100 flex items-center justify-center"><span className="w-2 h-2 rounded-full bg-gray-400" /></span>

  const handleStartEdit = () => {
    setEditValue(value || '')
    setEditing(true)
  }

  const handleSaveEdit = () => {
    onEdit?.(code, editValue)
    setEditing(false)
  }

  return (
    <>
      <div
        className={`field-row flex flex-col sm:flex-row sm:items-center gap-2 px-4 py-3 cursor-pointer ${isMissing ? 'bg-amber-50/30' : ''}`}
        onClick={() => !editing && setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2 sm:w-40 flex-shrink-0">
          {statusIcon}
          <span className="text-xs font-medium text-gray-600">{name}</span>
        </div>
        <div className="flex-1 flex items-center gap-2">
          {isMissing ? (
            <span className="text-xs text-amber-600 italic">Not found — will enrich</span>
          ) : editing ? (
            <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
              <input
                type="text"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                className="px-2 py-1 border border-blue-300 rounded text-sm outline-none focus:ring-1 focus:ring-blue-400 w-48"
                autoFocus
                onKeyDown={(e) => { if (e.key === 'Enter') handleSaveEdit(); if (e.key === 'Escape') setEditing(false); }}
              />
              <button onClick={handleSaveEdit} className="px-2 py-1 bg-blue-600 text-white text-[10px] font-medium rounded">Save</button>
              <button onClick={() => setEditing(false)} className="text-[10px] text-gray-500">Cancel</button>
            </div>
          ) : (
            <>
              <span className="text-sm text-gray-900">{value}</span>
              {field.unit && <span className="text-xs text-gray-400">{field.unit}</span>}
            </>
          )}
          {isFound && !editing && (
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${SOURCE_COLORS[source] || 'bg-gray-100 text-gray-600'}`}>
              {SOURCE_LABELS[source] || source}
            </span>
          )}
          {showTech && isFound && confidence > 0 && (
            <span className={`text-[10px] ${confidence >= 85 ? 'text-green-600' : confidence >= 60 ? 'text-amber-600' : 'text-red-600'}`}>
              {confidence}%
            </span>
          )}
        </div>
        {isFound && !editing && (
          <div className="flex items-center gap-2 ml-auto" onClick={e => e.stopPropagation()}>
            <button onClick={handleStartEdit} className="edit-btn text-[10px] text-blue-600 font-medium hover:underline transition-opacity">Edit</button>
            {reviewStatus !== 'auto_approved' && reviewStatus !== 'human_approved' && reviewStatus !== 'human_edited' && (
              <button onClick={() => onApprove?.(code)} className="px-2 py-1 bg-green-50 text-green-700 text-[10px] font-medium rounded hover:bg-green-100">Approve</button>
            )}
          </div>
        )}
        {isMissing && (
          <div className="ml-auto" onClick={e => e.stopPropagation()}>
            <button onClick={handleStartEdit} className="text-[10px] text-blue-600 font-medium hover:underline">Enter manually</button>
          </div>
        )}
      </div>

      {/* Expandable detail with confidence explanation */}
      {expanded && isFound && (
        <div className="bg-gray-50/50 px-4 py-3 border-l-4 border-blue-200 space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[10px]">
            <div>
              <span className="text-gray-400 block">Source</span>
              <span className="font-medium text-gray-700">{SOURCE_LABELS[source] || source}</span>
            </div>
            <div>
              <span className="text-gray-400 block">Status</span>
              <span className="font-medium text-gray-700 capitalize">{reviewStatus?.replace('_', ' ')}</span>
            </div>
            {showTech && 'model_name' in field && field.model_name && (
              <div>
                <span className="text-gray-400 block">Model</span>
                <span className="font-medium text-gray-700">{field.model_name}</span>
              </div>
            )}
            {'agreement_count' in field && (field.agreement_count ?? 0) > 1 && (
              <div>
                <span className="text-gray-400 block">Sources Agree</span>
                <span className="font-medium text-green-700">{field.agreement_count} sources confirm</span>
              </div>
            )}
          </div>
          {/* Confidence explainer — always visible on expand */}
          <ConfidenceExplainer
            confidence={confidence}
            breakdown={'confidence_breakdown' in field ? field.confidence_breakdown : undefined}
            explanation={'confidence_explanation' in field ? (field as any).confidence_explanation : undefined}
            factors={'confidence_factors' in field ? (field as any).confidence_factors : undefined}
          />
        </div>
      )}
    </>
  )
}
