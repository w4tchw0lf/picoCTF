#!/usr/bin/env python3
from pwn import *
from fractions import Fraction
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import ast
import re
import struct
import sys
import time

HOST = sys.argv[1] if len(sys.argv) > 1 else "lonely-island.picoctf.net"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 64029

SALT_LEN = 256
KEY_LEN = 32

# SHA-512 constants
K = [
    0x428a2f98d728ae22, 0x7137449123ef65cd, 0xb5c0fbcfec4d3b2f, 0xe9b5dba58189dbbc,
    0x3956c25bf348b538, 0x59f111f1b605d019, 0x923f82a4af194f9b, 0xab1c5ed5da6d8118,
    0xd807aa98a3030242, 0x12835b0145706fbe, 0x243185be4ee4b28c, 0x550c7dc3d5ffb4e2,
    0x72be5d74f27b896f, 0x80deb1fe3b1696b1, 0x9bdc06a725c71235, 0xc19bf174cf692694,
    0xe49b69c19ef14ad2, 0xefbe4786384f25e3, 0x0fc19dc68b8cd5b5, 0x240ca1cc77ac9c65,
    0x2de92c6f592b0275, 0x4a7484aa6ea6e483, 0x5cb0a9dcbd41fbd4, 0x76f988da831153b5,
    0x983e5152ee66dfab, 0xa831c66d2db43210, 0xb00327c898fb213f, 0xbf597fc7beef0ee4,
    0xc6e00bf33da88fc2, 0xd5a79147930aa725, 0x06ca6351e003826f, 0x142929670a0e6e70,
    0x27b70a8546d22ffc, 0x2e1b21385c26c926, 0x4d2c6dfc5ac42aed, 0x53380d139d95b3df,
    0x650a73548baf63de, 0x766a0abb3c77b2a8, 0x81c2c92e47edaee6, 0x92722c851482353b,
    0xa2bfe8a14cf10364, 0xa81a664bbc423001, 0xc24b8b70d0f89791, 0xc76c51a30654be30,
    0xd192e819d6ef5218, 0xd69906245565a910, 0xf40e35855771202a, 0x106aa07032bbd1b8,
    0x19a4c116b8d2d0c8, 0x1e376c085141ab53, 0x2748774cdf8eeb99, 0x34b0bcb5e19b48a8,
    0x391c0cb3c5c95a63, 0x4ed8aa4ae3418acb, 0x5b9cca4f7763e373, 0x682e6ff3d6b2b8a3,
    0x748f82ee5defb2fc, 0x78a5636f43172f60, 0x84c87814a1f0ab72, 0x8cc702081a6439ec,
    0x90befffa23631e28, 0xa4506cebde82bde9, 0xbef9a3f7b2c67915, 0xc67178f2e372532b,
    0xca273eceea26619c, 0xd186b8c721c0c207, 0xeada7dd6cde0eb1e, 0xf57d4f7fee6ed178,
    0x06f067aa72176fba, 0x0a637dc5a2c898a6, 0x113f9804bef90dae, 0x1b710b35131c471b,
    0x28db77f523047d84, 0x32caab7b40c72493, 0x3c9ebe0a15c9bebc, 0x431d67c49c100d4c,
    0x4cc5d4becb3e42b6, 0x597f299cfc657e2a, 0x5fcb6fab3ad6faec, 0x6c44198c4a475817,
]

MASK = (1 << 64) - 1

def rotr(x, n):
    return ((x >> n) | (x << (64 - n))) & MASK

def sha512_pad(length):
    return (
        b"\x80"
        + b"\x00" * ((112 - (length + 1) % 128) % 128)
        + (length * 8).to_bytes(16, "big")
    )

