import { useNavigate } from 'react-router-dom'
import { useProducts, exportProduct } from '../api/products'

export default function PublishedPage() {
  const navigate = useNavigate()
  const { data: products, isLoading } = useProducts('published')

  return (
    <div className="p-4 lg:p-6 max-w-[1400px]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Published Records</h2>
          <p className="text-sm text-gray-500">{products?.length || 0} records published</p>
        </div>
        <button className="px-3 py-2 bg-white border border-gray-200 text-xs font-medium rounded-lg hover:bg-gray-50">Export All CSV</button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        {isLoading ? (
          <div className="p-8 text-center text-sm text-gray-400">Loading...</div>
        ) : !products?.length ? (
          <div className="p-8 text-center text-sm text-gray-400">No published records yet</div>
        ) : (
          <table className="w-full text-xs">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-4 py-2.5 font-medium text-gray-500">Product</th>
                <th className="text-left px-4 py-2.5 font-medium text-gray-500 hidden md:table-cell">Model</th>
                <th className="text-left px-4 py-2.5 font-medium text-gray-500 hidden lg:table-cell">Supplier</th>
                <th className="text-left px-4 py-2.5 font-medium text-gray-500">Score</th>
                <th className="text-left px-4 py-2.5 font-medium text-gray-500 hidden md:table-cell">Published</th>
                <th className="text-right px-4 py-2.5 font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {products.map(p => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{p.product_name || '—'}</td>
                  <td className="px-4 py-3 hidden md:table-cell text-gray-500">{p.model_number}</td>
                  <td className="px-4 py-3 hidden lg:table-cell text-gray-500">{p.supplier_name}</td>
                  <td className="px-4 py-3">
                    <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded font-medium">
                      {p.overall_confidence || p.completeness_pct || '—'}%
                    </span>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell text-gray-500">
                    {p.published_at ? new Date(p.published_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-4 py-3 text-right flex gap-2 justify-end">
                    <button onClick={() => navigate('/pipeline')} className="text-blue-600 font-medium hover:underline">View</button>
                    <button onClick={() => exportProduct(p.id, 'csv')} className="text-gray-500 font-medium hover:underline">CSV</button>
                    <button onClick={() => exportProduct(p.id, 'json')} className="text-gray-500 font-medium hover:underline">JSON</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
