import { createConfig } from '@privy-io/wagmi'
import { http } from 'viem'
import { config } from '@/lib/config'
import { monad } from '@/lib/web3/chains'

/** wagmi's config, bridged to Privy's connected wallets via
 * @privy-io/wagmi's createConfig/WagmiProvider -- once a Privy wallet is
 * active, wagmi's own useAccount()/useConnect() reflect it automatically. */
export const wagmiConfig = createConfig({
  chains: [monad],
  transports: {
    [monad.id]: http(config.monadRpcUrl),
  },
})
