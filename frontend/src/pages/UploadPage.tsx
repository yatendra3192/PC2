import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useBatches, useUploadBatch, useProcessBatch } from '../api/products'
import { usePipelineStore } from '../stores/pipelineStore'
import { useClientStore } from '../stores/clientStore'

export default function UploadPage() {
  const [dragActive, setDragActive] = useState(false)
  const activeClientId = useClientStore(s => s.activeClientId)
  const activeClient = useClientStore(s => s.activeClient)
  const { data: batches } = useBatches()
  const uploadMutation = useUploadBatch()
  const processMutation = useProcessBatch()
  const navigate = useNavigate()
  const setProduct = usePipelineStore(s => s.setProduct)

  const handleFile = useCallback(async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('client_id', activeClientId || '')

    try {
      const batch = await uploadMutation.mutateAsync(formData)
      // Auto-process
      const result = await processMutation.mutateAsync(batch.id)
      // Navigate to the first product
      if (result.results?.length > 0) {
        setProduct(result.results[0].product_id)
        navigate(`/batch?id=${batch.id}`)
      }
    } catch (err) {
      console.error('Upload failed:', err)
    }
  }, [uploadMutation, processMutation, navigate, setProduct])

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0])
  }

  const statusColors: Record<string, string> = {
    queued: 'bg-gray-100 text-gray-600',
    processing: 'bg-blue-100 text-blue-700',
    complete: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-600',
  }

  return (
    <div className="p-4 lg:p-6 max-w-[1400px]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Bulk Upload</h2>
          <p className="text-sm text-gray-500">
            Upload supplier batches for <span className="font-medium text-gray-700">{activeClient?.name || 'unknown client'}</span>
          </p>
        </div>
      </div>

      {/* Upload Zone */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div
          className={`border-2 border-dashed rounded-xl p-10 text-center transition cursor-pointer ${
            dragActive ? 'border-blue-400 bg-blue-50' : 'border-blue-300 bg-blue-50/50 hover:border-blue-400'
          }`}
          onDragOver={(e) => { e.preventDefault(); setDragActive(true) }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          onClick={() => document.getElementById('fileInput')?.click()}
        >
          <input
            id="fileInput"
            type="file"
            className="hidden"
            accept=".pdf,.csv,.xlsx,.xls,.jpg,.png"
            onChange={(e) => { if (e.target.files?.[0]) handleFile(e.target.files[0]) }}
          />
          <div className="w-16 h-16 mx-auto bg-blue-100 rounded-2xl flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <p className="text-sm font-medium text-gray-700">
            {uploadMutation.isPending ? 'Uploading...' : processMutation.isPending ? 'Processing...' : 'Drag & drop files here to upload'}
          </p>
          <p className="text-xs text-gray-400 mt-1">PDF, CSV, XLSX, Images — Max 50MB each</p>
          {!uploadMutation.isPending && !processMutation.isPending && (
            <button className="mt-4 px-6 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">
              Browse Files
            </button>
          )}
        </div>
      </div>

      {/* Batch Queue */}
      {batches && batches.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-100">
            <h3 className="text-sm font-semibold text-gray-900">Batch Queue</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-4 py-2.5 font-medium text-gray-500">File</th>
                  <th className="text-left px-4 py-2.5 font-medium text-gray-500">Items</th>
                  <th className="text-left px-4 py-2.5 font-medium text-gray-500">Status</th>
                  <th className="text-left px-4 py-2.5 font-medium text-gray-500 hidden md:table-cell">Uploaded</th>
                  <th className="text-right px-4 py-2.5 font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {batches.map((b) => (
                  <tr key={b.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{b.file_name}</td>
                    <td className="px-4 py-3">{b.item_count || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded font-medium ${statusColors[b.status] || 'bg-gray-100'}`}>
                        {b.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell text-gray-500">
                      {new Date(b.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {b.status === 'complete' && (
                        <button className="text-blue-600 font-medium hover:underline" onClick={() => navigate(`/batch?id=${b.id}`)}>
                          View
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
