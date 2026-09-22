import { createContext, useContext } from 'react'
import type { UnsignedTransactionOut } from '@/types/api'

/** One interface, two backends (see PrivyWalletSession.tsx and
 * DevWalletSession.tsx) -- everything else in the app (the auth bridge,
 * the transaction-approval flow) talks to a wallet only through this
 * shape and never needs to know whether Privy or the sandbox dev wallet
 * is behind it. */
export interface WalletSession {
  address: `0x${string}` | null
  isConnected: boolean
  /** True while a connect/login attempt is in flight. */
  isConnecting: boolean
  /** True once the underlying provider (Privy, or the dev wallet) has
   * finished its own startup check -- before this, isConnected may not
   * yet reflect an existing session. */
  isReady: boolean
  connect: () => Promise<void> | void
  disconnect: () => Promise<void> | void
  /** Signs an unsigned transaction from POST /blockchain/transactions/prepare
   * and returns the 0x-prefixed signed raw transaction hex, ready for
   * POST /blockchain/transactions/{id}/submit. Never broadcasts anything
   * itself -- signing and submission stay separate, matching the
   * backend's non-custodial design. */
  signTransaction: (unsignedTx: UnsignedTransactionOut) => Promise<`0x${string}`>
  /** 'privy' or 'dev' -- surfaced only so Settings can show which mode is
   * active; nothing else should branch on it. */
  mode: 'privy' | 'dev'
}

export const WalletSessionContext = createContext<WalletSession | null>(null)

export function useWalletSession(): WalletSession {
  const ctx = useContext(WalletSessionContext)
  if (!ctx) throw new Error('useWalletSession must be used within a WalletSessionContext provider.')
  return ctx
}
