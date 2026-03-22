import { useState } from 'react'
import { usePipelineStore } from '../stores/pipelineStore'

interface TransformEntry {
  iksula_field: string
  client_field: string
  transform: { type: string; [key: string]: unknown }
  status: string
}

interface Props {
  metadata: Record<string, unknown>
  clientValues: Array<{ client_field_name: string; client_value: string; iksula_raw_value: string | null; transform_applied: string | null }>
  onAdvance: () => void
  onMapField: (iksulaField: string, clientField: string) => void
}

const TRANSFORM_LABELS: Record<string, string> = {
  direct: 'Pass through',
  unit_convert: 'Unit conversion',
  lookup: 'Value lookup',
  boolean_format: 'Boolean format',
  case: 'Case transform',
  duration_format: 'Duration format',
  join: 'Join array',
  concat: 'Concatenate',
  truncate: 'Truncate',
}

export default function Stage6Transform({ metadata, clientValues, onAdvance, onMapField }: Props) {
  const showTech = usePipelineStore(s => s.showTechDetails)
  const [activeFormat, setActiveFormat] = useState('csv')

  const templateName = metadata?.template as string || 'Unknown Template'
  const templateVersion = metadata?.template_version as string || ''
  const maintainedBy = metadata?.maintained_by as string || 'Iksula'
  const mapped = metadata?.mapped as number || 0
  const unmapped = metadata?.unmapped as number || 0
  const coverage = metadata?.coverage_pct as number || 100
  const unmappedAttrs = (metadata?.unmapped_attrs as string[]) || []
  const transformSummary = (metadata?.transform_summary as TransformEntry[]) || []
  const exportFormats = (metadata?.export_formats as string[]) || ['csv']

  return (
    <div className="space-y-6">
      {/* Template Selector */}
      <div className="flex gap-3">
        <button className="flex-1 p-4 bg-blue-50 border-2 border-blue-300 rounded-xl text-left">
          <span className="text-xs font-semibold text-blue-700">{templateName}</span>
          <p className="text-[10px] text-gray-500 mt-1">Maintained by {maintainedBy} · Version {templateVersion}</p>
        </button>
        <button className="flex-1 p-4 bg-white border-2 border-gray-200 rounded-xl text-left hover:border-gray-300 opacity-60">
          <span className="text-xs font-semibold text-gray-700">THD Template v6.1</span>
          <p className="text-[10px] text-gray-500 mt-1">Switch to The Home Depot format</p>
        </button>
      </div>

      {/* Mapping Coverage */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-gray-900">Field Mapping</span>
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
            coverage >= 95 ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
          }`}>
            {coverage}% auto-mapped — {unmapped} need manual mapping
          </span>
        </div>
      </div>

      {/* Mapping Table */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">Field Mapping Detail</h3>
          {showTech && <span className="text-[10px] text-gray-400">{templateName}</span>}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-4 py-2.5 font-medium text-gray-500">PC2 Internal Field</th>
                <th className="text-center px-2 py-2.5 font-medium text-gray-400">→</th>
                <th className="text-left px-4 py-2.5 font-medium text-gray-500">Client Field</th>
                {showTech && <th className="text-left px-4 py-2.5 font-medium text-gray-500">Transform</th>}
                <th className="text-center px-4 py-2.5 font-medium text-gray-500">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {transformSummary.map((entry, i) => {
                const isUnmapped = entry.status === 'unmapped'
                return (
                  <tr key={i} className={isUnmapped ? 'bg-amber-50/50' : ''}>
                    <td className="px-4 py-2.5 font-medium text-gray-700">{entry.iksula_field}</td>
                    <td className="px-2 py-2.5 text-center text-gray-300">
                      {isUnmapped ? '?' : '→'}
                    </td>
                    <td className="px-4 py-2.5">
                      {isUnmapped ? (
                        <select className="w-full text-xs border border-amber-200 rounded px-2 py-1 bg-white outline-none"
                          onChange={(e) => onMapField(entry.iksula_field, e.target.value)}>
                          <option>Select field...</option>
                          <option>Compatible Accessories</option>
                          <option>Related Components</option>
                          <option>Valve Compatibility</option>
                        </select>
                      ) : (
                        <span className="font-medium text-gray-900">{entry.client_field}</span>
                      )}
                    </td>
                    {showTech && (
                      <td className="px-4 py-2.5 text-gray-500">
                        {TRANSFORM_LABELS[entry.transform.type] || entry.transform.type}
                      </td>
                    )}
                    <td className="px-4 py-2.5 text-center">
                      {isUnmapped ? (
                        <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-[9px] font-medium">Unmapped</span>
                      ) : entry.status === 'corrected' ? (
                        <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-[9px] font-medium">Corrected</span>
                      ) : (
                        <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded text-[9px] font-medium">Auto</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Output Preview */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-100 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-gray-900">Output Preview</h3>
          <div className="flex gap-1">
            {exportFormats.map(fmt => (
              <button
                key={fmt}
                onClick={() => setActiveFormat(fmt)}
                className={`px-2.5 py-1 text-[10px] font-medium rounded border ${
                  activeFormat === fmt ? 'bg-blue-50 text-blue-700 border-blue-200' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                }`}
              >{fmt.toUpperCase()}</button>
            ))}
          </div>
        </div>
        <div className="p-4 overflow-x-auto">
          {clientValues.length > 0 ? (
            <table className="w-full text-[10px] border border-gray-200 rounded">
              <thead className="bg-gray-100">
                <tr>
                  {clientValues.map((cv, i) => (
                    <th key={i} className="px-2 py-1.5 text-left text-gray-600 font-medium whitespace-nowrap">{cv.client_field_name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  {clientValues.map((cv, i) => (
                    <td key={i} className="px-2 py-1.5 font-medium whitespace-nowrap">{cv.client_value}</td>
                  ))}
                </tr>
              </tbody>
            </table>
          ) : (
            <p className="text-xs text-gray-400 text-center py-4">Run transformation to see preview</p>
          )}
        </div>
      </div>

      {/* Advance */}
      <div className="flex justify-end">
        <button onClick={onAdvance} className="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 flex items-center gap-1.5">
          Approve & Continue to Final Review
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
        </button>
      </div>
    </div>
  )
}
