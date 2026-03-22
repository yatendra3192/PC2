import { useEffect, useState } from 'react'
import { useProduct, useAdvanceProduct, useEditField, usePublishProduct, exportProduct } from '../api/products'
import { useRunStage } from '../api/pipeline'
import { usePipelineStore } from '../stores/pipelineStore'
import StepperBar from '../components/pipeline/StepperBar'
import FieldRow from '../components/pipeline/FieldRow'
import ActionBar from '../components/pipeline/ActionBar'
import Stage2Classify from '../stages/Stage2Classify'
import Stage3Dedup from '../stages/Stage3Dedup'
import Stage4Enrich from '../stages/Stage4Enrich'
import Stage5Validate from '../stages/Stage5Validate'
import Stage6Transform from '../stages/Stage6Transform'
import Stage7Review from '../stages/Stage7Review'

// Missing fields that Stage 1 won't find (will be enriched in Stage 4)
const MISSING_ATTRS = [
  { attribute_code: 'material', attribute_name: 'Material' },
  { attribute_code: 'colour', attribute_name: 'Colour' },
  { attribute_code: 'weight_kg', attribute_name: 'Weight' },
  { attribute_code: 'shipping_weight_kg', attribute_name: 'Shipping Weight' },
  { attribute_code: 'width_cm', attribute_name: 'Width' },
  { attribute_code: 'depth_cm', attribute_name: 'Depth' },
  { attribute_code: 'height_cm', attribute_name: 'Height' },
  { attribute_code: 'operating_temp_min_c', attribute_name: 'Operating Temp Min' },
  { attribute_code: 'operating_temp_max_c', attribute_name: 'Operating Temp Max' },
  { attribute_code: 'certifications', attribute_name: 'Certifications' },
  { attribute_code: 'compatible_valve_types', attribute_name: 'Compatible Valve Types' },
  { attribute_code: 'app_name', attribute_name: 'Connected App Name' },
  { attribute_code: 'warranty_months', attribute_name: 'Warranty' },
]

