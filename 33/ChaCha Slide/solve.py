import struct
from pwn import *
from sympy import Symbol, Poly, GF

# ==========================================
# 1. Configuración y Utilidades
# ==========================================
context.log_level = 'error'
HOST = 'activist-birds.picoctf.net'
PORT = 49195

P = 2**130 - 5  # Primo del campo de Galois de Poly1305

def to_poly_blocks(c):
    """Convierte el ciphertext en los bloques de 16 bytes que usa Poly1305."""
    pad_c = c + b'\x00' * ((16 - len(c) % 16) % 16)
    mac_data = pad_c + struct.pack('<QQ', 0, len(c)) 
    
    blocks = []
    for i in range(0, len(mac_data), 16):
        block = mac_data[i:i+16]
        val = int.from_bytes(block, 'little')
        val += 2**128
        blocks.append(val)
    return blocks

def check_clamp(r_val):
    val = int(r_val) % P
    if val >= 2**128: return False
    r_bytes = val.to_bytes(16, 'little')
    for i in [3, 7, 11, 15]:
        if r_bytes[i] & 0xf0 != 0: return False
    for i in [4, 8, 12]:
        if r_bytes[i] & 0x03 != 0: return False
    return True

def fast_poly_eval(blocks, r_val):
    """Evaluación polinómica ultrarrápida en Python puro."""
    acc = 0
    for b in blocks:
        acc = ((acc + b) * r_val) % P
    return acc

# ==========================================
# 2. Conexión y Extracción de Datos
# ==========================================
r_conn = remote(HOST, PORT)

def get_msg():
    r_conn.recvuntil(b"Plaintext: ")
    p = eval(r_conn.recvline().strip())
    r_conn.recvuntil(b"Ciphertext (hex): ")
    c_full = bytes.fromhex(r_conn.recvline().strip().decode())
    return p.encode(), c_full

print("[*] Conectando y obteniendo mensajes...")
p1, c1_full = get_msg()
p2, c2_full = get_msg()

c1, tag1, nonce = c1_full[:-28], c1_full[-28:-12], c1_full[-12:]
c2, tag2 = c2_full[:-28], c2_full[-28:-12]

# ¡CLAVE! Leemos el prompt del servidor AHORA para vaciar el buffer de red 
# antes de someter a la CPU a cálculos pesados.
r_conn.recvuntil(b"What is your message? ")

# ==========================================
# 3. Modelado Polinómico con SymPy
# ==========================================
print("[*] Construyendo polinomios para extraer la clave...")
x = Symbol('x')
F = GF(P)

def build_poly_expr(blocks):
    expr = 0
    for b in blocks:
        expr = (expr + b) * x
    return expr

blocks1 = to_poly_blocks(c1)
blocks2 = to_poly_blocks(c2)

poly1 = build_poly_expr(blocks1)
poly2 = build_poly_expr(blocks2)

t1_int = int.from_bytes(tag1, 'little')
t2_int = int.from_bytes(tag2, 'little')
diff_T = (t1_int - t2_int) % (2**128)

real_r = None

print("[*] Calculando raíces (esto puede tomar unos segundos en SymPy)...")
for k in range(-5, 6):
    eq = poly1 - poly2 - (diff_T + k * 2**128)
    p_eq = Poly(eq, x, domain=F)
    roots = p_eq.ground_roots()
    
    for root in roots.keys():
        r_val = int(root) % P
        if check_clamp(r_val):
            real_r = r_val
            print(f"[+] Clave 'r' recuperada: {hex(real_r)}")
            break
    if real_r: 
        break

if not real_r:
    print("[-] Error: No se pudo recuperar 'r'.")
    exit()

# Calcular 's' usando la función rápida
V1 = fast_poly_eval(blocks1, real_r)
s = (t1_int - V1) % (2**128)
print(f"[+] Clave 's' recuperada: {hex(s)}")

# ==========================================
# 4. Forjado del Mensaje y Extracción de Flag
# ==========================================
print("[*] Construyendo payload final...")
keystream = bytes(a ^ b for a, b in zip(c1, p1))
goal = b"But it's only secure if used correctly!"
new_c = bytes(a ^ b for a, b in zip(goal, keystream[:len(goal)]))

# Forjar el nuevo tag con matemática rápida
blocks_new = to_poly_blocks(new_c)
V_new = fast_poly_eval(blocks_new, real_r)
new_tag_int = (V_new + s) % (2**128)
new_tag = new_tag_int.to_bytes(16, 'little')

payload = new_c + new_tag + nonce

print("[*] Enviando payload...")
try:
    r_conn.sendline(payload.hex().encode())
    print("[+] Payload enviado. Esperando flag...\n")
    # recvall leerá hasta el EOF o hasta que pase el timeout
    flag = r_conn.recvall(timeout=5).decode().strip()
    
    if "picoCTF{" in flag:
        print(f"====================\nFLAG OBTENIDA:\n{flag}\n====================")
    else:
        print(f"Respuesta del servidor:\n{flag}")
except EOFError:
    print("[-] El servidor cerró la conexión prematuramente.")
