import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from './client'

export interface ReviewItem {
  id: string
  product_id: string
  product_name: string | null
  model_number: string | null
  attribute_code: string
  attribute_name: string
  value: string | null
  unit: string | null
  source: string
  model_name: string | null
  confidence: number
  review_status: string
  stage: number
  batch_name: string | null
}

export interface ReviewProductCard {
  product_id: string
  product_name: string | null
  model_number: string | null
  brand: string | null
  image_url: string | null
  completeness_pct: number | null
  product_title: string | null
  short_description: string | null
  attributes: Array<{
    id: string
    code: string
    name: string
    value: string | null
    unit: string | null
    group: string | null
    mandatory: boolean
    source: string
    confidence: number
    status: string
  }>
  review_items: Array<Record<string, unknown>>
  total_fields: number
  auto_approved: number
  needs_review: number
  human_approved: number
}

export interface ReviewStats {
  total_pending: number
  must_fix: number
  low_confidence: number
  needs_review: number
  auto_approved: number
  human_approved: number
  human_edited: number
}

export function useReviewQueue(filters?: Record<string, string | number>) {
  return useQuery({
    queryKey: ['review-queue', filters],
    queryFn: () => api.get<ReviewItem[]>('/review/queue', { params: filters }).then(r => r.data),
  })
}

export function useReviewProductCard(productId: string | null) {
  return useQuery({
    queryKey: ['review-product', productId],
    queryFn: () => api.get<ReviewProductCard>(`/review/product/${productId}`).then(r => r.data),
    enabled: !!productId,
  })
}

export function useReviewStats() {
  return useQuery({
    queryKey: ['review-stats'],
    queryFn: () => api.get<ReviewStats>('/review/stats').then(r => r.data),
  })
}

export function useBulkApprove() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (fieldIds: string[]) => api.post('/review/approve', { field_ids: fieldIds }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review-queue'] })
      qc.invalidateQueries({ queryKey: ['review-stats'] })
      qc.invalidateQueries({ queryKey: ['review-product'] })
    },
  })
}

export function useBulkReject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ fieldIds, reason }: { fieldIds: string[]; reason: string }) =>
      api.post('/review/reject', { field_ids: fieldIds, reason }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review-queue'] })
      qc.invalidateQueries({ queryKey: ['review-stats'] })
    },
  })
}

export function useEditAndApprove() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ fieldId, value, reason }: { fieldId: string; value: string; reason?: string }) =>
      api.post(`/review/${fieldId}/edit`, { value, reason }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review-queue'] })
      qc.invalidateQueries({ queryKey: ['review-stats'] })
      qc.invalidateQueries({ queryKey: ['review-product'] })
    },
  })
}
