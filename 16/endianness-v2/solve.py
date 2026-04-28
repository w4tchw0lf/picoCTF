# Abre el archivo corrupto en modo lectura binaria ('rb')
with open("challengefile", "rb") as f:
    datos = bytearray(f.read())

# Recorre los datos saltando de 4 en 4 bytes (32-bits)
for i in range(0, len(datos), 4):
    bloque = datos[i:i+4]
    
    # Si el bloque tiene exactamente 4 bytes, le damos la vuelta
    if len(bloque) == 4:
        datos[i:i+4] = bloque[::-1]

# Guarda el resultado en un nuevo archivo sano
with open("archivo_reparado", "wb") as f:
    f.write(datos)

print("[+] ¡Archivo reconstruido con éxito!")
