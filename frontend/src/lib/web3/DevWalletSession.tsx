import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { privateKeyToAccount } from 'viem/accounts'
import { config } from '@/lib/config'
import { WalletSessionContext, type WalletSession } from '@/lib/web3/WalletSessionContext'
import { normalizeUnsignedTx, toViemTransaction } from '@/lib/web3/txConvert'
import type { UnsignedTransactionOut } from '@/types/api'

/** Stands in for Privy in this build sandbox, where auth.privy.io /
 * api.privy.io aren't reachable (see the Phase 5 kickoff decision). Signs
 * with a real local account (viem's privateKeyToAccount) against the same
 * local anvil devnet the backend targets, so the entire rest of the app --
 * dashboard, AI copilot, transaction approval + signing + submission,
 * activity, settings -- can be built and verified end-to-end. Swapping in
 * a real VITE_PRIVY_APP_ID switches the app to PrivyWalletSession with no
 * other code changes (see AppProviders.tsx). */
export function DevWalletSessionProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false)

  const account = useMemo(() => {
    if (!config.devWalletPrivateKey) return null
    try {
      return privateKeyToAccount(config.devWalletPrivateKey as `0x${string}`)
    } catch {
      return null
    }
  }, [])

  const connect = useCallback(() => {
    setConnected(true)
  }, [])

  const disconnect = useCallback(() => {
    setConnected(false)
  }, [])

  const signTransaction = useCallback(
    async (unsignedTx: UnsignedTransactionOut): Promise<`0x${string}`> => {
      if (!account) {
        throw new Error(
          'No dev wallet configured (VITE_DEV_WALLET_PRIVATE_KEY is empty) and no VITE_PRIVY_APP_ID is set either.',
        )
      }
      const normalized = normalizeUnsignedTx(unsignedTx)
      return account.signTransaction(toViemTransaction(normalized))
    },
    [account],
  )

  const value: WalletSession = {
    address: connected ? (account?.address ?? null) : null,
    isConnected: connected && account != null,
    isConnecting: false,
    isReady: true,
    connect,
    disconnect,
    signTransaction,
    mode: 'dev',
  }

  return <WalletSessionContext.Provider value={value}>{children}</WalletSessionContext.Provider>
}
