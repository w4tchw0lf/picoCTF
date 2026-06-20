#!/usr/bin/env python3
from pwn import *
import re

HOST = "fickle-tempest.picoctf.net"
PORT = 57390

p = remote(HOST, PORT)

def decode_value(text):
    # Binario: 01110100 01100101 ...
    binary = re.findall(r"\b[01]{8}\b", text)
    if binary:
        return "".join(chr(int(x, 2)) for x in binary)

    # Octal con prefijo o: o163 o154 o165 ...
    octal_o = re.findall(r"\bo[0-7]{2,3}\b", text)
    if octal_o:
        return "".join(chr(int(x[1:], 8)) for x in octal_o)

    # Octal sin prefijo: 163 154 165 ...
    octal = re.findall(r"\b[0-7]{3}\b", text)
    if octal and len(octal) > 1:
        return "".join(chr(int(x, 8)) for x in octal)

    # Hexadecimal: 74657374
    hex_candidates = re.findall(r"\b[0-9a-fA-F]{6,}\b", text)
    for h in hex_candidates:
        if len(h) % 2 == 0:
            try:
                decoded = bytes.fromhex(h).decode()
                if decoded.isprintable():
                    return decoded
            except Exception:
                pass

    return None

while True:
    try:
        data = p.recvuntil(b"Input:", timeout=10)
    except EOFError:
        break

    if not data:
        break

    text = data.decode(errors="ignore")
    print(text, end="")

    ans = decode_value(text)

    if ans is None:
        print("\n[!] No pude decodificar. Paso a modo interactivo.")
        p.interactive()
        break

    print(f"[+] respuesta: {ans}")
    p.sendline(ans.encode())

    try:
        extra = p.recvline(timeout=2)
        if extra:
            print(extra.decode(errors="ignore"), end="")
            if b"picoCTF{" in extra:
                p.interactive()
                break
    except EOFError:
        break

p.interactive()
