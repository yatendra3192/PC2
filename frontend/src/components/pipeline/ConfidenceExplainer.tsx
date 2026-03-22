interface Props {
  confidence: number
  breakdown?: Record<string, number> | null
  explanation?: string | null
  factors?: string[] | null
  stage?: number
}

const COMPONENT_LABELS: Record<string, string> = {
  ocr_quality: 'OCR Quality',
  field_match: 'Field Match Certainty',
  value_completeness: 'Value Completeness',
  source_reliability: 'Source Reliability',
  consistency: 'Consistency',
  completeness: 'Completeness',
  model_confidence: 'Model Confidence',
  taxonomy_depth: 'Taxonomy Depth Match',
  attribute_alignment: 'Attribute Alignment',
  exact_match: 'Exact ID Match',
  semantic_similarity: 'Semantic Similarity',
  attribute_overlap: 'Attribute Overlap',
  picklist_consistency: 'Picklist Match',
  multi_source_agreement: 'Multi-Source Agreement',
}

export default function ConfidenceExplainer({ confidence, breakdown, explanation, factors, stage }: Props) {
  const color = confidence >= 85 ? 'green' : confidence >= 60 ? 'amber' : 'red'
  const colors = {
    green: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-800', bar: 'bg-green-500', badge: 'bg-green-100 text-green-700' },
    amber: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-800', bar: 'bg-amber-500', badge: 'bg-amber-100 text-amber-700' },
    red: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-800', bar: 'bg-red-500', badge: 'bg-red-100 text-red-700' },
  }[color]

  return (
    <div className={`${colors.bg} border ${colors.border} rounded-lg p-3`}>
      {/* Score header */}
      <div className="flex items-center justify-between mb-2">
        <span className={`text-xs font-semibold ${colors.text}`}>
          Confidence Score: {confidence}%
        </span>
        <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${colors.badge}`}>
          {confidence >= 85 ? 'Auto-approved' : confidence >= 60 ? 'Needs review' : 'Low confidence'}
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-white rounded-full h-2 mb-3">
        <div className={`h-2 rounded-full ${colors.bar} transition-all`} style={{ width: `${confidence}%` }} />
      </div>

      {/* Breakdown bars */}
      {breakdown && Object.keys(breakdown).length > 0 && (
        <div className="space-y-1.5 mb-3">
          {Object.entries(breakdown).map(([key, value]) => (
            <div key={key} className="flex items-center gap-2">
              <span className="text-[10px] text-gray-500 w-28 flex-shrink-0">{COMPONENT_LABELS[key] || key}</span>
              <div className="flex-1 bg-white rounded-full h-1.5">
                <div className={`h-1.5 rounded-full ${value >= 80 ? 'bg-green-400' : value >= 60 ? 'bg-amber-400' : 'bg-red-400'}`} style={{ width: `${value}%` }} />
              </div>
              <span className="text-[10px] text-gray-600 w-8 text-right">{value}%</span>
            </div>
          ))}
        </div>
      )}

      {/* Explanation text */}
      {explanation && (
        <p className="text-[10px] text-gray-600 mb-2 leading-relaxed">{explanation}</p>
      )}

      {/* Factor bullets */}
      {factors && factors.length > 0 && (
        <ul className="space-y-1">
          {factors.map((factor, i) => (
            <li key={i} className="text-[10px] text-gray-500 flex items-start gap-1.5">
              <span className="text-gray-400 mt-0.5">&#8226;</span>
              <span>{factor}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
