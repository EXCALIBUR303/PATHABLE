import { Link } from 'react-router-dom'
import logo from '../assets/logo.svg'

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link className={`brand ${compact ? 'brand-compact' : ''}`} to="/" aria-label="PathAble home">
      <img src={logo} width="164" height="40" alt="PathAble" />
    </Link>
  )
}
