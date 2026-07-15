import struct

# 1. Leer el archivo binario
with open('flag.bin', 'rb') as f:
    flag_bin = f.read()

# 2. Ahora sí, intentar el unpack saltando los primeros 8 bytes
# (Usamos el slice [8:] para empezar desde el byte 9)
words = struct.unpack(f'<{len(flag_bin[8:])//2}H', flag_bin[8:])

# Cambia el offset inicial. Si 16 es Flag 1, intenta ver qué hay en 20, 24, etc.
# Puedes probar esto cambiando el valor '16' en tu loop:

for i in range(len(words)):
    val = words[i]
    
    # Intenta cambiar 16 por 24 o 32 (esto desplaza dónde empieza tu shellcode)
    # offset_objetivo = 24 
    target_node = (65536 - 2048 + 24 + i) % 65536 
    
    # ... resto de tu lógica igual

# 3. Imprime 'words' para ver qué obtuviste
print(words)
