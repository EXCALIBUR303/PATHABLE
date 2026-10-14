import { createContext, useContext } from 'react'
import type { Session } from '../services/api'

export interface SessionState {
  session?: Session
  loading: boolean
  error: Error | null
  refresh: () => Promise<unknown>
}
export const SessionContext = createContext<SessionState>({
  loading: true,
  error: null,
  refresh: async () => undefined,
})
export const useSession = () => useContext(SessionContext)
