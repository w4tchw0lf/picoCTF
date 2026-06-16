#!/usr/bin/env python3
import socket

HOST = "wily-courier.picoctf.net"
PORT = 61961
KEY_LEN = 50000


def recv_until(sock, marker):
    data = b""
    while marker not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return data


def xor_bytes(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


s = socket.create_connection((HOST, PORT))

# Leer hasta la flag cifrada
data = recv_until(s, b"This is the encrypted flag!\n")
enc_flag_hex = b""

while not enc_flag_hex:
    enc_flag_hex = s.recv(4096).splitlines()[0].strip()

enc_flag = bytes.fromhex(enc_flag_hex.decode())
flag_len = len(enc_flag)

print("[+] encrypted flag:", enc_flag_hex.decode())
print("[+] flag length:", flag_len)

# Esperar prompt
recv_until(s, b"What data would you like to encrypt? ")

# Consumir la clave restante hasta volver a offset 0
padding_len = KEY_LEN - flag_len
s.sendall(b"A" * padding_len + b"\n")

# Leer la respuesta enorme y esperar el siguiente prompt
recv_until(s, b"What data would you like to encrypt? ")

# Ahora el puntero de clave está en 0.
# Pedimos cifrar texto conocido del mismo tamaño que la flag.
known_plain = b"A" * flag_len
s.sendall(known_plain + b"\n")

# Leer ciphertext del texto conocido
recv_until(s, b"Here ya go!\n")
known_ct_hex = b""

while not known_ct_hex:
    known_ct_hex = s.recv(4096).splitlines()[0].strip()

known_ct = bytes.fromhex(known_ct_hex.decode())

# Recuperar key[0:flag_len]
key = xor_bytes(known_ct, known_plain)

# Recuperar flag
flag = xor_bytes(enc_flag, key)

print("[+] raw flag:", flag.decode(errors="replace"))
print("[+] submit:", f"picoCTF{{{flag.decode(errors='replace')}}}")
