import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import * as Tooltip from '@radix-ui/react-tooltip'
import '@fontsource-variable/inter'
import 'leaflet/dist/leaflet.css'
import './styles/app.css'
import { AppRouter } from './app/Router'
import { SessionProvider } from './app/SessionProvider'
import { ErrorBoundary } from './app/ErrorBoundary'
import { ApiError } from './services/api'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (count, error) =>
        count < 1 && (!(error instanceof ApiError) || error.status === 0 || error.status >= 500),
    },
    mutations: { retry: false },
  },
})
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <Tooltip.Provider delayDuration={250}>
          <SessionProvider>
            <AppRouter />
          </SessionProvider>
        </Tooltip.Provider>
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>,
)
