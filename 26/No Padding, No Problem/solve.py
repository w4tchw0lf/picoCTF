from pwn import *

# 1. Nos conectamos al oráculo
host = "wily-courier.picoctf.net"
port = 55742

print("[*] Conectando al oráculo RSA...")
r = remote(host, port)

# 2. Extraemos los valores públicos y el criptograma bloqueado
r.recvuntil(b"n: ")
n = int(r.recvline().strip())
r.recvuntil(b"e: ")
e = int(r.recvline().strip())
r.recvuntil(b"ciphertext: ")
c = int(r.recvline().strip())

print("[+] Datos capturados correctamente.")

# 3. Calculamos nuestro criptograma falso (C * 2^e mod N)
multiplier = 2
c_prime = (c * pow(multiplier, e, n)) % n

# 4. Engañamos al oráculo enviándole el criptograma falso
print("[*] Enviando el criptograma modificado al oráculo...")
r.sendlineafter(b"Give me ciphertext to decrypt: ", str(c_prime).encode())

# 5. Recibimos el mensaje falso (M * 2)
r.recvuntil(b"Here you go: ")
m_prime = int(r.recvline().strip())

# 6. Revertimos la multiplicación (M' * inverso_modular(2) mod N)
print("[*] Revirtiendo las matemáticas para obtener la flag...")
m = (m_prime * pow(multiplier, -1, n)) % n

# 7. Convertimos el número a texto ASCII
flag = m.to_bytes((m.bit_length() + 7) // 8, 'big').decode('utf-8')

print(f"\n[+] FLAG REVELADA: {flag}\n")

r.close()
