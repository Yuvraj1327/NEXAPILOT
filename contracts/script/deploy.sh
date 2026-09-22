#!/usr/bin/env bash
# Deploy NexaPilotExecutor and record the result to deployments/<network>.json
# so the backend has a single, generated source of truth for the address —
# never hand-copied into backend config.
#
# Usage:
#   DEPLOYER_PRIVATE_KEY=0x... ./script/deploy.sh local
#   DEPLOYER_PRIVATE_KEY=0x... MONAD_RPC_URL=https://testnet-rpc.monad.xyz ./script/deploy.sh monad_testnet
set -euo pipefail

NETWORK="${1:?usage: deploy.sh <local|monad_testnet>}"
cd "$(dirname "$0")/.."

if [ -z "${DEPLOYER_PRIVATE_KEY:-}" ]; then
  echo "ERROR: DEPLOYER_PRIVATE_KEY is not set." >&2
  exit 1
fi

case "$NETWORK" in
  local)
    RPC_URL="http://127.0.0.1:8545"
    ;;
  monad_testnet)
    RPC_URL="${MONAD_RPC_URL:-https://testnet-rpc.monad.xyz}"
    ;;
  *)
    echo "ERROR: unknown network '$NETWORK' (expected: local | monad_testnet)" >&2
    exit 1
    ;;
esac

echo "Deploying NexaPilotExecutor to $NETWORK ($RPC_URL)..."
forge script script/Deploy.s.sol:Deploy --rpc-url "$RPC_URL" --broadcast

CHAIN_ID=$(cast chain-id --rpc-url "$RPC_URL")
BROADCAST_FILE="broadcast/Deploy.s.sol/${CHAIN_ID}/run-latest.json"

python3 - "$BROADCAST_FILE" "$NETWORK" "$CHAIN_ID" "$RPC_URL" <<'PYEOF'
import json, sys, pathlib

broadcast_file, network, chain_id, rpc_url = sys.argv[1:5]
data = json.loads(pathlib.Path(broadcast_file).read_text())
tx = next(t for t in data["transactions"] if t["contractName"] == "NexaPilotExecutor")

out = {
    "network": network,
    "chainId": int(chain_id),
    "rpcUrl": rpc_url,
    "contract": "NexaPilotExecutor",
    "address": tx["contractAddress"],
    "deployTxHash": tx["hash"],
    "constructorArgs": tx["arguments"],
}

out_path = pathlib.Path("deployments") / f"{network}.json"
out_path.write_text(json.dumps(out, indent=2) + "\n")
print(f"Wrote {out_path}")
PYEOF

echo ""
echo "Next step: allow-list every protocol contract this deployment should be able to call:"
echo "  cast send <address> \"setAllowedTarget(address,bool)\" <protocol_address> true --rpc-url $RPC_URL --private-key \$DEPLOYER_PRIVATE_KEY"
