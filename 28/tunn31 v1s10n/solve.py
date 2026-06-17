# Abrimos el archivo corrupto en modo lectura binaria
with open('tunn3l_v1s10n', 'rb') as f:
    data = bytearray(f.read())

# 1. Arreglar el Offset de los píxeles (Bytes 10 al 13)
# Cambiamos "ba d0 00 00" por "36 00 00 00"
data[10] = 0x36
data[11] = 0x00

# 2. Arreglar el tamaño de la cabecera DIB (Bytes 14 al 17)
# Cambiamos "ba d0 00 00" por "28 00 00 00"
data[14] = 0x28
data[15] = 0x00

# 3. Curar la "Visión de Túnel" aumentando la altura (Bytes 22 y 23)
# Originalmente pone "32 01" (306 píxeles). Lo subiremos a "32 03" (818 píxeles)
data[22] = 0x32
data[23] = 0x03

# Guardamos el archivo curado
with open('fixed_V2.bmp', 'wb') as f:
    f.write(data)

print("[+] Cabecera reconstruida. Altura expandida.")
print("[+] Imagen guardada como 'fixed.bmp'")
