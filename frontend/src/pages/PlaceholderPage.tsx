export default function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <div className="p-4 lg:p-6 max-w-[1400px]">
      <h2 className="text-xl font-bold text-gray-900">{title}</h2>
      <p className="text-sm text-gray-500 mt-1">{description}</p>
      <div className="mt-8 flex items-center justify-center p-12 bg-white rounded-xl border border-gray-200 border-dashed">
        <div className="text-center">
          <p className="text-gray-400 text-sm">Coming in Phase 2+</p>
          <p className="text-gray-300 text-xs mt-1">This page will be built next</p>
        </div>
      </div>
    </div>
  )
}
