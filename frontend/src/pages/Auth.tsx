import { useState } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Check, Compass, Eye, EyeOff, ShieldCheck } from 'lucide-react'
import { api } from '../services/api'
import { useSession } from '../app/session-context'
import { Badge, Button } from '../components/ui'

export default function Auth({ mode }: { mode: 'login' | 'register' }) {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { session, loading, refresh } = useSession()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [visible, setVisible] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [registered, setRegistered] = useState(false)
  const destinations = ['/navigate', '/profile', '/dashboard', '/admin', '/reports', '/reports/new']
  const returnTo = destinations.includes(params.get('returnTo') ?? '')
    ? params.get('returnTo')!
    : '/dashboard'
  if (!loading && session?.user) return <Navigate to={returnTo} replace />

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setPending(true)
    try {
      if (mode === 'register') {
        await api.register({ email: email.trim(), password, display_name: name.trim() })
        setPassword('')
        setRegistered(true)
      } else {
        await queryClient.cancelQueries({
          predicate: (query) =>
            [
              'profile',
              'saved',
              'me',
              'session',
              'reports',
              'report',
              'admin-reports',
              'predictions',
              'inference-jobs',
              'analytics',
              'audit',
            ].includes(String(query.queryKey[0])),
        })
        const next = await api.login({ email: email.trim(), password })
        queryClient.removeQueries({
          predicate: (query) =>
            [
              'profile',
              'saved',
              'me',
              'reports',
              'report',
              'admin-reports',
              'predictions',
              'inference-jobs',
              'analytics',
              'audit',
            ].includes(String(query.queryKey[0])),
        })
        queryClient.setQueryData(['session'], next)
        setPassword('')
        navigate(returnTo, { replace: true })
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Please try again.')
      void refresh()
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="auth-page page-container">
      <aside className="auth-story">
        <Badge tone="good">Every journey belongs</Badge>
        <h1>
          A little more
          <br />
          campus.
          <br />
          <span>A lot more you.</span>
        </h1>
        <p>Save places you return to. Keep your preferences close. Make this space your own.</p>
        <div className="auth-illustration" aria-hidden="true">
          <span className="illustration-node n1">
            <Compass />
          </span>
          <span className="illustration-node n2">
            <ShieldCheck />
          </span>
          <span className="illustration-node n3">
            <Check />
          </span>
          <svg viewBox="0 0 340 180">
            <path
              d="M40 140V75Q40 40 80 40H165Q200 40 200 80V105Q200 140 240 140H305"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
              strokeDasharray="6 7"
            />
          </svg>
        </div>
        <small>No detailed journey history is stored.</small>
      </aside>
      <section className="auth-form-panel">
        {registered ? (
          <div className="registration-success">
            <span className="context-icon">
              <Check size={28} />
            </span>
            <h2>You’re all set.</h2>
            <p>Your account has been created. Sign in to save your preferences and places.</p>
            <Button asChild>
              <Link to={`/login?returnTo=${encodeURIComponent(returnTo)}`}>
                Sign in to continue <ArrowRight size={17} />
              </Link>
            </Button>
          </div>
        ) : (
          <>
            <div className="eyebrow">
              {mode === 'register' ? 'Make yourself at home' : 'Good to have you back'}
            </div>
            <h2>{mode === 'register' ? 'Create your account' : 'Welcome back.'}</h2>
            <p className="muted">
              {mode === 'register'
                ? 'A few details, then a campus that feels more yours.'
                : 'Sign in to your own corner of PathAble.'}
            </p>
            <form onSubmit={(event) => void submit(event)}>
              {mode === 'register' && (
                <div className="field">
                  <label htmlFor="name">Your name</label>
                  <input
                    id="name"
                    name="name"
                    autoComplete="name"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    required
                    minLength={1}
                    maxLength={80}
                  />
                </div>
              )}
              <div className="field">
                <label htmlFor="email">Email address</label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  maxLength={254}
                />
              </div>
              <div className="field">
                <label htmlFor="password">Password</label>
                <div className="password-input">
                  <input
                    id="password"
                    name="password"
                    type={visible ? 'text' : 'password'}
                    autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    minLength={12}
                    maxLength={128}
                    aria-describedby="password-hint"
                  />
                  <button
                    type="button"
                    aria-label={visible ? 'Hide password' : 'Show password'}
                    onClick={() => setVisible((value) => !value)}
                  >
                    {visible ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                <small id="password-hint">
                  At least 12 characters. Password managers and spaces are welcome.
                </small>
              </div>
              {error && (
                <div className="form-error-box" role="alert">
                  {error}
                </div>
              )}
              <Button type="submit" className="full-width" busy={pending}>
                {mode === 'register' ? 'Create account' : 'Sign in'} <ArrowRight size={17} />
              </Button>
              <p className="auth-alternative">
                {mode === 'register' ? 'Already have an account?' : 'New to PathAble?'}{' '}
                <Link
                  to={`/${mode === 'register' ? 'login' : 'register'}?returnTo=${encodeURIComponent(returnTo)}`}
                >
                  {mode === 'register' ? 'Sign in' : 'Create an account'}
                </Link>
              </p>
            </form>
            <div className="auth-privacy">
              <ShieldCheck size={18} />
              <p>
                Your preferences are functional settings. No diagnosis or disability proof is
                required.
              </p>
            </div>
          </>
        )}
      </section>
    </div>
  )
}
