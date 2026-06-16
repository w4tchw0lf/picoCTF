from pwn import *

# 1. Conectamos al servidor
r = remote('wily-courier.picoctf.net', 61961)

# 2. Capturamos la bandera cifrada inicial
r.recvuntil(b"This is the encrypted flag!\n")
enc_flag_hex = r.recvline().strip().decode()
enc_flag_bytes = bytes.fromhex(enc_flag_hex)
flag_len = len(enc_flag_bytes)

print(f"[*] Bandera cifrada original capturada: {enc_flag_hex}")
print(f"[*] Longitud calculada: {flag_len} bytes")

# 3. Calculamos la basura necesaria para reiniciar el puntero
key_len = 50000
basura_necesaria = key_len - flag_len

print(f"[*] Enviando {basura_necesaria} bytes de relleno para resetear la clave...")
r.recvuntil(b"What data would you like to encrypt? ")
r.sendline(b"a" * basura_necesaria)

# Ignoramos la respuesta de la basura
r.recvuntil(b"Here ya go!\n")
r.recvline()

# 4. El puntero vuelve a estar en 0. Enviamos un texto conocido (todo "A"s)
texto_conocido = b"A" * flag_len
print(f"[*] Puntero a cero. Inyectando texto conocido: {texto_conocido}")
r.recvuntil(b"What data would you like to encrypt? ")
r.sendline(texto_conocido)

# Capturamos cómo el servidor cifra nuestras "A"s
r.recvuntil(b"Here ya go!\n")
enc_conocido_hex = r.recvline().strip().decode()
enc_conocido_bytes = bytes.fromhex(enc_conocido_hex)

# 5. ¡Ataque Criptográfico! Extraemos la clave y desencriptamos
# Clave = (Texto Cifrado de las A) XOR (Texto Plano de las A)
clave = xor(enc_conocido_bytes, texto_conocido)

# Bandera = (Bandera Cifrada) XOR (Clave descubierta)
bandera = xor(enc_flag_bytes, clave)

# El reto dice "Wrap with picoCTF{}"
print(f"\n[+] ¡ÉXITO! Tu bandera es: picoCTF{{{bandera.decode()}}}")

r.close()
