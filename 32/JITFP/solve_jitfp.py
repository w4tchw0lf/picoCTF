#!/usr/bin/env python3
import os
import re
import ctypes
import signal
import subprocess
import time

BIN = "./ad7e550b"
FLAGLEN = 33

# Offsets conocidos del binario del reto
TEXT_OFF = 0x1000
TEXT_SIZE = 0x1000
CALL_RDX_OFF = 0x1a7d
JNE_PATCH_OFF = 0x1a81

libc = ctypes.CDLL("libc.so.6", use_errno=True)

PTRACE_ATTACH     = 16
PTRACE_DETACH     = 17
PTRACE_CONT       = 7
PTRACE_GETREGS    = 12
PTRACE_SETREGS    = 13
PTRACE_SINGLESTEP = 9

class Regs(ctypes.Structure):
    _fields_ = [
        ("r15", ctypes.c_ulonglong),
        ("r14", ctypes.c_ulonglong),
        ("r13", ctypes.c_ulonglong),
        ("r12", ctypes.c_ulonglong),
        ("rbp", ctypes.c_ulonglong),
        ("rbx", ctypes.c_ulonglong),
        ("r11", ctypes.c_ulonglong),
        ("r10", ctypes.c_ulonglong),
        ("r9", ctypes.c_ulonglong),
        ("r8", ctypes.c_ulonglong),
        ("rax", ctypes.c_ulonglong),
        ("rcx", ctypes.c_ulonglong),
        ("rdx", ctypes.c_ulonglong),
        ("rsi", ctypes.c_ulonglong),
        ("rdi", ctypes.c_ulonglong),
        ("orig_rax", ctypes.c_ulonglong),
        ("rip", ctypes.c_ulonglong),
        ("cs", ctypes.c_ulonglong),
        ("eflags", ctypes.c_ulonglong),
        ("rsp", ctypes.c_ulonglong),
        ("ss", ctypes.c_ulonglong),
        ("fs_base", ctypes.c_ulonglong),
        ("gs_base", ctypes.c_ulonglong),
        ("ds", ctypes.c_ulonglong),
        ("es", ctypes.c_ulonglong),
        ("fs", ctypes.c_ulonglong),
        ("gs", ctypes.c_ulonglong),
    ]

def ptrace(req, pid, addr=0, data=0):
    ctypes.set_errno(0)
    res = libc.ptrace(
        ctypes.c_ulong(req),
        ctypes.c_ulong(pid),
        ctypes.c_void_p(addr),
        ctypes.c_void_p(data),
    )
    err = ctypes.get_errno()
    if res == -1 and err:
        raise OSError(err, os.strerror(err))
    return res

def wait_stopped(pid):
    while True:
        wpid, status = os.waitpid(pid, 0)
        if wpid == pid:
            return status

def read_mem(pid, addr, n):
    with open(f"/proc/{pid}/mem", "rb", buffering=0) as f:
        f.seek(addr)
        return f.read(n)

def write_mem(pid, addr, data):
    with open(f"/proc/{pid}/mem", "r+b", buffering=0) as f:
        f.seek(addr)
        f.write(data)

def get_base(pid):
    maps = open(f"/proc/{pid}/maps").read().splitlines()
    candidates = []
    for line in maps:
        if BIN.strip("./") in line and "00000000" in line:
            start = int(line.split("-", 1)[0], 16)
            candidates.append(start)
    if not candidates:
        for line in maps:
            if "ad7e550b" in line and "00000000" in line:
                return int(line.split("-", 1)[0], 16)
        raise RuntimeError("No encontré base PIE en /proc/pid/maps")
    return min(candidates)

def build_addr_to_char(pid, base):
    text = read_mem(pid, base + TEXT_OFF, TEXT_SIZE)
    out = {}

    # Mini comparadores contienen:
    # 80 7d fc XX    cmp byte ptr [rbp-0x4], XX
    for m in re.finditer(rb"\x80\x7d\xfc(.)", text):
        cmp_off = TEXT_OFF + m.start()
        imm = m.group(1)[0]

        # Buscar hacia atrás el prólogo típico de función: 55 push rbp
        j = m.start() - 1
        while j >= 0 and m.start() - j <= 40 and text[j] != 0x55:
            j -= 1

        if j >= 0 and text[j] == 0x55:
            func_off = TEXT_OFF + j
            out[func_off] = chr(imm)

    return out

def main():
    # Entrada dummy de longitud correcta. Luego parcheamos el salto de fallo
    # para que no salga al primer carácter incorrecto.
    p = subprocess.Popen(
        [BIN, "A" * FLAGLEN],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    pid = p.pid

    time.sleep(0.05)
    base = get_base(pid)
    print(f"[+] pid  = {pid}", flush=True)
    print(f"[+] base = {base:#x}", flush=True)

    ptrace(PTRACE_ATTACH, pid)
    wait_stopped(pid)

    addr_to_char = build_addr_to_char(pid, base)
    print(f"[+] comparadores encontrados: {len(addr_to_char)}", flush=True)

    # Patch: jne -> jmp para evitar salida temprana.
    # 0x75 -> 0xeb en base+0x1a81
    try:
        old_jcc = read_mem(pid, base + JNE_PATCH_OFF, 1)
        write_mem(pid, base + JNE_PATCH_OFF, b"\xeb")
        print(f"[+] patch {base + JNE_PATCH_OFF:#x}: {old_jcc.hex()} -> eb", flush=True)
    except Exception as e:
        print(f"[!] no pude parchear JNE, sigo igualmente: {e}", flush=True)

    bp = base + CALL_RDX_OFF
    orig_bp = read_mem(pid, bp, 1)
    write_mem(pid, bp, b"\xcc")
    print(f"[+] breakpoint en call rdx: {bp:#x}", flush=True)

    flag = []

    ptrace(PTRACE_CONT, pid)

    for i in range(FLAGLEN):
        wait_stopped(pid)

        r = Regs()
        ptrace(PTRACE_GETREGS, pid, 0, ctypes.addressof(r))

        target = r.rdx
        target_off = target - base
        ch = addr_to_char.get(target_off, "?")
        flag.append(ch)

        print(f"[{i:02d}] rdx={target:#x} off={target_off:#x} char={ch!r}", flush=True)

        # Restaurar instrucción original y re-ejecutar desde bp.
        write_mem(pid, bp, orig_bp)
        r.rip = bp
        ptrace(PTRACE_SETREGS, pid, 0, ctypes.addressof(r))

        # Single-step sobre el call rdx.
        ptrace(PTRACE_SINGLESTEP, pid)
        wait_stopped(pid)

        # Reponer breakpoint y continuar.
        write_mem(pid, bp, b"\xcc")
        ptrace(PTRACE_CONT, pid)

    recovered = "".join(flag)
    print(f"\n[+] password/flag candidate: {recovered}", flush=True)

    # Limpieza suave
    try:
        write_mem(pid, bp, orig_bp)
        ptrace(PTRACE_DETACH, pid)
    except Exception:
        pass

    try:
        p.kill()
    except Exception:
        pass

    # Si ya parece flag, listo. Si no, probarlo explícitamente.
    if recovered.startswith("picoCTF{") and recovered.endswith("}"):
        print(recovered)
    else:
        print("[*] Probando el candidato contra el binario...", flush=True)
        q = subprocess.run([BIN, recovered], capture_output=True, text=True)
        print(q.stdout)
        print(q.stderr)

if __name__ == "__main__":
    main()
