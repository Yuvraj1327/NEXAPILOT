import type { ReactNode } from 'react'
import { usingDevWallet } from '@/lib/config'
import { DevWalletSessionProvider } from '@/lib/web3/DevWalletSession'
import { PrivyWalletSessionProvider } from '@/lib/web3/PrivyWalletSession'

/** The one place that decides which wallet backend is active. Set
 * VITE_PRIVY_APP_ID in .env to switch this app to real Privy login --
 * nothing else in the codebase changes. */
export function AppProviders({ children }: { children: ReactNode }) {
  if (usingDevWallet) {
    return <DevWalletSessionProvider>{children}</DevWalletSessionProvider>
  }
  return <PrivyWalletSessionProvider>{children}</PrivyWalletSessionProvider>
}
