import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchSession } from '../services/api'
import { SessionContext } from './session-context'

export function SessionProvider({ children }: { children: ReactNode }) {
  const query = useQuery({
    queryKey: ['session'],
    queryFn: fetchSession,
    staleTime: 60_000,
    refetchOnWindowFocus: true,
  })
  return (
    <SessionContext.Provider
      value={{
        session: query.data,
        loading: query.isPending,
        error: query.error,
        refresh: query.refetch,
      }}
    >
      {children}
    </SessionContext.Provider>
  )
}
