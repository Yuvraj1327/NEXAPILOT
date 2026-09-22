// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {Script, console} from "forge-std/Script.sol";
import {NexaPilotExecutor} from "../src/NexaPilotExecutor.sol";

/// @notice Deploys NexaPilotExecutor.
///
/// Usage (real Monad testnet):
///   forge script script/Deploy.s.sol:Deploy \
///     --rpc-url monad_testnet \
///     --private-key $DEPLOYER_PRIVATE_KEY \
///     --broadcast
///
/// Usage (local devnet, e.g. anvil pinned to Monad's chain id for testing):
///   forge script script/Deploy.s.sol:Deploy --rpc-url local --broadcast \
///     --private-key <anvil-default-key>
///
/// Env vars:
///   DEPLOYER_PRIVATE_KEY        required — the deployer/owner's key
///   MAX_TRANSACTION_AMOUNT_WEI  optional — defaults to 100 MON (matches the
///                               backend Policy Engine's default ceiling)
contract Deploy is Script {
    function run() external returns (NexaPilotExecutor executor) {
        uint256 deployerKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address deployer = vm.addr(deployerKey);

        uint256 maxTx = vm.envOr("MAX_TRANSACTION_AMOUNT_WEI", uint256(100 ether));

        vm.startBroadcast(deployerKey);
        executor = new NexaPilotExecutor(maxTx, deployer);
        vm.stopBroadcast();

        console.log("NexaPilotExecutor deployed at:", address(executor));
        console.log("Owner:", deployer);
        console.log("Max transaction amount (wei):", maxTx);
    }
}
