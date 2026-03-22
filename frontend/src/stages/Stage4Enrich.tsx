import { useState } from 'react'
import type { ProductIksulaValue } from '../api/products'
import { usePipelineStore } from '../stores/pipelineStore'
import FieldRow from '../components/pipeline/FieldRow'

interface WebResult {
  url: string
  title?: string
  attrs: Record<string, string>
}

interface Props {
  metadata: Record<string, unknown>
  iksulaValues: ProductIksulaValue[]
  product: { product_title?: string | null; short_description?: string | null; long_description?: string | null }
  onApprove: (code: string) => void
  onEdit: (code: string, value: string) => void
  onAdvance: () => void
}

export default function Stage4Enrich({ metadata, iksulaValues, product, onApprove, onEdit, onAdvance }: Props) {
  const showTech = usePipelineStore(s => s.showTechDetails)
  const [showAllAmazon, setShowAllAmazon] = useState(false)

  const completeBefore = (metadata?.completeness_before as number) ?? 44
  const completeAfter = (metadata?.completeness_after as number) ?? 93
  const webScrape = metadata?.web_scrape as { google_results?: WebResult[]; amazon_results?: WebResult[] } | undefined
  const modelsUsed = (metadata?.models_used as Array<{ model: string; role: string }>) || []
  const copyPrompt = metadata?.copy_prompt as string | undefined

  const googleResults = webScrape?.google_results || []
  const amazonResults = webScrape?.amazon_results || []
  const amazonVisible = showAllAmazon ? amazonResults : amazonResults.slice(0, 2)

  // Fields enriched at stage 4
  const enrichedFields = iksulaValues.filter(v => v.set_at_stage === 4)
  const reviewCount = enrichedFields.filter(v => v.review_status === 'needs_review' || v.review_status === 'low_confidence').length

  return (
    <div className="space-y-6">
      {/* Completeness Meter */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-gray-900">Field Completeness</span>
          <span className="text-sm font-bold text-green-700">{completeBefore}% → {completeAfter}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
          <div className="h-3 rounded-full bg-gradient-to-r from-amber-400 to-green-500 transition-all duration-1000" style={{ width: `${completeAfter}%` }} />
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-[10px] text-gray-400">Before enrichment</span>
          <span className="text-[10px] text-gray-400">After enrichment</span>
        </div>
      </div>

      {/* Web Scrape Panel */}
      {(googleResults.length > 0 || amazonResults.length > 0) && (
        <div className="bg-white rounded-xl border border-blue-200 overflow-hidden">
          <div className="px-4 py-3 bg-blue-50 border-b border-blue-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9" /></svg>
              <span className="text-xs font-semibold text-blue-800">Web Attribute Extraction</span>
            </div>
            <span className="text-[10px] text-blue-600">{googleResults.length + amazonResults.length} sources scraped</span>
          </div>

          {/* Google Results */}
          {googleResults.length > 0 && (
            <div className="px-4 py-3 border-b border-gray-100">
              <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Google Search — Top {googleResults.length} URLs</p>
              <div className="space-y-2">
                {googleResults.map((r, i) => (
                  <div key={i} className="flex items-start gap-2 p-2 bg-gray-50 rounded-lg">
                    <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-[9px] font-bold mt-0.5 flex-shrink-0">G{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-[10px] text-blue-600 truncate">{r.url}</p>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {Object.entries(r.attrs).map(([k, v]) => (
                          <span key={k} className="px-1.5 py-0.5 bg-green-50 text-green-700 rounded text-[9px]">{k}: {v}</span>
                        ))}
                      </div>
                    </div>
                    <span className="text-[9px] text-gray-400 flex-shrink-0">{Object.keys(r.attrs).length} attrs</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Amazon Results */}
          {amazonResults.length > 0 && (
            <div className="px-4 py-3">
              <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Amazon — Top Results</p>
              <div className="space-y-2">
                {amazonVisible.map((r, i) => (
                  <div key={i} className="flex items-start gap-2 p-2 bg-orange-50/50 rounded-lg">
                    <span className="px-1.5 py-0.5 bg-orange-100 text-orange-700 rounded text-[9px] font-bold mt-0.5 flex-shrink-0">A{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-[10px] text-orange-700 truncate">{r.title || r.url}</p>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {Object.entries(r.attrs).map(([k, v]) => (
                          <span key={k} className="px-1.5 py-0.5 bg-green-50 text-green-700 rounded text-[9px]">{k}: {v}</span>
                        ))}
                      </div>
                    </div>
                    <span className="text-[9px] text-gray-400 flex-shrink-0">{Object.keys(r.attrs).length} attrs</span>
                  </div>
                ))}
              </div>
              {amazonResults.length > 2 && (
                <button onClick={() => setShowAllAmazon(!showAllAmazon)} className="mt-2 text-[10px] text-blue-600 font-medium hover:underline">
                  {showAllAmazon ? 'Show less' : `Show all ${amazonResults.length}`}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Enriched Fields */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-gray-900">Enriched Attributes</h3>
            <span className="px-2 py-0.5 bg-green-50 text-green-700 text-[10px] font-medium rounded-full">{enrichedFields.length} filled</span>
            {reviewCount > 0 && (
              <span className="px-2 py-0.5 bg-amber-50 text-amber-700 text-[10px] font-medium rounded-full">{reviewCount} need review</span>
            )}
          </div>
          {showTech && modelsUsed.length > 0 && (
            <span className="text-[10px] text-gray-400">{modelsUsed.map(m => m.model).join(' · ')}</span>
          )}
        </div>
        <div className="divide-y divide-gray-50">
          {enrichedFields.map((field) => (
            <FieldRow key={field.attribute_code} field={field} onApprove={onApprove} onEdit={onEdit} />
          ))}
        </div>
      </div>

      {/* Copy Generation */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">Generated Copy</h3>
          {showTech && copyPrompt && <span className="text-[10px] text-gray-400">{copyPrompt}</span>}
        </div>
        <div className="p-4 space-y-4">
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-gray-600">Product Title</label>
              <span className="text-[10px] text-gray-400">{(product.product_title || '').length} / 80 chars</span>
            </div>
            <input
              type="text"
              defaultValue={product.product_title || ''}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
            />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-gray-600">Short Description</label>
              <span className="text-[10px] text-gray-400">{(product.short_description || '').length} / 150 chars</span>
            </div>
            <textarea
              rows={2}
              defaultValue={product.short_description || ''}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none"
            />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-gray-600">Long Description</label>
              <span className="text-[10px] text-gray-400">{(product.long_description || '').length} / 400 chars</span>
            </div>
            <textarea
              rows={4}
              defaultValue={product.long_description || ''}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none"
            />
          </div>
        </div>

        {/* Models used panel */}
        {showTech && modelsUsed.length > 0 && (
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-100 rounded-b-xl">
            <p className="text-[10px] font-semibold text-gray-500 mb-2">Models used in this enrichment</p>
            <div className="flex flex-wrap gap-2">
              {modelsUsed.map((m, i) => (
                <span key={i} className="px-2 py-1 bg-white border border-gray-200 rounded text-[10px] text-gray-600">
                  <span className="font-medium text-gray-800">{m.model}</span> — {m.role}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Advance */}
      <div className="flex justify-end">
        <button onClick={onAdvance} className="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 flex items-center gap-1.5">
          Approve & Continue to Validation
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
        </button>
      </div>
    </div>
  )
}
