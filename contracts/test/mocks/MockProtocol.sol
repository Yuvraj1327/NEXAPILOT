// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

/// @notice Trivial stand-in for a real DeFi protocol contract, used only in
/// tests to exercise NexaPilotExecutor.execute()'s external call path.
/// Not part of the deployed product surface.
contract MockProtocol {
    uint256 public totalReceived;
    bool public shouldRevert;

    event Received(address indexed from, uint256 amount, bytes data);

    function setShouldRevert(bool value) external {
        shouldRevert = value;
    }

    receive() external payable {
        _handle();
    }

    fallback() external payable {
        _handle();
    }

    function _handle() internal {
        if (shouldRevert) revert("MockProtocol: forced failure");
        totalReceived += msg.value;
        emit Received(msg.sender, msg.value, msg.data);
    }
}
