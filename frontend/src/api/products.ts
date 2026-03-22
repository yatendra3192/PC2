import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from './client'

export interface ProductRawValue {
  id: string
  supplier_field_name: string
  raw_value: string | null
  source: string
  source_page_ref: string | null
  extraction_model: string | null
  extraction_confidence: number | null
}

export interface ProductIksulaValue {
  id: string
  attribute_id: string
  attribute_code: string
  attribute_name: string
  unit: string | null
  value_text: string | null
  value_numeric: number | null
  value_boolean: boolean | null
  value_array: string[] | null
  source: string
  model_name: string | null
  raw_extracted: string | null
  confidence: number
  confidence_breakdown: Record<string, number> | null
  review_status: string
  set_at_stage: number
}

export interface Product {
  id: string
  client_id: string
  batch_id: string | null
  product_name: string | null
  model_number: string | null
  supplier_name: string | null
  brand: string | null
  current_stage: number
  status: string
  completeness_pct: number | null
  overall_confidence: number | null
  published_at: string | null
  stage_metadata: Record<string, unknown>
  product_title: string | null
  short_description: string | null
  long_description: string | null
  raw_values: ProductRawValue[]
  iksula_values: ProductIksulaValue[]
  client_values: Array<{
    client_field_name: string
    client_value: string
    iksula_raw_value: string | null
    transform_applied: string | null
    review_status: string
  }>
}

export interface Batch {
  id: string
  client_id: string
  file_name: string
  file_type: string
  item_count: number | null
  processed_count: number
  status: string
  created_at: string
}

export function useProducts(status?: string) {
  return useQuery({
    queryKey: ['products', status],
    queryFn: () => api.get<Product[]>('/products', { params: { status } }).then(r => r.data),
  })
}

export function useProduct(id: string | null) {
  return useQuery({
    queryKey: ['product', id],
    queryFn: () => api.get<Product>(`/products/${id}`).then(r => r.data),
    enabled: !!id,
  })
}

export function useBatches() {
  return useQuery({
    queryKey: ['batches'],
    queryFn: () => api.get<Batch[]>('/batches').then(r => r.data),
  })
}

export function useUploadBatch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (formData: FormData) => api.post<Batch>('/batches', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['batches'] })
    },
  })
}

export function useProcessBatch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (batchId: string) => api.post(`/batches/${batchId}/process`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['batches'] })
      qc.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

export function useAdvanceProduct() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (productId: string) => api.post(`/products/${productId}/advance`).then(r => r.data),
    onSuccess: (_, productId) => {
      qc.invalidateQueries({ queryKey: ['product', productId] })
    },
  })
}

export function useEditField() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ productId, attributeCode, value }: { productId: string; attributeCode: string; value: string }) =>
      api.patch(`/products/${productId}/fields/${attributeCode}`, null, { params: { value } }).then(r => r.data),
    onSuccess: (_, { productId }) => {
      qc.invalidateQueries({ queryKey: ['product', productId] })
    },
  })
}

export function usePublishProduct() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (productId: string) =>
      api.post(`/products/${productId}/publish`, { target: 'staging' }).then(r => r.data),
    onSuccess: (_, productId) => {
      qc.invalidateQueries({ queryKey: ['product', productId] })
      qc.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

export function exportProduct(productId: string, format: string) {
  window.open(`/api/v1/products/${productId}/export?format=${format}`, '_blank')
}
