interface Props {
  reviewCount: number
  approvedCount: number
  failCount: number
  onApproveAll: () => void
  onNext: () => void
  onPrev?: () => void
  isFirst?: boolean
  isLast?: boolean
}

export default function ActionBar({ reviewCount, approvedCount, failCount, onApproveAll, onNext, onPrev, isFirst, isLast }: Props) {
  return (
    <div className="sticky bottom-0 bg-white border-t border-gray-200 shadow-lg z-40 rounded-b-xl">
      <div className="px-4 py-3 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-4 text-xs">
          {onPrev && !isFirst && (
            <button onClick={onPrev} className="flex items-center gap-1 text-gray-500 hover:text-gray-700">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
              <span className="hidden sm:inline">Previous</span>
            </button>
          )}
          <div className="flex items-center gap-3 text-[11px]">
            {reviewCount > 0 && (
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                {reviewCount} need review
              </span>
            )}
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              {approvedCount} auto-approved
            </span>
            {failCount > 0 && (
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-500" />
                {failCount} failures
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {reviewCount > 0 && (
            <button onClick={onApproveAll} className="px-3 py-2 bg-white border border-gray-200 text-xs font-medium text-gray-700 rounded-lg hover:bg-gray-50">
              Approve All
            </button>
          )}
          <button
            onClick={onNext}
            disabled={failCount > 0}
            className="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 transition flex items-center gap-1.5 disabled:opacity-50"
          >
            {isLast ? 'Publish' : 'Approve & Continue'}
            {!isLast && (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
