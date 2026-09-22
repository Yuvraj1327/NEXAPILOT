# NexaPilot Smart Contracts

A single, minimal, security-focused contract for the MVP execution flow —
see `src/NexaPilotExecutor.sol` for the full rationale in comments.

## What it does (and doesn't)

- Users deposit native MON into their own tracked balance in the contract.
- `execute(target, amount, data, protocol, actionType)` forwards **only the
  caller's own previously-deposited balance** to an owner-allow-listed
  target contract — there is no way for one user's call to move another
  user's funds.
- On-chain `maxTransactionAmount` and `allowedTargets` are a defense-in-depth
  backstop. They are **not** a replacement for the backend's Risk Engine /
  Policy Engine (Phase 4) — those run first, off-chain, before a user is
  ever asked to approve anything.
- No governance, tokenomics, bridging, or upgradeability — immutable and
  small on purpose.

## Toolchain

Built with [Foundry](https://getfoundry.sh) (forge/anvil/cast) and
OpenZeppelin Contracts (`Ownable`, `ReentrancyGuard`, `Pausable`).

```bash
forge build      # compile (via-ir enabled — see foundry.toml)
forge test -vv   # 15 tests: deposits, withdrawals, execute, access control,
                  # pause, and the cross-user-drain-safety property
```

## Deploying

`script/deploy.sh` wraps `forge script` and writes the result to
`deployments/<network>.json` — that file is the single source of truth the
backend reads the contract address from (never hand-copied into backend
config).

**Local devnet** (anvil, pinned to Monad's real chain id `10143` so the
whole stack is proven against the real JSON-RPC surface):

```bash
anvil --chain-id 10143 &
DEPLOYER_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
  ./script/deploy.sh local
```
(That's anvil's well-known default account #0 — fine for a local devnet,
never use it anywhere real funds could reach it.)

**Real Monad testnet:**

```bash
DEPLOYER_PRIVATE_KEY=0xYOUR_FUNDED_TESTNET_KEY \
MONAD_RPC_URL=https://testnet-rpc.monad.xyz \
  ./script/deploy.sh monad_testnet
```

You'll need testnet MON from the [faucet](https://faucet.monad.xyz) in the
deployer address first. After deploying, allow-list every real protocol
contract you want `execute()` to be able to reach:

```bash
cast send <executor_address> "setAllowedTarget(address,bool)" <protocol_address> true \
  --rpc-url https://testnet-rpc.monad.xyz --private-key $DEPLOYER_PRIVATE_KEY
```

### Monad testnet network details
- Chain ID: `10143`
- RPC: `https://testnet-rpc.monad.xyz` (or Ankr/Monad Foundation alternates — see [docs](https://docs.monad.xyz/developer-essentials/testnet))
- Currency: `MON`
- Explorer: https://testnet.monadscan.com
- Faucet: https://faucet.monad.xyz

## Why this wasn't deployed to the real testnet from this session

This contract was built and fully tested (unit tests + a live local
deployment) from an Anthropic cloud sandbox whose outbound network is
allow-listed to package registries and GitHub only — the Monad RPC
endpoints aren't reachable from here (confirmed: 403 at the egress proxy).
`deployments/local.json` is a real deployment (real bytecode, real mined
transactions, same chain id and ABI Monad testnet will see) on a local
devnet standing in for it. Run the one command above from an environment
with real network access (your machine, CI, etc.) to go live — nothing
about the contract or backend code changes.

## Layout

```
src/NexaPilotExecutor.sol   the contract
test/                        forge tests + MockProtocol test fixture
script/Deploy.s.sol          forge deployment script
script/deploy.sh             deploy + auto-record deployments/<network>.json
deployments/                 generated deployment records + ABI (backend reads these)
```
