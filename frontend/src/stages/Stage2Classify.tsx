import { usePipelineStore } from '../stores/pipelineStore'

interface Props {
  metadata: Record<string, unknown>
  onApprove: () => void
}

export default function Stage2Classify({ metadata, onApprove }: Props) {
  const showTech = usePipelineStore(s => s.showTechDetails)

  const taxonomyLevels = [
    { level: 'Department', name: 'Hardware & Tools', confidence: 96 },
    { level: 'Category', name: 'Irrigation', confidence: 95 },
    { level: 'Class', name: 'Controllers', confidence: 94 },
    { level: 'Sub-class', name: 'Smart Controllers', confidence: 94 },
  ]

  const mandatoryAttrs = (metadata?.mandatory_attrs as Array<{ code: string; name: string; found: boolean }>) || []
  const alternatives = (metadata?.alternatives as Array<{ path: string; confidence: number }>) || []
  const foundCount = metadata?.mandatory_found as number || 0
  const totalMandatory = metadata?.mandatory_total as number || 0

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Taxonomy Assignment */}
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              <h3 className="text-sm font-semibold text-gray-900">SiteOne Taxonomy</h3>
            </div>
            {showTech && (
              <span className="text-[10px] text-gray-400">{String(metadata?.taxonomy_version || '')}</span>
            )}
          </div>
          <div className="p-4 space-y-3">
            {taxonomyLevels.map((t) => (
              <div key={t.level} className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
                <div>
                  <span className="text-[10px] text-gray-400 block">{t.level}</span>
                  <span className="text-sm font-medium text-gray-900">{t.name}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-xs font-medium text-green-700">{t.confidence}%</span>
                  <span className="w-4 h-4 rounded-full bg-green-500 text-white flex items-center justify-center text-[8px]">✓</span>
                </div>
              </div>
            ))}
          </div>
          {showTech && (
            <div className="px-4 py-2 bg-gray-50 border-t border-gray-100 rounded-b-xl">
              <span className="text-[10px] text-gray-500">{String(metadata?.total_classes || 847)} classes · Iksula proprietary</span>
            </div>
          )}

          {/* Alternatives */}
          {alternatives.length > 0 && (
            <div className="px-4 py-3 border-t border-gray-100">
              <p className="text-[10px] text-gray-400 font-medium mb-2">Alternative classifications</p>
              {alternatives.slice(1).map((alt, i) => (
                <div key={i} className="flex items-center justify-between py-1.5 text-xs">
                  <span className="text-gray-500">{alt.path}</span>
                  <span className="text-gray-400">{alt.confidence}%</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Mandatory Attributes */}
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-100">
            <h3 className="text-sm font-semibold text-gray-900">Mandatory Attributes — Smart Controllers</h3>
            <p className="text-[10px] text-gray-400 mt-0.5">{totalMandatory} attributes required for this class</p>
          </div>
          <div className="p-4 space-y-2">
            {mandatoryAttrs.map((attr) => (
              <div key={attr.code} className="flex items-center justify-between py-1.5">
                <span className="text-xs text-gray-700">{attr.name}</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                  attr.found ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'
                }`}>
                  {attr.found ? 'Found' : 'Missing'}
                </span>
              </div>
            ))}
          </div>
          <div className="px-4 py-2 bg-amber-50 border-t border-amber-100 rounded-b-xl">
            <div className="flex items-center gap-2">
              <div className="w-full bg-gray-200 rounded-full h-1.5">
                <div className="bg-green-500 h-1.5 rounded-full" style={{ width: `${(foundCount / totalMandatory) * 100}%` }} />
              </div>
              <span className="text-[10px] font-medium text-amber-700 whitespace-nowrap">{foundCount} / {totalMandatory}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Approve button */}
      <div className="flex justify-end">
        <button onClick={onApprove} className="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 flex items-center gap-1.5">
          Approve Classification & Continue
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
        </button>
      </div>
    </div>
  )
}