def sha512_compress(block, h):
    w = list(struct.unpack(">16Q", block))

    for i in range(16, 80):
        s0 = rotr(w[i - 15], 1) ^ rotr(w[i - 15], 8) ^ (w[i - 15] >> 7)
        s1 = rotr(w[i - 2], 19) ^ rotr(w[i - 2], 61) ^ (w[i - 2] >> 6)
        w.append((w[i - 16] + s0 + w[i - 7] + s1) & MASK)

    a, b, c, d, e, f, g, hh = h

    for i in range(80):
        S1 = rotr(e, 14) ^ rotr(e, 18) ^ rotr(e, 41)
        ch = (e & f) ^ ((~e) & g)
        t1 = (hh + S1 + ch + K[i] + w[i]) & MASK
        S0 = rotr(a, 28) ^ rotr(a, 34) ^ rotr(a, 39)
        maj = (a & b) ^ (a & c) ^ (b & c)
        t2 = (S0 + maj) & MASK
        hh, g, f, e, d, c, b, a = g, f, e, (d + t1) & MASK, c, b, a, (t1 + t2) & MASK

    return [(x + y) & MASK for x, y in zip(h, [a, b, c, d, e, f, g, hh])]

def sha512_length_extend(old_digest_hex, known_total_len, append_bytes):
    h = list(struct.unpack(">8Q", bytes.fromhex(old_digest_hex)))

    glue = sha512_pad(known_total_len)
    processed_len = known_total_len + len(glue)

    data = append_bytes + sha512_pad(processed_len + len(append_bytes))

    for i in range(0, len(data), 128):
        h = sha512_compress(data[i:i + 128], h)

    new_digest = "".join(f"{x:016x}" for x in h)
    return new_digest, glue

def escape_for_unicode_escape(raw):
    out = ""
    for b in raw:
        if 0x20 <= b <= 0x7e and b != 0x5c:
            out += chr(b)
        else:
            out += f"\\x{b:02x}"
    return out

def forge_vector(original_vector, original_hash, append_bytes):
    # El servidor hashea vector_input[1:-1].
    # Para str([1, -2, 3]), eso es b"1, -2, 3".
    original_message = str(original_vector)[1:-1].encode("latin-1")

    new_hash, glue = sha512_length_extend(
        original_hash,
        SALT_LEN + len(original_message),
        append_bytes,
    )

    forged_inner = original_message + glue + append_bytes
    forged_input = "[" + escape_for_unicode_escape(forged_inner) + "]"

    return forged_input, new_hash

def parse_banner(text):
    iv = bytes.fromhex(re.search(r"IV:\s*([0-9a-f]+)", text).group(1))
    ct = bytes.fromhex(re.search(r"Ciphertext:\s*([0-9a-f]+)", text).group(1))

    trusted = []
    for line in text.splitlines():
        line = line.strip()
        try:
            obj = ast.literal_eval(line)
        except Exception:
            continue

        if (
            isinstance(obj, tuple)
            and len(obj) == 2
            and isinstance(obj[0], list)
            and isinstance(obj[1], str)
        ):
            trusted.append(obj)

    if len(trusted) != 5:
        raise RuntimeError(f"No pude parsear los 5 vectores trusted. Encontré {len(trusted)}")

    return iv, ct, trusted

def query_dot(io, vector_input, vector_hash):
    io.sendline(vector_input.encode("ascii"))
    io.recvuntil(b"Enter its salted hash: ")
    io.sendline(vector_hash.encode())

    out = io.recvuntil(b"Enter your vector: ", timeout=5).decode("latin-1", "replace")

    if "Untrusted vector detected" in out:
        raise RuntimeError("Hash rechazado")
    if "Invalid vector" in out:
        raise RuntimeError("Vector inválido")

    m = re.search(r"The computed dot product is:\s*(-?\d+)", out)
    if not m:
        raise RuntimeError(f"No pude leer dot product:\n{out}")

    return int(m.group(1))

