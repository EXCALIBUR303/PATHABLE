import type { ReactNode } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'
import { useSession } from '../app/session-context'
import { Button, ErrorNotice, Loading } from './ui'

export function Protected({ children, admin = false }: { children: ReactNode; admin?: boolean }) {
  const { session, loading, error, refresh } = useSession()
  const location = useLocation()
  if (loading) return <Loading label="Checking your account" />
  if (error)
    return (
      <div className="page-container">
        <ErrorNotice error={error} retry={() => void refresh()} />
      </div>
    )
  if (!session?.user)
    return <Navigate to={`/login?returnTo=${encodeURIComponent(location.pathname)}`} replace />
  if (admin && session.user.role !== 'admin')
    return (
      <section className="page-container access-state">
        <ShieldCheck size={40} aria-hidden="true" />
        <h1>Campus management is for administrators</h1>
        <p>Your account can explore the campus, save places, and set preferences.</p>
        <Button asChild>
          <Link to="/navigate">Explore campus</Link>
        </Button>
      </section>
    )
  return children
}
