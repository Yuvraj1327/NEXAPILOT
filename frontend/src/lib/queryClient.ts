import { QueryClient } from '@tanstack/react-query'

/** One shared QueryClient for the whole app -- including wagmi's own
 * internal queries (via @privy-io/wagmi's WagmiProvider), so there's a
 * single cache and a single place to configure defaults. */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 15_000,
    },
  },
})