export default function PipelinePage() {
  const productId = usePipelineStore(s => s.currentProductId)
  const currentStage = usePipelineStore(s => s.currentStage)
  const setStage = usePipelineStore(s => s.setStage)
  const showTech = usePipelineStore(s => s.showTechDetails)
  const toggleTech = usePipelineStore(s => s.toggleTechDetails)

  const { data: product, isLoading } = useProduct(productId)
  const advanceMutation = useAdvanceProduct()
  const editMutation = useEditField()
  const publishMutation = usePublishProduct()
  const runStageMutation = useRunStage()
  const [stageMetadata, setStageMetadata] = useState<Record<string, unknown>>({})

  // Sync stage from product
  useEffect(() => {
    if (product) setStage(product.current_stage)
  }, [product, setStage])

  if (!productId) {
    return (
      <div className="p-4 lg:p-6 max-w-[1400px]">
        <h2 className="text-xl font-bold text-gray-900">Item Pipeline</h2>
        <p className="text-sm text-gray-500 mt-1">No product selected. Upload a file first.</p>
        <div className="mt-8 flex items-center justify-center p-12 bg-white rounded-xl border border-gray-200 border-dashed">
          <p className="text-gray-400 text-sm">Go to Bulk Upload to upload a file and start processing</p>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="p-4 lg:p-6 flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Loading product...</p>
        </div>
      </div>
    )
  }

  if (!product) return null

  const iksulaValues = product.iksula_values || []
  const foundCodes = new Set(iksulaValues.map(v => v.attribute_code))
  const missingFields = MISSING_ATTRS.filter(a => !foundCodes.has(a.attribute_code))

  const reviewCount = iksulaValues.filter(v => v.review_status === 'needs_review' || v.review_status === 'low_confidence').length
  const approvedCount = iksulaValues.filter(v => v.review_status === 'auto_approved' || v.review_status === 'human_approved').length
  const failCount = 0

  const handleApprove = (_code: string) => {
    // In full implementation, this would call a per-field approve endpoint
  }

  const handleEdit = (code: string, value: string) => {
    if (productId) editMutation.mutate({ productId, attributeCode: code, value })
  }

  const handleAdvance = async () => {
    if (!productId) return
    // Approve current stage
    await advanceMutation.mutateAsync(productId)
    const nextStage = currentStage + 1
    if (nextStage <= 7) {
      // Run next stage processor
      try {
        const result = await runStageMutation.mutateAsync({ productId, stageNum: nextStage })
        setStageMetadata(result.metadata || {})
        setStage(nextStage)
      } catch {
        // Stage processor not available yet — just advance the UI
        setStage(nextStage)
      }
    }
  }

  const handleDedupResolve = async (decision: string) => {
    if (!productId) return
    // For demo, any decision advances to stage 4
    await advanceMutation.mutateAsync(productId)
    try {
      const result = await runStageMutation.mutateAsync({ productId, stageNum: 4 })
      setStageMetadata(result.metadata || {})
    } catch { /* stage 4 not ready yet */ }
    setStage(4)
  }

  return (
    <div className="p-4 lg:p-6 max-w-[1400px]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900">{product.product_name || 'Processing...'}</h2>
          <p className="text-xs text-gray-500">
            {product.model_number && `Model ${product.model_number} · `}
            {product.supplier_name || 'Unknown supplier'}
            {product.completeness_pct != null && ` · ${product.completeness_pct}% complete`}
          </p>
        </div>
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" checked={showTech} onChange={toggleTech} className="w-3.5 h-3.5 rounded border-gray-300 text-blue-600" />
          <span className="text-[10px] text-gray-500">Technical details</span>
        </label>
      </div>

      {/* Stepper */}
      <StepperBar
        currentStage={currentStage}
        completedStages={Array.from({ length: currentStage - 1 }, (_, i) => i + 1)}
        reviewCounts={{ [currentStage]: reviewCount }}
        onStageClick={setStage}
      />

      {/* Stage content — renders different UI per stage */}
      {currentStage === 1 && (
        <div className="bg-white rounded-xl border border-gray-200 mb-4">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-gray-900">Stage 1 — Extracted Fields</h3>
              <span className="px-2 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-medium rounded-full">
                {iksulaValues.length} found · {missingFields.length} missing
              </span>
            </div>
            {showTech && (
              <span className="text-[10px] text-gray-400">Models: Iksula OCR Engine v2 + GPT-4o</span>
            )}
          </div>
          <div className="divide-y divide-gray-50">
            {iksulaValues.map((field) => (
              <FieldRow key={field.attribute_code} field={field} onApprove={handleApprove} onEdit={handleEdit} />
            ))}
            {missingFields.length > 0 && (
              <>
                <div className="px-4 py-2 bg-amber-50/50">
                  <span className="text-[10px] font-semibold text-amber-700 uppercase tracking-wider">Missing — will enrich in Stage 4</span>
                </div>
                {missingFields.map((attr) => (
                  <FieldRow key={attr.attribute_code} field={{ ...attr, value: null, source: 'not_found' as const, confidence: 0, review_status: 'pending' } as any} onEdit={handleEdit} />
                ))}
              </>
            )}
          </div>
        </div>
      )}

      {currentStage === 2 && (
        <Stage2Classify
          metadata={stageMetadata}
          onApprove={handleAdvance}
        />
      )}

      {currentStage === 3 && (
        <Stage3Dedup
          metadata={stageMetadata}
          onResolve={handleDedupResolve}
        />
      )}

      {currentStage === 4 && product && (
        <Stage4Enrich
          metadata={stageMetadata}
          iksulaValues={iksulaValues}
          product={product}
          onApprove={handleApprove}
          onEdit={handleEdit}
          onAdvance={handleAdvance}
        />
      )}

      {currentStage === 5 && (
        <Stage5Validate
          metadata={stageMetadata}
          onAdvance={handleAdvance}
          onFixField={(field, value) => handleEdit(field, value)}
        />
      )}

      {currentStage === 6 && (
        <Stage6Transform
          metadata={stageMetadata}
          clientValues={product?.client_values || []}
          onAdvance={handleAdvance}
          onMapField={(_iksula, _client) => { /* mapping correction — Phase 7 admin */ }}
        />
      )}

      {currentStage === 7 && product && (
        <Stage7Review
          metadata={stageMetadata}
          iksulaValues={iksulaValues}
          product={product}
          onApprove={handleApprove}
          onEdit={handleEdit}
          onPublish={() => productId && publishMutation.mutate(productId)}
          onExport={(format) => productId && exportProduct(productId, format)}
        />
      )}

      {/* Action bar */}
      <ActionBar
        reviewCount={reviewCount}
        approvedCount={approvedCount}
        failCount={failCount}
        onApproveAll={() => {}}
        onNext={handleAdvance}
        isFirst={currentStage === 1}
        isLast={currentStage === 7}
      />
    </div>
  )
}
