/* eslint-disable prettier/prettier */
/* src/components/Login.tsx ********************************************* */
import { useEffect, useState, FormEvent } from 'react'
import {
  EyeIcon,
  EyeSlashIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/solid'
import { motion } from 'framer-motion'

/* ------------------------------------------------------------------ */
/*  Hard-coded demo credentials                                       */
/* ------------------------------------------------------------------ */
const USERS = [
  { username: 'nafe',  password: '0597785625' },
  { username: 'abood', password: '0597785625' },
  { username: 'ody',   password: '0597785625' },
  { username: 'admin', password: '1234' },
]

/* ------------------------------------------------------------------ */
/*  Animated traffic-light logo                                       */
/* ------------------------------------------------------------------ */
const TrafficLight = () => {
  const cycle: Array<'red' | 'yellow' | 'green' | 'yellow'> = [
    'red',
    'yellow',
    'green',
    'yellow',
  ]
  const [idx, setIdx] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setIdx((v) => (v + 1) % cycle.length), 700)
    return () => clearInterval(id)
  }, [])
  const active = cycle[idx]
  const cls = {
    red: 'bg-signal-red',
    yellow: 'bg-signal-yellow',
    green: 'bg-signal-green',
  } as const

  return (
    <div className="mx-auto mb-8 w-24 rounded-2xl bg-gray-900 p-3 shadow-inner flex flex-col gap-2">
      {(Object.keys(cls) as Array<keyof typeof cls>).map((c) => (
        <div
          key={c}
          className={`h-5 rounded-lg transition-all duration-300
                      ${cls[c]} ${active === c ? 'opacity-100 scale-105' : 'opacity-25'}`}
        />
      ))}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Main component                                                    */
/* ------------------------------------------------------------------ */
type Props = { onLogin: (username: string) => void }

export default function Login({ onLogin }: Props) {
  const [username, setUsername] = useState(
    localStorage.getItem('rememberUser') ?? '',
  )
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(
    Boolean(localStorage.getItem('rememberUser')),
  )
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    await new Promise((r) => setTimeout(r, 600)) // fake latency

    const ok = USERS.some(
      (u) => u.username === username && u.password === password,
    )
    if (ok) {
      remember
        ? localStorage.setItem('rememberUser', username)
        : localStorage.removeItem('rememberUser')
      onLogin(username)
    } else {
      setError('Invalid username or password')
      setLoading(false)
    }
  }

  return (
    <div className="md:flex h-screen overflow-hidden">
      {/* ░░░ Illustration column ░░░ */}
      <div className="hidden md:block w-1/2 h-full relative overflow-hidden">
        <img
          src="/traffic-light.png"
          alt="Intersection illustration"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-black/20" />
        <div className="absolute left-8 bottom-8 text-white space-y-2">
          <h1 className="text-3xl font-heading tracking-tight">Smart Traffic</h1>
          <p className="max-w-xs text-sm text-gray-200/90">
            Keep the city moving.
          </p>
        </div>
      </div>

      {/* ░░░ Form column (scrollbar removed) ░░░ */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-sm bg-white dark:bg-gray-800 rounded-xl shadow-card p-8"
        >
          <TrafficLight />

          <h2 className="text-center text-2xl font-heading mb-6">
            Sign in to <span className="text-signal-blue">Smart{' '}Traffic</span>
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username */}
            <div>
              <label className="block text-sm font-medium mb-1">Username</label>
              <input
                aria-invalid={!!error}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-700
                           bg-gray-50 dark:bg-gray-900/40 px-3 py-2
                           focus:outline-none focus:ring-2 focus:ring-signal-blue"
                placeholder="johndoe"
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium mb-1">Password</label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-700
                             bg-gray-50 dark:bg-gray-900/40 px-3 py-2 pr-10
                             focus:outline-none focus:ring-2 focus:ring-signal-blue"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPw((s) => !s)}
                  className="absolute inset-y-0 right-0 px-2 text-gray-500 hover:text-signal-blue"
                >
                  {showPw ? (
                    <EyeSlashIcon className="w-5 h-5" />
                  ) : (
                    <EyeIcon className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>

            {/* Remember me */}
            <label className="flex items-center gap-2 text-sm select-none">
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
                className="h-4 w-4 accent-signal-blue rounded"
              />
              Remember me
            </label>

            {/* Feedback */}
            <p
              className={`h-5 text-sm text-center ${
                error ? 'text-signal-red' : ''
              }`}
              aria-live="polite"
            >
              {error || (loading && 'Signing in…')}
            </p>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2 rounded-lg bg-signal-blue text-white font-medium
                         flex items-center justify-center gap-2
                         hover:bg-signal-blue/90 disabled:opacity-60"
            >
              {loading ? (
                <svg
                  className="w-5 h-5 animate-spin"
                  viewBox="0 0 24 24"
                  fill="none"
                >
                  <circle
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    className="opacity-25"
                  />
                  <path
                    d="M4 12a8 8 0 018-8v4"
                    fill="currentColor"
                    className="opacity-75"
                  />
                </svg>
              ) : (
                <ArrowRightOnRectangleIcon className="w-5 h-5" />
              )}
              {loading ? 'Signing in' : `Sign${'\u00A0'}In`}
            </button>
          </form>

          <p className="mt-8 text-xs text-center text-gray-400">
            &copy; {new Date().getFullYear()} Smart Traffic System
          </p>
        </motion.div>
      </div>
    </div>
  )
}
