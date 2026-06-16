# pow.py
import hashlib
import string
import itertools
import sys

if len(sys.argv) != 3:
    print("Uso: python3 pow.py <vals1> <vals2>")
    sys.exit(1)

vals1 = sys.argv[1]
vals2 = sys.argv[2]

print("[*] Calculando fuerza bruta para el MD5...")
chars = string.ascii_letters + string.digits
for length in range(1, 6):
    for p in itertools.product(chars, repeat=length):
        guess = vals1 + "".join(p)
        if hashlib.md5(guess.encode()).hexdigest()[-6:] == vals2:
            print(f"[+] Respuesta encontrada: {guess}")
            sys.exit(0)
