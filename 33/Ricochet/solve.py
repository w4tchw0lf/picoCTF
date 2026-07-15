import os
import json
import time
import requests
import monocypher

# ==========================================
# 1. Configuración de Red (radio_interface)
# ==========================================
SERVER_URL = "http://activist-birds.picoctf.net:56389"

def receive_radio_messages():
    try:
        return requests.get(SERVER_URL + "/radio_rx").json()
    except:
        return []

def inject_radio_message(message):
    requests.post(SERVER_URL + "/radio_tx", json=message)

def start_robot():
    requests.get(SERVER_URL + "/start")

def stop_robot():
    requests.get(SERVER_URL + "/stop")

def get_board_state():
    try:
        return requests.get(SERVER_URL + "/state").json()
    except:
        return {}

# ==========================================
# 2. Inicialización y Reconocimiento
# ==========================================
MY_ADDR = 0xAA
CTRL_ADDR = 0x10
ROBOT_ADDR = None

print(f"[*] Conectando a la instancia: {SERVER_URL}")
print("[*] Iniciando el robot para descubrir su dirección de red...")
start_robot()
time.sleep(1)

# Descubrir la IP del Robot interceptando tráfico inicial
for m in receive_radio_messages():
    if m.get("src") not in [None, CTRL_ADDR, MY_ADDR, 0xFF]:
        ROBOT_ADDR = m["src"]
        break

if not ROBOT_ADDR:
    ROBOT_ADDR = 0x11 # Fallback estándar

print(f"[+] Robot detectado en la dirección: {hex(ROBOT_ADDR)}")

# Reiniciar para limpiar el estado y comenzar el ataque
print("[*] Reiniciando entorno para ataque MITM...")
stop_robot()
time.sleep(1)
receive_radio_messages() # Limpiar buffer viejo
start_robot()
time.sleep(0.5) 

# ==========================================
# 3. MITM - Secuestro de Claves Diffie-Hellman
# ==========================================
print("[*] Secuestrando claves Diffie-Hellman...")
my_priv = os.urandom(32)
my_pub = monocypher.compute_key_exchange_public_key(my_priv)

ctrl_shared = None
robot_shared = None
intentos = 0

print("[*] Esperando ACKs (reintentando si hay pérdida de paquetes)...")
while not ctrl_shared or not robot_shared:
    # Reenviamos los paquetes cada 1 segundo (10 ticks de 0.1s)
    # Esto previene que el script se cuelgue si el servidor pierde el paquete inicial
    if intentos % 10 == 0:
        inject_radio_message({"msg_type": "key_exchange", "src": MY_ADDR, "dst": CTRL_ADDR, "key": my_pub.hex()})
        inject_radio_message({"msg_type": "key_exchange", "src": MY_ADDR, "dst": ROBOT_ADDR, "key": my_pub.hex()})
        
    for m in receive_radio_messages():
        if m.get("msg_type") == "ack_key_exchange" and m.get("dst") == MY_ADDR:
            if m["src"] == CTRL_ADDR and not ctrl_shared:
                ctrl_shared = monocypher.key_exchange(my_priv, bytes.fromhex(m["key"]))
                print("    [+] ¡Clave del Controlador obtenida!")
            elif m["src"] == ROBOT_ADDR and not robot_shared:
                robot_shared = monocypher.key_exchange(my_priv, bytes.fromhex(m["key"]))
                print("    [+] ¡Clave del Robot obtenida!")
    
    time.sleep(0.1)
    intentos += 1

print("[+] ¡Claves criptográficas interceptadas con éxito!")

# ==========================================
# 4. Funciones Criptográficas
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

def ask_oracle(challenge_str):
    """Explota la vulnerabilidad de validación para forjar firmas MAC"""
    inject_radio_message({
        "msg_type": "validate",
        "src": MY_ADDR,
        "dst": CTRL_ADDR,
        "challenge": challenge_str
    })
    while True:
        for m in receive_radio_messages():
            if m.get("msg_type") == "ack_validate" and m.get("dst") == MY_ADDR:
                return m["response"]
        time.sleep(0.1)

# ==========================================
# 5. Explotación y Desvío de Nonce
# ==========================================
print("[*] Aplicando el desvío de paridad (Nonce Parity Shift)...")
empty_hmac = ask_oracle("") 
dummy_enc_robot = encrypt_for(robot_shared, "", 0, empty_hmac)
dummy_enc_ctrl = encrypt_for(ctrl_shared, "", 0, empty_hmac)

inject_radio_message({"msg_type": "secure_data", "src": CTRL_ADDR, "dst": ROBOT_ADDR, "encrypted": dummy_enc_robot})
inject_radio_message({"msg_type": "secure_data", "src": ROBOT_ADDR, "dst": CTRL_ADDR, "encrypted": dummy_enc_ctrl})

print("[+] ¡Proxy Transparente iniciado!")
print("[!] Mantente atento: el script te pedirá direcciones para mover el robot hacia la flag.\n")

# ==========================================
# 6. Bucle de Proxy Transparente y Pilotaje
# ==========================================
while True:
    for m in receive_radio_messages():
        m_type = m.get("msg_type")
        
        # Flujo: Robot -> Controlador
        if m.get("src") == ROBOT_ADDR and m.get("dst") == CTRL_ADDR:
            if "encrypted" in m:
                pt = decrypt_from(robot_shared, m["encrypted"])
                if pt:
                    re_enc = encrypt_for(ctrl_shared, pt["message"], pt["nonce"], pt["hmac"])
                    m["encrypted"] = re_enc
                    m["src"] = ROBOT_ADDR
                    inject_radio_message(m)

        # Flujo: Controlador -> Robot
        if m.get("src") == CTRL_ADDR and m.get("dst") == ROBOT_ADDR:
            if "encrypted" in m:
                pt = decrypt_from(ctrl_shared, m["encrypted"])
                if pt:
                    n = pt["nonce"]
                    # Ventana de ataque abierta (nonce termina en 0)
                    if m_type == "secure_data_response" and n > 0 and n % 10 == 0:
                        print(f"\n" + "="*50)
                        print(f"[!!!] VENTANA CRIPTOGRÁFICA ABIERTA EN EL NONCE {n} [!!!]")
                        
                        state = get_board_state()
                        if 'grid' in state:
                            print("\nMapa Actual:")
                            for row in state['grid']:
                                print(row)
                        
                        cmd = input("\nIntroduce tu movimiento (north, south, east, west) [o 'skip' para demo]: ").strip().lower()
                        if cmd in ['north', 'south', 'east', 'west']:
                            print(f"[*] Forjando firma HMAC maliciosa para '{cmd}'...")
                            forged_hmac = ask_oracle(cmd + str(n)[:-1])
                            re_enc = encrypt_for(robot_shared, cmd, n, forged_hmac)
                            m["encrypted"] = re_
