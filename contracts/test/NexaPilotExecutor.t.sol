// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {Test} from "forge-std/Test.sol";
import {NexaPilotExecutor} from "../src/NexaPilotExecutor.sol";
import {MockProtocol} from "./mocks/MockProtocol.sol";

contract NexaPilotExecutorTest is Test {
    NexaPilotExecutor internal executor;
    MockProtocol internal protocol;

    address internal owner = address(this);
    address internal alice = makeAddr("alice");
    address internal bob = makeAddr("bob");

    uint256 internal constant MAX_TX = 100 ether; // "100 MON" per project defaults

    function setUp() public {
        executor = new NexaPilotExecutor(MAX_TX, owner);
        protocol = new MockProtocol();

        vm.deal(alice, 1_000 ether);
        vm.deal(bob, 1_000 ether);
    }

    // --- deposit ---

    function test_deposit_creditsBalance() public {
        vm.prank(alice);
        executor.deposit{value: 10 ether}();

        assertEq(executor.balanceOf(alice), 10 ether);
        assertEq(address(executor).balance, 10 ether);
    }

    function test_deposit_zeroAmountReverts() public {
        vm.prank(alice);
        vm.expectRevert(NexaPilotExecutor.AmountMustBePositive.selector);
        executor.deposit{value: 0}();
    }

    function test_deposit_revertsWhenPaused() public {
        executor.pause();
        vm.prank(alice);
        vm.expectRevert();
        executor.deposit{value: 1 ether}();
    }

    // --- withdraw ---

    function test_withdraw_returnsFundsAndDecrementsBalance() public {
        vm.startPrank(alice);
        executor.deposit{value: 10 ether}();
        uint256 balanceBefore = alice.balance;
        executor.withdraw(4 ether);
        vm.stopPrank();

        assertEq(executor.balanceOf(alice), 6 ether);
        assertEq(alice.balance, balanceBefore + 4 ether);
    }

    function test_withdraw_moreThanBalanceReverts() public {
        vm.startPrank(alice);
        executor.deposit{value: 1 ether}();
        vm.expectRevert(
            abi.encodeWithSelector(NexaPilotExecutor.InsufficientBalance.selector, 2 ether, 1 ether)
        );
        executor.withdraw(2 ether);
        vm.stopPrank();
    }

    function test_withdraw_cannotTouchAnotherUsersBalance() public {
        vm.prank(alice);
        executor.deposit{value: 10 ether}();

        // Bob never deposited, so Bob withdrawing anything must fail —
        // this is the core cross-user-drain-safety property of the vault.
        vm.prank(bob);
        vm.expectRevert(
            abi.encodeWithSelector(NexaPilotExecutor.InsufficientBalance.selector, 1 ether, 0)
        );
        executor.withdraw(1 ether);
    }

    // --- execute ---

    function test_execute_forwardsValueToAllowedTarget() public {
        executor.setAllowedTarget(address(protocol), true);

        vm.startPrank(alice);
        executor.deposit{value: 20 ether}();
        (bool success, ) = executor.execute(address(protocol), 5 ether, "", "aave", "STAKE");
        vm.stopPrank();

        assertTrue(success);
        assertEq(executor.balanceOf(alice), 15 ether);
        assertEq(protocol.totalReceived(), 5 ether);
    }

    function test_execute_revertsForNonAllowedTarget() public {
        vm.startPrank(alice);
        executor.deposit{value: 20 ether}();
        vm.expectRevert(
            abi.encodeWithSelector(NexaPilotExecutor.TargetNotAllowed.selector, address(protocol))
        );
        executor.execute(address(protocol), 5 ether, "", "aave", "STAKE");
        vm.stopPrank();
    }

    function test_execute_revertsAboveMaxTransactionAmount() public {
        executor.setAllowedTarget(address(protocol), true);

        vm.startPrank(alice);
        executor.deposit{value: 500 ether}();
        vm.expectRevert(
            abi.encodeWithSelector(
                NexaPilotExecutor.ExceedsMaxTransactionAmount.selector, 200 ether, MAX_TX
            )
        );
        executor.execute(address(protocol), 200 ether, "", "aave", "STAKE");
        vm.stopPrank();
    }

    function test_execute_revertsWhenUnderlyingCallFails_andPreservesBalance() public {
        executor.setAllowedTarget(address(protocol), true);
        protocol.setShouldRevert(true);

        vm.startPrank(alice);
        executor.deposit{value: 10 ether}();
        vm.expectRevert(); // ActionCallFailed(bytes) — revert reason not asserted here
        executor.execute(address(protocol), 5 ether, "", "aave", "STAKE");
        vm.stopPrank();

        // Balance must be untouched since the whole call reverted.
        assertEq(executor.balanceOf(alice), 10 ether);
    }

    function test_execute_cannotSpendMoreThanCallersOwnBalance() public {
        executor.setAllowedTarget(address(protocol), true);

        vm.prank(alice);
        executor.deposit{value: 5 ether}();

        // Bob has no balance in the vault, even though the contract itself
        // now holds Alice's 5 ether — Bob must not be able to move it.
        vm.prank(bob);
        vm.expectRevert(
            abi.encodeWithSelector(NexaPilotExecutor.InsufficientBalance.selector, 1 ether, 0)
        );
        executor.execute(address(protocol), 1 ether, "", "aave", "STAKE");
    }

    // --- admin / access control ---

    function test_onlyOwner_canSetAllowedTarget() public {
        vm.prank(alice);
        vm.expectRevert();
        executor.setAllowedTarget(address(protocol), true);
    }

    function test_onlyOwner_canSetMaxTransactionAmount() public {
        vm.prank(alice);
        vm.expectRevert();
        executor.setMaxTransactionAmount(1 ether);
    }

    function test_onlyOwner_canPauseAndUnpause() public {
        vm.prank(alice);
        vm.expectRevert();
        executor.pause();

        executor.pause();
        assertTrue(executor.paused());
        executor.unpause();
        assertFalse(executor.paused());
    }

    // --- misc safety ---

    function test_receive_rejectsStrayTransfers() public {
        vm.prank(alice);
        (bool success, ) = address(executor).call{value: 1 ether}("");
        assertFalse(success);
    }
}
