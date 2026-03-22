import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../api/client'
import { useClientStore } from '../../stores/clientStore'

export default function TemplatesPage() {
  const clientId = useClientStore(s => s.activeClientId)
  const clientName = useClientStore(s => s.activeClient?.name)
  const qc = useQueryClient()
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [templateName, setTemplateName] = useState('')

  const { data: templates } = useQuery({
    queryKey: ['templates'],
    queryFn: () => api.get('/templates').then(r => r.data),
  })

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!uploadFile || !clientId) return
      const formData = new FormData()
      formData.append('file', uploadFile)
      formData.append('client_id', clientId)
      formData.append('taxonomy_node_id', '33333333-3333-3333-3333-444444444444') // Smart Controllers for demo
      formData.append('template_name', templateName || uploadFile.name)
      return api.post('/templates/upload-and-map', formData, { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data)
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['templates'] })
      setUploadFile(null)
      setTemplateName('')
      if (data) alert(`Mapping complete: ${data.mapping_result?.mapped} fields auto-mapped, ${data.mapping_result?.unmapped} need manual mapping`)
    },
  })

  const clientTemplates = (templates as Array<Record<string, unknown>>)?.filter(t => t.client_id === clientId) || []

  return (
    <div className="p-4 lg:p-6 max-w-[1400px]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Retailer Templates</h2>
          <p className="text-sm text-gray-500">Manage output templates for <span className="font-medium">{clientName}</span></p>
        </div>
      </div>

      {/* Upload new template */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Upload Client Template (CSV)</h3>
        <p className="text-xs text-gray-500 mb-3">Upload a CSV with the client's column headers. AI will auto-map fields to Iksula normalised attributes.</p>
        <div className="flex flex-col sm:flex-row gap-3">
          <input type="text" placeholder="Template name" value={templateName} onChange={e => setTemplateName(e.target.value)} className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm outline-none" />
          <input type="file" accept=".csv" onChange={e => setUploadFile(e.target.files?.[0] || null)} className="text-xs" />
          <button onClick={() => uploadMutation.mutate()} disabled={!uploadFile || uploadMutation.isPending} className="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap">
            {uploadMutation.isPending ? 'Mapping...' : 'Upload & Auto-Map'}
          </button>
        </div>
      </div>

      {/* Template cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {clientTemplates.map(t => (
          <div key={t.id as string} className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-bold text-gray-900">{t.template_name as string}</h4>
              <span className="px-2 py-0.5 bg-green-100 text-green-700 text-[10px] font-medium rounded">{t.is_active ? 'Active' : 'Inactive'}</span>
            </div>
            <div className="space-y-1 text-[10px] text-gray-500 mb-3">
              <p>Version: <span className="font-medium text-gray-700">{t.version as string}</span></p>
              <p>Maintained by: <span className="font-medium text-gray-700">{t.maintained_by as string}</span></p>
              <p>Last updated: <span className="font-medium text-gray-700">{t.last_updated ? new Date(t.last_updated as string).toLocaleDateString() : '—'}</span></p>
              <p>Export formats: <span className="font-medium text-gray-700">{(t.export_formats as string[])?.join(', ')}</span></p>
            </div>
            <div className="flex gap-2 pt-2 border-t border-gray-100">
              <button className="text-xs text-blue-600 font-medium hover:underline">View Mappings</button>
              <button className="text-xs text-gray-500 hover:underline">Preview</button>
              <button className="text-xs text-gray-500 hover:underline">Export Schema</button>
            </div>
          </div>
        ))}
        {clientTemplates.length === 0 && (
          <div className="col-span-2 p-8 text-center bg-white rounded-xl border border-dashed border-gray-300">
            <p className="text-sm text-gray-400">No templates for this client. Upload one above.</p>
          </div>
        )}
      </div>
    </div>
  )
}
