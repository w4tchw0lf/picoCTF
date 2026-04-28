import socket
import time
import subprocess

# El ciphertext original del archivo password.enc
c_pass = 2336150584734702647514724021470643922433811330098144930425575029773908475892259185520495303353109615046654428965662643241365308392679139063000973730368839

print("[*] Iniciando ataque RSA en vivo...")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("titan.picoctf.net", 63861))

# Esperar el banner inicial
time.sleep(0.5)
s.recv(4096)

# ==========================================
# FASE 1: Obtener un multiplicador fresco
# ==========================================
print("[*] Fase 1: Pidiendo al oráculo que encripte el texto '2'...")
s.sendall(b"E\n")
time.sleep(0.5)
s.recv(4096)
s.sendall(b"2\n")  # El ASCII de '2' es 50 en decimal
time.sleep(0.5)
resp_enc = s.recv(4096).decode('utf-8', errors='ignore')

# Extraer el ciphertext de '2' (nuestro c_2)
c_2 = None
for line in resp_enc.split('\n'):
    if "ciphertext" in line and "mod n" in line:
        c_2 = int(line.split()[-1].strip())
        break

if not c_2:
    print("[-] Error: No se pudo obtener la trampa en vivo. Reintenta.")
    exit(1)

print(f"[+] Trampa generada con éxito: {str(c_2)[:15]}... (oculto)")

# ==========================================
# FASE 2: Inyectar la contraseña modificada
# ==========================================
c_truco = c_pass * c_2
print("[*] Fase 2: Enviando la contraseña cegada al oráculo...")
s.sendall(b"D\n")
time.sleep(0.5)
s.recv(4096)
s.sendall(f"{c_truco}\n".encode())
time.sleep(1)
resp_dec = s.recv(4096).decode('utf-8', errors='ignore')
s.close()

# Extraer el resultado en hexadecimal
hex_val = None
for line in resp_dec.split('\n'):
    if "as hex" in line.lower():
        hex_val = line.split(":")[-1].strip()
        break

if not hex_val:
    print("[-] Error: El oráculo no devolvió el hexadecimal.")
    exit(1)

print(f"[+] El oráculo mordió el anzuelo. Hex recibido: {hex_val}")

# ==========================================
# FASE 3: Matemáticas Inversas y OpenSSL
# ==========================================
m_truco = int(hex_val, 16)

# Verificación de seguridad matemática
if m_truco % 50 != 0:
    print("[-] Advertencia: Las matemáticas fallaron (no es divisible por 50).")
    
# Revertimos la multiplicación
m_real = m_truco // 50

byte_len = (m_real.bit_length() + 7) // 8
password = m_real.to_bytes(byte_len, 'big').decode('utf-8', errors='ignore')
print(f"[+] ¡Contraseña extraída de las matemáticas!: {password}")

print("\n[*] Ejecutando OpenSSL para abrir la bóveda...")
try:
    # Usamos capture_output=True sin text=True para manejar los bytes puros y no crashear
    resultado = subprocess.run(
        ['openssl', 'enc', '-aes-256-cbc', '-d', '-in', 'secret.enc', '-pass', f'pass:{password}', '-pbkdf2'],
        capture_output=True, check=True
    )
    flag = resultado.stdout.decode('utf-8', errors='ignore').strip()
    print("\n" + "★"*50)
    print(f"🚩 FLAG: {flag}")
    print("★"*50 + "\n")
except subprocess.CalledProcessError as e:
    print("\n[-] Error de OpenSSL.")
    print("Asegúrate de que 'secret.enc' esté en la misma carpeta que este script.")
    print("Detalle:", e.stderr.decode('utf-8', errors='ignore').strip())
