import { create } from 'zustand'

interface PipelineState {
  currentProductId: string | null
  currentStage: number
  isProcessing: boolean
  showTechDetails: boolean
  setProduct: (id: string) => void
  setStage: (stage: number) => void
  setProcessing: (val: boolean) => void
  toggleTechDetails: () => void
}

export const usePipelineStore = create<PipelineState>((set) => ({
  currentProductId: null,
  currentStage: 1,
  isProcessing: false,
  showTechDetails: false,
  setProduct: (id) => set({ currentProductId: id }),
  setStage: (stage) => set({ currentStage: stage }),
  setProcessing: (val) => set({ isProcessing: val }),
  toggleTechDetails: () => set((s) => ({ showTechDetails: !s.showTechDetails })),
}))
