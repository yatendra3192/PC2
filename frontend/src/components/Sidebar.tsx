import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { useClientStore } from '../stores/clientStore'

const mainLinks = [
  { path: '/dashboard', label: 'Dashboard', icon: 'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z' },
  { path: '/upload', label: 'Bulk Upload', icon: 'M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12', badge: '3' },
  { path: '/pipeline', label: 'Item Pipeline', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' },
  { path: '/review', label: 'HIL Review Queue', icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z', badge: '24' },
  { path: '/published', label: 'Published Records', icon: 'M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4' },
]

const adminLinks = [
  { path: '/admin/clients', label: 'Client Management', icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4' },
  { path: '/admin/users', label: 'User Management', icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z' },
  { path: '/admin/confidence', label: 'Confidence Config', icon: 'M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4' },
  { path: '/admin/models', label: 'Model Registry', icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' },
  { path: '/admin/templates', label: 'Templates', icon: 'M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm0 8a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6z' },
  { path: '/admin/pipeline', label: 'Pipeline Config', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' },
  { path: '/admin/audit', label: 'Audit Logs', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01' },
]

function NavLink({ path, label, icon, badge }: { path: string; label: string; icon: string; badge?: string }) {
  const location = useLocation()
  const navigate = useNavigate()
  const active = location.pathname === path

  return (
    <button
      onClick={() => navigate(path)}
      className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-[13px] transition-all ${
        active ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
      }`}
    >
      <svg className="w-[18px] h-[18px] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={icon} />
      </svg>
      <span className="flex-1 text-left">{label}</span>
      {badge && (
        <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded-full ${
          active ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
        }`}>{badge}</span>
      )}
    </button>
  )
}

export default function Sidebar() {
  const { user, logout } = useAuthStore()
  const { clients, activeClientId, setActiveClient, loadClients } = useClientStore()
  const navigate = useNavigate()
  const isAdmin = user?.role === 'admin'

  useEffect(() => {
    loadClients()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <aside className="w-[240px] bg-white border-r border-gray-200 flex flex-col flex-shrink-0 h-screen sticky top-0 overflow-y-auto hidden md:flex">
      {/* Logo */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-blue-700 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-xs">PC2</span>
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900 leading-tight">Product Content</p>
            <p className="text-[10px] text-gray-400">Creator v2.0</p>
          </div>
        </div>
      </div>

      {/* Client Selector */}
      <div className="px-3 py-3 border-b border-gray-100">
        <label className="text-[10px] text-gray-400 font-medium uppercase tracking-wider">Client</label>
        <select
          className="w-full mt-1 text-xs font-medium bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1.5 outline-none cursor-pointer text-gray-800"
          value={activeClientId || ''}
          onChange={(e) => setActiveClient(e.target.value)}
        >
          {clients.map(c => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        <p className="text-[10px] text-gray-400 font-medium uppercase tracking-wider px-3 mb-2">Main</p>
        {mainLinks.map((link) => (
          <NavLink key={link.path} {...link} />
        ))}

        {isAdmin && (
          <>
            <p className="text-[10px] text-gray-400 font-medium uppercase tracking-wider px-3 mb-2 mt-6">Admin</p>
            {adminLinks.map((link) => (
              <NavLink key={link.path} {...link} />
            ))}
          </>
        )}
      </nav>

      {/* User footer */}
      <div className="p-3 border-t border-gray-100">
        <div className="flex items-center gap-2.5 px-2 py-2">
          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
            <span className="text-xs font-semibold text-blue-700">
              {user?.full_name?.split(' ').map(n => n[0]).join('') || '?'}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-gray-900 truncate">{user?.full_name || 'User'}</p>
            <p className="text-[10px] text-gray-400 capitalize">{user?.role}</p>
          </div>
          <button
            onClick={() => { logout(); navigate('/login') }}
            className="text-gray-400 hover:text-gray-600"
            title="Sign out"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>
    </aside>
  )
}
