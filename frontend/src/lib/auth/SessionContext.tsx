import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { connectWallet } from '@/lib/api/resources'
import { tokenStore } from '@/lib/api/client'
import { useWalletSession } from '@/lib/web3/WalletSessionContext'
import type { UserRead, WalletRead } from '@/types/api'

type SessionStatus = 'disconnected' | 'authenticating' | 'ready' | 'error'

interface SessionValue {
  status: SessionStatus
  user: UserRead | null
  wallet: WalletRead | null
  error: string | null
  /** Disconnects the wallet and clears the backend session together --
   * the two are always kept in lock-step. */
  logout: () => Promise<void> | void
}

const SessionContext = createContext<SessionValue | null>(null)

export function useSession(): SessionValue {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('useSession must be used within SessionProvider.')
  return ctx
}

/** Bridges wallet connection to the backend's own session: once a wallet
 * address is available, calls POST /auth/connect (see
 * backend/app/api/v1/endpoints/auth.py) to get-or-create the User/Wallet
 * rows and a JWT, and stores that JWT for every subsequent API call
 * (src/lib/api/client.ts). This is the ONLY place that calls
 * /auth/connect -- no other component re-implements this handshake. */
export function SessionProvider({ children }: { children: ReactNode }) {
  const wallet = useWalletSession()
  const [status, setStatus] = useState<SessionStatus>('disconnected')
  const [user, setUser] = useState<UserRead | null>(null)
  const [walletRead, setWalletRead] = useState<WalletRead | null>(null)
  const [error, setError] = useState<string | null>(null)
  const authenticatedAddress = useRef<string | null>(null)

  useEffect(() => {
    if (!wallet.isReady) return

    if (!wallet.isConnected || !wallet.address) {
      authenticatedAddress.current = null
      tokenStore.set(null)
      setUser(null)
      setWalletRead(null)
      setStatus('disconnected')
      return
    }

    if (authenticatedAddress.current === wallet.address) return

    let cancelled = false
    setStatus('authenticating')
    setError(null)

    connectWallet(wallet.address)
      .then((token) => {
        if (cancelled) return
        tokenStore.set(token.access_token)
        authenticatedAddress.current = wallet.address
        setUser(token.user)
        setWalletRead(token.wallet)
        setStatus('ready')
      })
      .catch((err: unknown) => {
        if (cancelled) return
        tokenStore.set(null)
        setStatus('error')
        setError(err instanceof Error ? err.message : 'Could not establish a backend session.')
      })

    return () => {
      cancelled = true
    }
  }, [wallet.isReady, wallet.isConnected, wallet.address])

  const logout = async () => {
    tokenStore.set(null)
    authenticatedAddress.current = null
    setUser(null)
    setWalletRead(null)
    setStatus('disconnected')
    await wallet.disconnect()
  }

  return (
    <SessionContext.Provider value={{ status, user, wallet: walletRead, error, logout }}>
      {children}
    </SessionContext.Provider>
  )
}
