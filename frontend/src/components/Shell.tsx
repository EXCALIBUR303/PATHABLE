import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  ArrowUpRight,
  ChevronDown,
  Compass,
  Heart,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  ShieldCheck,
  SlidersHorizontal,
} from 'lucide-react'
import { useSession } from '../app/session-context'
import { api } from '../services/api'
import { Brand } from './Brand'
import { Badge, Button, Dialog } from './ui'

const navigation = [
  { to: '/navigate', label: 'Explore campus', icon: Compass },
  { to: '/profile', label: 'Preferences', icon: SlidersHorizontal },
  { to: '/reports', label: 'Community', icon: MessageSquare },
]

export function Shell() {
  const { session, error, refresh } = useSession()
  const user = session?.user
  const location = useLocation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [accountOpen, setAccountOpen] = useState(false)
  const [logoutError, setLogoutError] = useState('')
  const accountRef = useRef<HTMLDivElement>(null)
  const mobileTrigger = useRef<HTMLButtonElement>(null)
  const mainRef = useRef<HTMLElement>(null)

  useEffect(() => {
    mainRef.current?.focus({ preventScroll: true })
    window.scrollTo(0, 0)
  }, [location.pathname])
  useEffect(() => {
    if (!accountOpen) return
    const close = (event: PointerEvent) => {
      if (!accountRef.current?.contains(event.target as Node)) setAccountOpen(false)
    }
    document.addEventListener('pointerdown', close)
    return () => document.removeEventListener('pointerdown', close)
  }, [accountOpen])

  async function logout() {
    setLogoutError('')
    try {
      await queryClient.cancelQueries()
      const anonymous = await api.logout()
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
      queryClient.setQueryData(['session'], anonymous)
      setAccountOpen(false)
      navigate('/')
    } catch (error) {
      setLogoutError(
        error instanceof Error ? error.message : 'Unable to sign out. Please try again.',
      )
    }
  }

  return (
    <div className="site-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <header className="site-header">
        <div className="header-inner">
          <Brand />
          <nav className="desktop-nav" aria-label="Main navigation">
            {navigation.map(({ to, label }) => (
              <NavLink key={to} to={to}>
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="header-actions">
            <Badge tone="good">
              <span className="status-dot" />
              Campus demo
            </Badge>
            {user ? (
              <div className="account-menu" ref={accountRef}>
                <button
                  className="account-trigger"
                  aria-expanded={accountOpen}
                  aria-controls="account-links"
                  onClick={() => setAccountOpen((value) => !value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Escape') setAccountOpen(false)
                  }}
                >
                  <span className="avatar">{user.display_name.slice(0, 1).toUpperCase()}</span>
                  <span className="account-name">{user.display_name}</span>
                  <ChevronDown size={14} aria-hidden="true" />
                </button>
                {accountOpen && (
                  <div className="account-dropdown" id="account-links">
                    <Link to="/dashboard" onClick={() => setAccountOpen(false)}>
                      <LayoutDashboard size={16} />
                      My dashboard
                    </Link>
                    {user.role === 'admin' && (
                      <Link to="/admin" onClick={() => setAccountOpen(false)}>
                        <ShieldCheck size={16} />
                        Campus management
                      </Link>
                    )}
                    <button onClick={() => void logout()}>
                      <LogOut size={16} />
                      Sign out
                    </button>
                    {logoutError && <p role="alert">{logoutError}</p>}
                  </div>
                )}
              </div>
            ) : (
              <Link className="header-login" to="/login">
                Sign in <ArrowUpRight size={15} aria-hidden="true" />
              </Link>
            )}
            <Button
              ref={mobileTrigger}
              className="mobile-nav-toggle"
              variant="ghost"
              size="icon"
              aria-label="Open navigation"
              onClick={() => setMobileOpen(true)}
            >
              <Menu size={22} />
            </Button>
          </div>
        </div>
      </header>
      {error && (
        <div role="alert" className="connection-banner">
          Account connection unavailable. <button onClick={() => void refresh()}>Reconnect</button>
        </div>
      )}
      <Dialog
        title="Where would you like to go?"
        open={mobileOpen}
        onOpenChange={(open) => {
          setMobileOpen(open)
          if (!open) requestAnimationFrame(() => mobileTrigger.current?.focus())
        }}
      >
        <nav className="mobile-nav" aria-label="Mobile navigation">
          {navigation.map(({ to, label, icon: Icon }) => (
            <Link key={to} to={to} onClick={() => setMobileOpen(false)}>
              <Icon size={20} />
              {label}
            </Link>
          ))}
          <Link to="/dashboard" onClick={() => setMobileOpen(false)}>
            <LayoutDashboard size={20} />
            My dashboard
          </Link>
          {user?.role === 'admin' && (
            <Link to="/admin" onClick={() => setMobileOpen(false)}>
              <ShieldCheck size={20} />
              Campus management
            </Link>
          )}
        </nav>
      </Dialog>
      <main ref={mainRef} tabIndex={-1} id="main-content">
        <Outlet />
      </main>
      <footer className="site-footer">
        <Brand compact />
        <span>Every path should be possible.</span>
        <span className="footer-note">
          <Heart size={13} aria-hidden="true" />
          Designed for more inclusive journeys.
        </span>
        <Link to="/navigate">
          Explore the demo <ArrowUpRight size={13} />
        </Link>
      </footer>
    </div>
  )
}