def solve_linear_fraction(A, b):
    n = len(A)
    m = len(A[0])

    mat = [
        [Fraction(x) for x in A[i]] + [Fraction(b[i])]
        for i in range(n)
    ]

    row = 0
    pivots = []

    for col in range(m):
        pivot = None
        for r in range(row, n):
            if mat[r][col] != 0:
                pivot = r
                break

        if pivot is None:
            continue

        mat[row], mat[pivot] = mat[pivot], mat[row]

        div = mat[row][col]
        mat[row] = [x / div for x in mat[row]]

        for r in range(n):
            if r != row and mat[r][col] != 0:
                factor = mat[r][col]
                mat[r] = [mat[r][c] - factor * mat[row][c] for c in range(m + 1)]

        pivots.append(col)
        row += 1

        if row == m:
            break

    if len(pivots) < m:
        return None

    sol = [Fraction(0) for _ in range(m)]
    for r, col in enumerate(pivots):
        sol[col] = mat[r][-1]

    if any(x.denominator != 1 for x in sol):
        return None

    sol = [int(x) for x in sol]

    if any(x < 0 or x > 255 for x in sol):
        return None

    return sol

def solve_one_connection():
    io = remote(HOST, PORT)

    banner = io.recvuntil(b"Enter your vector: ", timeout=5).decode("latin-1", "replace")
    iv, ct, trusted = parse_banner(banner)

    lengths = [len(v) for v, _ in trusted]
    m = min(lengths)

    log.info(f"trusted lengths = {lengths}, min = {m}")

    # Solo tenemos 5 ecuaciones base. Si el vector más corto mide >5,
    # normalmente no podremos recuperar los primeros m bytes.
    if m > 5:
        io.close()
        raise RuntimeError("instancia probablemente no resoluble: min length > 5")

    # Productos base para los 5 vectores trusted originales.
    base_dots = []
    for v, h in trusted:
        d = query_dot(io, str(v), h)
        base_dots.append(d)

    # Usamos el vector más corto para recuperar key[m]..key[31]
    short_idx = lengths.index(m)
    short_v, short_h = trusted[short_idx]

    key = [None] * KEY_LEN

    log.info("Recuperando bytes de key por length extension...")

    for pos in range(m, KEY_LEN):
        count = pos - m + 1

        zero_entries = [0] * count
        one_entries = [0] * count
        one_entries[-1] = 1

        append_zero = ("," + ",".join(map(str, zero_entries))).encode()
        append_one = ("," + ",".join(map(str, one_entries))).encode()

        vec0, hash0 = forge_vector(short_v, short_h, append_zero)
        vec1, hash1 = forge_vector(short_v, short_h, append_one)

        d0 = query_dot(io, vec0, hash0)
        d1 = query_dot(io, vec1, hash1)

        key[pos] = d1 - d0

        if not (0 <= key[pos] <= 255):
            io.close()
            raise RuntimeError(f"byte sospechoso en key[{pos}] = {key[pos]}")

        log.info(f"key[{pos:02d}] = {key[pos]:02x}")

    # Resolver los primeros m bytes usando las 5 ecuaciones base.
    A = []
    B = []

    for (v, _), dot in zip(trusted, base_dots):
        parsed = [abs(x) for x in v]

        rhs = dot
        for j in range(m, min(len(parsed), KEY_LEN)):
            rhs -= parsed[j] * key[j]

        A.append(parsed[:m])
        B.append(rhs)

    first = solve_linear_fraction(A, B)

    if first is None:
        io.close()
        raise RuntimeError("sistema lineal no tiene rango suficiente")

    for i in range(m):
        key[i] = first[i]
        log.info(f"key[{i:02d}] = {key[i]:02x}")

    key_bytes = bytes(key)
    log.success(f"AES key = {key_bytes.hex()}")

    pt = unpad(AES.new(key_bytes, AES.MODE_CBC, iv).decrypt(ct), 16)
    flag = pt.decode(errors="replace")

    io.close()

    return flag

def main():
    context.log_level = "info"

    for attempt in range(1, 40):
        log.info(f"Intento {attempt}")

        try:
            flag = solve_one_connection()
        except Exception as e:
            log.warning(str(e))
            time.sleep(0.2)
            continue

        if "picoCTF{" in flag:
            log.success(flag)
            print(flag)
            return

        log.warning(f"Descifrado raro: {flag!r}")

    log.failure("No salió. Relanza el script; algunas instancias no son resolubles.")

if __name__ == "__main__":
    main()
