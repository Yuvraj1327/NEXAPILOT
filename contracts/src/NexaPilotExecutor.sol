// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

/// @title NexaPilotExecutor
/// @notice Minimal, security-focused execution contract for the NexaPilot MVP.
///
/// Scope, deliberately kept small:
///  - Each user deposits native MON into their OWN tracked balance here.
///  - `execute` can only ever move a user's OWN previously-deposited balance,
///    to a protocol address the contract owner has allow-listed, never another
///    user's funds. Worst case for a bad `execute` call is the caller's own
///    deposit reverting or failing — there is no cross-user drain vector.
///  - This contract is the on-chain backstop, not the only line of defense:
///    the NexaPilot backend's Risk Engine and Policy Engine (off-chain,
///    deterministic) evaluate every proposed action BEFORE a user is ever
///    asked to approve it. `maxTransactionAmount` and `allowedTargets` here
///    are a second, independent enforcement layer in case the backend is
///    ever wrong or compromised — not a replacement for it.
///  - No governance, no tokenomics, no bridging, no upgradeability/proxy
///    complexity, no arbitrary allowance/approval patterns. Immutable and
///    small on purpose for a hackathon MVP handling real (test) funds.
contract NexaPilotExecutor is Ownable, ReentrancyGuard, Pausable {
    /// @notice Per-user balance held by this contract, in wei.
    mapping(address => uint256) public balanceOf;

    /// @notice Protocol/target addresses `execute` is allowed to call.
    /// @dev Defense-in-depth mirror of the backend Policy Engine's
    ///      "allowed protocols" rule — enforced here too, on-chain.
    mapping(address => bool) public allowedTargets;

    /// @notice Hard on-chain ceiling for a single `execute` call.
    /// @dev Independent of (and in addition to) the backend's per-user
    ///      Policy Engine limits, which are stricter/finer-grained.
    uint256 public maxTransactionAmount;

    event Deposited(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event ActionExecuted(
        address indexed user,
        address indexed target,
        string protocol,
        string actionType,
        uint256 amount,
        bool success
    );
    event AllowedTargetUpdated(address indexed target, bool allowed);
    event MaxTransactionAmountUpdated(uint256 oldValue, uint256 newValue);

    error AmountMustBePositive();
    error InsufficientBalance(uint256 requested, uint256 available);
    error ExceedsMaxTransactionAmount(uint256 requested, uint256 max);
    error TargetNotAllowed(address target);
    error NativeTransferFailed();
    error ActionCallFailed(bytes returnData);

    constructor(uint256 _maxTransactionAmount, address initialOwner) Ownable(initialOwner) {
        maxTransactionAmount = _maxTransactionAmount;
    }

    /// @notice Deposit native MON into the caller's tracked balance.
    function deposit() external payable whenNotPaused {
        if (msg.value == 0) revert AmountMustBePositive();
        balanceOf[msg.sender] += msg.value;
        emit Deposited(msg.sender, msg.value);
    }

    /// @notice Withdraw up to the caller's own tracked balance.
    function withdraw(uint256 amount) external nonReentrant whenNotPaused {
        if (amount == 0) revert AmountMustBePositive();
        uint256 available = balanceOf[msg.sender];
        if (amount > available) revert InsufficientBalance(amount, available);

        // Effects before interaction.
        balanceOf[msg.sender] = available - amount;

        (bool success, ) = msg.sender.call{value: amount}("");
        if (!success) revert NativeTransferFailed();

        emit Withdrawn(msg.sender, amount);
    }

    /// @notice Execute a DeFi action by forwarding `amount` of the caller's
    ///         own deposited balance (plus optional `data`) to an
    ///         allow-listed `target` protocol contract.
    /// @dev The caller (a user's own wallet, or — for Phase 2 integration
    ///      testing only — a locally-configured test signer) must already
    ///      have had this exact action validated by the backend's
    ///      deterministic Risk/Policy checks and approved by the user
    ///      before this is ever called. This function re-checks the
    ///      amount ceiling and target allow-list independently on-chain.
    function execute(address target, uint256 amount, bytes calldata data, string calldata protocol, string calldata actionType)
        external
        nonReentrant
        whenNotPaused
        returns (bool success, bytes memory result)
    {
        if (amount == 0) revert AmountMustBePositive();
        if (amount > maxTransactionAmount) revert ExceedsMaxTransactionAmount(amount, maxTransactionAmount);
        if (!allowedTargets[target]) revert TargetNotAllowed(target);

        uint256 available = balanceOf[msg.sender];
        if (amount > available) revert InsufficientBalance(amount, available);

        // Effects before interaction.
        balanceOf[msg.sender] = available - amount;

        (success, result) = target.call{value: amount}(data);
        if (!success) revert ActionCallFailed(result);

        emit ActionExecuted(msg.sender, target, protocol, actionType, amount, success);
    }

    /// @notice Owner-only: allow or revoke a protocol/target address.
    function setAllowedTarget(address target, bool allowed) external onlyOwner {
        allowedTargets[target] = allowed;
        emit AllowedTargetUpdated(target, allowed);
    }

    /// @notice Owner-only: adjust the on-chain single-transaction ceiling.
    function setMaxTransactionAmount(uint256 newMax) external onlyOwner {
        emit MaxTransactionAmountUpdated(maxTransactionAmount, newMax);
        maxTransactionAmount = newMax;
    }

    /// @notice Owner-only circuit breaker: halts deposit/withdraw/execute.
    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    /// @dev Reject stray native transfers — deposits must go through
    ///      `deposit()` so they're credited to a tracked balance.
    receive() external payable {
        revert("use deposit()");
    }
}
