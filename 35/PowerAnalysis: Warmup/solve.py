#!/usr/bin/env python3

import ast
import os
import re
import socket
import sys
import time

import numpy as np

HOST = "saturn.picoctf.net"
PORT = 65291

INITIAL_TRACES = 800
EXTRA_TRACES = 400
MAX_TRACES = 2000
VERIFY_TRACES = 20


def load_sbox(filename="encrypt.py"):
    """
    Extrae Sbox desde encrypt.py sin ejecutar el programa.
    """
    with open(filename, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filename)

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue

        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "Sbox":
                value = ast.literal_eval(node.value)

                if len(value) != 256:
                    raise ValueError("La Sbox no contiene 256 entradas")

                return np.array(value, dtype=np.uint8)

    raise RuntimeError("No se encontró Sbox en encrypt.py")


def recv_until(sock, marker, timeout=8):
    sock.settimeout(timeout)
    data = bytearray()

    while marker not in data:
        chunk = sock.recv(4096)

        if not chunk:
            break

        data.extend(chunk)

    return bytes(data)


def query_server(plaintext, retries=8):
    """
    Abre una conexión, envía un plaintext de 16 bytes
    y devuelve el entero leakage result.
    """
    payload = plaintext.hex().encode() + b"\n"

    for attempt in range(1, retries + 1):
        try:
            with socket.create_connection((HOST, PORT), timeout=8) as sock:
                banner = recv_until(sock, b"hex:")

                if b"hex:" not in banner:
                    raise RuntimeError(
                        "No se recibió el prompt esperado: "
                        + repr(banner[-200:])
                    )

                sock.sendall(payload)
                sock.shutdown(socket.SHUT_WR)

                response = bytearray()

                while True:
                    chunk = sock.recv(4096)

                    if not chunk:
                        break

                    response.extend(chunk)

                match = re.search(
                    rb"leakage\s+result\s*:\s*(\d+)",
                    bytes(response),
                    re.IGNORECASE,
                )

                if not match:
                    raise RuntimeError(
                        "Respuesta inesperada: " + repr(bytes(response))
                    )

                return int(match.group(1))

        except (OSError, RuntimeError) as exc:
            if attempt == retries:
                raise

            print(
                f"\r[!] Consulta fallida: {exc}; reintentando...",
                end="",
                flush=True,
            )
            time.sleep(0.25)

    raise RuntimeError("No se pudo consultar el servidor")


def collect_traces(count, plaintexts, leakages):
    start = len(plaintexts)
    target = start + count

    while len(plaintexts) < target:
        pt = os.urandom(16)
        leakage = query_server(pt)

        plaintexts.append(pt)
        leakages.append(leakage)

        done = len(plaintexts)
        print(
            f"\r[*] Muestras: {done}/{target} "
            f"última fuga={leakage:2d}",
            end="",
            flush=True,
        )

    print()


def recover_key(sbox, plaintexts, leakages):
    pts = np.frombuffer(b"".join(plaintexts), dtype=np.uint8).reshape(-1, 16)
    measured = np.asarray(leakages, dtype=np.float64)

    measured -= measured.mean()
    measured_norm = np.sqrt(np.dot(measured, measured))

    key = bytearray()
    confidence = []

    guesses = np.arange(256, dtype=np.uint16)

    print(f"[*] Ejecutando CPA con {len(plaintexts)} muestras...")

    for position in range(16):
        # shape: numero_muestras x 256_candidatos
        indices = np.bitwise_xor(
            pts[:, position, None].astype(np.uint16),
            guesses[None, :],
        )

        predicted = (sbox[indices] & 1).astype(np.float64)
        predicted -= predicted.mean(axis=0)

        numerator = predicted.T @ measured
        denominator = (
            np.sqrt(np.sum(predicted * predicted, axis=0))
            * measured_norm
        )

        correlations = np.divide(
            numerator,
            denominator,
            out=np.zeros_like(numerator),
            where=denominator != 0,
        )

        order = np.argsort(correlations)[::-1]
        best = int(order[0])
        second = int(order[1])

        key.append(best)
        confidence.append(
            (
                float(correlations[best]),
                float(correlations[second]),
            )
        )

        print(
            f"[+] K[{position:02d}] = {best:02x} "
            f"corr={correlations[best]:.5f} "
            f"segundo={second:02x}/{correlations[second]:.5f}"
        )

    return bytes(key), confidence


def predict_leakage(sbox, plaintext, key):
    return sum(
        int(sbox[plaintext[i] ^ key[i]] & 1)
        for i in range(16)
    )


def verify_key(sbox, key, count=VERIFY_TRACES):
    print(f"[*] Verificando la clave con {count} consultas nuevas...")

    for number in range(1, count + 1):
        pt = os.urandom(16)
        real = query_server(pt)
        predicted = predict_leakage(sbox, pt, key)

        if real != predicted:
            print(
                f"[-] Fallo en verificación {number}: "
                f"servidor={real}, predicho={predicted}"
            )
            return False

        print(
            f"\r[*] Verificación correcta: {number}/{count}",
            end="",
            flush=True,
        )

    print()
    return True


def main():
    try:
        sbox = load_sbox()
    except Exception as exc:
        print(f"[-] No se pudo cargar encrypt.py: {exc}")
        sys.exit(1)

    plaintexts = []
    leakages = []

    collect_traces(INITIAL_TRACES, plaintexts, leakages)

    while True:
        key, confidence = recover_key(sbox, plaintexts, leakages)

        print()
        print(f"[*] Clave candidata: {key.hex()}")
        print(f"[*] Flag candidata: picoCTF{{{key.hex()}}}")

        if verify_key(sbox, key):
            print()
            print("[+] CLAVE CONFIRMADA")
            print(f"[+] picoCTF{{{key.hex()}}}")
            return

        if len(plaintexts) >= MAX_TRACES:
            print(
                "[-] No se confirmó la clave tras alcanzar "
                f"{MAX_TRACES} muestras."
            )
            sys.exit(1)

        additional = min(
            EXTRA_TRACES,
            MAX_TRACES - len(plaintexts),
        )

        print(
            f"[*] La correlación todavía no es concluyente; "
            f"recogiendo {additional} muestras adicionales."
        )
        collect_traces(additional, plaintexts, leakages)


if __name__ == "__main__":
    main()
