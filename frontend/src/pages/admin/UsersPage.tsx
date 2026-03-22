import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../api/client'
import { useClientStore } from '../../stores/clientStore'

interface User {
  id: string
  email: string
  full_name: string | null
  role: string
  client_id: string | null
  is_active: boolean
  last_active_at: string | null
  created_at: string | null
}

const ROLE_COLORS: Record<string, string> = {
  admin: 'bg-blue-100 text-blue-700',
  reviewer: 'bg-amber-100 text-amber-700',
  viewer: 'bg-gray-100 text-gray-600',
}

export default function UsersPage() {
  const qc = useQueryClient()
  const { clients } = useClientStore()
  const [showInvite, setShowInvite] = useState(false)
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [role, setRole] = useState('reviewer')
  const [userClientId, setUserClientId] = useState('')

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: () => api.get('/admin/users').then(r => r.data as User[]),
  })

  const inviteMutation = useMutation({
    mutationFn: () => api.post('/admin/users', { email, full_name: name, role, client_id: userClientId || null, password: 'changeme123' }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); setShowInvite(false); setEmail(''); setName('') },
  })

  return (
    <div className="p-4 lg:p-6 max-w-[1400px]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">User Management</h2>
          <p className="text-sm text-gray-500">Manage users, roles, and client access</p>
        </div>
        <button onClick={() => setShowInvite(true)} className="px-3 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700">+ Invite User</button>
      </div>

      {showInvite && (
        <div className="bg-white rounded-xl border border-blue-200 p-4 mb-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Invite New User</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            <div><label className="text-xs text-gray-600 block mb-1">Email</label><input type="email" value={email} onChange={e => setEmail(e.target.value)} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm outline-none" /></div>
            <div><label className="text-xs text-gray-600 block mb-1">Full Name</label><input type="text" value={name} onChange={e => setName(e.target.value)} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm outline-none" /></div>
            <div><label className="text-xs text-gray-600 block mb-1">Role</label>
              <select value={role} onChange={e => setRole(e.target.value)} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm outline-none bg-white">
                <option value="admin">Admin</option><option value="reviewer">Reviewer</option><option value="viewer">Viewer</option>
              </select>
            </div>
            <div><label className="text-xs text-gray-600 block mb-1">Client</label>
              <select value={userClientId} onChange={e => setUserClientId(e.target.value)} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm outline-none bg-white">
                <option value="">All clients (super admin)</option>
                {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="flex items-end gap-2">
              <button onClick={() => inviteMutation.mutate()} disabled={!email} className="px-4 py-2 bg-blue-600 text-white text-xs font-medium rounded-lg disabled:opacity-50">Invite</button>
              <button onClick={() => setShowInvite(false)} className="px-4 py-2 bg-white border border-gray-200 text-xs font-medium rounded-lg">Cancel</button>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-4 py-2.5 font-medium text-gray-500">User</th>
              <th className="text-left px-4 py-2.5 font-medium text-gray-500">Role</th>
              <th className="text-left px-4 py-2.5 font-medium text-gray-500 hidden md:table-cell">Client</th>
              <th className="text-left px-4 py-2.5 font-medium text-gray-500">Status</th>
              <th className="text-right px-4 py-2.5 font-medium text-gray-500">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {users?.map(u => (
              <tr key={u.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-[10px] font-bold text-blue-700">{u.full_name?.split(' ').map(n => n[0]).join('') || '?'}</span>
                    </div>
                    <div><p className="font-medium">{u.full_name || '—'}</p><p className="text-[10px] text-gray-400">{u.email}</p></div>
                  </div>
                </td>
                <td className="px-4 py-3"><span className={`px-2 py-0.5 rounded font-medium ${ROLE_COLORS[u.role]}`}>{u.role}</span></td>
                <td className="px-4 py-3 hidden md:table-cell text-gray-500">{clients.find(c => c.id === u.client_id)?.name || 'All'}</td>
                <td className="px-4 py-3"><span className={`w-2 h-2 rounded-full inline-block ${u.is_active ? 'bg-green-500' : 'bg-gray-300'}`} /> {u.is_active ? 'Active' : 'Inactive'}</td>
                <td className="px-4 py-3 text-right"><button className="text-blue-600 font-medium hover:underline">Edit</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
