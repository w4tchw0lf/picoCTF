#!/usr/bin/env python3

file_name = "advanced-potion-making"
output_name = "pocion_reparada.png"

# Cabecera correcta para un archivo PNG
png_header = b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'

try:
    with open(file_name, "rb") as f:
        data = f.read()

    # Reemplazamos los primeros 8 bytes con la cabecera correcta
    fixed_data = png_header + data[8:]

    with open(output_name, "wb") as f:
        f.write(fixed_data)

    print(f"[+] Archivo reparado exitosamente como '{output_name}'")

except FileNotFoundError:
    print(f"[-] Error: No se encontró el archivo '{file_name}'")
except Exception as e:
    print(f"[-] Ocurrió un error: {e}")
