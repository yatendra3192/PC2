const STAGES = [
  { num: 1, label: 'Ingestion' },
  { num: 2, label: 'Categorisation' },
  { num: 3, label: 'Deduplication' },
  { num: 4, label: 'Enrichment' },
  { num: 5, label: 'Validation' },
  { num: 6, label: 'Transform' },
  { num: 7, label: 'Review & Publish' },
]

interface Props {
  currentStage: number
  completedStages?: number[]
  reviewCounts?: Record<number, number>
  onStageClick?: (stage: number) => void
}

export default function StepperBar({ currentStage, completedStages = [], reviewCounts = {}, onStageClick }: Props) {
  return (
    <div className="flex items-center gap-1 overflow-x-auto pb-2 mb-4">
      {STAGES.map((stage, idx) => {
        const isActive = stage.num === currentStage
        const isDone = completedStages.includes(stage.num)
        const reviewCount = reviewCounts[stage.num] || 0

        return (
          <div key={stage.num} className="flex items-center gap-1">
            {idx > 0 && (
              <svg className="w-3 h-3 text-gray-300 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            )}
            <button
              onClick={() => onStageClick?.(stage.num)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border-2 text-xs font-medium whitespace-nowrap transition-all ${
                isActive
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : isDone
                    ? 'border-green-400 bg-green-50 text-green-700'
                    : 'border-gray-200 text-gray-500 hover:border-gray-300'
              }`}
            >
              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : isDone
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-200 text-gray-500'
              }`}>
                {isDone ? '✓' : stage.num}
              </span>
              <span>{stage.label}</span>
              {reviewCount > 0 && (
                <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 font-medium">
                  {reviewCount}
                </span>
              )}
            </button>
          </div>
        )
      })}
    </div>
  )
}
