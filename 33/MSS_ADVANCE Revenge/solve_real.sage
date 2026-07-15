import re
import ast
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from fpylll import IntegerMatrix, LLL, CVP

print("[*] Leyendo output.txt...")

txt = open("output.txt", "r").read()

p = Integer(re.search(r"p = (\d+)", txt).group(1))
pairs = ast.literal_eval(re.search(r"pairs = (\[.*?\])\nenc_flag", txt, re.S).group(1))
enc_flag = ast.literal_eval(re.search(r"enc_flag = (\(.*\))", txt, re.S).group(1))

m = 20
n = 30

print("[*] p bits:", p.nbits())
print("[*] pares:", len(pairs))

A = []
Y = []

for x, y in pairs:
    x = Integer(x)
    y = Integer(y)

    # eval_poly usa Horner:
    # c0*x^29 + c1*x^28 + ... + c29
    row = [pow(x, n - 1 - j, p) for j in range(n)]
    A.append(row)
    Y.append(y)

print("[*] Haciendo RREF modular...")

# RREF manual sobre GF(p)
M = [[Integer(A[i][j] % p) for j in range(n)] + [Integer(Y[i] % p)] for i in range(m)]

pivots = []
r = 0

for c in range(n):
    pivot = None
    for i in range(r, m):
        if M[i][c] % p != 0:
            pivot = i
            break

    if pivot is None:
        continue

    M[r], M[pivot] = M[pivot], M[r]

    inv_piv = inverse_mod(M[r][c], p)
    M[r] = [(v * inv_piv) % p for v in M[r]]

    for i in range(m):
        if i != r and M[i][c] % p != 0:
            factor = M[i][c] % p
            M[i] = [(M[i][j] - factor * M[r][j]) % p for j in range(n + 1)]

    pivots.append(c)
    r += 1

    if r == m:
        break

print("[*] rango:", r)

free = [j for j in range(n) if j not in pivots]
print("[*] variables libres:", len(free))

# Solución particular con libres = 0
sol = [Integer(0)] * n
for row, c in enumerate(pivots):
    sol[c] = Integer(M[row][n] % p)

# Base del kernel modular
ker = []

for f in free:
    v = [Integer(0)] * n
    v[f] = Integer(1)

    for row, c in enumerate(pivots):
        v[c] = Integer((-M[row][f]) % p)

    ker.append(v)

def center(a):
    a = Integer(a % p)
    if a > p // 2:
        return a - p
    return a

print("[*] Montando lattice de la coset...")

rows = []

# p * I permite cambiar representantes mod p
for i in range(n):
    row = [Integer(0)] * n
    row[i] = p
    rows.append(row)

# kernel modular
for v in ker:
    rows.append([center(x) for x in v])

B0 = IntegerMatrix(len(rows), n)

for i, row in enumerate(rows):
    for j, val in enumerate(row):
        B0[i, j] = int(val)

print("[*] LLL inicial...")
LLL.reduction(B0, delta=0.99)

# Tomamos 30 filas no nulas después de LLL.
basis_rows = []
for i in range(B0.nrows):
    row = [Integer(B0[i, j]) for j in range(n)]
    if any(row):
        basis_rows.append(row)
    if len(basis_rows) == n:
        break

if len(basis_rows) != n:
    print("[-] No pude extraer base completa.")
    exit()

B = IntegerMatrix(n, n)

for i, row in enumerate(basis_rows):
    for j, val in enumerate(row):
        B[i, j] = int(val)

print("[*] LLL final...")
LLL.reduction(B, delta=0.99)

target = [-center(x) for x in sol]

print("[*] CVP: buscando el vector de coeficientes pequeño...")
cv = CVP.closest_vector(B, [int(x) for x in target])

coeffs = [center(sol[i]) + Integer(cv[i]) for i in range(n)]

print("[*] Máximo tamaño encontrado:", max(abs(c).nbits() for c in coeffs), "bits")

# Verificación modular
for i in range(m):
    lhs = sum((A[i][j] * (coeffs[j] % p)) % p for j in range(n)) % p
    assert lhs == Y[i] % p

print("[+] Coeficientes verifican todos los pares.")

if not all(0 <= c < 2**256 for c in coeffs):
    print("[-] Los coeficientes no están todos en rango 0..2^256.")
    print("[*] Primeros coeficientes:", coeffs[:5])
    exit()

# Verificar la cadena SHA:
# coeffs[0] = MASTER_KEY como entero
# coeffs[i+1] = sha256(long_to_bytes(coeffs[i]))
def long_to_bytes_sage(x):
    x = int(x)
    if x == 0:
        return b"\x00"
    return x.to_bytes((x.bit_length() + 7) // 8, "big")

test = [coeffs[0]]

for _ in range(29):
    h = hashlib.sha256(long_to_bytes_sage(test[-1])).digest()
    test.append(Integer(int.from_bytes(h, "big")))

if test != coeffs:
    print("[-] La cadena SHA no coincide. Vector incorrecto.")
    exit()

print("[+] Cadena SHA correcta.")

key = int(coeffs[0]).to_bytes(32, "big")
iv = bytes.fromhex(enc_flag[0])
ct = bytes.fromhex(enc_flag[1])

pt = unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(ct), 16)

print("[+] FLAG:", pt.decode())
