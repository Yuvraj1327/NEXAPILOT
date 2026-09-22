import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { App } from '@/App'
import { queryClient } from '@/lib/queryClient'
import { AppProviders } from '@/lib/web3/AppProviders'
import { SessionProvider } from '@/lib/auth/SessionContext'
import '@/index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AppProviders>
        <SessionProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </SessionProvider>
      </AppProviders>
    </QueryClientProvider>
  </StrictMode>,
)
