import os
import json
import time
import requests
import monocypher
from radio_interface import receive_radio_messages, inject_radio_message, start_robot, stop_robot, get_board_state

# URL ACTUALIZADA
SERVER_URL = "http://activist-birds.picoctf.net:61764"

MY_ADDR = 0xAA
ORIG_CTRL = 0x10
NEW_CTRL = 0x99
ROBOT_ADDR = None

print(f"[*] Conectando a la instancia: {SERVER_URL}")
print("[*] PREPARANDO EL ATAQUE MITM...")

# Sistema de lectura con búfer para no perder paquetes
msg_buffer = []
def get_message():
    global msg_buffer
    while not msg_buffer:
        msgs = receive_radio_messages()
        if msgs:
            msg_buffer.extend(msgs)
        else:
            time.sleep(0.05)
    return msg_buffer.pop(0)

# ==========================================
# 1. Aislamiento del Controlador
# ==========================================
inject_radio_message({"msg_type": "set_addr", "src": MY_ADDR, "dst": ORIG_CTRL, "new_addr": NEW_CTRL})
time.sleep(0.5)

# ==========================================
# 2. Reinicio y Captura del Handshake
# ==========================================
stop_robot()
receive_radio_messages() 
time.sleep(0.5)
start_robot()

my_priv = os.urandom(32)
my_pub = monocypher.compute_key_exchange_public_key(my_priv)
robot_shared = None
ctrl_shared = None

print("[*] Esperando a que el Robot solicite las claves...")
while not robot_shared:
    m = get_message()
    if m.get("msg_type") == "key_exchange" and m.get("dst") == ORIG_CTRL:
        ROBOT_ADDR = m["src"]
        robot_shared = monocypher.key_exchange(my_priv, bytes.fromhex(m["key"]))
        inject_radio_message({"msg_type": "ack_key_exchange", "src": ORIG_CTRL, "dst": ROBOT_ADDR, "key": my_pub.hex()})
        print(f"    [+] ¡Robot ({hex(ROBOT_ADDR)}) SECUESTRADO!")

inject_radio_message({"msg_type": "key_exchange", "src": MY_ADDR, "dst": NEW_CTRL, "key": my_pub.hex()})
while not ctrl_shared:
    m = get_message()
    if m.get("msg_type") == "ack_key_exchange" and m.get("src") == NEW_CTRL:
        ctrl_shared = monocypher.key_exchange(my_priv, bytes.fromhex(m["key"]))
        print("    [+] ¡Controlador vinculado como Oráculo!")

# ==========================================
# 3. Funciones Criptográficas
# ==========================================
def encrypt_for(shared_key, message_str, nonce, hmac_hex):
    key = monocypher.blake2b(shared_key)[:32]
    nonce_bytes = os.urandom(24)
    payload = json.dumps({"message": message_str, "nonce": nonce, "hmac": hmac_hex}).encode()
    tag, ciphertext = monocypher.lock(key, nonce_bytes, payload)
    return ciphertext.hex() + ";" + tag.hex() + ";" + nonce_bytes.hex()

def decrypt_from(shared_key, enc_str):
    key = monocypher.blake2b(shared_key)[:32]
    c_hex, t_hex, n_hex = enc_str.split(";")
    try:
        pt = monocypher.unlock(key, bytes.fromhex(n_hex), bytes.fromhex(t_hex), bytes.fromhex(c_hex))
        return json.loads(pt.decode())
    except:
        return None

# ==========================================
# 4. Proxy Transparente y Pilotaje
# ==========================================
print("\n[+] BUCLE PROXY INICIADO. Esperando datos...")

while True:
    m = get_message()
    m_type = m.get("msg_type")
    
    if m.get("src") == ROBOT_ADDR and m.get("dst") == ORIG_CTRL:
        if "encrypted" in m:
            pt = decrypt_from(robot_shared, m["encrypted"])
            if pt:
                m["encrypted"] = encrypt_for(ctrl_shared, pt["message"], pt["nonce"], pt["hmac"])
                m["src"] = MY_ADDR
                m["dst"] = NEW_CTRL
                inject_radio_message(m)

    elif m.get("src") == NEW_CTRL and m.get("dst") == MY_ADDR:
        if "encrypted" in m:
            pt = decrypt_from(ctrl_shared, m["encrypted"])
            if pt:
                n = pt["nonce"]
                if m_type == "secure_data_response" and n >= 0 and n % 10 == 0:
                    print(f"\n[!!!] VENTANA CRIPTOGRÁFICA ABIERTA (Nonce: {n}) [!!!]")
                    state = get_board_state()
                    if 'grid' in state:
                        for row in state['grid']: print(row)
                    
                    cmd = input("\nMovimiento (north, south, east, west) [skip]: ").strip().lower()
                    if cmd in ['north', 'south', 'east', 'west']:
                        inject_radio_message({"msg_type": "validate", "src": MY_ADDR, "dst": NEW_CTRL, "challenge": cmd + str(n)[:-1]})
                        forged_hmac = None
                        while not forged_hmac:
                            om = get_message()
                            if om.get("msg_type") == "ack_validate" and om.get("src") == NEW_CTRL: forged_hmac = om["response"]
                        
                        m["encrypted"] = encrypt_for(robot_shared, cmd, n, forged_hmac)
                        m["src"] = ORIG_CTRL
                        m["dst"] = ROBOT_ADDR
                        inject_radio_message(m)
                        print(f"[+] Comando '{cmd}' inyectado.")
                        continue
                
                m["encrypted"] = encrypt_for(robot_shared, pt["message"], n, pt["hmac"])
                m["src"] = ORIG_CTRL
                m["dst"] = ROBOT_ADDR
                inject_radio_message(m)
