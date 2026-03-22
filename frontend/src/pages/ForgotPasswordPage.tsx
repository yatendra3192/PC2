import { useState } from 'react'
import { Link } from 'react-router-dom'

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false)

  if (sent) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-blue-950 via-blue-900 to-slate-900">
        <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8 text-center">
          <div className="w-16 h-16 mx-auto bg-green-100 rounded-2xl flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
          </div>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Check your email</h2>
          <p className="text-sm text-gray-500 mb-6">We've sent a password reset link to your email address.</p>
          <Link to="/login" className="text-sm text-blue-600 font-medium hover:underline">Back to login</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-blue-950 via-blue-900 to-slate-900">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8">
        <Link to="/login" className="text-xs text-gray-500 hover:text-gray-700 mb-4 flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
          Back to login
        </Link>
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Reset your password</h2>
        <p className="text-sm text-gray-500 mb-6">Enter your email and we'll send a reset link.</p>
        <form onSubmit={(e) => { e.preventDefault(); setSent(true) }} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">Email address</label>
            <input type="email" placeholder="you@company.com" className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none" required />
          </div>
          <button type="submit" className="w-full py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition">Send Reset Link</button>
        </form>
      </div>
    </div>
  )
}
