import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../api/client'
import { useClientStore } from '../../stores/clientStore'

const STAGES = [
  { num: 1, label: 'Ingestion', locked: true },
  { num: 2, label: 'Categorisation', locked: false },
  { num: 3, label: 'Deduplication', locked: false },
  { num: 4, label: 'Enrichment', locked: false },
  { num: 5, label: 'DIM Validation', locked: false },
  { num: 6, label: 'Template Transformation', locked: false },
  { num: 7, label: 'Review & Publish', locked: true },
]

export default function PipelineConfigPage() {
  const clientId = useClientStore(s => s.activeClientId)
  const clientName = useClientStore(s => s.activeClient?.name)
  const qc = useQueryClient()

  const { data: config } = useQuery({
    queryKey: ['pipeline-config', clientId],
    queryFn: () => api.get(`/admin/pipeline/${clientId}`).then(r => r.data),
    enabled: !!clientId,
  })

  const saveMutation = useMutation({
    mutationFn: (stages: Record<string, boolean>) => api.put(`/admin/pipeline/${clientId}`, { stages_enabled: stages }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline-config'] }),
  })

  const stagesEnabled = config?.stages_enabled || {}

  const toggleStage = (num: number) => {
    const updated = { ...stagesEnabled, [String(num)]: !stagesEnabled[String(num)] }
    saveMutation.mutate(updated)
  }

  return (
    <div className="p-4 lg:p-6 max-w-[1400px]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Pipeline Configuration</h2>
          <p className="text-sm text-gray-500">Toggle stages for <span className="font-medium">{clientName}</span></p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="space-y-3">
          {STAGES.map(stage => {
            const enabled = stagesEnabled[String(stage.num)] !== false
            return (
              <div key={stage.num} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${enabled ? 'bg-blue-600 text-white' : 'bg-gray-300 text-gray-500'}`}>{stage.num}</span>
                  <div>
                    <span className="text-sm font-medium text-gray-900">{stage.label}</span>
                    {stage.locked && <span className="text-[10px] text-gray-400 ml-2">(always enabled)</span>}
                  </div>
                </div>
                <button
                  onClick={() => !stage.locked && toggleStage(stage.num)}
                  disabled={stage.locked}
                  className={`w-10 h-5 rounded-full relative transition ${enabled ? 'bg-blue-600' : 'bg-gray-300'} ${stage.locked ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
                >
                  <div className={`w-4 h-4 bg-white rounded-full absolute top-0.5 shadow transition ${enabled ? 'right-0.5' : 'left-0.5'}`} />
                </button>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
