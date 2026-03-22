import { useMutation, useQueryClient } from '@tanstack/react-query'
import api from './client'

export interface StageRunResult {
  product_id: string
  stage: number
  status: string
  fields_count: number
  fields_needing_review: number
  fields_auto_approved: number
  metadata: Record<string, unknown>
}

export function useRunStage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ productId, stageNum }: { productId: string; stageNum: number }) =>
      api.post<StageRunResult>(`/pipeline/${productId}/run-stage/${stageNum}`).then(r => r.data),
    onSuccess: (_, { productId }) => {
      qc.invalidateQueries({ queryKey: ['product', productId] })
    },
  })
}
